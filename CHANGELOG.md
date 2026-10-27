# Changelog

## [2026-10-27] — #53 inbox.py: Abgekürzte Dateinamen, falsch nummerierte Dateien, Folge 0 (Echttests Big Bang S05, Doctor Who)

### Fixed
- Dateien mit abgekürztem Namen (`itn-tbbt.s05e01.mkv`, `tv4a-doctorwho.2005.s02e01.mkv`) im Release-Ordner (`The.Big.Bang.Theory.S05E01…`, `Doctor.Who.2005.S02E01…`) blieben liegen: Der Ordnername wird jetzt als zweite Quelle für den Seriennamen genutzt.
- Der Zwischenspeicher der Serien-Suche setzte `doctorwho` und `Doctor Who` gleich; das Nicht-Treffer-Ergebnis des ersten blockierte den zweiten. Schlüssel jetzt der unveränderte Name.
- Nennen Ordner und Datei verschiedene Folgen (Ordner `S02E00` enthält `…s02e01.mkv`) und liegt genau ein Video (ohne Sample) im Ordner, gilt die Nummer im Ordnernamen.
- `episode_info`: TVDb ignoriert bei `episodeNumber=0` den Filter und liefert die erste Folge der Staffel; es wird nur noch eine Folge mit passender Staffel/Nummer genommen (sonst kein Titel statt falschem Titel).
- Tests: 76 grün (neu: FolderNameFallback, EpisodeInfoMatch). Auf der NAS eingespielt 27.10. (Sicherung `*.bak-20261027`), Probelauf gegen echten Eingang: 14 Doctor-Who-Folgen zugeordnet, 0 unklar.

## [2026-10-26] — #53 inbox.py: Liste `_Unklar.txt`

### Added
- Dateien, die die Eingangs-Automatik nicht sicher zuordnen kann (kein Titel/Jahr, Serie nicht eindeutig, mehrere Videos im Ordner, andere TVDb-ID), bleiben wie bisher unverändert liegen und stehen jetzt mit Grund in `Eingang/_Unklar.txt` (in Alltagssprache; wird bei jedem `--apply`-Lauf neu geschrieben und entfernt, sobald nichts mehr unklar ist). Es werden bewusst keine Dateien verschoben. 69 Tests.

## [2026-10-26] — #53 inbox.py: Auflösung hinter SxxExx stört die Erkennung nicht mehr

### Added (Trailer)
- Neue Serien aus dem Eingang bekommen in der `tvshow.nfo` einen `<trailer>` (YouTube, Jellyfin zeigt dann den Trailer-Knopf, wie bei tinyMediaManager). Quelle: TheTVDB `series/<id>/extended` → `trailers`, Deutsch vor Englisch vor anderen Sprachen, nur YouTube (`enricher.youtube_trailer_tag`, `build_tvshow_nfo(series, trailer)`). Fehlt der Trailer oder schlägt die Abfrage fehl, wird trotzdem normal einsortiert. 3 Tests (54 gesamt). Filme: noch offen (TMDb `/movie/<id>/videos`).

### Fixed (Echttest "The Big Bang Theory", 2026-10-26)
- Scene-Dateinamen mit Release-Gruppe vorn (`jajunge-the.big.bang.theory.s01e01.1080p.mkv`) wurden als Serie "jajunge-the big bang theory" gesucht und blieben liegen. `strip_group_prefix`: findet TVDb den Namen nicht, wird es noch einmal ohne das Gruppenwort vor dem ersten `-` versucht (nur bei eindeutigem Treffer; 'Star Trek - Enterprise' bleibt unberührt). 68 Tests.
- Deployt auf die NAS (`/volume1/dvb-library/`, Sicherung `*.bak-20261026`). Die geplante DSM-Aufgabe (stündlich, root) hat 4 Folgen selbständig einsortiert, Jellyfin zeigt sie mit deutschen Titeln. `unpack.py` liegt dort, ist aber AUS (`--unpack` fehlt in `inbox_run.sh`).

