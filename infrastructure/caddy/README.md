# Caddy

Reverse proxy z automatycznym HTTPS dla API na VPS. Konfiguracja: [`Caddyfile`](Caddyfile) (adres z
`API_DOMAIN`), uruchamiana przez `docker-compose.prod.yml`. Całość procedury: `docs/release/vps-runbook.md`.

- Bez dyrektywy `log`: brak access logów (parametr `q` wyszukiwania miejscowości nie trafia na dysk).
- Adres Caddy w sieci docker jest stały (`172.28.0.2`) i jest wpisany jako `FORWARDED_ALLOW_IPS` dla API
  (prawdziwy adres klienta do limitów żądań, ADR-029). Zmiana jednego wymaga zmiany drugiego.
- Lokalny development nie używa Caddy (porty bezpośrednio).
