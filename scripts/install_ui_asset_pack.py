#!/usr/bin/env python3
"""Install and validate the approved Za Oknem raster asset pack v2."""

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

# archive path -> runtime path, expected dimensions, sha256
FILES = {
    "android/app-icon-1024.png": ("android/app-icon-1024.png", (1024, 1024), "3f004c9f18ac1c193896887f258c7b0e3409264111fefc5ce469c8a593aad3a5"),
    "android/adaptive-icon-foreground-1024.png": ("android/adaptive-icon-foreground-1024.png", (1024, 1024), "63e5c4c79a3217eaabfb7e74b3ba90f383e207774f176ccc356280833637f5af"),
    "android/adaptive-icon-background-1024.png": ("android/adaptive-icon-background-1024.png", (1024, 1024), "95e5f5bc3cc51c74e2bb3500d7fc25dda50c69ac7aac8b9592979066b5a7e27b"),
    "android/adaptive-icon-monochrome-1024.png": ("android/adaptive-icon-monochrome-1024.png", (1024, 1024), "6ab70b23f0d92881b89974c9207ca6f9ce83ff0aa23e0de5002d007932988ad4"),
    "android/play-store-icon-512.png": ("android/play-store-icon-512.png", (512, 512), "06a755029cd80e140a3e6d1ff86c2e42911def44d01f4d4704ac4223ed0b9509"),

    "brand/logo-mark-1024.png": ("brand/logo-mark-1024.png", (1024, 1024), "ea3f1d1d01173aedc172c6a5296d866d2125049afa5ecef9398be2aaf5c03189"),
    "brand/logo-mark-512.png": ("brand/logo-mark-512.png", (512, 512), "c34fc5c1d2937ef3d8d87930e5c2e454d1c6b0bc6e7f52d66376893a3afaa261"),
    "brand/logo-mark-256.png": ("brand/logo-mark-256.png", (256, 256), "9c4153577e2cab8efd83934531880382a96028e18c39dea82107e65072a3957d"),

    "backgrounds/welcome-hero-1242x2688.jpg": ("backgrounds/welcome-hero-1242x2688.jpg", (1242, 2688), "2ae92a3da3b074e6175e8e9ae55cd89d7962a4f433dfe4a85f43674290b1aaea"),
    "backgrounds/dashboard-sunny-1242x2688.jpg": ("backgrounds/dashboard-sunny-1242x2688.jpg", (1242, 2688), "59c0ad87a526a0ec6b0cfa020b04688b08f7da7a5f4cd17b460ae6f3c19b8b72"),
    "backgrounds/dashboard-cloudy-1242x2688.jpg": ("backgrounds/dashboard-cloudy-1242x2688.jpg", (1242, 2688), "f16fc43a52658ee559b1aa2b706a8afb4a78921477e57c592cafacab5fa062c6"),
    "backgrounds/dashboard-evening-1242x2688.jpg": ("backgrounds/dashboard-evening-1242x2688.jpg", (1242, 2688), "85496f42a6087a4ca7a82fe3420053dad95510c3daf02dd8edf7492a2a0057a8"),

    "illustrations/condition-good-1200x800.png": ("illustrations/condition-good-1200x800.png", (1200, 800), "7f9b3b10dc848ee76bae340717bbbce6d07ee1e01a4944cf84e8ee704b95fc92"),
    "illustrations/condition-caution-1200x800.png": ("illustrations/condition-caution-1200x800.png", (1200, 800), "655fd2a02d76d66f0aeeab3370d02f6b9bfa86fff6367d64e3e3ee47204889ab"),
    "illustrations/condition-bad-1200x800.png": ("illustrations/condition-bad-1200x800.png", (1200, 800), "f9d463a7473c363e5a504078528521fc3242a2ea1c88e9ed182a0e6e7ee50226"),
    "illustrations/no-alerts-1200x800.png": ("illustrations/no-alerts-1200x800.png", (1200, 800), "46983953b10c07c2bda8d6ee1661a654daa06e3c4157fa0887658052b751387d"),
    "illustrations/no-data-1200x800.png": ("illustrations/no-data-1200x800.png", (1200, 800), "c8cf770b9a7835a6a8cc2f7148c1b68765f466c3fb9f965f5b58d2546a1000cf"),
    "illustrations/offline-1200x800.png": ("illustrations/offline-1200x800.png", (1200, 800), "344811ef9c9fa0dbec1bdd07254a16a3f7eeb36f900d4db20705e00996cfe934"),
    "illustrations/location-required-1200x800.png": ("illustrations/location-required-1200x800.png", (1200, 800), "a86745a729fba3edfc9e361d77e407d82444716b04c031feabb5c77de409c66f"),
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
            length = int.from_bytes(data[i:i + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height = int.from_bytes(data[i + 3:i + 5], "big")
                width = int.from_bytes(data[i + 5:i + 7], "big")
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

        candidates = [tmp / "za_oknem_asset_pack_v2", tmp]
        source_root = next((p for p in candidates if all((p / rel).exists() for rel in FILES)), None)
        if source_root is None:
            print("Archive does not contain the complete expected Za Oknem asset structure.")
            return 3

        for src_rel, (dst_rel, expected_size, expected_hash) in FILES.items():
            src = source_root / src_rel
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

    print("\nZa Oknem asset pack v2 installed successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
