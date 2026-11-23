"""Create, update or delete the OIDC client of an app in Velydock's Keycloak realm.

Runs inside a throwaway container on Velydock's Docker network (see `keycloak()` in ../vdp),
standard library only. Input comes from the environment:

    KC_URL           internal address of Keycloak, e.g. http://keycloak:8080
    KC_REALM         velydock
    KC_ADMIN_SECRET  secret of Velydock's service account client "velydock-admin"
    KC_SPEC          JSON, see ensure() below

Prints one line of JSON as its result.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ["KC_URL"].rstrip("/")
REALM = os.environ["KC_REALM"]
ADMIN = f"{BASE}/admin/realms/{REALM}"


def token() -> str:
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": "velydock-admin",
        "client_secret": os.environ["KC_ADMIN_SECRET"],
    }).encode()
    request = urllib.request.Request(
        f"{BASE}/realms/{REALM}/protocol/openid-connect/token", data=body, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)["access_token"]


TOKEN = token()


def api(method: str, path: str, data=None, ok=()):
    request = urllib.request.Request(
        ADMIN + path,
        data=None if data is None else json.dumps(data).encode(),
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        if error.code in ok:
            return None
        detail = error.read().decode(errors="replace")[:500]
        raise SystemExit(f"Keycloak {method} {path}: {error.code} {detail}")


def find(client_id: str):
    found = api("GET", "/clients?" + urllib.parse.urlencode({"clientId": client_id}))
    return found[0] if found else None


def ensure(spec: dict) -> dict:
    attributes = {
        "post.logout.redirect.uris": "##".join(spec.get("postLogoutRedirectUris", [])),
        "backchannel.logout.session.required": "true",
        "backchannel.logout.revoke.offline.tokens": "false",
    }
    if spec.get("pkce"):
        attributes["pkce.code.challenge.method"] = "S256"
    if spec.get("backchannelLogoutUrl"):
        attributes["backchannel.logout.url"] = spec["backchannelLogoutUrl"]

    representation = {
        "clientId": spec["clientId"],
        "name": spec["name"],
        "description": "Managed by VelydockPlugins (vdp). Changes here are overwritten.",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "secret": spec["secret"],
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "frontchannelLogout": False,
        "fullScopeAllowed": False,
        "rootUrl": spec["rootUrl"],
        "baseUrl": spec.get("baseUrl", "/"),
        "redirectUris": spec["redirectUris"],
        "webOrigins": ["+"],
    }

    current = find(spec["clientId"])
    if current:
        merged = {**current, **representation}
        merged["attributes"] = {**current.get("attributes", {}), **attributes}
        api("PUT", f"/clients/{current['id']}", merged)
        uuid, created = current["id"], False
    else:
        api("POST", "/clients", {**representation, "attributes": attributes})
        uuid, created = find(spec["clientId"])["id"], True

    if spec.get("organizationScope"):
        # The app asks for organization:<alias>; Keycloak only grants it if the scope is
        # available to the client. New clients get it as optional by default – make sure.
        optional = api("GET", f"/clients/{uuid}/optional-client-scopes") or []
        if not any(s["name"] == "organization" for s in optional):
            scopes = api("GET", "/client-scopes") or []
            scope = next((s for s in scopes if s["name"] == "organization"), None)
            if scope is None:
                raise SystemExit("Realm has no client scope 'organization' (Keycloak < 26?).")
            api("PUT", f"/clients/{uuid}/optional-client-scopes/{scope['id']}", ok=(409,))
    return {"clientId": spec["clientId"], "created": created}


def delete(spec: dict) -> dict:
    current = find(spec["clientId"])
    if current:
        api("DELETE", f"/clients/{current['id']}", ok=(404,))
    return {"clientId": spec["clientId"], "deleted": bool(current)}


if __name__ == "__main__":
    action = sys.argv[1]
    spec = json.loads(os.environ["KC_SPEC"])
    # Never touch Velydock's own clients or anything not created by vdp.
    if not spec["clientId"].startswith("vdp-"):
        raise SystemExit(f"Refusing to manage client {spec['clientId']!r}: not a vdp- client.")
    result = {"ensure": ensure, "delete": delete}[action](spec)
    print(json.dumps(result))
