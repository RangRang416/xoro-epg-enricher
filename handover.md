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
- Script `migrate_sclotland.py` liegt auf NAS + im Repo (Commit 0d8d5e2)

### lockdata + EnableInternetProviders
- 2701 NFOs mit `<lockdata>true</lockdata>` versehen (Serien + Filme)
- 11 Film-NFOs übersprungen (falsche Zeichenkodierung: Star Wars, HdR, Schwarzenegger)
- `EnableInternetProviders=true` in Serien/options.xml gesetzt
- TheTVDB Plugin von Bernd installiert + Scan lief
- Jellyfin neu gestartet

## Jellyfin-Status
- EnableInternetProviders: true
- PreferredMetadataLanguage: de / MetadataCountryCode: DE
- lockdata: 2701 NFOs gesperrt
- SaveLocalMetadata: false (Jellyfin schreibt NICHT in NFO-Dateien zurück)
- EnableRealtimeMonitor: steht auf true (war früher mal auf false — prüfen ob Problem)

## Bekannter Ist-Zustand NFO-Beschreibungen
- Death in Paradise, Columbo → deutsche Beschreibungen ✅ (durch lockdata geschützt)
- Fargo → englische Beschreibung, durch lockdata blockiert ❌
- Weitere Serien mit englischen Beschreibungen: unbekannt, nicht systematisch geprüft

## Nächste Session — Ziel: alle Serien auf Deutsch

**Bernd will deutsche Beschreibungen für alle Serien.**

### Plan (ein Schritt, überschaubar):
`lockdata` aus `tvshow.nfo`-Dateien mit englischen Beschreibungen entfernen.
TheTVDB holt dann automatisch deutsche Daten (PreferredMetadataLanguage=de).
Episode-NFOs behalten lockdata (Enricher-Daten sind korrekt).

**Zwei Optionen — Bernd entscheidet:**
- A) **Gezielt**: nur englische tvshow.nfo identifizieren und lockdata entfernen
- B) **Pauschal**: lockdata aus ALLEN tvshow.nfo entfernen → TheTVDB überschreibt alle mit Deutsch

Nach lockdata-Entfernung: einmaligen Jellyfin-Scan anstoßen (Bernd gibt OK, blockiert NAS ~1h).

### Offene Issues
- #14: Web-Dashboard (Optional, niedrige Prio)
- #13: Serien/Episoden-Support (Optional, niedrige Prio)
