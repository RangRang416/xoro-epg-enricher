# Handover — xoro-epg-enricher (2026-06-20)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Diese Session

### #25 abgeschlossen
- 7 Dateien aus `Adam Dalgliesh, Sclotland Yard/` in Jellyfin-Struktur verschoben:
  - Block 1: `P.D. James Adam Dalgliesh/Season 06/` → 2 MP4 als -part1/-part2 (1 Episode)
  - Block 2: `P.D. James Adam Dalgliesh/Season 11/` → 3 Episoden Original Sin 1997
  - Block 3: `Death Comes to Pemberley (2013)/Season 01/` → 2 Episoden
- NFOs mit Platzhalter-Titeln (kein TVDb-Key verfügbar)
- Script `migrate_sclotland.py` liegt auf NAS + im Repo

### lockdata + EnableInternetProviders
- 2701 NFOs mit `<lockdata>true</lockdata>` versehen (Serien + Filme)
- 11 Film-NFOs übersprungen (falsche Zeichenkodierung: Star Wars, HdR, Schwarzenegger)
- `EnableInternetProviders=true` in Serien/options.xml gesetzt
- Jellyfin neu gestartet

## Offenes Problem: Englische NFO-Beschreibungen
Fargo (und vermutlich weitere Serien) hat NFO mit englischer Beschreibung.
Durch lockdata=true kann TheTVDB diese NICHT korrigieren.

Lösung: lockdata selektiv aus NFOs mit englischen Inhalten entfernen.
→ Ruben hat Session beendet, Entscheidung offen.

## Rubens Sentiment
"Das ganze Projekt ist ein Fass ohne Boden" — jedes Fix zieht neues Problem nach sich.
Nächste Session: erst Scope-Entscheidung bevor weitergearbeitet wird.

## Offene Issues
- #14: Web-Dashboard (Optional)
- #13: Serien/Episoden-Support (Optional)

## Jellyfin-Status
- EnableInternetProviders: true
- lockdata: 2701 NFOs gesperrt
- TheTVDB Plugin: installiert + Scan läuft
- EnableRealtimeMonitor: steht auf true (war mal auf false gesetzt — prüfen)
