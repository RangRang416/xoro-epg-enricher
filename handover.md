# Handover — xoro-epg-enricher (2026-07-01)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Nachtrag: Session 2026-06-26 wurde nie sauber übergeben
Die Session vom 26.06. (nach diesem Handover) hat Commits bis 17:12 Uhr gemacht
(#34, #29 Fixes) und lief danach lokal weiter (Mount-Reparatur, Gratuitous-ARP-
Zwischenfall, Serien-Scan), bis sie am Nutzungslimit abbrach — **ohne** Commit
des Scan-Ergebnisses oder Handover-Update. Ergebnis nachträglich rekonstruiert:
- Serien-Scan auf `buffalo-archiv/Filme II/Serien`: **64 NFOs erstellt, 0 Fehler**
  (u.a. `Goliath S04`→Goliath, `Kir_Royale`→Kir Royal erkannt dank #34-Fix)
- **Zweiter Scan-Durchlauf auf dem Rest von `Serien` wurde NIE gestartet** — offen für nächste Session
- Mount-Fix: `timeout=5` Parameter aus CIFS-Mount-Optionen entfernt (ungültig, ist ein NFS-Parameter, keine Regression bekannt)

## Abgeschlossen Session 2026-06-25
- **#33**: Staffelordner mit römischen Ziffern (#33) — `_parse_season_num()` erkennt I–XII (commit `d112728`)
  - Bugfix Python 3.8-Kompatibilität (int|None → ohne Typhinweis)
- **Scans durchgeführt:**
  - `buffalo-archiv/Filme II/Spielfilme`: 174 erkannt, 38 Fallback
  - `buffalo-archiv/Filme II/Fernsehfilme + Archiv_II`: 54 erkannt, 6 Fallback
  - `windows-e` (gestern): 42 erkannt, 10 Fallback

## Neu Session 2026-07-01 — Wake-on-LAN für PC + Linkstation
Anlass: Stromausfall bei Ruben, dabei ging eine lokale Claude-Code-Session auf
dem Windows-PC verloren (dort nicht wiederherstellbar, war nicht in diesem Repo).
Zusätzlich Ruben-Wunsch: PC + Linkstation sind nicht dauerhaft an, sollen aber
abends ab 20 Uhr für Jellyfin verfügbar sein.
- `/volume1/dvb-library/wol-wake.sh` angelegt (NAS-only, nicht im Repo, wie `mount-cifs.sh`)
- DSM-Task 7 "WOL Wake PC+Linkstation": täglich 19:50 Uhr (einmalig), sendet Magic Packets
- Bewusst KEIN On-Demand-Wecken bei Jellyfin-Play (Abwägung: Boot-Zeit lässt sich
  nicht wegtricksen, zusätzlicher Reverse-Proxy/Plugin würde die 1GB-RAM-NAS belasten)
- **Offen / von Ruben zu prüfen:** WOL in Windows-BIOS + Gerätemanager aktiviert?
  Windows-Schnellstart deaktiviert? Linkstation (2015er-Firmware) unterstützt im
  ausgeschalteten Zustand überhaupt WOL (Standby-Strom)? Kein Admin-Zugriff zur Prüfung.
  Details siehe CHANGELOG.md [2026-07-01].

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
