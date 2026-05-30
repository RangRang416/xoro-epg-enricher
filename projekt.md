# Projekt: xoro-epg-enricher — Aktiver Plan

**Stand: 2026-04-25 | Planner: Opus (2× revidiert) | Status: Phase I bereit**

---

## Finale Architektur

```
Xoro HRT 8772 → USB-Stick
       ↓ (Stick in Synology USB-Port)
  Synology USB Copy (DSM, auto-kopiert auf /volume1/aufnahmen/inbox/)
       ↓
  Python-Skript (Synology Task Scheduler, alle 10 Min)
       ↓ RECInfo.txt → TMDb API → .nfo + poster.jpg
  Jellyfin Docker (auf Synology, 24/7)
       ↓
  Jellyfin Android-App
```

---

## Architektur-Entscheidungen (final)

| Entscheidung | Begründung |
|---|---|
| Python 3.11 + venv in Shared Folder | Package Center liefert unterschiedliche Versionen je Synology-Modell |
| Synology Task Scheduler (alle 10 Min) | SMB/NFS keine zuverlässigen Inotify-Events; Polling robust |
| USB-Copy Hook optional | Nicht in allen DSM-Versionen verfügbar |
| Ordner NICHT umbenennen | Xoro-Indexdateien (.idx/.meta) haben Pfad-Referenzen |
| Fallback-NFO immer | Lieber leer als fehlend in Jellyfin |
| TMDb statt XMLTV | Ruben wählt Filme via KLACK → Mainstream-Titel → TMDb trifft zuverlässig |
| Jellyfin docker-compose | Versionierbar, portabel, Multi-Arch (ARM64 + x86) |
| Read-Only Volume-Mount | Jellyfin schreibt nicht in Aufnahmen-Verzeichnis |
| Windows-PC komplett eliminiert | NAS übernimmt Enrichment + Media-Server |

---

## Issue-Übersicht

| # | Titel | Klasse | Impl | Reviewer | Status |
|---|-------|--------|------|----------|--------|
| #0 | Repo-Setup | A+ | Haiku | — | ✅ DONE |
| #1 | PoC — Synology End-to-End | B | Sonnet | — | OFFEN |
| #2 | Grundgerüst (POSIX, venv, Multi-Arch) | C | Sonnet | Haiku | OFFEN |
| #3 | RECInfo.txt-Parser | B | Sonnet | Opus | OFFEN |
| #4 | TMDb-Client mit Scoring | C | Sonnet | Opus | OFFEN |
| #5 | Cover-Downloader | A+ | Haiku | Sonnet | OFFEN |
| #6 | NFO-Generator | B | Sonnet | Opus | OFFEN |
| #7 | Orchestrator + Idempotenz | B | Sonnet | Opus | OFFEN |
| #8 | Synology Setup-Doku | A+ | Sonnet | Opus | OFFEN |
| #9 | Jellyfin Docker (docker-compose) | B | Sonnet | Opus | OFFEN |
| #10 | E2E-Test 10+ Aufnahmen | B | Sonnet | — | OFFEN |
| #11 | Fehlerbehandlung & Härtung | B | Sonnet | Opus | OFFEN |
| #12 | (Optional) Serien-Support | C | Sonnet | Opus | OPTIONAL |
| #13 | (Optional) Web-Dashboard | C | Sonnet | Opus | OPTIONAL |

**Critic-Pflicht:** #1, #2, #4, #6, #9

---

## Phasen

### Phase I — PoC (Stopp-Bedingung)
Issue #1: Alle 6 Hardware-Punkte ✓ → weiter. ✗ → Plan-Revision.

### Phase II — Kernmodule
Issues #2–#6 (Grundgerüst, Parser, TMDb, Cover, NFO)

### Phase III — Automatisierung
Issues #7–#9 (Orchestrator, Synology-Setup, Jellyfin Docker)

### Phase IV — Validation
Issues #10–#11 (E2E-Test, Härtung)

### Phase V — Optional
Issues #12–#13

---

## Xoro-Aufnahme-Format (ermittelt 2026-04-25)

