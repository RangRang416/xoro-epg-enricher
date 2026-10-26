# Projekt: xoro-epg-enricher — Aktiver Stand

**Stand: 2026-10-26 | gepflegt vom Orchestrator (kein Planner-Spawn, Direktentscheidung) — Abschnitt Eingangsordner und Phasenstand #29/#53 neu; übrige Teile Stand 2026-09-27**

Diese Datei ist Zustandsbeschreibung, keine Historie. Für Entscheidungsverläufe: `CHANGELOG.md`, GitHub-Issues, `handover.md`. Für den WI-3-Plan im Detail: `wi3-plan-metadaten-luecke.md`.

---

## Architektur (as-built)

```
Xoro HRT 8772 → USB-Stick → Synology USB Copy → /volume1/aufnahmen/inbox/
       ↓ (DSM Task, alle 10 Min)
  enricher.py: RECInfo.txt → TMDb/TVDb API → NFO + Cover, verschiebt nach
  /volume1/1/Filme (Movies) bzw. .../Serien (Show/Season NN/SxxEyy.*)
       ↓
  Jellyfin (Docker auf Synology, 24/7) — Bibliotheken: Filme, Serien,
  Komo Filme/Fotos/Gifs (zweiter Nutzer, read-only Zusatz-Freigabe)
       ↓
  Wiedergabe: Chromecast with Google TV (Direct Play) + Jellyfin Android-App
```

