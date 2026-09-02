# Handover — xoro-epg-enricher (2026-09-02, Session-Ende)

**Jellyfin-Diagnose+Fixes (01.09.):** Playback-Crash "Glückliche Männer" (HEVC, Opera/Chromium kann kein HW-Decode, ffmpeg OOM exit 137) → Video-/Audio-Transcoding für User Ruben per Policy deaktiviert (Server-Config, nicht im Repo, Details `synology.md`). Root-Cause-Bug gefunden: Xoro schreibt Aufnahmen ohne validen Zeitstempel (Epoche 1970) → Jellyfins "Kürzlich hinzugefügt" sortiert falsch. Fix in `enricher.py` (`_touch_now()`, Commit ac4879d, deployed) + 181 bestehende Dateien auf NAS nachträglich korrigiert (mtime=ctime, brauchte Rubens sudo — admin-SSH reicht nicht für root-eigene Dateien). Jellyfin-Scan manuell angestoßen 01.09. 16:40 UTC.

**Issue #41 (neu, offen):** `--rename-in-place`-Flag implementiert + getestet + deployed (Commit 81dc558) für Stick-Workflow bei Bozena (2. Xoro). **Aber:** Kommentar auf #41 (02.09.) zeigt, das Feature löst vermutlich NICHT das eigentliche Problem — Xoro-eigene Aufnahmenliste zeigt bereits umbenannte Filme weiterhin nur mit Nummer statt Titel, liest offenbar aus interner Datenbank/Index statt Dateiname. Wartet auf Rubens Entscheidung: (1) Nummer-Liste manuell führen oder (2) riskantes Reverse-Engineering des proprietären Xoro-Metadatenformats (RECInfo.txt/URIInfo.bin) wagen.

**Unverändert offen aus 29.08. (in dieser Session nicht bearbeitet):** WI-3-Plan zu #32 wartet weiter auf Freigabe zum Start (Details: `wi3-plan-metadaten-luecke.md`, Issue-#32-Kommentare). #29, #37, Linkstation-Duplikat aus #38 unbearbeitet.

**Nächster Schritt:** Rubens Entscheidung zu #41 abwarten. WI-3.1-Freigabe weiterhin ausstehend.
