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

---

# Phase VI — Planner-Entwurf (1. Entwurf, wartet auf Controller-Freigabe)

**Stand: 2026-05-30 | Planner: Opus | Status: Entwurf**

## Kernentscheidung Planner

Jellyfin bleibt. Wiedergabegerät: Chromecast with Google TV. Lösung: Transcode-Ursache empirisch ermitteln (Gate), dann eliminieren — nicht Hardware aufrüsten.

## Issue-Übersicht Phase VI

| # | Titel | Klasse | Impl | Reviewer | Status | Branch |
|---|-------|--------|------|----------|--------|--------|
| VI-1 | Diagnose: Transcode-Ursache + Codec (GATE) | A | Haiku | — | OFFEN | — |
| VI-2a | Remux-Hook im Enricher `.ts`→`.mkv` (`-c copy`) | B | Sonnet | Opus | OFFEN | nur H.264 |
| VI-2b | Re-Encode-Branch (Planner-Re-Spec nach Messung) | C | Opus→Sonnet | Opus | OFFEN | nur MPEG-2 |
| VI-3 | Direct-Play-Device-Profil per Jellyfin-API | B | Sonnet | Opus | OPTIONAL | Restfälle |

VI-2a und VI-2b sind mutually exclusive. VI-1 ist hartes Gate — kein weiteres Issue startet ohne Ergebnis.

## Architektur-Entscheidungen Phase VI

| Entscheidung | why: |
|---|---|
| Gate-Struktur (VI-1 zuerst) | Video-Codec (H.264 vs. MPEG-2) bestimmt ob `-c copy` hilft. Chromecast hat keinen MPEG-2-Decoder — ohne Messung ist Variantenwahl Raten. |
| Remux via `docker exec jellyfin-ffmpeg` | Synology-Host hat kein ffmpeg, kein Root-Zugang. Wiederverwendung des bekannten Builds. |
| Remux-Hook hinter `move_recording` in enricher.py | Minimaler Eingriff (Ziel 3); bestehende Idempotenz (skip via `movie.nfo`) bleibt unangetastet. |
| Variante B (DLNA→VLC) verworfen | Reintroduziert den Katalog-Umweg, den Ziel 2 explizit eliminieren soll. |
| Variante A nur als Fallback (VI-3) | Device-Profile per API fragil (Reset bei App-Update). C braucht null Jellyfin-Config. |

## Akzeptanzkriterien Phase VI (gesamt)

1. Jellyfin-Dashboard zeigt bei Chromecast-Wiedergabe **Direct Play** (kein ffmpeg-Spike in `docker stats`)
2. Enricher-Idempotenz unverändert (Re-Run → skip)
3. NFO/Cover/Bibliothek unberührt
4. Auswahl und Steuerung vollständig über Jellyfin (kein VLC-Umweg)
5. Konfigurierbar per Jellyfin-API durch Claude Code

## Risiken Phase VI

| Risiko | Gegenmaßnahme |
|---|---|
| Aufnahmen sind MPEG-2 → `-c copy` löst nichts | VI-1 als hartes Gate; Branch VI-2b vordefiniert |
| Falsches Audio-Stream-Mapping → Ton fehlt | ffprobe-gestütztes `-map`, Opus-Review, Ton-Verifikation als AK |
| `.ts`+`.mkv` verdoppelt Speicher | Nach Remux `.ts` löschen als AK in VI-2a |
| Enricher-Task von laufendem Jellyfin-Container abhängig | In Doku + handover.md vermerken |
| Mehrdeutiger Transcode-Grund | VI-1 protokolliert verbatim; bei Mehrdeutigkeit → Planner, nicht raten |

---

# Phase VI — Controller-Befund (externer Controller, Claude-Web)

**Stand: 2026-05-30 | Controller: Claude-Web | Bezug: Planner-Entwurf oben + Projektmanager-Notiz**

**Verdict: noch keine Freigabe.** Gate-first ist richtig, der Kern trägt — aber der Entwurf enthält einen inneren Widerspruch zur eigenen Projektmanager-Notiz, der vor VI-2-Start aufzulösen ist.