### Changed (Opus-Review `unpack.py`, 2026-10-26)
- Inhaltsverzeichnis jetzt mit `unrar lt -v -c-` (ohne `-idq`, sonst leer — auf der NAS bestätigt) und Prüfung, dass genau so viele `Archive:`-Blöcke kommen wie Teile da sind (sonst würde ein Link in Teil 2 nicht geprüft). Nur an `\n` trennen (nicht `splitlines`, Zeilenumbruch im Namen konnte den Typ fälschen), je Eintrag genau ein `Type`, kein `Target`, keine Steuerzeichen, keine doppelten Dateinamen.
- Nach dem Auspacken `lstat` jedes Eintrags (nur normale Dateien), `-ai`, Speicherdeckel 700 MB, kein stdin, Plausibilität (entpackt ≤ 1,5 × gepackt) und Platz + 5 GB Reserve anhand der echten Größen.
- Archive werden nie überschrieben (`_Reste/Archive-<Tag>/<name>[_n]`); Temp-/Zielordner neben dem Paket; Wiederaufnahme nach Abbruch; `.RAR` groß geschrieben erkannt, alte `.r00`-Benennung abgelehnt; JDownloader-Vortritt (Dateien schon da → nichts tun); Fehlschläge in `_Reste/entpacken-fehler.json` vermerkt (erst nach Änderung neuer Versuch); `--max-unpack` Standard 1. 33 Auspack-Tests (66 gesamt).

### Added
- `unpack.py` (Notlösung, standardmäßig AUS): packt vollständige mehrteilige RAR-Pakete im Eingang aus, die JDownloader nicht selbst ausgepackt hat. Nur mit `inbox.py --unpack`; Pakete müssen ≥ 24 h unverändert liegen (JDownloader hat Vortritt). Sicherheit: nur vollständige Pakete, Inhaltsverzeichnis wird vorher geprüft (nur Dateien/Ordner, keine Verknüpfungen/`..`/absolute Pfade, sonst Abbruch), flaches Auspacken in Temp-Ordner mit `nice`/`ionice`, höchstens 3 Pakete pro Lauf, mind. doppelter Platz frei. Archive werden nie gelöscht, sondern nach `_Reste/Archive-<Datum>/` verschoben. 17 Tests (`tests/test_unpack.py`).

### Fixed
- `_SXXEYY_RE`: Namen wie `Wednesday.S01E01-1080p.GERMAN` wurden als mögliche Bereichsangabe verworfen und blieben im Eingang liegen. Jetzt nur noch `-02`/`_02` (1–2 Ziffern) direkt hinter der Folge als unklar; `-1080p`, `_720p` usw. sind unkritisch. Test `test_resolution_after_episode_is_not_a_range` (34 Tests grün).

## [2026-10-25] — Wächter für Laufwerk E: (Healthchecks.io)

### Added
- `scripts/e_waechter.sh`: meldet an Healthchecks.io, wenn der PC erreichbar ist (Port 445), Laufwerk E: aber ≥ 15 Min fehlt oder hängt; `/fail`-Ping enthält den Kernel-Grund des letzten PC-Mount-Versuchs (z. B. `STATUS_LOGON_FAILURE` = Windows-Passwort geändert). PC aus oder E: ok → Erfolg-Ping. Ohne Ping-Adresse sendet es nichts.
- Auf der NAS: `/volume1/dvb-library/e_waechter.sh`, Aufruf am Ende von `mount-cifs.sh` (alle 5 Min., root; Sicherung `mount-cifs.sh.bak-20261025`). Ping-Adresse gehört nach `/volume1/dvb-library/.e-waechter.conf` (`HC_URL=…`), nie ins Repo.
- Getestet im Probemodus (`E_WAECHTER_DRYRUN=1`) lokal und auf der NAS: PC aus, E: ok, E: fehlt frisch, E: fehlt > 15 Min, wieder ok.

## [2026-10-25] — #53/#29 Bestandsserien: Reparatur mit tinyMediaManager PRO (TVDB)

