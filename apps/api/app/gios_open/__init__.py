"""Shared foundation for the seven new GIOŚ datasets (dane.gios.gov.pl, ADR-032, GIOS-02).

NOT a connector: the connectors (`gios_noise`, `gios_prtr`, ...) stay isolated in
`app/connectors/<source>/` and only reuse the mechanisms that are genuinely common:
the HTTP client with the real envelope rules (`client`), safe paging (`paging`),
snapshot staging/promotion with a per-service lock (`snapshots`, `runner`) and the
operator's evidence probe (`probe`). The existing hourly air connector `gios` is separate.
"""
