#!/bin/sh
# Runs as www-data before every start of the Nextcloud container (official image hook), after the
# installation on the first start. Every step is idempotent: the instance is brought to the state
# described by its environment, whatever changed in between.
set -eu

occ() { php /var/www/html/occ "$@"; }
log() { echo "[velydock] $*"; }

# --- Embedding in Velydock -------------------------------------------------------------------
# A tiny app that adds Velydock's address to Nextcloud's CSP frame-ancestors (Nextcloud has no
# setting for it). Copied, not mounted, so Nextcloud's own file checks see a normal app.
rm -rf /var/www/html/custom_apps/velydock_embed
cp -r /opt/vdp/velydock_embed /var/www/html/custom_apps/velydock_embed
occ app:enable velydock_embed >/dev/null
occ config:app:set velydock_embed frame_ancestors --value="$VDP_VELYDOCK_URL" >/dev/null
log "embedding allowed for $VDP_VELYDOCK_URL"

# --- Sign-in through Keycloak ----------------------------------------------------------------
if ! occ app:list --output=json | grep -q '"user_oidc"'; then
  log "installing user_oidc"
  occ app:install user_oidc
fi
occ app:enable user_oidc >/dev/null

# Nextcloud fetches tokens and keys from Keycloak's internal address (http://keycloak:8080),
# which is a private address – Nextcloud refuses those unless told otherwise.
occ config:system:set allow_local_remote_servers --type=boolean --value=true >/dev/null

set -- \
  --clientid="$VDP_OIDC_CLIENT_ID" \
  --clientsecret="$VDP_OIDC_CLIENT_SECRET" \
  --discoveryuri="$VDP_OIDC_DISCOVERY_URL" \
  --scope="$VDP_OIDC_SCOPE" \
  --unique-uid=0 \
  --mapping-uid="$VDP_UID_CLAIM" \
  --mapping-display-name=name \
  --mapping-email=email \
  --check-bearer=0 \
  --send-id-token-hint=1

if [ -n "$VDP_ORG" ]; then
  # Only members of this Velydock organization get in: Keycloak puts the claim "organization"
  # into the token only for them; Nextcloud treats its values as groups and admits only users
  # with the whitelisted one.
  set -- "$@" \
    --mapping-groups=organization \
    --group-provisioning=1 \
    --group-whitelist-regex="/^${VDP_ORG}\$/" \
    --group-restrict-login-to-whitelist=1
else
  set -- "$@" --group-provisioning=0 --group-restrict-login-to-whitelist=0
fi
occ user_oidc:provider velydock "$@" >/dev/null
log "OIDC provider 'velydock' -> client $VDP_OIDC_CLIENT_ID${VDP_ORG:+, organization $VDP_ORG only}"

# Straight to Keycloak instead of Nextcloud's own login form. The local admin still signs in at
# /login?direct=1.
occ config:app:set user_oidc allow_multiple_user_backends --value=0 >/dev/null

# --- Housekeeping ----------------------------------------------------------------------------
# The welcome wizard would greet every user inside the Velydock frame.
occ app:disable firstrunwizard >/dev/null 2>&1 || true
occ background:cron >/dev/null
occ config:system:set default_phone_region --value="$VDP_DEFAULT_PHONE_REGION" >/dev/null
occ config:system:set maintenance_window_start --type=integer --value=1 >/dev/null
occ db:add-missing-indices >/dev/null 2>&1 || true
log "ready"