### Added
- `scripts/bestand_tmm.py` (`plan` / `apply` je Serie): tinyMediaManager arbeitet nie direkt auf der NAS, sondern in einer Sandbox mit Platzhalter-Videos; `apply` schiebt den alten Serienordner komplett in die Quarantäne (`Eingang/_Reste/Bestand-<Datum>/`, nichts wird gelöscht), legt die Folgen in `Serie/Season NN/Serie - SxxEyy - Titel.ext` zurück, benennt Untertitel passend (`….de.forced.idx`) und lädt die neuen NFOs/Bilder hoch. Vor dem Verschieben: Plan-Abgleich mit dem aktuellen Ordnerinhalt, Prüfung aller Quellen/Ziele, `UNDO.sh` auf der NAS neben der Quarantäne. Sperren u. a. bei anderer TVDB-ID, doppelten Zielpfaden, großen nicht übernommenen Dateien.
- Opus-Review (Befunde: falsche Rückgängig-Anleitung, fehlende Vorabprüfung, Wiederholschutz, Sample-Regel, Namenskollisionen) vollständig umgesetzt; Apply + UNDO lokal nachgebildet (Hash-Vergleich vor/nach UNDO, Wayward + Wednesday).

### Changed (Werkzeug, nicht im Repo)
- tinyMediaManager 5.3.4 PRO (Lizenz 25.10.2026–25.10.2027, lokal in `~/.local/share/tinyMediaManager/data/tmm.lic`, nie ins Repo), Jellyfin-Preset (`TvShowSettingsDefaults.setDefaultSettingsForJellyfin`), TheTVDB als Scraper, Sprache de, `Season ${seasonNr2}`.

### Migriert (echt auf der NAS)
- Wayward.Unberechenbar → "Wayward – Unberechenbar" (8 Folgen, TVDB 433309, in Jellyfin geprüft).
- Wednesday (16 Folgen, 50 Untertitel, Ordnername unverändert).

### Hinweis
- Warum nicht `enricher.py --scan-existing`: überspringt NFOs mit vorhandenem Text (die falschen Altlast-NFOs enthalten den englischen Serien-Overview) und braucht Season-Ordner.
- Ohne PRO-Lizenz scrapt tinyMediaManager nur über TMDb (Nummerierung weicht bei alten Serien von TVDB ab).
- Noch offen: übrige ~50 Serien (Sopranos, Star Trek, Bonanza/Waltons lose …), Bestandsfilme (gleiches Problem).

## [2026-10-21] — #53 Filme auf der NAS aktiv

- Neue `inbox.py` und erweiterte `inbox_run.sh` (`--dest-movies`, `--tmdb-key`, `--jellyfin-movies-path-map`) auf der NAS eingetragen (Sicherungen `*.bak-20261021`). "12 Monkeys (1995)" probeweise einsortiert (12 GB, `movie.nfo`, `poster.jpg`, Jellyfin gezielt informiert).

## [2026-10-21] — #53 Schritt 2: Filme im Eingangsordner

### Added
- `inbox.py`: Filme werden mit `--dest-movies` + `--tmdb-key` einsortiert (`Titel (Jahr)/Titel (Jahr).ext`, `movie.nfo`, `poster.jpg`, Untertitel). Nur bei eindeutigem Treffer (Jahr im Dateinamen, genau ein TMDb-Treffer mit gleichem Titel und Jahr, Akzente egal); sonst bleibt alles liegen. Ordner mit mehreren Videos werden nicht angefasst. Ohne `--dest-movies` verhält sich alles wie bisher.
- Optional `--jellyfin-movies-path-map`: meldet den neuen Filmordner gezielt an Jellyfin.
- 11 neue Tests (33 gesamt, alle grün). Noch nicht auf der NAS getestet (Probelauf mit "12 Monkeys" steht aus).

## [2026-10-20] — NAS-Check: Laufwerk E: + Zeitzone (nur NAS-Einstellungen, kein Repo-Code)

