# Handover — xoro-epg-enricher (2026-06-25)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Abgeschlossen diese Session
- **#33**: Staffelordner mit römischen Ziffern (#33) — `_parse_season_num()` erkennt I–XII (commit `d112728`)
  - Bugfix Python 3.8-Kompatibilität (int|None → ohne Typhinweis)
- **Scans durchgeführt:**
  - `buffalo-archiv/Filme II/Spielfilme`: 174 erkannt, 38 Fallback
  - `buffalo-archiv/Filme II/Fernsehfilme + Archiv_II`: 54 erkannt, 6 Fallback
  - `windows-e` (gestern): 42 erkannt, 10 Fallback

## Jellyfin-Stand (2026-06-25 Abend)
- Filme gesamt: 1321 — ohne TMDb: 590 (45%) — ohne Beschreibung: 439
- Episoden gesamt: 2863 — ohne TVDb: 608 (21%) — ohne Beschreibung: 2476 (87%)

## Offene Probleme für morgen

### Nächste Scans
- `buffalo-archiv/Filme II/Serien` Serien-Scan: 0 NFOs — TVDb findet Ordner nicht
  - Ursache: Unterstriche + Staffelinfo im Ordnernamen (`Goliath S04`, `Kir_Royale`)
  - Fix nötig: Ordnernamen vor TVDb-Suche bereinigen (Unterstriche → Leerzeichen, Staffelangaben entfernen)
- `windows-e/Archiv/Fernsehen/Spielfilm/`: Flat .flv-Dateien, kein Unterordner pro Film → Enricher kann nicht verarbeiten

### Issue #29: Serien ohne Deutsche Beschreibung (87% ohne Beschreibung)
- TVDb-Erkennung okay (21% fehlen), aber Beschreibungen kommen nicht an

## Morgen-Auftrag (vereinbart)
Ruben hat Orchestrator-Auftrag gegeben: **Erfassung + Beschreibung in Jellyfin selbstständig durchziehen**, inklusive vollem Workflow (Planner, Issues, Doku).

Checkpoints die Freigabe brauchen:
1. Nach Planner-Output
2. Jellyfin Library-Scan (blockiert NAS 1h+)
3. Datei-Umbenennungen (irreversibel)
4. Push nach Test

## DSM / Docker / NAS
- docker-compose.yml: `/volume1/dvb-library/docker-compose.yml`
- CIFS Mounts: `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}`
- mount-cifs.sh: als root via DSM Task Scheduler "mount-cifs-shares"

## Jellyfin
- URL: http://192.168.2.9:8096, Key: 0fa51eb22d174aca876c01c8621dd1dc
- Library-Scan Task-ID: 7738148ffcd07979c7ceb148e06b3aed
- Serien-Library ID: 43cfe12fe7d9d8d21251e0964e0232e2
