# Handover — xoro-epg-enricher (2026-04-25, Rev 2)

## Status: Plan finalisiert (2× Planner-Revision), bereit für Issue #1 (PoC)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Finale Architektur
Xoro → USB-Stick → Synology USB Copy → Python auf NAS → Jellyfin Docker → Android

## Nächster Schritt: Issue #1 — PoC manuell (6 Punkte)
1. Xoro USB-Stick-Format = SATA-Format?
2. Synology USB Copy funktioniert?
3. Python ≥ 3.9 auf Synology?
4. pip install rapidfuzz/chardet/requests auf ARM/x86?
5. TMDb-API-Key + manueller .nfo-Test
6. Jellyfin Docker + .ts auf Android abspielen?

Alle ✓ → Issue #2 starten. Ein ✗ → Eskalation.

## Issues
13 offen (#1–#13), #0 geschlossen.
#1, #2, #7, #8, #9 revidiert (Synology-Architektur). #3–#6, #10–#13 unverändert.