### Fixed
- Laufwerk E: (Windows-PC) war seit 05.10. nicht eingebunden: Windows-Passwort geändert, `.cifs-windows-creds` noch alt (`STATUS_LOGON_FAILURE`). Bernd hat das neue Passwort selbst eingetragen; seit 20.10. 20:30 wieder eingebunden, 268 Filme von E: wieder abspielbar.
- Jellyfin-Container auf `TZ=Europe/Berlin` (vorher UTC), Nachtaufgaben auf Ortszeit 23:00/23:40/23:50 — Zeitumstellung verschiebt sie nicht mehr.

### Hinweis
- `/volume1/docker/jellyfin/docker-compose.yml` (veraltete Kopie ohne Komo-Mounts) an die Hauptdatei angeglichen; Sicherungen `*.bak-20261020`.
- `mount-cifs.sh` verwirft Mount-Fehler still — eine erneute Passwortänderung fällt nur über `dmesg` auf.

## [2026-10-11] — #53 Eingangsordner-Automatik + #29-Fehlerkorrekturen

### Added
- `inbox.py`: sortiert entpackte Serien-Downloads aus `/volume1/1/Eingang` automatisch ein (`Serien/<Name>/Season NN/<Name> - SxxEyy - <deutscher Titel>.ext` + Folgen-NFO, tvshow.nfo, Poster), TVDb-Zuordnung nur wenn eindeutig (Jahr aus Dateinamen, Remakes → unklar), Jellyfin-Refresh nur dieser Serie. Probelauf ist Standard, `--apply` für echten Lauf. Reste (Scene-NFO/Sample) nach `Eingang/_Reste`, nie gelöscht; Ordner mit Videos/Archiven/Teil-Downloads werden nicht angefasst.
- `tests/test_inbox.py` (22 Tests), `/volume1/dvb-library/inbox_run.sh` auf dem NAS (nicht im Repo, enthält Schlüssel).

### Fixed (enricher.py)
- TVDb-ID mit Vorsatz `series-NNN` (Folgen-Abfrage schlug still fehl, Serie doppelt in Jellyfin): neu `_tvdb_id()`.
- Episoden-NFO fiel bei leerem Folgentext auf den Serien-Overview zurück (alle Folgen gleicher Text): Rückfall entfernt.
- `best_series`: Vergleich ohne Satzzeichen, inkl. deutschem Namen/Aliasen; tvshow.nfo mit deutschem Titel/Text.

### Hinweis
- Live-Test Tulsa King (9 Folgen): ok. Opus-Review: kritische Befunde (Aufräumen, ID-Prüfung) behoben.
- Filme: zweiter Schritt, noch nicht umgesetzt. Bestandsserien im Archiv unverändert.

## [Unreleased]

