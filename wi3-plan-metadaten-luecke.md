# WI-3 — Plan: Metadaten-Lücke schließen (Issue #32)

**Stand: 2026-08-29 | Planner: Opus | Status: wartet auf Rubens Freigabe**

Basis: WI-2-Inventur-Spike (Issue-#32-Kommentare, 29.08.). Branch B (Jellyfin-API statt NFO-Writes) und <20%-Ziel sind bereits entschieden, nicht Teil dieses Plans.

---

## Die entscheidende Korrektur: (1) + Branch-B-Write reichen bereits

| Schritt | Items ohne ProviderId | Quote |
|---|---|---|
| Ist-Zustand | 399/1298 | 30,7 % |
| nach (1) URIInfo-Ausschluss | 239/1138 | 21,0 % |
| + Branch-B-Write, Matching unverändert (45% von 124 ≈ 56 Treffer) | 183/1138 | **16,1 % ✅** |
| + strenges Score-Gate (1/3 der Treffer verworfen) | 202/1138 | 17,8 % ✅ |
| + Titel-Normalisierung (65% von 124 ≈ 81) | 158/1138 | 13,9 % |
| + Serien zusätzlich rausziehen | 154/1053 | 14,6 % |

**Folge:** (3) Serien-Extraktion und (4) VIDEO_EXTS-Erweiterung sind fürs <20%-Ziel nicht nötig, zurückgestellt. Titel-Normalisierung (2) ist Reserve, nicht kritischer Pfad — kritischer Pfad ist (1) + der schlichte Branch-B-Write mit bestehender Matching-Logik.

**Ehrlichkeitshinweis:** Serien aus der Movie-Library zu ziehen verbessert die Kennzahl, schließt aber keine Lücke — sie wandert in die TV-Library. Kennzahl-Verschiebung, kein Fortschritt. Deshalb zurückgestellt, nicht "gespart".

---

## Architektur-Entscheidungen

| Entscheidung | why |
|---|---|
| Kandidaten-Generator statt Titel-Mutation bei Normalisierung | „ae/oe/ue→äöü" ist destruktiv falsch für reale Titel (`Michael`→`Michäl`, `Manuel`→`Manül`, `Duell`→`Düll`, `Aeon Flux`→`Äon Flux`, `Poseidon`→`Posidon`). Die n=20-Stichprobe kann diese Fälle nicht enthalten haben, sonst wäre die Quote nicht gestiegen. In-place-Ersetzung würde bestehende Treffer kaputtmachen. |
| Minimum-Score-Gate vor jedem Write | `best_match_movie` liefert das beste Ergebnis ohne Untergrenze. Ab Branch B schreiben wir direkt in die Jellyfin-DB — ein Fehlgriff verbessert die Kennzahl und verschlechtert die Bibliothek gleichzeitig. Ohne Gate ist das <20%-Ziel unabsichtlich manipulierbar. |
| Snapshot vor erstem Write-Lauf, LockData/LockedFields beim Write | `jellyfin_refresh` wird vom Enricher an 4 Stellen selbst aufgerufen und kann gesetzte ProviderIds überschreiben. Ohne Snapshot kein Rollback-Pfad für DB-Writes. |
| Gemeinsames Messskript (`scripts/provider_coverage.py`) | 3 Issues brauchen dieselbe Zahl — ohne gemeinsames Skript sind Vorher/Nachher-Vergleiche wertlos. |
| Kein selbst gestarteter Full-Library-Scan | NAS blockiert dabei 1h+ (1GB RAM). Verifikation nur über gezielte `POST /Items/{id}/Refresh` auf einzelne Ordner. |
| Endpunktfrage `POST /Items/{id}` vs. `POST /Items/RemoteSearch/Apply/{itemId}` — offen für WI-3.1 | Branch B selbst steht nicht zur Debatte, nur die Endpunktwahl innerhalb Branch B wird lesend geklärt; `POST /Items/{id}` bleibt Fallback. |

## Prior Art

- **Emby.Naming `VideoFileExtensions`** (Jellyfins eigener Parser) — übernommen als Referenz. Erklärt vermutlich sowohl `.bin` als Video-Trigger als auch ob `.flv/.vob/.iso` schon indiziert werden. Fest einkompiliert, nicht per LibraryOptions konfigurierbar (deckt sich mit Spike-Befund: kein Ignore-Feld in `GET /Library/VirtualFolders`).
- **`.ignore`-Marker** — Kandidat mit Vorbehalt: überspringt den ganzen Ordner, damit fiele auch der echte Film weg. Nur brauchbar, falls WI-3.1 Dateiebene bestätigt.
- **guessit/parse-torrent-title** — als Laufzeit-Dependency verworfen (enricher.py bewusst stdlib-only auf Synology-NAS), Tag-Liste als Vorlage für `_RELEASE_TAG_RE`-Erweiterung übernommen (fehlen: `UNCUT`, `Final Cut`, `Theatrical`, `Kinofassung`, `DC`).
- **tinyMediaManager/Kodi-NFO-Scraper** — verworfen, schreiben NFOs an die Quelle (widerspricht Branch B).

## Datenpipeline

- **Eingabe:** `GET /Items?Recursive=true&IncludeItemTypes=Movie&Fields=ProviderIds,Path` gefiltert auf leere ProviderIds — Arbeitsliste ist die Jellyfin-DB, nicht das Dateisystem.
- **Verarbeitung:** `Path`→Ordnername→`parse_folder_title`→Varianten-Liste (ab WI-3.4)→`TMDbClient.best_match_movie`→Score-Gate.
- **Speichern:** (1) Jellyfin-DB: ProviderId je Item mit LockData/LockedFields. (2) Lokales Append-only-JSONL je Lauf: `ts, item_id, path, parsed_title, parsed_year, query_variant, tmdb_id, tmdb_title, score, action, http_status`.
- **Konsumenten:** Enricher selbst (Idempotenz), Messskript (Vorher/Nachher), Ruben (Stichprobenprüfung sortiert nach niedrigstem Score). `path` zusätzlich zu `item_id` geführt, weil Jellyfin-GUIDs pfadabgeleitet sind und sich bei Library-Rebuild/Mount-Wechsel ändern.

---

## Issues

### WI-3.1 — Spike: URIInfo.bin-Ausschlussmechanismus + Messskript
**Was:** Rein lesende Klärung: (a) ist `/bestehende-filme` beschreibbar (Testdatei anlegen+löschen)? (b) enthält Emby.Naming `VideoFileExtensions` `.bin`, was zu `.flv/.vob/.iso/.wmv/.mpg/.m2ts`? (c) indiziert Jellyfin die 5 `.flv`-only-Quellordner schon? (d) existiert `POST /Items/RemoteSearch/Apply/{itemId}`, welches Payload braucht `POST /Items/{id}`? Plus Bau von `scripts/provider_coverage.py`.
**Wie:** Read-only API-Calls + ein Schreibtest im Dateisystem.
**Ergebnis:** Skript reproduziert 399/1298=30,7% exakt (sonst Stopp). Je eine belegte Antwort zu (a)-(d), bei (c) Anzahl indizierter Items.
**Modell:** Opus (Umsetzung) / Sonnet (Gegenprüfung der 4 Zahlen).
why_modell: Mechanismus unbekannt, LibraryOptions liefert nicht die Antwort → Opus-Pflicht "nicht reproduzierbare Fehler". Gegenprüfung bewusst billig, muss nur ≠Opus sein.
**Reihenfolge: 1** — blockiert alles; (a) entscheidet ob Ausschlussweg existiert, (c) entscheidet Priorität von WI-3.6, Messskript ist Voraussetzung für jeden Nachweis.

**⚠️ Entscheidungs-Gate nach WI-3.1 (Ruben, Schicht 1):** Falls (a) "read-only" UND kein Ignore-Mechanismus auf Dateiebene existiert → bleibt nur, Phantom-Items aus dem Nenner der Kennzahl zu nehmen (Zielverschiebung statt Umsetzung). Das entscheidet Ruben, nicht der Implementer — sonst wählt ein Implementer unter Zieldruck still die Nenner-Variante.

### WI-3.2 — URIInfo.bin-Ausschluss: Pilot auf 2 Ordnern
**Was:** Mechanismus aus WI-3.1 auf 2 Ordnern anwenden, Phantom-Items per `DELETE /Items/{id}` entfernen, gezielt neu einlesen, prüfen dass sie nicht wiederkommen und der echte Film unbeschädigt bleibt.
**Wie:** Mechanismus anwenden → DELETE Phantome → `POST /Items/{id}/Refresh` nur auf Elternordner → `GET /Items` Pfadfilter. Kein Full-Library-Scan.
**Ergebnis:** 2 Phantome weg, 2 echte Filme unverändert mit je 2 ProviderIds. Hochrechnung auf alle 160 im Kommentar, Vollrollout noch nicht ausgeführt.
**Modell:** Sonnet (Umsetzung) / Opus (Review).
why_modell: Umsetzung mechanisch sobald Weg bekannt. Review braucht Opus — hier wird gelöscht, ein zu breiter Filter nimmt echte Filme mit (vgl. `feedback_mechanical_prompt_shifts_need_opus_review`).
**Reihenfolge: 2** — größter Einzelhebel, einziger für Ruben sichtbarer Effekt, Vollrollout braucht abgestimmtes Zeitfenster (früh anstoßen). Kein technischer Blocker für WI-3.3.
**Blockiert durch:** WI-3.1

### WI-3.3 — Branch-B-Write-Pfad: Score-Gate, Snapshot, Dry-Run-Report
**Was:** `_process_existing_movie` umbauen: `nfo.write_text` → Jellyfin-API-Write. Matching-Logik unverändert. Neu: Score-Gate, Snapshot, JSONL-Protokoll, Dry-Run-Report. Braucht POST-Helfer mit JSON-Body (bestehendes `http_post` sendet `data=b''` ohne Content-Type).
**Wie:** Dry-Run über alle 124 Kandidaten → JSONL-Report → Ruben prüft 20 Zeilen → erst dann Schreiblauf → Messskript vorher/nachher → 24h später erneut messen.
**Ergebnis:** Quote ≤20,0% (erwartet 16-18%). Präzision in 20er-Stichprobe ≥18/20 korrekt. Snapshot-JSONL vollständig. Zweiter Lauf: 0 Writes. Nach 24h keine verlorene ProviderId. **<20% erreicht aber Präzisionshürde gerissen = nicht bestanden.**
**Modell:** Sonnet (Umsetzung) / Opus (Review).
why_modell: Umbau ist normale Arbeit auf bekannter Logik. Review braucht Opus: erste schreibende DB-Zugriffe des Projekts + die 4 `jellyfin_refresh`-Aufrufe sind ein Konsumenten-Effekt, den isolierte Tests nicht finden (`feedback_isolated_tests_miss_cross_consumer_effects`).
**Reihenfolge: 3** — erreicht laut Rechnung das Ziel allein (16,1%), steht aber hinter WI-3.2 wegen dessen Zeitfenster-Abhängigkeit und weil die Nennerbereinigung die Messung erst aussagekräftig macht.
**Blockiert durch:** WI-3.1 (Endpunktfrage). Nicht durch WI-3.2.

### WI-3.4 — Titel-Normalisierung als Kandidaten-Generator (Reserve)
**Was:** Funktion erzeugt geordnete TMDb-Suchvarianten aus geparstem Titel: Original; Release-Zusätze abgeschnitten; Umlaut-Rückschrift als zusätzliche Variante; Titel aus Ordnername statt Szene-Dateiname. Geparster Titel wird nie überschrieben.
**Wie:** Unit-Tests auf Regressionsset (offline): `Michael Collins`, `Manuel`, `Duell`, `Aeon Flux`, `Poseidon`, `Israel`, `Samuel` — Umlaut-Variante darf Original nicht verdrängen. Dann Dry-Run über verbliebene Kandidaten, JSONL-Diff gegen vorherigen Lauf.
**Ergebnis:** Regressionsset 7/7 grün. Trefferquote steigt ggü. WI-3.3. Diff: 0 geänderte tmdb_id bei bereits zugeordneten Items.
**Modell:** Opus (Umsetzung) / Sonnet (Review).
why_modell: CLAUDE.md §3 listet Regex explizit unter Opus-Pflicht — die Umlaut-Regel sieht in der Stichprobe gut aus und zerstört in der Breite Titel.
**Reihenfolge: 4** — bewusst nach dem Zielerreichungs-Issue (Sicherheitsmarge, kein kritischer Pfad). Rückt auf Position 3, falls WI-3.3 unerwartet über 20% ausfällt.
**Blockiert durch:** WI-3.3 (braucht dessen JSONL als Vergleichsbasis)

### WI-3.5 — Serien aus Movie-Library ziehen — ZURÜCKGESTELLT
Optionen: physisch verschieben (scheitert auf read-only Quellen) oder Library-Ordnerzuordnung ändern. Modell bei Aktivierung: Sonnet/Opus-Review (Fehler dort erzwingt Full-Rescan).
why: Fürs Ziel nicht nötig, verschiebt Lücke nur in TV-Library statt sie zu schließen — macht Kennzahl schöner statt Zustand besser. Getrennt aufnehmen mit eigener Begründung.
**Blockiert durch:** Ruben-Entscheidung ob überhaupt gewollt.

### WI-3.6 — `VIDEO_EXTS` erweitern — ZURÜCKGESTELLT, Richtung abhängig von WI-3.1(c)
Erweiterung um `.vob/.flv/.wmv/.mpg/.m2ts/.iso/.img` (47 VIDEO_TS-Ordner, 53 ISO/IMG, 153 Einzeldateien betroffen). Wenn Jellyfin sie schon indiziert: kennzahl-positiv, rückt auf. Wenn nicht: bringt für die Kennzahl nichts und verschlechtert sie später (~250 unzugeordnete Items in den Nenner).
why_modell: `.iso`/VIDEO_TS sind Container-Strukturen, `count_video_files` zählt nur Dateien direkt im Ordner — ändert die Sammelordner-Erkennung mit, kein Ein-Zeiler trotz Anschein.
**Blockiert durch:** WI-3.1

### Nicht eingeplant: `_SKIP_DIRS`-Filterlücke
Bestätigt (Sample/-Unterordner zählt fälschlich als Video-Unterordner), aber nur 1 von 40 betroffenen Ordnern hat ein metadatenloses Item. Backlog-Eintrag, nicht Teil von WI-3.
why: Fund ehrlich benennen, Fix klein halten — jetzt mitnehmen würde den Diff im kritischen Pfad ohne Wirkung aufs Ziel erweitern.

## Haiku-Eignung (geprüft)
Geeignet: Wiederholte Ausführung von `provider_coverage.py` + Zahlen ins Issue eintragen, NACH Validierung in WI-3.1. Nicht geeignet: alles andere, auch WI-3.6 (ändert Sammelordner-Erkennung) und WI-3.2 nicht (dort wird gelöscht).

## Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Falschtreffer erhöhen Kennzahl, verschlechtern Bibliothek | Score-Gate, Pflicht-Dry-Run, Ruben prüft 20 Zeilen vor erstem Write. ~6 Punkte Luft: selbst 1/3 verworfene Treffer landen bei 17,8%. |
| `jellyfin_refresh` (4 Stellen) überschreibt ProviderIds | LockData/LockedFields beim Write, 24h-Nachmessung ist Pflicht-AK in WI-3.3. |
| `/bestehende-filme` read-only | WI-3.1(a) klärt das zuerst; falls ja → Ruben-Gate greift, WI-3.3 muss Ziel ohne Puffer allein tragen (tut es rechnerisch). |
| DB-Writes nicht trivial rückholbar | Snapshot-JSONL vor erstem Schreiblauf, Rückspielskript im selben Issue. |
| n=20 dünne Basis für 45/65%-Quoten | Plan hängt nicht kritisch daran — selbst bei 25% (31 Treffer) landen wir bei 18,3%. Erst unter ~10% wird WI-3.4 Pflicht. |
| WI-3.2-Vollrollout braucht Wartungsfenster, evtl. nicht diese Session | WI-3.3 ausdrücklich nicht durch WI-3.2 blockiert; bleibt Fenster aus, läuft WI-3.3 auf unbereinigtem Nenner (1298) vor, Fortschritt bleibt sichtbar. |
| Zwei parallele Sessions am Repo möglich | Vor Umsetzungsbeginn `git pull` + Issue-Stand prüfen. |

---

**Gelesene Dateien:** `enricher.py` (Zeilen 25-46, 150-290, 463-527, 990-1130 + gezielte Treffer). Tragende Fundstellen: `best_match_movie` ohne Score-Untergrenze (Z.181-186), `http_post` ohne Body/Content-Type (Z.37-45), `_SKIP_DIRS` nicht angewandt in Sammelordner-Erkennung (Z.1081-1085 vs. Z.277), `VIDEO_EXTS` (Z.747), 4× `jellyfin_refresh` (Z.1239, 1256, 1269, 1332).
