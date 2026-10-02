#!/usr/bin/env python3
"""
Install the approved Za Oknem raster asset pack into apps/mobile/assets/za-oknem.

Usage:
  python scripts/install_ui_asset_pack.py /path/to/za_oknem_asset_pack_v2.zip

This script intentionally copies only the approved production assets. It also
renames optimized "-q" files to stable runtime names so app code never depends
on export-internal filenames.
"""

from __future__ import annotations

import hashlib
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "apps" / "mobile" / "assets" / "za-oknem"

# archive path -> runtime path, expected dimensions, sha256 of approved source
FILES = {
    "android/app-icon-1024-q.png": (
        "android/app-icon-1024.png", (1024, 1024),
        "227aaaac21ae930552b9e590b72a8597c5efa6e106bc8ad7b52fd7f752e0c499",
    ),
    "android/adaptive-icon-foreground-1024-q.png": (
        "android/adaptive-icon-foreground-1024.png", (1024, 1024),
        "80b1ad678fbea10112b7b49a5bf64ba2ef4c30fbefc176bb1c8e2e9db40eafe3",
    ),
    "android/adaptive-icon-background-1024-q.png": (
        "android/adaptive-icon-background-1024.png", (1024, 1024),
        "5fba554b4b2d9d0fe7bff17ed4426b0ecac7c7b6b22edfedba869998a84b1599",
    ),
    "android/adaptive-icon-monochrome-1024-q.png": (
        "android/adaptive-icon-monochrome-1024.png", (1024, 1024),
        "570ae8eab0c0345be91b8624e33b9910a65d2ae736e9698e885e0146e7631d56",
    ),
    "android/play-store-icon-512-q.png": (
        "android/play-store-icon-512.png", (512, 512),
        "423f9b2395e7cd1bd5405e9b231d970ba28d414f8933d61c18ac1eedb5716dc3",
    ),
    "brand/logo-mark-512-q.png": (
        "brand/logo-mark-512.png", (512, 512),
        "5dd9b8546ab022b04e2bc4703895d5149052d271d333e23202ff8232636c1daf",
    ),
    # The final approved welcome background is supplied in the package under this stable name.
    "backgrounds/welcome-hero-1242x2688.jpg": (
        "backgrounds/welcome-hero-1242x2688.jpg", (1242, 2688),
        "b8f33806452d87eb7f33423fed739ba5eb29821e32205f4f7e25b5e97b7cf73e",
    ),
    "illustrations/condition-good-1200x800-q.png": (
        "illustrations/condition-good-1200x800.png", (1200, 800),
        "540c9f5ff4c1655aa840be00a456f1e63a29b750cc4c87d2a4dd43f49b48e0e1",
    ),
    "illustrations/condition-caution-1200x800-q.png": (
        "illustrations/condition-caution-1200x800.png", (1200, 800),
        "b7caf3f3b2ef25af055e9e903b861b2235c5268375e67c79c12956255ab07466",
    ),
    "illustrations/condition-bad-1200x800-q.png": (
        "illustrations/condition-bad-1200x800.png", (1200, 800),
        "17caccbd9d38487cf325ec23acbd1b626f20d4c67e69b63d0ddc799fb2ff417b",
    ),
    "illustrations/no-alerts-1200x800-q.png": (
        "illustrations/no-alerts-1200x800.png", (1200, 800),
        "5bd16532f6a23638d20b9136872c652e49ef4f00973bc5b5ba6e54f7ad088622",
    ),
    "illustrations/no-data-1200x800-q.png": (
        "illustrations/no-data-1200x800.png", (1200, 800),
        "7478216dd7993d9beb37f7626ccd35a42207157a42a8b53a3c401f9580fc8bb9",
    ),
    "illustrations/offline-1200x800-q.png": (
        "illustrations/offline-1200x800.png", (1200, 800),
        "e36746e8c2b7e6d5f4dde202cf8bebae8c4ad08c6cae6a5098965c332b74d4b8",
    ),
    "illustrations/location-required-1200x800-q.png": (
        "illustrations/location-required-1200x800.png", (1200, 800),
        "8e004fb399ea3f83b77b63d0124ef9534c967d544c5fec76111f275dffc76d9d",
    ),
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in {0xD8, 0xD9}:
                continue
            if i + 2 > len(data):
                break
            length = int.from_bytes(data[i:i+2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height = int.from_bytes(data[i+3:i+5], "big")
                width = int.from_bytes(data[i+5:i+7], "big")
                return width, height
            i += length
    raise ValueError(f"Unsupported image format: {path}")

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/install_ui_asset_pack.py /path/to/za_oknem_asset_pack_v2.zip")
        return 2

    archive = Path(sys.argv[1]).expanduser().resolve()
    if not archive.exists():
        print(f"Asset pack not found: {archive}")
        return 2

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(tmp)

        # tolerate package root directory or flat archive
        candidates = [tmp / "za_oknem_asset_pack_v2", tmp]
        source_root = next((p for p in candidates if any((p / k).exists() for k in FILES)), None)
        if source_root is None:
            print("Archive does not contain the expected Za Oknem asset structure.")
            return 3

        for src_rel, (dst_rel, expected_size, expected_hash) in FILES.items():
            src = source_root / src_rel
            if not src.exists():
                print(f"Missing approved asset: {src_rel}")
                return 4

            actual_hash = sha256(src)
            if actual_hash != expected_hash:
                print(f"Hash mismatch for {src_rel}\nexpected {expected_hash}\nactual   {actual_hash}")
                return 5

            actual_size = image_size(src)
            if actual_size != expected_size:
                print(f"Dimension mismatch for {src_rel}: expected {expected_size}, got {actual_size}")
                return 6

            dst = TARGET / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"installed {dst.relative_to(ROOT)}")

    print("\nZa Oknem asset pack installed successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
