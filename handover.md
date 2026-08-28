# Handover — xoro-epg-enricher (2026-08-28)

**#38-Diagnose abgeschlossen** (Live-Test mit Ruben, direkt am Server mitverfolgt). "Jellyfin crasht" war kein einheitliches Symptom, sondern drei getrennte Ursachen — aufgeteilt in:

1. **#22 (App-Absturz, Root Cause jetzt bekannt):** Jellyfin Android-TV-App (0.19.10) sendet beim Wiedergabe-Ende gelegentlich negative `PositionTicks`, Server wirft ungefangene `ArgumentOutOfRangeException` → HTTP 500 → App-Absturz beim Zurückgehen ins Hauptmenü. Stacktrace jetzt in #22 dokumentiert. Ruben-Entscheidung: nur als Upstream-Bug vermerken, kein eigener Server-Patch (kein Custom-Image).
2. **#39 (neu, Transcoding-Problem):** Phase VI aus `projekt.md`/`controller-briefing-phase6.md` wiederaufgenommen — war seit 2026-05-30 vom Controller freigegeben, aber nie als Issue umgesetzt. Konkreter Beleg heute: altes XviD/AVI-Rip von der Linkstation zwingt Jellyfin zum Transkodieren (Chromecast kann den Container/Codec nicht direkt). Kein Absturz bei diesem Test, aber das dokumentierte OOM-Risiko (1GB-RAM-NAS) bleibt bei größeren Dateien. Plan liegt fertig vor: VI-1 (Diagnose-Gate) → VI-3 (Server-Profil, primär) → VI-2 (Remux-Fallback).
3. **#32 (ergänzt):** Neue Beobachtung — Serie von der Linkstation erstmals aufgerufen, noch nicht erkannt, existiert evtl. doppelt (Linkstation + Synology-nativ). Noch nicht weiter untersucht.

**#38 geschlossen** (FREIGABE Ruben 28.08., zugunsten #22/#39/#32).

**Sehzeit-Restart-Nebenfund (aus #36, weiterhin ohne eigenes Issue):** Mounts während Rubens Sehzeit lösen einen `docker restart jellyfin` aus. Noch zu entscheiden.

**Scan-Status:** Voller Scan vom 22.08. nie fertig geworden (letzter abgeschlossener Scan: 19.08.). Neuer Scan-Zeitpunkt weiterhin offen.

**Unverändert offen:** #29 (hängt an WI-1→WI-2, seit Juni bei `POST /Library/Refresh` blockiert, `projekt.md` seit 17.06. nicht mehr gepflegt — Achtung: nicht verwechseln mit dem PM-Zieldokument `project.md`, das existiert separat und ist aktuell), #37 (Backlog, F:-Laufwerk).

Nächster Schritt: **#39 (VI-1-Diagnose-Gate)** als nächstes inhaltliches Thema — Plan liegt fertig vor, kann direkt starten.
