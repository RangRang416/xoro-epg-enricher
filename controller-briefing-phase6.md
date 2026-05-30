# Controller-Briefing: Phase VI — Wiedergabe ohne Server-Transkodierung

**Datum:** 2026-05-30 | **Planner:** Opus | **Reviewer:** Controller

---

## Kontext

Jellyfin auf Synology (1 GB RAM) transkodiert `.ts`-Aufnahmen → OOM-Kill. Hardware-Transcoding nicht realisierbar. Chromecast with Google TV vorhanden; Direct Play grundsätzlich möglich (VLC-Beweis existiert). Kodi final verworfen (kein API-Weg, Client statt Server).

---

## Plan-Zusammenfassung

**Gate-Struktur, 4 Issues:**

| # | Was | Modell | Branch |
|---|-----|--------|--------|
| VI-1 | Diagnose: `ffprobe` auf 3 Aufnahmen + Jellyfin-Log + Idle-RAM | Haiku | Gate — blockiert alles |
| VI-2a | Remux-Hook in `enricher.py`: `.ts`→`.mkv` via `ffmpeg -c copy`, DVBSUB droppen | Sonnet/Opus | nur H.264 |
| VI-2b | Re-Encode-Branch: Planner re-spezifiziert nach Messung | Opus-Replan | nur MPEG-2, exklusiv zu VI-2a |
| VI-3 | Direct-Play-Device-Profil per Jellyfin-API | Sonnet/Opus | optional, Restfälle |

---

## Kritische Entscheidungen zur Prüfung

1. **Gate ist zwingend:** Chromecast hat keinen MPEG-2-Decoder. Bei MPEG-2-Aufnahmen kollabiert Variante C (Remux) lautlos — VI-1 muss zuerst laufen.

2. **ffmpeg-Quelle = `docker exec jellyfin-ffmpeg`:** Kein Host-ffmpeg auf Synology, kein Root. Enricher-Task wird damit vom laufenden Jellyfin-Container abhängig.

3. **Remux-Hook in `enricher.py` hinter `move_recording` (Zeilen 375–383):** Minimaler Eingriff, Idempotenz bleibt. Nach Remux muss `.ts` gelöscht werden — sonst Speicherverdopplung.

4. **Variante B (DLNA→VLC) verworfen:** Reintroduziert Katalog-Umweg (gegen Ziel 2). Endgültig oder Fallback behalten?

5. **Issue #19 (Kodi) schließen:** Final verworfen. Braucht Rubens Freigabe.

---

## Offene Fragen an Controller

- Gate-Ansatz so gewollt (kein Commit vor VI-1-Ergebnis)?
- Enricher-Abhängigkeit von laufendem Jellyfin-Container akzeptabel?
- Variante B endgültig verworfen?
