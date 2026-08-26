# Handover — xoro-epg-enricher (2026-08-26)

**#36 geschlossen** (FREIGABE Ruben 26.08.). Verifiziert: 4 saubere Trigger (23.-26.08.), Live-Inode-Vergleich Host=Container bestanden, kein Fehler im Jellyfin-Log um die Restart-Zeitpunkte.

**Neu, WICHTIG (#38, akut gemeldet von Ruben, noch nicht diagnostiziert):** Jellyfin crasht bei jedem Versuch, Medien von externen Mount-Laufwerken (windows-e, buffalo-archiv) abzuspielen — nur die native NAS-Bibliothek funktioniert. Laut Ruben besteht das schon länger, **kein Zusammenhang mit #36** (von ihm explizit bestätigt, nicht selbst verifiziert). Passt zu zwei bekannten offenen Fäden: (1) `projekt.md` Phase VI — Transcode-Last bei `.ts`-Wiedergabe sprengt das 1GB-RAM-NAS, Controller-Freigabe seit 30.05. erteilt, aber nie als GitHub-Issue umgesetzt (VI-1/VI-2/VI-3 existieren nirgends als Issue); (2) eigener Fund vom 26.08.: 131 ffprobe-Fehler am 24.08. bei rohen Dateien auf windows-e. Nächste Session: mit Rubens Freigabe live auf der NAS diagnostizieren (Container-Status, RAM, Jellyfin-Logs während eines Wiedergabeversuchs).

**Sehzeit-Restart-Nebenfund (aus #36, weiterhin ohne eigenes Issue):** Mounts während Rubens Sehzeit lösen jetzt einen `docker restart jellyfin` aus. Noch zu entscheiden: eigenes Issue oder Backlog-Vermerk.

**Scan-Status:** Voller Scan vom 22.08. nie fertig geworden (letzter abgeschlossener Scan: 19.08., vor den 5 neuen E:-Ordnern). Neuer Scan-Zeitpunkt mit Ruben noch abzustimmen (auf "später" verschoben, 25.08.).

**Unverändert offen:** #22 (Upstream-Jellyfin-Bug), #29 (hängt an WI-1→WI-2, seit Juni bei `POST /Library/Refresh` blockiert, `projekt.md` seit 17.06. nicht mehr gepflegt), #32 (Metadaten-Lücke), #37 (Backlog, F:-Laufwerk).

Nächster Schritt: **#38 zuerst** (akuter Nutzer-Blocker) — Live-Diagnose auf der NAS. Danach Sehzeit-Nebenfund klären, Scan nachholen, #32/WI-2 fortsetzen.
