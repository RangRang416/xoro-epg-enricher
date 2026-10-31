#!/bin/bash
# Wendet den tMM-Plan EINER Serie an (scripts/bestand_tmm.py apply). Holt den Jellyfin-Schlüssel selbst von der NAS.
# Verwendung: bash scripts/bestand_apply.sh "Fargo"
set -e
[ -n "$1" ] || { echo "Serienordner angeben, z. B.: bash scripts/bestand_apply.sh \"Fargo\""; exit 1; }
cd "$(dirname "$0")/.."
export JELLYFIN_KEY=$(ssh synology 'grep -o -- "--jellyfin-key [^ ]*" /volume1/dvb-library/inbox_run.sh | cut -d" " -f2' | sed "s/[\"\\\\']//g")
[ -n "$JELLYFIN_KEY" ] || { echo "Jellyfin-Schlüssel nicht gefunden"; exit 1; }
exec python3 scripts/bestand_tmm.py apply "$1"
