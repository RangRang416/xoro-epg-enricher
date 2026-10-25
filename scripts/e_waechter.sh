#!/bin/bash
# Waechter fuer Laufwerk E: (Windows-PC) — meldet an Healthchecks.io, wenn der PC
# erreichbar ist, das NAS ihn aber laenger als 15 Min nicht nutzen kann.
# Anlass: Windows-Passwort am 05.10.2026 geaendert -> E: 15 Tage still weg, weil
# mount-cifs.sh Mount-Fehler verwirft (siehe CHANGELOG 2026-10-20).
#
# Aufruf: am Ende von /volume1/dvb-library/mount-cifs.sh (alle 5 Min., root).
# Ping-Adresse steht nur auf dem NAS in /volume1/dvb-library/.e-waechter.conf
# (Zeile HC_URL=https://hc-ping.com/...), nie im Repo.
#
# Zustaende:
#   PC aus (Port 445 zu)             -> Erfolg-Ping (nichts zu tun)
#   PC an, E: eingebunden + lesbar   -> Erfolg-Ping
#   PC an, E: fehlt/haengt >= 15 Min -> /fail-Ping mit Grund aus dmesg
# Kommt gar kein Ping (NAS aus, Router aus), meldet Healthchecks.io nach Period+Grace.
#
# Test ohne Ping: E_WAECHTER_DRYRUN=1, Host/Mount/Status-Datei per Umgebung ueberschreibbar.

CONF=${E_WAECHTER_CONF:-/volume1/dvb-library/.e-waechter.conf}
STATE=${E_WAECHTER_STATE:-/volume1/dvb-library/.e-waechter.state}
WINDOWS_HOST=${E_WAECHTER_HOST:-192.168.2.2}
WINDOWS_PORT=${E_WAECHTER_PORT:-445}
WINDOWS_MOUNT=${E_WAECHTER_MOUNT:-/volume1/dvb-library/mounts/windows-e}
SCHWELLE=${E_WAECHTER_SCHWELLE:-900}

HC_URL=$(grep '^HC_URL=' "$CONF" 2>/dev/null | cut -d= -f2- | tr -d '"\r ')

melde() {  # $1 = "" (Erfolg) oder "/fail", $2 = Text fuer das Healthchecks-Protokoll
  if [ -n "$E_WAECHTER_DRYRUN" ]; then
    echo "PING${1:-/ok}: $2"
    return 0
  fi
  [ -n "$HC_URL" ] || return 0
  curl -fsS -m 10 --retry 2 -o /dev/null --data-raw "$2" "$HC_URL$1" 2>/dev/null
}

if ! timeout 3 bash -c "echo > /dev/tcp/$WINDOWS_HOST/$WINDOWS_PORT" 2>/dev/null; then
  rm -f "$STATE"
  melde "" "PC aus"
  exit 0
fi

if grep -q " $WINDOWS_MOUNT " /proc/mounts && timeout 20 ls "$WINDOWS_MOUNT" >/dev/null 2>&1; then
  rm -f "$STATE"
  melde "" "E: eingebunden"
  exit 0
fi

# PC erreichbar, E: fehlt oder haengt
jetzt=$(date +%s)
[ -s "$STATE" ] || echo "$jetzt" > "$STATE"
seit=$(( jetzt - $(cat "$STATE") ))
if [ "$seit" -ge "$SCHWELLE" ]; then
  # Fehlerzeilen nur des letzten Mount-Versuchs auf den PC (nicht Buffalo o.ae.)
  grund=$(dmesg 2>/dev/null | awk -v h="Attempting to mount //$WINDOWS_HOST/" '
    index($0, h) { buf = ""; an = 1; next }
    /Attempting to mount/ { an = 0 }
    an && /STATUS_|[Ee]rror|failed/ { sub(/^\[[^]]*\] /, ""); buf = buf $0 " " }
    END { print buf }')
  melde "/fail" "PC erreichbar, aber E: seit $((seit / 60)) Min nicht nutzbar. ${grund:-Kein Kernel-Hinweis.} STATUS_LOGON_FAILURE = Windows-Passwort geaendert -> /root/nas-passwort.sh"
fi
exit 0
