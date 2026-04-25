# Handover — Xoro EPG Projekt (2026-04-25)

## Status: Erkundungsphase abgeschlossen, Planner NICHT gespawnt (Rate-Limit)

## Erkenntnisse
- Aufnahmen in nummerierten Ordnern: N:\PVR\REC\00029\ etc.
- Jeder Ordner: record.ts + RECInfo.txt (Sender + Titel, KEINE Langbeschreibung)
- Kein DLNA auf Xoro, keine Firmware-Modifikation möglich
- Ruben nutzt KLACK Android-App → alle Aufnahmen sind bekannte Titel → TMDb reicht
- Ziel: Jellyfin (lokal, Android-App) als mobile Mediathek
- n8n Hetzner scheidet aus (N: lokal) → lokales Skript auf Windows

## Architektur (entschieden)
RECInfo.txt → Titel + Sender → TMDb API → .nfo + poster.jpg → Jellyfin → Android

## Nächste Session
1. Planner (Opus) spawnen mit obigem Kontext
2. GitHub Repo anlegen: xoro-epg-enricher (RangRang416)
3. KEIN weiterer Erkundungsaufwand nötig — alle Fragen geklärt
