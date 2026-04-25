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
