# Handover — xoro-epg-enricher (2026-06-19)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Was heute repariert wurde (kritischer Regression-Fix)

### Serien-Library war komplett unsichtbar
Ursache: Rubens manuelle Pfad-Änderung in Jellyfin-UI hat `ParentId` der Serien-CollectionFolder
von `UserRootFolder` auf `AggregateFolder` geändert → Jellyfin baut User-Views nur aus
UserRootFolder-Kindern → Serien verschwand von Startseite.

Fixes (direkt in SQLite + XML):
1. `ParentId` Serien → zurück auf `E9D5075A-555C-1CBC-394E-EC4CEF295274` (UserRootFolder) ✅
2. Duplicate `/config/root/default/Serien` aus `PhysicalLocationsList` entfernt ✅
3. LibraryOptions via API gesetzt ✅
4. `options.xml` korrigiert: `EnableRealtimeMonitor=false`, `EnableInternetProviders=true` ✅
5. TheTVDB aus options.xml entfernt (Plugin nicht installiert) ✅

**ENTSCHIEDEN:** `EnableInternetProviders=true` bleibt bis #24 abgeschlossen ist (Typ-B ohne NFO brauchen TMDb als Fallback). Nach #24: auf `false` → in AK6 von #24 verankert.

## Dalgliesh NFOs — geschrieben, noch nicht von Jellyfin übernommen

Folgendes wurde geschrieben:
- `/volume1/1/Serien/Dalgliesh (2021)/tvshow.nfo` — DE-Serienbeschreibung, TVDb-ID 400910
- S02E05 NFO: DE-Titel "Im Saal der Mörder – Teil 1", DE-Plot, TVDb-ID 9703949
- S02E06 NFO: DE-Titel "Im Saal der Mörder – Teil 2", DE-Plot, TVDb-ID 9703950

Item-Refresh via API getriggert (HTTP 204) — Jellyfin zeigt aber noch alten Stand.
**Nächster Schritt:** Library-Scan (erst nach Rubens OK — blockiert NAS ~1h) ODER
manuell in Jellyfin-UI: Serien → Dalgliesh → "Metadaten aktualisieren"

TVDb hat deutsche Daten für Dalgliesh bestätigt. Enricher-Code `episode_overview()` ist korrekt.
Problem war nur: alte NFOs vor WI-1 geschrieben, Enricher überschreibt keine bestehenden NFOs.

## Offene Issues

### #22 (HTTP 500 nach Episode)
Laut letzter Handover: "Client-seitiger NPE, kein Server-Fix nötig"
AK3-Retest (kein HTTP 500) noch ausstehend.

### #23 (Watched-Status / Nächste Folge)
WI-1/WI-3 implementiert. Verifikation ausstehend — braucht Library-Scan + Android-TV-Test.

### #24 (--scan-existing)
Ruben hat richtig bemängelt: Plan hat Typ-B-Serien nicht berücksichtigt.

Befund Typ-B-Serien heute geprüft:
- ~35 Serien haben korrekte NFOs vom Download (Breaking Bad, GoT, Sopranos...) ✅
- Breaking Bad Struktur korrekt: `Show/Breaking.Bad.S01/Episode.mkv+.nfo`
- Columbo: liegt entpackt vor, in --scan-existing einzubeziehen ✅

Fehlende tvshow.nfo (5 Serien — Dalgliesh heute erledigt):
- Archie (Enricher-Version)
- Geheimnisse des Kaiserreichs
- Goulag Une histoire soviétique
- Miss Marple
- Wild Congo

## Jellyfin-Status
- Serien-Library: wieder auf Startseite ✅
- 42 Serien erkannt (inkl. Duplikate: Archie 2×, Dalgliesh 2×)
- TheTVDB Plugin: NICHT installiert (nur TMDb, OMDb, MusicBrainz, AudioDB, Studio Images)
- Kein Library-Scan diese Session getriggert

## Heute abgeschlossen (2026-06-19)

- **Dalgliesh S02E05/E06** ✅ — NFOs korrekt, Library-Scan hat Episoden neu indiziert
- **#17** ✅ — geschlossen (bereits behoben)
- **#22** ✅ — InactiveSessionThreshold auf 90 Min gesetzt, HTTP 500 behoben
- **#23** ✅ — Watched-Status + "Als nächstes" funktioniert
- **#24** ✅ — --scan-existing implementiert (113 NFOs, 0 Fehler), EnableInternetProviders=false, Commit 1a042c0
- **#25** NEU — Sclotland Yard Block (title-basierter Lookup, MP4, Death Comes to Pemberley)

## Jellyfin-Status
- InactiveSessionThreshold: 90 Min (Session-Timeout Fix)
- EnableInternetProviders: false (Offline-Modus, alle NFOs vorhanden)
- Library-Scan läuft im Hintergrund (nach --scan-existing getriggert)

## #25 Plan (Planner-Output 2026-06-19, FREIGABE AUSSTEHEND)

**WI-25.1+2 (Opus):** `migrate_sclotland.py` — Dry-run-Mapping-Report. Je Block eigene Lookup-Strategie:
- Block 1 (Mord an heiliger Stätte, 2 Xoro-MP4): Episodentitel-Suche TVDb
- Block 2 (One Sine 1997 / Original Sin 1997): Wort-zu-Zahl ("Episode Two"→S1E2)
- Block 3 (Death Comes to Pemberley): E-ohne-S-Regex, Ziel AUSSERHALB Dalgliesh-Ordner

**WI-25.3 (Sonnet):** Move + NFO-Write — NUR nach Rubens Bestätigung des Dry-run-Reports.
Kritische Frage VOR WI-25.3: Sind die 2 Xoro-MP4 in Block 1 zwei separate Episoden oder zwei Teile einer Episode?

Importiert: `TVDb`, `build_episode_nfo`, `build_tvshow_nfo`, `_sanitize` aus `enricher.py`
Vorlage: `migrate_series.py` im Repo

## Nächste Session (Prioritäten)
1. **#25 Freigabe** von Ruben einholen (Plan oben)
2. **projekt.md aktualisieren** (Planner-Pflicht vor Impl)
3. **WI-25.1+2** Opus-Spawn: `migrate_sclotland.py` + Dry-run
4. Dry-run-Report Ruben vorlegen → Bestätigung → WI-25.3 (Sonnet)
