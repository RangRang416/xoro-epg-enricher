# Handover — xoro-epg-enricher (2026-06-21)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Abgeschlossen diese Session
- **#28** --flatten-downloads: 714 Dateien, 39 Ordner (Commit f6e879a), DSM-Task 3 erweitert
- **#26** Verifikation: GoT deutsch ✓, Fargo/Midsomer englisch (kein DE-Content in TVDb)
- **Midsomer S01-S06**: 27 Jellyfin-Items refreshed, NFOs eingelesen
- **Midsomer S04**: 6 NFOs manuell erstellt (7p-Dekodierung, Unterordner Inspector.Barnaby.S04.GERMAN...)
- **Midsomer S01 NFO-Korrektur**: 7p-100=Pilot(S01E00), 7p-101=S01E02..7p-104=S01E05
- **Der Therapeut von Nebenan**: In Serienordner verschoben, tvshow.nfo+episode NFO erstellt

## Offenes Problem: Midsomer S01 Jellyfin-Episodennummern
Jellyfin zeigt S01 noch falsch — NFOs wurden korrigiert, Refresh lief, aber IndexNumber
wird von Jellyfin nicht aus der NFO übernommen:
- 7p-101 → zeigt S01E01 "Tod in Badger's Drift" (soll S01E02 "Blutige Anfänger")
- 7p-102 → zeigt S01E02 "Blutige Anfänger" (soll S01E03)
- 7p-103 → zeigt S01E03 "Requiem für einen Mörder" (soll S01E04)
- 7p-104 → zeigt S01E04 "Treu bis in den Tod" (soll S01E05)
Jellyfin User-ID: 1edb78b2e1a648d5b68f49a686cb3115
Versuch: POST /Items/{id} mit korrektem IndexNumber (war beim Session-Ende offen)

## Offene Kleinigkeiten
- `7p-809.mkv` (S08E09 Midsomer): Fallback-NFO, echter Titel unbekannt
- `Der Therapeut von Nebenan`: Jellyfin-Scan nötig (Ordner neu)
- S02-S06 Midsomer: Verschiebung wie S01 prüfen (nur S01 bestätigt)

## NAS-Pfade
- Serien: `/volume1/1/Serien/`
- Enricher: `/volume1/dvb-library/enricher.py`
- DSM-Task 3: flatten → enrich → normalize-episodes (täglich 09:00)

## Issues
- #26 + #28: können geschlossen werden
