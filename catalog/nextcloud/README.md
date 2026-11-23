# Plugin `nextcloud`

Nextcloud (offizielles Image, Apache) mit PostgreSQL, Redis und einem Cron-Container.

```bash
./vdp add nextcloud cloud --host cloud.example.com              # für alle Benutzer
./vdp add nextcloud cloud-acme --host cloud-acme.example.com --org acme   # nur Organisation acme
./vdp up cloud
```

## Was eingerichtet wird

Bei jedem Start des Containers (`hooks/before-starting/10-velydock.sh`, idempotent):

- App **`velydock_embed`** (in diesem Verzeichnis, `nextcloud-app/`): fügt Velydocks Adresse in
  `frame-ancestors` der Content-Security-Policy jeder Seite ein. Nextcloud hat dafür keine
  Einstellung. `X-Frame-Options` entfernt die Traefik-Route.
- App **`user_oidc`** mit dem Anbieter `velydock`: Discovery über Keycloaks interne Adresse,
  Benutzer-ID aus `preferred_username` (= Velydock-Benutzername; `UID_CLAIM` ändert das), Name und
  E-Mail aus dem Token. Die Anmeldeseite leitet direkt zu Keycloak.
- Mit `--org`: Scope `organization:<kurzname>`, der Claim `organization` wird als Gruppe gelesen,
  nur die passende Gruppe darf sich anmelden.
- Back-Channel-Logout: Keycloak meldet Abmeldungen an Nextcloud über das interne Netz.
- `firstrunwizard` aus, Cron als Hintergrunddienst, Telefonregion, Wartungsfenster.

## Einstellungen (`--set` / `./vdp set`)

| Schlüssel | Vorgabe |
|---|---|
| `NEXTCLOUD_IMAGE` | `nextcloud:35-apache` |
| `POSTGRES_IMAGE`, `REDIS_IMAGE` | `postgres:18-alpine`, `redis:8-alpine` |
| `ADMIN_USER` | `ncadmin` (Passwort in `secrets.env`) |
| `PHP_UPLOAD_LIMIT`, `PHP_MEMORY_LIMIT` | `16G`, `1G` |
| `DEFAULT_PHONE_REGION` | `DE` |
| `UID_CLAIM` | `preferred_username` |

**Update:** `./vdp set cloud NEXTCLOUD_IMAGE=nextcloud:36-apache && ./vdp up cloud`. Nextcloud
erlaubt nur eine Hauptversion pro Schritt.

## Notfallzugang

Lokaler Administrator unter `https://<host>/login?direct=1`, Passwort in
`instances/<instanz>/secrets.env`. Benutzer aus Keycloak sind keine Nextcloud-Administratoren;
das vergibt der lokale Administrator.

## Bekannt

- `allow_local_remote_servers` ist an, damit Nextcloud Keycloak intern erreicht. Das erlaubt
  Nextcloud auch andere Anfragen an private Adressen (z. B. externe Speicher im LAN).
- Läuft die Keycloak-Sitzung ab, bleibt der Frame leer (Keycloaks Anmeldeseite ist nicht
  einbettbar); Velydock bietet dann „In neuem Tab öffnen“.
