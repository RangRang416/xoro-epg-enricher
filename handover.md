# Handover — xoro-epg-enricher (2026-06-24)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Abgeschlossen diese Session
- **#31**: CIFS-Mounts aus Docker → Bind-Mounts mit nofail-Logik
  - Docker-managed CIFS-Volumes entfernt, Bind-Mounts auf `/volume1/dvb-library/mounts/` 
  - `mount-cifs.sh` deployed, Credentials-Datei `.cifs-windows-creds` (chmod 600)
  - Jellyfin startet jetzt auch wenn PC/Linkstation aus (leere Dirs, kein Mount-Fehler)
  - DSM Task Scheduler Boot-Aufgabe `mount-cifs-shares` angelegt und getestet ✓
- CIFS-Shares erfolgreich über neue Pfade gemountet ✓
- Library-Scan angestoßen, bei ~81% abgebrochen (Ruben wollte gucken)

## Nächste Session
1. **#32**: Planner für Metadaten-Lücke — 56% Filme / 88% Episoden ohne Erkennung
   - buffalo-archiv read-only → Schreibzugang Linkstation klären
   - bestehende-filme: 141 Filme ohne Metadaten (prüfen warum)

## DSM Task Scheduler Anleitung (für #31)
Einmalig in DSM Web UI (http://192.168.2.9:5000):
1. Systemsteuerung → Aufgabenplaner → Erstellen → Ausgelöste Aufgabe → Benutzerdefiniertes Script
2. **Allgemein**: Name: `mount-cifs-shares` | Benutzer: `root` | Ereignis: `Booten`
3. **Aufgabeneinstellungen**: Befehl: `/volume1/dvb-library/mount-cifs.sh`
4. OK → Aufgabe aktivieren (Häkchen)
5. Log unter `/volume1/dvb-library/mount-cifs.log`

## Docker / NAS
- docker-compose.yml: `/volume1/dvb-library/docker-compose.yml` (AUCH Container Manager: `/var/packages/ContainerManager/var/all_shares/docker/jellyfin/docker-compose.yml`)
- CIFS Mount-Punkte: `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}`
- Mount-Script: `/volume1/dvb-library/mount-cifs.sh` (als root ausführen)
- Jellyfin Library-Scan: `POST /ScheduledTasks/Running/7738148ffcd07979c7ceb148e06b3aed`
- Scan nur sinnvoll wenn PC + Linkstation AN sind

## Jellyfin
- URL: http://192.168.2.9:8096, Key: 0fa51eb22d174aca876c01c8621dd1dc
- UserId: 1edb78b2e1a648d5b68f49a686cb3115
- Serien-Library ID: 43cfe12fe7d9d8d21251e0964e0232e2
- Hinweis: Jellyfin liest IndexNumber nicht aus NFO → per POST /Items/{id} setzen
- MetadataSavers = [] für alle Libraries (NFO-Schreibfehler behoben)

## Medien-Stand
- Filme: 1.232 (56% ohne Metadaten)
- Serien: 59 / Episoden: 2.863 (88% ohne Metadaten)
- Dokumentationen: 8

## Offene Kleinigkeiten
- `7p-809.mkv` (S08E09 Midsomer): Fallback-NFO, echter Titel unbekannt
- Issues #13, #14: optional
- Issue #32: Metadaten-Lücke (groß, Planung nötig)
