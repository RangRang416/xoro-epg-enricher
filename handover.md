# Handover — xoro-epg-enricher (2026-08-28)

**#38-Diagnose abgeschlossen** (Live-Test mit Ruben, direkt am Server mitverfolgt). "Jellyfin crasht" war kein einheitliches Symptom, sondern drei getrennte Ursachen — aufgeteilt in:

1. **#22 (App-Absturz, Root Cause jetzt bekannt):** Jellyfin Android-TV-App (0.19.10) sendet beim Wiedergabe-Ende gelegentlich negative `PositionTicks`, Server wirft ungefangene `ArgumentOutOfRangeException` → HTTP 500 → App-Absturz beim Zurückgehen ins Hauptmenü. Stacktrace jetzt in #22 dokumentiert. Ruben-Entscheidung: nur als Upstream-Bug vermerken, kein eigener Server-Patch (kein Custom-Image).
2. **#39 (neu, Transcoding-Problem):** Phase VI aus `projekt.md`/`controller-briefing-phase6.md` wiederaufgenommen — war seit 2026-05-30 vom Controller freigegeben, aber nie als Issue umgesetzt. Konkreter Beleg heute: altes XviD/AVI-Rip von der Linkstation zwingt Jellyfin zum Transkodieren (Chromecast kann den Container/Codec nicht direkt). Kein Absturz bei diesem Test, aber das dokumentierte OOM-Risiko (1GB-RAM-NAS) bleibt bei größeren Dateien. Plan liegt fertig vor: VI-1 (Diagnose-Gate) → VI-3 (Server-Profil, primär) → VI-2 (Remux-Fallback).
3. **#32 (ergänzt):** Neue Beobachtung — Serie von der Linkstation erstmals aufgerufen, noch nicht erkannt, existiert evtl. doppelt (Linkstation + Synology-nativ). Noch nicht weiter untersucht.

**#38 geschlossen** (FREIGABE Ruben 28.08., zugunsten #22/#39/#32).

**#39 VI-1-Test durchgeführt (28.08.), Ergebnis widerlegt die Ausgangshypothese teilweise:** `ffprobe` bestätigt HEVC 1080p + EAC3/AAC_LATM in den nativen `.ts`-Aufnahmen, 2 von 3 getesteten Dateien mit `dvb_subtitle`-Bild-Untertitel. Live-Test "Monster House" am Chromecast: **kein Server-seitiges Transcoding** (keine ffmpeg-Logs, kein Transcode-Cache-Eintrag) — war Direct Play trotz Untertitel-Stream. Tatsächliches Symptom: Wiedergabe stockte massiv, lief nach Google-TV-Geräte-Neustart normal — deutet auf Client-seitiges Problem (HEVC-Hardware-Decoder?), nicht auf das RAM-/Transcode-Risiko, das Phase VI ursprünglich adressieren wollte. Häufigkeit des Stockens unbekannt (Ruben hat nicht bewusst darauf geachtet bisher). **Ruben-Entscheidung: #39 zurückstellen**, kein akuter Handlungsdruck. Ergebnis in #39 dokumentiert.

**Sehzeit-Restart-Nebenfund (aus #36, weiterhin ohne eigenes Issue):** Mounts während Rubens Sehzeit lösen einen `docker restart jellyfin` aus. Noch zu entscheiden.

**Scan gestartet (FREIGABE Ruben 28.08., per API angestoßen):** Voller Library-Scan läuft seit 28.08. (Task-ID `7738148ffcd07979c7ceb148e06b3aed`), Ziel: die 5 seit 22.08. hängenden neuen E:-Ordner vollständig erfassen (voriger Versuch vom 22.08. nie fertig geworden). Dauer laut Erfahrung bis zu ~1h. **Ergebnis noch nicht geprüft** — nächste Session: Scan-Abschluss verifizieren (`GET /ScheduledTasks/{id}`, State sollte "Idle" sein, `LastExecutionResult` "Completed"), dann Item-Counts der 5 Ordner erneut prüfen (gleiches Vorgehen wie am 26.08.: `/Items?Recursive=true&IncludeItemTypes=Movie&Fields=Path,ProviderIds` und nach `windows-e`-Unterpfaden filtern) und mit Ruben abgleichen, ob die Erkennung jetzt sauber ist oder viel "Nicht erkannt" bleibt (passt dann zu #32).

**Unverändert offen:** #29 (hängt an WI-1→WI-2, seit Juni bei `POST /Library/Refresh` blockiert, `projekt.md` seit 17.06. nicht mehr gepflegt — Achtung: nicht verwechseln mit dem PM-Zieldokument `project.md`, das existiert separat und ist aktuell), #32 (inkl. Linkstation-Duplikat-Beobachtung aus #38), #37 (Backlog, F:-Laufwerk).

Nächster Schritt: Scan-Ergebnis verifizieren (siehe oben). Falls das Stocken-Symptom aus #39 nochmal auftritt — Häufigkeit/Muster beobachten, dann ggf. eigenes Issue. Danach #32 (Metadaten/Linkstation-Duplikat) oder WI-2-Fortsetzung.