## 1. Branch-Taxonomie widerspricht der eigenen Verifikations-Notiz
Die Projektmanager-Notiz hält bereits fest: Quelle ist HEVC, Auslöser vermutlich Ton-Codec und/oder DVB-Untertitel — „nicht das Bild". Der Planner-Entwurf verzweigt aber nach „H.264 vs. MPEG-2" (VI-2a/VI-2b) und begründet das Gate mit „Chromecast hat keinen MPEG-2-Decoder". Das fällt hinter den schon dokumentierten Stand zurück. Deutsches DVB-T2 HD sendet HEVC; MPEG-2 war das alte DVB-T. Ist die Quelle HEVC (was VI-1 bestätigt), existiert der MPEG-2-Fall nicht real → VI-2b (der teuerste Knoten, Opus) ist ein toter Ast, und der Remux-Branch sollte „abspielbare Codecs (HEVC/H.264)" heißen statt „nur H.264". Das Risiko „Aufnahmen sind MPEG-2" plus vordefinierter VI-2b binden Planungs-Budget an einen Fall, den das Projekt selbst für unwahrscheinlich hält.

## 2. Der Auslöser, nicht der Video-Codec, sollte die Verzweigung steuern
Gut: VI-1 heißt „Transcode-Ursache + Codec". Inkonsequent: Begründungstabelle und Branch-Logik hängen am Video-Codec. Ist der Auslöser die DVB-Untertitel (Einbrennen) oder die MP2-Tonspur, entscheidet nicht der Video-Codec über die Lösung. Saubere Verzweigung: „Auslöser im Container entfernbar (Untertitel droppen, ggf. nur Audio umkodieren) → Remux genügt" vs. „Videobild selbst undekodierbar → Re-Encode (Randfall)". Der VLC-Beweis stützt das: das Bild ist abspielbar, Jellyfin transkodiert aus anderem Grund.

## 3. VI-3 (Geräteprofil) ist evtl. die Lösung, nicht der Restfall
Ist der Auslöser allein das Untertitel-Einbrennen, stellt ein Jellyfin-Profil „Bild-Untertitel nicht einbrennen, Direct Play" das Transkodieren ohne jeden Datei-Eingriff ab — einmalig konfiguriert statt ffmpeg pro Aufnahme, kein `enricher.py`-Hook, keine Speicher-Verdopplung. Das ist die ressourcen- und wartungssparsamste Variante. Der Entwurf stuft VI-3 mit „fragil, Reset bei App-Update" auf optional herab. Diese Begründung ist selbst zu prüfen: liegt die entscheidende Einstellung server-seitig (Jellyfin-Server/DLNA-Profil, persistent) oder client-seitig (vom Chromecast-App-Profil gepusht, rücksetzbar)? Davon hängt ab, ob VI-3 ein robuster Einmal-Fix ist, der VI-2 ganz erspart. VI-1 sollte explizit beantworten: „Löst ein Server-Profil das Problem allein?" — vor dem Pipeline-Umbau VI-2a.

## 4. ffmpeg aus dem Jellyfin-Container: dokumentiert statt entfernt
Die Risiko-Zeile „Enricher-Task von laufendem Jellyfin-Container abhängig → in Doku vermerken" behebt die Fragilität nicht, sie notiert sie nur. Der Enricher hinge an Lebenszyklus und ffmpeg-Version des Media-Servers; ein Jellyfin-Update kann die Pipeline still brechen. Ein eigener schlanker ffmpeg-Container (separater Compose-Service) entkoppelt das bei minimalem Mehraufwand und gibt Versionskontrolle. Trägt Befund 3 (Profil statt Remux), entfällt der Punkt ohnehin.

