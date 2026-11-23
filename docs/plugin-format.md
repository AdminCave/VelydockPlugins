# Ein Plugin schreiben

Ein Plugin ist ein Verzeichnis `catalog/<name>/` mit drei Pflichtdateien. Alles Weitere
(Hook-Skripte, Konfigurationsdateien) liegt daneben und wird aus `compose.yml` relativ
eingebunden – Compose läuft mit dem Plugin-Verzeichnis als Projektverzeichnis.

## `plugin.toml`

```toml
title = "Beispiel"
description = "Eine Zeile für ./vdp catalog"

# Werden bei ./vdp add einmal zufällig erzeugt (instances/<instanz>/secrets.env).
# OIDC_CLIENT_SECRET kommt bei Plugins mit [oidc] automatisch dazu.
secrets = ["DB_PASSWORD"]

# Einstellungen mit Vorgabe; eine Instanz ändert sie mit --set oder ./vdp set.
# Nur hier genannte Schlüssel sind erlaubt.
[defaults]
IMAGE = "example/app:1.2"

[route]
service = "app"   # Compose-Dienst, der im Velydock-Netz unter dem Alias vdp-<instanz> hängt
port = 80

# Weglassen, wenn die App keine Anmeldung über Keycloak braucht.
[oidc]
redirect_paths = ["/oauth/callback"]        # an APP_URL angehängt
post_logout_paths = ["/*"]
backchannel_logout_path = "/logout/backchannel"   # optional, über das interne Netz
pkce = true                                 # wenn die App PKCE sendet

# Nur für die Ausgabe von ./vdp up: so legt man die App in Velydock an.
[velydock_app]
name = "Beispiel"
type_label = "Eingebettet"   # oder "Neuer Tab"
icon = "…"
path = "/"
notes = ["Admin-Zugang: %%APP_URL%%/admin"]
```

## `compose.yml`

Normale Compose-Datei. Sie bekommt bei `./vdp up` eine `.env` mit allen Variablen (siehe unten).
Pflicht ist das externe Netz von Velydock für den Dienst aus `[route]`, mit dem Alias:

```yaml
services:
  app:
    networks:
      default: {}
      velydock:
        aliases: ["${APP_ALIAS}"]
networks:
  velydock:
    name: ${VELYDOCK_NETWORK:?}
    external: true
```

Datenbanken und Ähnliches gehören nur in ein eigenes Netz der Instanz (`internal: true`), nicht
ins Velydock-Netz: Dort hängen Velydock, Keycloak und Traefik.

## `route.yml`

Traefik-Konfiguration (File-Provider), die nach `<Velydock>/deploy/traefik/dynamic/vdp-<instanz>.yml`
geschrieben wird. Platzhalter haben die Form `%%NAME%%` – sie kollidieren weder mit YAML noch mit
Traefiks Go-Templates noch mit `${1}` in Regex-Ersetzungen. Router-, Middleware- und
Service-Namen beginnen mit `vdp-%%VDP_INSTANCE%%`, damit sich Instanzen nicht in die Quere kommen.
Vorlage: [catalog/nextcloud/route.yml](../catalog/nextcloud/route.yml).

## Variablen

In `compose.yml` als `${NAME}`, in `route.yml` und `notes` als `%%NAME%%`:

| Variable | Beispiel |
|---|---|
| `VDP_INSTANCE` | `cloud` |
| `APP_HOST`, `APP_URL` | `cloud.example.com`, `https://cloud.example.com` |
| `APP_ALIAS`, `APP_INTERNAL_URL` | `vdp-cloud`, `http://vdp-cloud:80` |
| `VELYDOCK_URL`, `VELYDOCK_NETWORK` | `https://dock.example.com`, `velydock_edge` |
| `KEYCLOAK_ISSUER` | `https://auth.example.com/realms/velydock` |
| `KEYCLOAK_INTERNAL_URL` | `http://keycloak:8080` |
| `OIDC_DISCOVERY_URL` | `http://keycloak:8080/realms/velydock/.well-known/openid-configuration` |
| `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | `vdp-cloud`, zufällig |
| `OIDC_SCOPE` | `openid profile email` (+ `organization:<org>` mit `--org`) |
| `ORG` | Kurzname der Organisation oder leer |
| `PUBLIC_PORT_SUFFIX` | leer, im Entwicklungs-Stack `:8443` |
| `TLS` | `{certResolver: letsencrypt}` oder `{}` |
| alle `[defaults]` und `secrets` | |

**Discovery über die interne Adresse.** Keycloak beantwortet Anfragen an `http://keycloak:8080`
mit internen Adressen für Token, Schlüssel und Userinfo, nennt aber weiterhin den öffentlichen
Aussteller und die öffentliche Anmeldeseite (`KC_HOSTNAME_BACKCHANNEL_DYNAMIC`). Apps müssen den
öffentlichen Hostnamen von Keycloak deshalb nie selbst erreichen. Viele Apps sperren private
Adressen für ausgehende Anfragen – das muss man ihnen dann erlauben (Nextcloud:
`allow_local_remote_servers`).

## Checkliste für eingebettete Apps

1. **Einbetten erlauben:** `Content-Security-Policy: frame-ancestors 'self' <VELYDOCK_URL>`
   – am besten in der App selbst. `X-Frame-Options` kann keinen fremden Origin erlauben und
   wird in `route.yml` entfernt (`customResponseHeaders: {X-Frame-Options: ""}`).
2. **Direkt zu Keycloak:** Die App soll ohne eigene Anmeldeseite auf Keycloak weiterleiten;
   besteht die Keycloak-Sitzung, kommt der Benutzer ohne Rückfrage zurück. Keycloaks
   Anmeldeseite selbst lässt sich nicht einbetten.
3. **Abmeldung:** Back-Channel-Logout eintragen, wenn die App es kann – dann endet ihre
   Sitzung, sobald jemand Velydock verlässt oder gesperrt wird.
4. **Willkommensdialoge** abschalten, sie erscheinen sonst in jedem Frame.
5. Prüfen mit einem Browser: Velydock anmelden, App im Frame öffnen, kein Login.