### Added
- `scripts/touch_new_movie_folders.py` — Erweiterung des #52-Nebenbefunds (manuell/extern hinzugefügte Filme fehlten in "Kürzlich hinzugefügt", da `enricher.py`s `_touch_now()` nur die Xoro-Pipeline abdeckt). Zustandsbasiert: merkt sich bekannte Ordner in `/volume1/1/Filme`, touched nur neu hinzukommende. **Selbstgefundener + selbstbehobener Bug (2026-09-27):** Erste Fassung hatte beim Erstlauf (leere Zustandsdatei) fälschlich ALLE bestehenden Ordner als "neu" behandelt und deren mtime auf "jetzt" gesetzt statt nur den Zustand zu vermerken — 196 Filme kurzzeitig mit falschem Datum. Per Jellyfins noch unverändertem `DateCreated` (kein Scan lief zwischenzeitlich) vollständig zurückgesetzt, verifiziert per Stichprobe. Ursache: Erstlauf-Sonderfall (`first_run`) steuerte nur die Log-Ausgabe, nicht die tatsächliche Touch-Schleife — der Dry-Run-Test hatte dieselbe Lücke und zeigte "0 getoucht" obwohl real 228 geplant gewesen wären. Fix: `first_run` schließt jetzt `new_folders` selbst aus, nicht nur die Anzeige.
- `scripts/uriinfo_hide.py` — #32/WI-3.2 Vollrollout + Rollback. Benennt `URIInfo.bin` zu `URIInfo.bin.xoro-hidden` um (`--mode hide`) bzw. zurück (`--mode restore`), reines Dateisystem-Rename, kein Löschen, kein Jellyfin-API-Zugriff. Feste Dateiliste (einmaliger Scan, sofort geloggt), idempotent (Zielzustand wird nie überschrieben), Pro-Datei-Fehlerbehandlung mit JSONL-Log statt stillem Erfolg, `--dry-run` zum Prüfen ohne Änderung.
- Vollrollout ausgeführt (2026-09-27, Ruben-Freigabe): 168/168 Dateien in `/volume1/1/Filme` umbenannt, 0 Fehler. Zusammen mit dem WI-3.2-Pilot (18.09.) jetzt 170 Ordner ohne `URIInfo.bin`-Phantom-Item. Jellyfin übernimmt die Änderung beim nächsten automatischen Bibliotheks-Scan (nachts 01:00), kein manueller Refresh ausgelöst. Log: `/volume1/dvb-library/uriinfo_hide_rollout_20260927.jsonl` (NAS-only).
- `scripts/provider_coverage.py` — gemeinsames Messskript für #32/WI-3 (WI-3.1). Rein lesend: zählt Movie-Items ohne ProviderId über `GET /Items`, aufgeschlüsselt nach Quell-Prefix (`/bestehende-filme`, `/windows-e`, `/buffalo-archiv`), mit expliziten `OTHER`-Eimer, ProviderId-Histogramm, `TotalRecordCount`-Konsistenzprüfung, optionalem Paging und JSON-Ausgabe für Vorher-/Nachher-Vergleiche. Nur stdlib, API-Key ausschließlich über `--jellyfin-key`/`JELLYFIN_KEY` (nicht im Code). Default-Scope = Library "Filme" (ParentId), weil der WI-2-Spike genau diese Library gemessen hat.
- `BASELINE` im Skript auf 2026-09-18 neu verankert (401/1310, 30,6%) — die alte WI-2-Baseline (399/1298, 29.08.) war durch Bestandsdrift veraltet (Sonnet-Gegenprüfung bestätigt: `buffalo-archiv` byte-identisch, `bestehende-filme`-Delta exakt durch URIInfo.bin-Wachstum 160→170 erklärt, `windows-e`-Delta von -9 Items bleibt ungeklärt, siehe Issue-#32-Kommentar).

## [2026-09-23] — #51: Immich-Jellyfin-Sync-Automatisierung

### Added
- `scripts/immich_jellyfin_bridge.py --all`: synct jetzt alle Immich-Alben statt nur eines
- Chunking (40er-Batches) gegen HTTP 414 bei großen Alben
- Windows Task Scheduler "ImmichJellyfinSync": täglich 18:00, `StartWhenAvailable` (holt verpasste Läufe nach)
- PC-seitig (nicht im Repo): `run_sync.sh` Wrapper, API-Keys in `/root/immich/.immich_api_key`/`.jellyfin_api_key` (chmod 600)

### Fixed
- Komo-Jellyfin-Nutzer hatte `IsAdministrator: true` (Ruben hatte das selbst gesetzt, unnötig — `EnableCollectionManagement: true` reicht). Zurückgesetzt auf `false`, `EnabledFolders` um "Sammlungen" erweitert (Ruben-Entscheidung, Komo sieht jetzt auch 7 vorbestehende Collections).

## [2026-09-23] — #50: Immich→Jellyfin-Brücke (Pilot)

### Added
- `scripts/immich_jellyfin_bridge.py`: Liest ein Immich-Album per API (read-only), matched Assets über den gemeinsamen NAS-Pfad auf Jellyfin-Items, legt/aktualisiert eine gleichnamige Jellyfin-Collection. API-Keys nur per `--immich-key`/`--jellyfin-key` oder `IMMICH_API_KEY`/`JELLYFIN_API_KEY`, nicht im Code.
- Live gegen Testalbum "Test Immich-Jellyfin" (6 Gifs) verifiziert: korrekte Collection, idempotent bei erneutem Lauf.
- Bewusst kein Cron/Automatismus — manueller Aufruf pro Album, kein Vollrollout auf die ganze Bibliothek.

## [2026-09-23] — #49: Immich als Foto-/Homevideo-Verwaltung (PC-seitig)

### Added
- PC-seitig (nicht im Repo): Immich (nativer Docker-Stack in WSL2 Ubuntu, `~/immich/`) liest read-only von der Komo-Freigabe (`Fotos`/`Gifs`/`Filme` — alle drei ohne echte TMDb-Titel, siehe #49). Dedizierter DSM-Nur-Lese-Benutzer, da Guest-Account auf dieser Synology deaktiviert ist. Mount per `/etc/fstab` persistent.
- `.wslconfig` (Windows-Profil): WSL2 auf Mirrored-Netzwerkmodus umgestellt, damit Handy-Auto-Backup den Server im LAN erreicht (192.168.2.2:2283 statt interner WSL-NAT-IP).

### Nicht geändert
- `enricher.py`/Jellyfin unverändert — Immich übernimmt ausschließlich Inhalte ohne Filmtitel/TMDb-Treffer, keine Überschneidung mit der bestehenden Pipeline.

## [2026-09-18] — #43: Zweiter Jellyfin-Nutzer "Komo" mit eigenen Bibliotheken

### Added
- NAS-seitig (nicht im Repo): Shared Folder `/volume1/komo/{Filme,Fotos,Gifs}` bereits in Vorsession befüllt.
- `docker-compose.yml` (NAS, `/volume1/dvb-library/`): drei neue `:ro`-Mounts (`komo-filme`, `komo-fotos`, `komo-gifs`).
- Jellyfin: 3 Bibliotheken ("Komo Filme" movies, "Komo Fotos"/"Komo Gifs" homevideos) + Nutzer "Komo" (aus abgebrochener Vorsession bereits vorhanden, aber ohne Bibliothekszugriff) auf diese 3 Bibliotheken beschränkt (`EnableAllFolders: false`), Passwort neu gesetzt. Kein Fernzugriff eingerichtet (nur LAN, laut Ruben ausreichend).

## [2026-09-01] — #41: Manuelles Umbenennen von Aufnahmen am Ort (Stick ohne NAS-Anbindung)

### Added
- `--rename-in-place`: benennt Aufnahme-Ordner + Videodatei direkt am Aufnahmeort um (`<Titel> (<Jahr>)` bzw. `<Show> SxxEyy <Episodentitel>`), ohne zu verschieben. Für den zweiten Xoro bei Bozena, dessen eigener Dateibrowser nur Datei-/Ordnernamen zeigt, keine NFO-Metadaten.
- Benennt auch bei unmatched/Fallback-NFO um (anders als `move_recording()`) — roher EPG-Titel ist lesbarer als `record.ts`.
- Schließt sich mit `--dest-movies`/`--dest-series`/`--dest-unmatched` gegenseitig aus (Fehlermeldung bei Kombination).

## [2026-09-01] — Fix: Xoro-Aufnahmen mit kaputtem Zeitstempel sortieren falsch in "Kürzlich hinzugefügt"

### Fixed
- `_touch_now()`: setzt mtime der verschobenen Video-Dateien auf den Verschiebezeitpunkt. Xoro schreibt Aufnahmen ohne gültigen Zeitstempel (Unix-Epoche, 1.1.1970) — Jellyfins "Kürzlich hinzugefügt" sortiert danach, betroffene Filme/Serien landeten ganz unten statt oben.
- Nur in `move_recording()` (Filme- + Serien-Direktpfad aus Xoro-Aufnahme) angewendet — NICHT in der generischen Serien-Reorganisation, da dort Dateien auch aus Fremdquellen (Buffalo-Archiv, Windows-E) mit gültigen Original-Zeitstempeln stammen, die nicht überschrieben werden dürfen.

## [2026-07-01] — Wake-on-LAN für PC + Linkstation vor Abendnutzung

### Added
- `/volume1/dvb-library/wol-wake.sh` (NAS-only, nicht im Repo): Sendet WOL-Magic-Packets an Windows-PC (`2c:f0:5d:a2:c7:c0`) und Linkstation/TeraStation TS-XL/R5 (`4c:e6:76:92:53:4b`) per Python3-UDP-Broadcast (kein root nötig).
- DSM-Task 7 "WOL Wake PC+Linkstation": täglich 19:50 Uhr, einmalig (kein Repeat). 10 Min. Puffer vor typischer Sehzeit ab 20:00 Uhr.
- Bestehender Mount-Task (Task 6, alle 5 Min.) mountet danach automatisch, sobald die Geräte hochgefahren sind — keine Änderung an `mount-cifs.sh` nötig.

### Bekannte Voraussetzungen (noch zu prüfen von Ruben)
- Windows-PC: WOL muss in BIOS/UEFI + Gerätemanager-Netzwerkadapter aktiviert sein, Schnellstart deaktiviert.
- Linkstation/TeraStation: unklar ob altes Firmware (2015) im ausgeschalteten Zustand noch Standby-Strom für WOL hat — kein Admin-Zugriff zum Verifizieren.
- Kein echtes On-Demand-Wecken bei Jellyfin-Play-Klick (siehe Diskussion) — nur planmäßig um 19:50 Uhr.

## [2026-06-26] — Issue #34 + #29: Ordnernamen-Fix + leere NFO-Plots befüllen

### Fixed
- `_clean_show_name()`: Neue Funktion bereinigt Ordnernamen vor TVDb-Suche.
  Entfernt Unterstriche, Punkte-als-Trennzeichen (wenn kein Leerzeichen im Namen),
  Staffelangaben (`S04`, `Season N`, `Staffel N`) und Jahreszahlen am Ende.
  Vorher: `Goliath S04`, `Kir_Royale`, `Der.Milliardaersbunker` → 0 TVDb-Treffer.
  Nachher: `Goliath`, `Kir Royale`, `Der Milliardaersbunker` → Treffer gefunden.
- `_nfo_plot()`: Liest `<plot>` aus NFO, ignoriert führenden Release-Notes-Text.
- `scan_existing_series`: Überspringt NFO jetzt nur noch wenn `<plot>` vorhanden.
  NFOs aus Fremdquellen (vorhanden aber ohne Beschreibung) werden neu befüllt.
  Betrifft `tvshow.nfo` und Episoden-NFOs gleichermaßen.

## [2026-06-25] — Issue #32 WI-3: Metadaten für bestehende Filme (scan-existing-movies)

### Added
- `enricher.py --scan-existing-movies <dirs>`: Neuer Modus für Film-Ordner ohne RECInfo.txt (Scene-Releases, Downloads). Parst Ordnernamen, sucht per TMDb, schreibt `movie.nfo`.
- `parse_folder_title()`: Extrahiert Titel + Jahr aus Release-Style-Namen (`Title.Year.DL.1080p.x264-GROUP`) und Jellyfin-Format (`Title (Year)`). Filtert filecrypt.cc-Seiten.
- `TMDb.best_match_movie()`: TMDb-Suche mit optionalem Jahres-Filter (`primary_release_year`), automatischer Fallback ohne Jahr.
- Sammlungsordner (Harry Potter, Star.Wars, etc.) werden automatisch rekursiv aufgelöst (eine Ebene).

### Changed
- `TMDb.search_movie()` akzeptiert optionalen `year`-Parameter.

### Fixed
- 52 Filme in `/volume1/1/Filme` (bestehende-filme) mit TMDb-Metadaten versorgt; 8 Fallback-NFOs wo TMDb kein Ergebnis lieferte.
- Korrekte Behandlung von gemischten Sammlungsordnern (Sub-Folder-Filme + direktes Video).
- `_SKIP_DIRS` (`Sample`, `Subs`, `@eaDir`) werden übersprungen.

## [2026-06-24] — Issue #31: CIFS-Mounts aus Docker → Bind-Mounts (nofail)

### Fixed
- Jellyfin startet jetzt auch wenn PC (192.168.2.2) und/oder Linkstation (192.168.2.124) abgeschaltet sind.
  Vorher: Docker-managed CIFS-Volumes blockierten den Container-Start bei nicht erreichbaren Hosts.
  Jetzt: Bind-Mounts auf `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}` (immer vorhanden, leer wenn CIFS nicht gemountet).

### Added
- `/volume1/dvb-library/mount-cifs.sh`: Montiert CIFS-Shares mit nofail-Logik (ping-Prüfung, graceful fallback). Startet Jellyfin nach erfolgreichem Mount neu. Log: `/volume1/dvb-library/mount-cifs.log`.
- `/volume1/dvb-library/.cifs-windows-creds` (chmod 600): Credentials-Datei für Windows-PC-Share.
- Mount-Verzeichnisse: `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}`.

### Changed
- `docker-compose.yml` (beide Pfade: `/volume1/dvb-library/` und Container Manager): CIFS-Volume-Section entfernt, zwei neue Bind-Mounts hinzugefügt.
- Alte Docker-Volumes `dvb-library_buffalo-archiv`, `dvb-library_windows-e` gelöscht.

### Pending (manueller Schritt)
- **Ruben**: DSM Task Scheduler → Ausgelöste Aufgabe bei Boot anlegen (User: root, Befehl: `/volume1/dvb-library/mount-cifs.sh`)

## [2026-06-20] — Metadaten-Bereinigung + normalize-episodes

### Added
- `enricher.py --normalize-episodes`: Erstellt Episode-NFOs für Serien mit kryptischen Dateinamen (kein S01E01-Muster). Liest TVDb-ID aus tvshow.nfo, mappt sortierte Videos sequenziell auf TVDb-Episodenliste.

### Changed
- 38 `tvshow.nfo`-Dateien: `<lockdata>true</lockdata>` entfernt (englische/spanische Beschreibungen) → TheTVDB kann beim nächsten Jellyfin-Scan deutsche Metadaten holen
- 6 `tvshow.nfo`-Dateien mit deutschen/franz. Beschreibungen bleiben unverändert (Breaking Bad, Dalgliesh 2021, Geheimnisse des Kaiserreichs, Goulag, Down Cemetery Road, Jim Bergerac)

## [2026-06-18] — WI-1/WI-3/WI-4/WI-5: Serien-Vollständig-Fix + Hardening

### Added (WI-3)
- `migrate_series.py`: einmalige Migration Flat-Folder → `Show/Season NN/` (11 Folder migriert)

### Changed (WI-5)
- Serien-Library: `EnableRealtimeMonitor=false` — enricher-seitiger `/Library/Refresh` ist einzige Refresh-Quelle; löst inotify-Limit-Erschöpfung (8192 watches)
- Jellyfin Library-Scan nach Migration getriggert

### Fixed (WI-4)
- #22: HTTP-500-Absturz war Client-seitiger NPE (stale Item-IDs nach Migration) — kein Server-Fix nötig, löst sich nach Lib-Scan + App-Neustart

---

## [2026-06-18] — WI-1: Episoden-Overview + Jellyfin-Serien-Struktur

### Added
- `TVDb.episode_overview()`: holt deutsche Episode-Overview via TVDb v4, Fallback auf EN
- `build_episode_nfo`: Fallback-Kette `episode_overview → epg_title → series.overview`

### Changed
- `move_recording` Serien-Branch: neue Zielstruktur `Show/Season NN/{basename}.*`
- NFO-Dateiname im Ziel: `{basename}.nfo` statt `movie.nfo` (Jellyfin-Sidecar-Konvention)

### Fixed
- #21: Jellyfin liest Episode-NFOs jetzt korrekt (falscher Dateiname war Ursache)

---

### Geplant
- Phase I: PoC — RECInfo.txt parsen + TMDb-Lookup + Jellyfin-Integration
- Phase II: Vollständige Python-Pipeline (RECInfo-Parser, TMDb-Client, NFO-Generator)
- Phase III: Automatisierung via Windows Task Scheduler
- Phase IV (optional): Serien-Support, Web-Dashboard
