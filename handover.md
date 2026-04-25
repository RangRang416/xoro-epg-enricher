# Handover — xoro-epg-enricher (2026-04-25)

## Status: Projekt-Setup abgeschlossen, bereit für Issue #1 (PoC)

## Repo
https://github.com/RangRang416/xoro-epg-enricher (Commit 521d49c)
Lokal: `/mnt/c/Users/Ruben/Projects/Xoro_Aufnahmen mit EPG_Beschreibung/`

## Nächster Schritt: Issue #1 — PoC manuell
Ruben muss: TMDb-API-Key registrieren (themoviedb.org, kostenlos), Jellyfin installieren, 1 Aufnahme manuell durch die Kette schieben.
Stopp-Bedingung: Falls .ts-Playback in Jellyfin Android nicht funktioniert → Plan-Revision.

## Architektur (final)
Python 3.11 + TMDb API + Jellyfin lokal + Windows Task Scheduler (alle 10 Min).
Kein n8n, kein XMLTV-Archiv.

## Xoro-Format
N:\PVR\REC\00NNN\ mit record.ts + RECInfo.txt (Sender + Titel, keine Langbeschreibung).

## Issues (13 offen, #0 geschlossen)
#1 PoC → #2 Grundgerüst → #3 Parser → #4 TMDb-Client → #5 Cover → #6 NFO → #7 Orchestrator → #8 Task Scheduler → #9 Jellyfin-Doku → #10 E2E-Test → #11 Härtung → (#12/#13 optional)
