# Handover — xoro-epg-enricher (2026-06-21)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Abgeschlossen diese Session
- **#28** --flatten-downloads: 714 Dateien, 39 Ordner (Commit f6e879a), DSM-Task 3 erweitert
- **#26** Verifikation: GoT deutsch ✓, Fargo/Midsomer englisch (kein DE-Content in TVDb)
- **Midsomer S01-S06**: 27 Jellyfin-Items refreshed (NFOs von normalize-episodes eingelesen)
- **Midsomer S04**: 6 NFOs manuell erstellt (7p-Kodierung, in Unterordner Inspector.Barnaby.S04.GERMAN.AC3.720p.HDTV)
- **Midsomer S01 Korrektur**: 7p-100=Pilot(S01E00), 7p-101=S01E02..7p-104=S01E05 — NFOs+Refresh
- **Der Therapeut von Nebenan**: In Serienordner verschoben, tvshow.nfo+episode NFO erstellt

## Issues
- **#26**: Kann geschlossen werden (Verifikation abgeschlossen)
- **#28**: Kann geschlossen werden (implementiert + deployed)

## NAS-Pfade
- Serien: `/volume1/1/Serien/`
- Enricher: `/volume1/dvb-library/enricher.py`
- DSM-Task 3: flatten → enrich → normalize-episodes (täglich 09:00)

## Offene Kleinigkeiten
- `7p-809.mkv` (S08E09 Midsomer): Fallback-NFO erstellt, echter Episodentitel unbekannt
- `Der Therapeut von Nebenan`: Jellyfin-Scan nötig damit neuer Ordner erkannt wird
- S02-S06 Midsomer: Verschiebung wie S01 prüfen (nur S01 bestätigt wegen Pilotfilm)