```
N:\PVR\REC\00029\   (SATA-Platte, direkt an PC)
  record.ts          (1-2 GB)
  RECInfo.txt        (Sender, Titel, Untertitel, Sprache — KEINE Langbeschreibung)
  record.ts.meta / .idx / .pmt
  URIInfo.bin
```
USB-Stick-Format vermutlich identisch — PoC #1 verifiziert das.

---

## Risiken

- USB-Stick-Format weicht von SATA ab → PoC #1 verifiziert
- rapidfuzz kein ARM-Wheel → Entware-Fallback in #2
- DSM USB-Copy Hook nicht verfügbar → Polling als Default
- Jellyfin .ts-Playback stottert → Hardware-Transcoding in #9

---

# Nachtrag: Phase VI — Wiedergabe ohne Server-Transkodierung

**Projektmanager** (Claude-Web) · 2026-05-30

## Anlass
Der Enrichment-Strang ist umgesetzt (Teilerfolg). Im Betrieb bestätigt sich das in der Risiko-Liste notierte Problem „Jellyfin .ts-Playback stottert": Jellyfin transkodierte, und das NAS war dafür zu schwach (1 GB RAM zu wenig). Der dort vorgesehene Ausweg „Hardware-Transcoding in #9" trägt nicht — die Hardware gibt das nicht her.

## Kernentscheidung
Jellyfin bleibt. Das Problem ist nicht Jellyfin, sondern das Transkodieren auf zu schwacher Hardware. Wiedergabegerät ist der vorhandene Chromecast with Google TV. Direct Play ist nachgewiesen möglich — VLC auf dem Chromecast spielt die `.ts` direkt ab. Kodi wurde geprüft und verworfen: keine API-Konfiguration wie bei Jellyfin, kein Bibliotheks-Import, Client statt Server, manuelle Einrichtung am Gerät.

## Ziele (für Planner / Architektur)
1. Wiedergabe ohne Transkodierungslast auf dem NAS — anstelle von Hardware-Transcoding, das hier nicht möglich ist.
2. Auswahl-Komfort erhalten: der manuelle Umweg (in Jellyfin aussuchen, in VLC wiederfinden) soll entfallen oder schrumpfen.
3. Enricher, Synology-Task-Kette und Bibliothek bleiben erhalten — minimaler Eingriff.
4. Konfiguration weiterhin per Jellyfin-API durch Claude Code (harte Voraussetzung des Nutzers; sonst kein Projekt).

## Lösungsraum (entscheidet der Planner, nicht der Projektmanager)
- **Client:** Direct Play im Google-TV-Player erzwingen. Hinweis: externer Player ist auf Google TV nicht verfügbar, nur in der Handy-/Tablet-App.
- **Katalog-Brücke:** VLC den Jellyfin-Katalog per DLNA durchsuchen lassen.
- **Ingest:** Der aktuelle Plan behält die `.ts` (kein Remux). Ein einmaliger Remux `.ts`→`.mkv` beim Import — mit direct-play-tauglicher Tonspur und ohne problematische DVB-Untertitel — würde Transkodieren ganz vermeiden. Das ist eine neue Option gegenüber dem bisherigen „.ts behalten + Hardware-Transcode".

## Zu verifizieren
- Welcher Auslöser zwingt Jellyfin zum Transkodieren? Verdacht: Tonspur-Codec und/oder DVB-Untertitel — nicht das Bild (HEVC kann der Chromecast).
- Passt Jellyfin im Leerlauf (ohne Transkodierung) in den verfügbaren RAM?
- SSH-Rechte: Genügen die Rechte des Claude-Code-Nutzers für Docker- und Config-Änderungen? Synology-Task-Erstellung braucht ggf. Admin/Root — klären, da Claude Code keinen Root-Zugang hat.

## Abgrenzung
Nur Wiedergabe gespeicherter Aufnahmen, kein Live-TV. Diese Ergänzung liefert Ziele für die Architektur-Erarbeitung — keinen Plan, keine Implementierung.

— Projektmanager
