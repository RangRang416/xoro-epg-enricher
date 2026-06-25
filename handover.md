# Handover — xoro-epg-enricher (2026-06-25)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Abgeschlossen diese Session
- **#32 WI-2 Inventur-Spike**: Root-Cause bestehende-filme = Scene-Releases ohne RECInfo.txt. ~95% auflösbar. buffalo-archiv/windows-e offline → kein Scan möglich.
- **#32 WI-3 Implementierung**: `--scan-existing-movies` deployed:
  - 52 Filme in `/volume1/1/Filme` per TMDb erkannt + NFO geschrieben
  - 8 Fallback-NFOs (kein TMDb-Match)
  - Sammlungsordner (Harry Potter, Herr der Ringe, Star.Trek, Star.Wars, Schwarzenegger) rekursiv aufgelöst
  - Sample-Ordner, filecrypt.cc, Multi-Video-Ordner korrekt übersprungen
- Commit: `42e29fa` gepusht

## Offene Punkte #32
- **buffalo-archiv / windows-e**: Scan nötig wenn Geräte online. Befehl:
  ```
  python3 /volume1/dvb-library/enricher.py --scan-existing-movies \
    --tmdb-key 944022b3c0d95c1d57601c7a32bc9e7f \
    /volume1/dvb-library/mounts/buffalo-archiv \
    /volume1/dvb-library/mounts/windows-e
  ```
- **Jellyfin-Scan**: Noch NICHT ausgelöst (blockiert NAS 1+ Std, Ruben muss freigeben)
- **Nicht verarbeitbar** (10 Fälle): Star.Wars Ep. I/IV/VII/VIII/IX (2 Videos: main+sample), Schwarzenegger/Total Recall (direktes MKV in Collection), Terminator (6 direkte MKV)

## Nächste Session
1. **Jellyfin-Scan** freigeben → prüfen ob Metadaten-Quote verbessert
2. **buffalo-archiv / windows-e** scannen wenn Geräte an
3. **Issue #29**: Serien ohne Deutsche Beschreibung (TVDb-Lücken)

## DSM Task Scheduler
- Enricher läuft täglich 09:00 (PVR/USB + normalize-episodes + flatten-downloads)
- `--scan-existing-movies` ist ein manueller Einmal-Lauf (nicht im DSM-Task)

## Docker / NAS
- docker-compose.yml: `/volume1/dvb-library/docker-compose.yml`
- CIFS Mount-Punkte: `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}`
- Mount-Script: `/volume1/dvb-library/mount-cifs.sh` (als root ausführen)

## Jellyfin
- URL: http://192.168.2.9:8096, Key: 0fa51eb22d174aca876c01c8621dd1dc
- UserId: 1edb78b2e1a648d5b68f49a686cb3115
- Library-Scan: `POST /ScheduledTasks/Running/7738148ffcd07979c7ceb148e06b3aed`
- Serien-Library ID: 43cfe12fe7d9d8d21251e0964e0232e2

## Medien-Stand (vor Jellyfin-Scan)
- bestehende-filme: 218 NFOs vorhanden (von ~228 Video-Ordnern), 10 nicht lösbar
- buffalo-archiv / windows-e: unbekannt (offline gewesen)