**Eingangsordner (#53, live seit 2026-10-11, Filme 2026-10-21):**
```
JDownloader (lädt + entpackt selbst) → /volume1/1/Eingang/
       ↓ (DSM-Aufgabe `inbox_run.sh`, root, zur vollen Stunde — beobachtet 17:00 und 18:00, Zeitplan in DSM nicht nachgesehen; Sperrdatei /tmp/inbox_sort.lock)
  inbox.py: Name lesen (SxxExx → Serie, Titel+Jahr → Film; Release-Gruppe vor dem Namen wird ignoriert)
  → TheTVDB (Serien) / TMDb (Filme) → Serie/Season NN/Serie - SxxEyy - Titel.ext bzw. Titel (Jahr)/
  + NFO (deutsch), Poster, Trailer (Serien, TVDb) → Reste nach Eingang/_Reste → Jellyfin: gezielt diese Serie auffrischen
```
Unsicheres bleibt im Eingang liegen (kein „Nicht erkannt"-Ordner, siehe Phasenstand). `unpack.py` (RAR-Notlösung, `--unpack`, AUS) packt nur Pakete, die ≥ 24 h komplett liegen, nie vor JDownloader; Archive wandern nach `_Reste/Archive-<Tag>/`, nie gelöscht. Code liegt auf der NAS unter `/volume1/dvb-library/` (inbox.py, enricher.py, unpack.py), Sicherung der Vorversion `*.bak-20261026`.

Windows-PC ist als Wiedergabe-/Verarbeitungsknoten eliminiert (läuft nur noch als Xoro-Aufnahmequelle über CIFS-Mount `windows-e`). Zusätzliche Quellen per CIFS-Bind-Mount: `buffalo-archiv` (alte Linkstation, Guest/SMBv1, unzuverlässig — siehe #52), `windows-e`.

Immich (separat, auf Rubens Windows-PC/WSL2) verwaltet Homevideos/Fotos ohne Filmtitel; per Brücke (`immich_jellyfin_bridge.py`) werden Alben als Jellyfin-Collections gespiegelt (täglich 18 Uhr).

## Phasenstand

| Bereich | Status |
|---|---|
| Kern-Pipeline (Aufnahme → NFO → Jellyfin) | Läuft produktiv |
| Wiedergabe ohne Transkodierung (ex-Phase VI) | Chromecast Direct Play funktioniert laut Feldbeobachtung 2026-05-30; kein VI-1/VI-3-Abschluss-Vermerk in der Historie — bei erneuten Transcoding-Problemen zuerst prüfen, ob das noch trägt, statt anzunehmen es sei formal abgeschlossen |
| Serien-Metadaten (Episode-TypeOptions, deutsche Beschreibungen) | **Geklärt (2026-09-27, Issue-Kommentare geprüft):** #29 hat einen fertigen Plan (WI-0-Spike + WI-1-Fix, Root Cause: leerer `<plot>`-Fallback auf Serien-Overview + vermutlich falsches TVDb-v4-ID-Format), aber **nie umgesetzt** — kein Kommentar nach der Planung. Hängt vermutlich weiterhin an WI-2 (Episode-TypeOptions, Stand 2026-06-17 unverändert: „Scan-Ansatz noch nicht getestet"). Nächster Schritt bei Wiederaufnahme: WI-2 abschließen, dann #29-WI-0/WI-1 |
| #53 Eingangsordner-Automatik | Serien + Filme live; Echttest „The Big Bang Theory" 2026-10-26 bestanden (4 Folgen automatisch einsortiert, Jellyfin zeigt deutsche Titel). **Offen:** (1) Unsicheres still im Eingang statt „Nicht erkannt"-Liste, (2) keine Zweitquelle (TVDb↔TMDb), (3) Film-Trailer, (4) Prüfung ob JDownloader „Archive nach Entpacken löschen" an hat |
| #29 Bestandsserien (tinyMediaManager PRO/TVDB, `scripts/bestand_tmm.py`) | 3 von 46 Plänen angewendet (Wayward, Wednesday, Slow Horses); Rest erst nach Ende des Big-Bang-Downloads (NAS-Last). Von 11 „gesperrten" sind Columbo/Monk/Straßen von SF/Raumschiff Enterprise nur RAR-Reste neben fertigen Videos (freigebbar); echte Lücken: Bonanza, GoT, The Wire, Simpsons, Waltons, Parlament; Dalgliesh (andere TVDB-ID), Miss Marple (nicht erkannt). Nach jedem apply: Jellyfin braucht je nach Last 2–30 Min, Folgenzahl erst dann prüfen |
| #22 (HTTP 500 bei Playback-Ende) | **Geklärt (2026-09-27):** Kein offener Arbeitsposten mehr. Root Cause seit 28.08. bekannt (Android-TV-App sendet gelegentlich negative `PositionTicks`, Server fängt das nicht ab) — Ruben-Entscheidung 28.08.: bewusst kein Server-Patch, nur als Upstream-Bug dokumentiert. Wartet auf App-Update, kein Handlungsbedarf unsererseits. Issue könnte mit Verweis auf diesen Stand geschlossen werden (Ruben-Freigabe nötig) |
| #32 Metadaten-Lücke (Filme ohne ProviderId) | WI-3.1 (Spike+Messskript) + WI-3.2 (URIInfo.bin-Ausschluss, Vollrollout 2026-09-27) fertig. **WI-3.3 (Branch-B-Write-Pfad) ist offen und der größte verbleibende Hebel** — siehe `wi3-plan-metadaten-luecke.md` |
| #52 Scan bricht bei Buffalo-Host-down ab | Nur einmalig workaround-behoben, strukturelle Lösung (eigene Library für Buffalo-Pfade) offen |
| Immich-Jellyfin-Brücke (#49-#51) | Pilot + Automatisierung fertig |
| Zweiter Jellyfin-Nutzer „Komo" (#43) | Fertig, GitHub-Issue noch offen (Ruben-Freigabe zum Schließen aussteht) |

## Offene Architektur-Fragen (Ruben-Entscheidung)

- #37 ("F:-Laufwerk einbinden") vs. #45 ("Desktop-PC raus") — sich widersprechende Anträge, ungeklärt seit 2026-09-23
- Nachtruhe-Wunsch (Router nachts aus) vs. nächtliche NAS-Tasks (Scan 01:00, Kapitelbilder 02:00, Trickplay 03:00) — noch nicht untersucht, ob ein abgeschalteter Router die NAS mit trifft

## Bekannte strukturelle Einschränkungen

- NAS: 1 GB RAM, kein Hardware-Transcoding, `admin`-SSH ohne passwortloses `sudo` (root-Aktionen brauchen Rubens eigenes Terminal)
- Buffalo-Linkstation (2015, SMBv1/Guest) ist unzuverlässig und blockiert bei Ausfall die komplette Jellyfin-„Filme"-Bibliothek (#52)

---

*Frühere Planner/Controller-Diskussionsverläufe (Phase VI Transcoding-Analyse, Serien-Issues #21-#23 Ursachenanalyse) sind in der Git-Historie dieser Datei erhalten, hier aber nicht mehr abgebildet — nur das Ergebnis oben.*
