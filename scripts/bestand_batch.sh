#!/bin/bash
# Stellt mehrere (vorher von Hand geprüfte) Bestandsserien nacheinander mit tMM um (#29).
# Je Serie: frischer Plan -> bricht ab bei unzugeordneten Dateien/Sperren -> apply -> wartet, bis Jellyfin
# alle Folgen kennt (NAS-Last!) -> nächste Serie. Jeder Fehler beendet den ganzen Lauf.
# Verwendung: bash scripts/bestand_batch.sh "Down Cemetery Road" "Geheimnisse des Kaiserreichs" ...
cd "$(dirname "$0")/.."
export JELLYFIN_KEY=$(ssh synology 'grep -o -- "--jellyfin-key [^ ]*" /volume1/dvb-library/inbox_run.sh | cut -d" " -f2' | sed "s/[\"\\\\']//g")
[ -n "$JELLYFIN_KEY" ] || { echo "Jellyfin-Schlüssel nicht gefunden"; exit 1; }
for serie in "$@"; do
  echo "=== $serie ($(date +%H:%M))"
  out=$(python3 scripts/bestand_tmm.py plan "$serie" 2>&1) || { echo "$out" | tail -5; echo "Plan fehlgeschlagen"; exit 1; }
  plan=$(echo "$out" | sed -n 's/^Plan: //p' | tail -1)
  [ -f "$plan" ] || { echo "Planpfad nicht gefunden"; exit 1; }
  info=$(python3 - "$plan" <<'P'
import json,sys
p=json.load(open(sys.argv[1])); exts=('.mkv','.avi','.mp4','.m4v','.mpg','.ts','.m2ts','.wmv')
vid=sum(1 for m in p['moves'] if m[1].lower().endswith(exts))
print(len(p['unmatched']),len(p['blocking']),vid,p['new_show'])
P
)
  unm=$(echo "$info" | cut -d' ' -f1); blk=$(echo "$info" | cut -d' ' -f2); vid=$(echo "$info" | cut -d' ' -f3)
  neu=$(echo "$info" | cut -d' ' -f4-)
  echo "  Plan: $vid Videos, unzugeordnet $unm, Sperren $blk, neuer Name: $neu"
  if [ "$unm" != "0" ] || [ "$blk" != "0" ]; then echo "  -> Auffälligkeit, Lauf beendet (bitte von Hand ansehen)"; exit 2; fi
  python3 scripts/bestand_tmm.py apply "$serie" 2>&1 | tail -4 || { echo "apply fehlgeschlagen"; exit 1; }
  echo "  warte auf Jellyfin ($vid Folgen) ..."
  ok=0
  for i in $(seq 1 80); do
    n=$(python3 scripts/jf_episode_count.py "$neu")
    [ -n "$n" ] && [ "$n" -ge "$vid" ] 2>/dev/null && { ok=1; break; }
    sleep 30
  done
  [ "$ok" = 1 ] || { echo "  Jellyfin kennt nach 40 Min erst ${n:-0} von $vid Folgen — Lauf beendet"; exit 3; }
  echo "  fertig: Jellyfin kennt $n Folgen"
done
echo "ALLE FERTIG ($(date +%H:%M))"
