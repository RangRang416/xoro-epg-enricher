# Projekt: xoro-epg-enricher — Aktiver Plan

**Stand: 2026-04-25 | Planner: Opus | Status: Phase I bereit**

---

## Architektur-Entscheidungen (final)

| Entscheidung | Begründung |
|---|---|
| Python 3.11+ statt n8n | SMB-Laufwerk lokal, kein Web-Service-Bedarf |
| Windows Task Scheduler (alle 10 Min) | SMB liefert keine zuverlässigen Filesystem-Events |
| Ordner NICHT umbenennen | Xoro-Indexdateien (.idx/.meta) haben Pfad-Referenzen |
| Fallback-NFO immer | Lieber leer als fehlend in Jellyfin |
| TMDb statt XMLTV/EPG-Archiv | Ruben wählt Filme via KLACK → alle sind bekannte Mainstream-Titel |
| Phase I: nur Filme | Serien/Episoden sind eigenes Klasse-C-Issue (Phase IV) |

---

## Issue-Übersicht

| # | Titel | Klasse | Impl | Reviewer | Status | Blockiert durch |
|---|-------|--------|------|----------|--------|-----------------|
| #0 | Repo-Setup + README + projekt.md | A+ | Haiku | — | OFFEN | — |
| #1 | PoC — 1 Aufnahme manuell durch komplette Kette | B | Sonnet | — | OFFEN | #0 |
| #2 | Skript-Grundgerüst + Modulstruktur + CLI | C | Sonnet | Opus | OFFEN | #1 |
| #3 | RECInfo.txt-Parser mit Encoding-Detection | B | Sonnet | Opus | OFFEN | #2 |
| #4 | TMDb-Client mit Scoring + Fallback | C | Sonnet | Opus | OFFEN | #2, #3 |
| #5 | Cover-Downloader | A+ | Haiku | Sonnet | OFFEN | #2 |
| #6 | NFO-Generator (Movie) mit Fallback-Pfad | B | Sonnet | Opus | OFFEN | #2, #3, #4 |
| #7 | Orchestrator + Idempotenz-Marker | B | Sonnet | Opus | OFFEN | #3, #4, #5, #6 |
| #8 | Windows Task Scheduler Setup + Doku | A+ | Haiku | Sonnet | OFFEN | #7 |
| #9 | Jellyfin-Setup-Doku | A | Haiku | — | OFFEN | #1 |
| #10 | E2E-Test mit 10+ realen Aufnahmen | B | Sonnet | — | OFFEN | #7, #9 |
| #11 | Fehlerbehandlung & Logging-Härtung | B | Sonnet | Opus | OFFEN | #10 |
| #12 | (Optional) Serien/Episoden-Support | C | Sonnet | Opus | OPTIONAL | #11 |
| #13 | (Optional) Web-Dashboard Status-Übersicht | C | Sonnet | Opus | OPTIONAL | #11 |

**Critic-Pflicht:** #1, #2, #4, #6

---

## Phasen

### Phase I — PoC (Pflicht)
Issues #0, #1  
Stopp-Bedingung: Falls .ts-Playback in Jellyfin Android unbrauchbar → Plan-Revision

### Phase II — Kernmodule
Issues #2–#6

### Phase III — Automatisierung + Jellyfin
Issues #7–#11

### Phase IV — Optional
Issues #12, #13

---

## Risiken

- TMDb-Trefferquote ZDFinfo-Dokus < 50% → Fallback-NFO greift immer
- .ts-Playback in Jellyfin stottert → PoC #1 prüft das früh
- RECInfo.txt-Encoding exotisch → chardet + Fallback-Reihenfolge in #3
- Doppelte Verarbeitung bei parallelen Läufen → atomic write via os.replace

---

## Xoro-Aufnahme-Format (ermittelt 2026-04-25)

```
N:\PVR\REC\00029\
  record.ts          (1-2 GB, Videoinhalt)
  RECInfo.txt        (Sender, Titel, Untertitel, Sprache — KEINE Langbeschreibung)
  record.ts.meta
  record.ts.idx
  record.ts.pmt
  URIInfo.bin
```

RECInfo.txt Beispiel-Inhalt: `ZDFinfo HD … deu … Polenfeldzug … Der Nervenkrieg`