## Antworten auf die offenen Fragen
- **Gate ohne Vorab-Commit:** richtig, beibehalten — inhaltlich am Auslöser ausrichten (Ton + Untertiteltyp + „löst ein Profil es allein?"), nicht primär am Video-Codec.
- **Abhängigkeit vom laufenden Jellyfin-Container:** technisch tragbar, aber unnötig fragil → eigener ffmpeg-Container, siehe Befund 4.
- **Variante B (DLNA→VLC) endgültig?** Als Primärweg verworfen ist sachlich ok (Katalog-Verlust, Ziel 2). Als manueller Notfall-Rückweg kostenlos, da bereits funktionsfähig — dokumentiert behalten, nicht aktiv pflegen.

— Externer Controller (Claude-Web)

---

# Phase VI — Planner-Revision 1 (wartet auf Controller-Freigabe, Turn 2)

**Stand: 2026-05-30 | Planner: Opus | Status: Revision 1**

## Architektur-Entscheidungen (revidiert)

| Entscheidung | why: |
|---|---|
| Verzweigung auf Auslöser-Typ statt Video-Codec | VLC spielt HEVC-Bild direkt ab → Videobild ist dekodierbar. Jellyfin transkodiert aus anderem Grund (DVB-Untertitel/MP2-Audio). Codec-Verzweigung plant für widerlegten Fall. |
| VI-3 (Server-Profil) ist Primärkandidat | Kein ffmpeg pro Aufnahme, keine Speicherverdopplung, kein Enricher-Eingriff (Ziel 3). Einmalig per API konfiguriert (Ziel 4). Spart VI-2 komplett, falls erfolgreich. |
| VI-2b gestrichen | HEVC ist Standard-Quelle (DVB-T2 HD), MPEG-2 war DVB-T (abgeschaltet). Echter Randfall → Kontingenz-Einzeiler in VI-1, kein eigenes Opus-Issue. |
| VI-2 (Remux) nur konditional | Wird nur gebaut wenn VI-3 scheitert. ffmpeg als eigener Compose-Service (`linuxserver/ffmpeg`), nicht `docker exec jellyfin`. |
| ffmpeg-Entkopplung über Compose-Service | `docker exec` koppelt Remux an Jellyfin-Update-Zyklus → fragil. Eigener Service gibt Versionskontrolle. Nur relevant falls VI-2 aktiviert wird. |

## Issue-Übersicht Phase VI (revidiert)

| # | Titel | Klasse | Impl | Reviewer | Status | Bedingung |
|---|-------|--------|------|----------|--------|-----------|
| VI-1 | Diagnose: Auslöser + Server-Profil-Machbarkeit (GATE) | A | Opus | — | OFFEN | — |
| VI-3 | Server-seitiges Jellyfin-Profil per API (PRIMÄR) | B | Sonnet | Opus | OFFEN | nach VI-1 |
| VI-2 | Remux-Hook `.ts`→`.mkv` + ffmpeg-Service (FALLBACK) | C | Opus | Sonnet | OFFEN | nur falls VI-3 scheitert |

## Issue VI-1 (GATE, Opus)

**Empirisch beantworten:**
- (a) Konkreter Transcode-Grund aus Jellyfin-Log / PlaybackInfo-API — DVB-Untertitel und/oder MP2-Audio?
- (b) Existiert ein server-seitig per API **persistierbarer** Hebel, der den Transcode abstellt?
- (c) Falls nur client-seitig: Ziel-4-Konflikt explizit markieren
- (d) Enricher-Vorprüfung: hängt NFO-Matching an `.ts`-Endung? (Datengrundlage für VI-2)
- (e) Kontingenz: Falls Videobild selbst nicht dekodierbar → Re-Encode, zurück an Planner

**Test:** Testwiedergabe über realen Jellyfin-Client (Chromecast-App), NICHT VLC. Profil-Hebel testweise per API setzen.

**Ergebnis:** GATE-Befund mit Entscheidung VI-3 ODER VI-2.

## Issue VI-3 (PRIMÄR, Sonnet/Opus)

Server-seitiges Profil per Jellyfin-API setzen, das Transcode-Auslöser aus VI-1 abstellt. Persistent über Container-Neustart.

**AK:** Direct Play im Jellyfin-Client bestätigt + Persistenz nach Neustart + per API konfiguriert (Ziel 4).

**Übergang zu VI-2 nur wenn:** Profil stoppt Transcode nicht ODER nicht server-seitig persistent ODER MP2-Audio bleibt zweiter unabhängiger Auslöser.

## Issue VI-2 (FALLBACK, Opus/Sonnet)

Remux-Hook in `enricher.py` hinter `move_recording`: `.ts`→`.mkv`, DVBSUB droppen, Audio bei MP2 umkodieren. ffmpeg über eigenen `linuxserver/ffmpeg`-Compose-Service.

**AK:** Direct Play bestätigt + Enricher-NFO-Matching überlebt Container-Wechsel + Jellyfin-Bibliothek ingestiert `.mkv` ohne Reset + ffmpeg läuft außerhalb Jellyfin-Container.

## Offener Punkt (Architektur-Weichenstellung, Ruben)

Falls VI-1 Ziel-4-Konflikt meldet (Hebel nur client-seitig, nicht per API persistierbar): VI-2-Fallback akzeptieren oder Ziel 4 lockern?

## Risiken (revidiert)

| Risiko | Gegenmaßnahme |
|---|---|
| Hebel nur client-seitig (Ziel-4-Konflikt) | VI-1-(c) zwingt Konflikt an Oberfläche vor VI-3-Implementierung |
| MP2-Audio als zweiter unabhängiger Auslöser | VI-1-(a) prüft beide Auslöser unabhängig; VI-3-Übergangsbedingung deckt Fall ab |
| VI-2 bricht Enricher-Matching / Library | VI-1-(d) Vorprüfung + VI-2-AK-(b) als hartes Gate |
| VLC-Trugschluss in Tests | Alle Wiedergabetests explizit gegen realen Jellyfin-Client, nicht VLC |

---

# Phase VI — Controller-Freigabe (externer Controller, Claude-Web)

**Stand: 2026-05-30 | Controller: Claude-Web | Bezug: Planner-Revision 1**

**Verdict: Freigabe.** Revision 1 räumt alle vier Befunde aus — Verzweigung jetzt auf Auslöser-Typ statt Video-Codec, VI-2b gestrichen, VI-3 (Server-Profil) als Primär mit expliziter Server-vs-Client-Prüfung in VI-1 (b)/(c), ffmpeg als eigener Compose-Service. Der eigenständige Zusatz „Tests gegen realen Jellyfin-Client statt VLC" ist die richtige Absicherung: der VLC-Beweis zeigt nur, dass das Bild dekodierbar ist, nicht, was der Jellyfin-Client tatsächlich direct-played.

**Eine Präzisierung für VI-1 (kein Freigabe-Vorbehalt):** Nicht jeder Auslöser kostet gleich viel. Untertitel-Einbrennen erzwingt eine **Video**-Transkodierung (das Bild muss neu kodiert werden) — das ist die schwere Last, die den 1-GB-RAM sprengt. Eine MP2-Tonspur erzwingt nur eine **Audio**-Transkodierung — die ist leicht und passt vermutlich in den RAM, während das Video weiter direct-played. Konsequenz: bleibt nach dem Untertitel-Fix nur MP2 übrig, ist das wahrscheinlich kein OOM-Fall und kein hinreichender Grund für den VI-2-Remux. VI-1 sollte deshalb pro Auslöser festhalten, ob er eine Video- oder nur eine Audio-Transkodierung erzwingt — sonst aktiviert die Übergangsbedingung „MP2 bleibt zweiter Auslöser" den Fallback unnötig.

— Externer Controller (Claude-Web)

---

## Feldbeobachtung (Bernd, 2026-05-30) → Eingang VI-1

Wiedergabe aus der Jellyfin-Android-App auf den Chromecast gelang spontan, ohne Änderung. Noch kein Beweis für „gelöst": anderer Wiedergabeweg (Cast aus der App) als die native Google-TV-App; möglich sind ein App-/Server-Update, ein abweichender Film (Tonspur/Untertitel) oder ein leichtes Audio-Transcode statt echtem Direct Play. VI-1 misst entsprechend: Dashboard / `docker stats` → Direct Play vs. Transcode(Audio); über mehrere Aufnahmen reproduzieren; Cast-Weg vs. native App vergleichen.
