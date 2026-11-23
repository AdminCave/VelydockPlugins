# Velydock Plugins

**Fertige Apps für [Velydock](https://github.com/AdminCave/Velydock): mit einem Befehl
installiert, per Single Sign-On an Velydocks Keycloak angebunden und im Workspace eingebettet.**

Ein *Plugin* ist eine Vorlage im Katalog (`catalog/<plugin>/`): Docker-Compose-Datei,
Traefik-Route und ein Manifest. Eine *Instanz* ist eine Installation davon unter einem eigenen
Hostnamen. Ein Plugin lässt sich beliebig oft installieren – etwa eine Nextcloud je Kunde.

| Plugin | Was es bringt |
|---|---|
| [`nextcloud`](catalog/nextcloud/README.md) | Nextcloud 35 mit PostgreSQL, Redis und Cron. Anmeldung über Keycloak, ohne zweiten Login im Frame, Abmeldung folgt Velydock. Optional nur für eine Organisation. |

## Was `vdp up` erledigt

```
./vdp up cloud
  1. Keycloak   OIDC-Client vdp-cloud im Realm velydock anlegen/aktualisieren
                (Redirect-URIs, Back-Channel-Logout, ggf. Scope organization)
  2. Container  docker compose -p vdp-cloud up --wait   (App hängt im Netz <velydock>_edge)
  3. Route      <Velydock>/deploy/traefik/dynamic/vdp-cloud.yml  → Velydocks Traefik routet
                den Hostnamen zur App, mit TLS wie Velydock selbst
```

Danach die App einmal in Velydock unter *Verwaltung → Apps* als „Eingebettet“ anlegen; `vdp up`
gibt Name und Adresse dafür aus. (Velydock hat noch keine API-Schlüssel, mit denen sich das
automatisieren ließe.)

## Schnellstart

Voraussetzungen: eine laufende Velydock-Installation auf demselben Server, Docker mit Compose,
Python 3.11 oder neuer. Keine weiteren Pakete.

```bash
git clone https://github.com/AdminCave/VelydockPlugins.git && cd VelydockPlugins
cp vdp.example.toml vdp.toml        # nur nötig, wenn Velydock nicht in ../Velydock liegt
./vdp catalog
./vdp add nextcloud cloud --host cloud.example.com
./vdp up cloud
```

Der Hostname gehört unter dieselbe Domain wie Velydock (`dock.example.com` →
`cloud.example.com`), sonst behandeln Browser die Cookies im Frame als Drittanbieter-Cookies
(Velydock: `docs/anwendungsintegration.md`).

## Befehle

| Befehl | Wirkung |
|---|---|
| `./vdp catalog` | verfügbare Plugins |
| `./vdp add <plugin> <instanz> --host <host> [--org <kurzname>] [--set KEY=WERT]` | Instanz anlegen, Geheimnisse erzeugen – startet noch nichts |
| `./vdp set <instanz> KEY=WERT …` | Einstellung ändern (z. B. Image-Version), dann `up` |
| `./vdp up <instanz>` | anlegen oder auf den Stand bringen; beliebig oft wiederholbar |
| `./vdp down <instanz>` | Route weg, Container stoppen, Daten bleiben |
| `./vdp remove <instanz> [--purge]` | zusätzlich Keycloak-Client löschen; `--purge` löscht auch die Daten |
| `./vdp status` | alle Instanzen mit Zustand der Container und Route |
| `./vdp compose <instanz> logs -f app` | beliebiger `docker compose`-Befehl für die Instanz |

`--org <kurzname>` beschränkt die Anmeldung auf Mitglieder einer Velydock-Organisation. Ohne
diese Angabe kann sich jeder Benutzer der Installation anmelden – im gemeinsamen Realm sind das
alle Mandanten (Velydock: `docs/sso.md`, „Apps eines einzelnen Kunden abgrenzen“).

## Aufbau

```
vdp                       das Werkzeug (Python, nur Standardbibliothek)
vdp.example.toml          wo Velydock liegt (Verzeichnis, .env, Compose-Projekt)
tools/keycloak_client.py  legt OIDC-Clients an; läuft in einem Wegwerf-Container im Velydock-Netz
catalog/<plugin>/         Vorlagen – versioniert
instances/<instanz>/      Installationen – NICHT versioniert, enthält Geheimnisse
  instance.json           Plugin, Hostname, Organisation, geänderte Einstellungen
  secrets.env             bei add erzeugt (Datenbank, Admin, Client-Secret) – ins Backup!
  .env                    bei jedem up neu erzeugt, für docker compose
```

Wie man ein neues Plugin schreibt: [docs/plugin-format.md](docs/plugin-format.md).
Wie das Ganze an Velydock andockt und was dabei zu bedenken ist:
[docs/konzept.md](docs/konzept.md).

## Lokal mit dem Entwicklungs-Stack von Velydock

```bash
cat > vdp.toml <<'TOML'
[velydock]
dir = "../Velydock"
env_file = ".env.dev"
project = "velydock-dev"
TOML
./vdp add nextcloud cloud --host cloud.velydock.localhost
./vdp up cloud        # https://cloud.velydock.localhost:8443
```

Lizenz: GPL-3.0-or-later. Teil von [Admin Cave](https://admincave.com).
