# Handover — xoro-epg-enricher (2026-06-20 S4)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Abgeschlossen (letzte Sessionen)
- #27 --normalize-episodes: 54 Midsomer-NFOs, DSM-Task täglich 09:00 (Commit e32759f)
- #26 lockdata: 38 tvshow.nfo entsperrt, 6 bleiben gesperrt
- Fargo S05: Pack-Ordner aufgelöst, 10 Episoden flach

## Offene Issues
- **#26**: OFFEN — Scan-Verifikation ausstehend (dt. Beschreibungen Fargo/Midsomer/GoT?)
- **#28**: NEU — --flatten-downloads Feature

## Nächste Session — #28 implementieren
Problem: Wednesday + Vikings haben verschachtelte Ordnerstrukturen
- Wednesday: `S01/EpisodeName/file.mkv` (2 Ebenen, + Sample-Ordner)
- Vikings: `Vikings 2/EpisodeName/file.mkv` (3 Ebenen, Staffel-Ordner falsch benannt)
- Serien-Pfad auf NAS: `/volume1/1/Serien/`
- Enricher-Pfad auf NAS: `/volume1/dvb-library/enricher.py`
- DSM-Task 3: täglich 09:00, nach Impl um --flatten-downloads erweitern

## Offene Kleinigkeiten
- `7p-809.mkv` (S08E09 Midsomer) bleibt ohne NFO (existiert nicht in TVDb)
- Down Cemetery Road + Jim Bergerac: englische Beschreibungen, lockdata behalten
