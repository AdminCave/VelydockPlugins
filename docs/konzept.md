# Konzept

## Warum ein eigenes Werkzeug und kein Ansible

Die eigentliche Arbeit machen Docker Compose (Container) und die APIs von Keycloak und der
jeweiligen App. `vdp` verbindet nur drei Schritte, die sich für jede App gleich anfühlen sollen,
und läuft dort, wo Velydock läuft – ohne Inventar, ohne Abhängigkeiten außer Python. Eine
Ansible-Rolle könnte `vdp` später aufrufen, um Plugins auf vielen Servern auszurollen.

## Wie eine App an Velydock andockt

```
Browser ─► Traefik (von Velydock) ─┬─► velydock / keycloak
                                   └─► vdp-cloud  (Nextcloud, Netz <velydock>_edge)
                                          │  db, redis  (eigenes internes Netz)
Keycloak ──Back-Channel-Logout──► vdp-cloud
Nextcloud ──Token, Schlüssel──► keycloak:8080 (intern)
```

- **Routing:** Velydocks Traefik liest jede Datei im Verzeichnis `deploy/traefik/dynamic`
  seines Checkouts, auch neue, ohne Neustart. `vdp` legt dort `vdp-<instanz>.yml` ab und entfernt
  sie bei `down`. In `git status` von Velydock erscheint die Datei als unversioniert – ein Eintrag
  `deploy/traefik/dynamic/vdp-*.yml` in Velydocks `.gitignore` würde das beheben.
- **Anmeldung:** Jede Instanz ist ein eigener OIDC-Client `vdp-<instanz>` im Realm `velydock`.
  `vdp` legt ihn mit Velydocks Dienstkonto (`velydock-admin`, Recht `manage-clients`) an und
  ändert nur Clients, deren ID mit `vdp-` beginnt.
- **Einbettung:** Die App muss Velydocks Adresse als `frame-ancestors` zulassen und unter
  derselben registrierbaren Domain laufen. Velydock zeigt sie dann im Frame; die Keycloak-Sitzung
  besteht schon, also meldet die App den Benutzer ohne Rückfrage an.

## Geprüft (Nextcloud 35.0.3, Keycloak 26.8.2, Velydock-Entwicklungs-Stack, Chromium)

| Fall | Ergebnis |
|---|---|
| Anmeldung bei Velydock, danach Nextcloud im Frame unter Velydocks Origin | Dashboard ohne zweite Anmeldung, Benutzer = Velydock-Benutzername |
| Abmeldung des Benutzers in Keycloak | Nextcloud-Sitzung beendet, nächster Aufruf geht zur Anmeldung |
| `--org acme`, Benutzer Mitglied | stille Anmeldung |
| `--org acme`, Benutzer kein Mitglied | im Frame: Keycloak fragt erneut nach dem Passwort (nicht einbettbar); im Tab: Nextcloud lehnt ab („Access forbidden“) |
| `down`, `up` | Daten bleiben, Hook bringt die Konfiguration wieder auf Stand |

Nicht geprüft: Firefox und Safari, ein Produktivbetrieb mit Let's Encrypt, das Anlegen der App
über Velydocks Oberfläche (der Test bettete Nextcloud in eine Seite unter Velydocks Origin ein).

## Grenzen und nächste Schritte

- **App in Velydock anlegen** bleibt ein Handgriff in der Oberfläche, bis Velydock API-Schlüssel
  hat (`docs/erweiterung.md` dort). Dann kann `vdp up` die App selbst anlegen und freigeben.
- **Zweig `feature/app-proxy` von Velydock** veröffentlicht Apps über Velydocks Proxy mit
  Forward-Auth. Sobald er in `main` ist, kann `route.yml` entfallen und `vdp` die Veröffentlichung
  über Velydock anlegen – Routen lägen dann nicht mehr als Datei im Checkout.
- **Gruppen:** Velydock spiegelt Gruppen noch nicht nach Keycloak. Wenn es das tut, lassen sie sich
  über `--mapping-groups` als Nextcloud-Gruppen übernehmen.
- **Backup:** Volumes `vdp-<instanz>_*` und `instances/` gehören ins Backup; `vdp` hat dafür noch
  keinen Befehl.
