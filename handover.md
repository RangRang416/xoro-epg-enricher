# Handover — xoro-epg-enricher (2026-09-18, Session-Ende)

**#43 (Jellyfin-Nutzer "Komo") erledigt.** 3 Bibliotheken + Nutzer "Komo" eingerichtet, Login verifiziert. Trickplay-Extraktion für "Komo Filme"/"Komo Gifs" aktiviert, Scan angestoßen — ob GIFs tatsächlich Thumbnails bekommen haben, wurde nicht mehr geprüft (offen). `EnableInternetProviders` war überall schon `false`. Details: CHANGELOG.md, Issue-#43-Kommentar.

**#32 WI-3.1 abgeschlossen, committed (`ba9c16e`).** Alle 4 Spike-Fragen beantwortet. `scripts/provider_coverage.py` neu, Baseline auf 401/1310 (2026-09-18) neu verankert. Kritischer Fund für WI-3.3: Jellyfin-Update-Endpoint überschreibt `ProviderIds` unbedingt → Read-Modify-Write Pflicht. Details: Issue-#32-Kommentare.

**#32 WI-3.2 — Pilot ausgeführt + Opus-Review durch, Vollrollout NICHT gestartet.** 2 Ordner umbenannt (`URIInfo.bin`→`.xoro-hidden`), Mechanismus als sauber bestätigt. Review deckte auf: die ursprüngliche DELETE-Ablehnungsbegründung war fachlich falsch (Entscheidung selbst bleibt richtig). **Blockierend für Vollrollout:** Nachmessung der beiden Piloten-Filme nach Phantom-Verschwinden steht noch aus — ein automatischer 12h-Library-Scan (nicht von uns, letzter Lauf fehlgeschlagen wegen Linkstation-Aussetzer) blockiert seit heute Vormittag die Job-Queue, Phantome waren bei Sessionende noch in der DB. 8 Auflagen vor Vollrollout dokumentiert in Issue-#32-Kommentar (u.a. offene Ruben-Frage: wird `URIInfo.bin` fürs Xoro-Gerät/Stick gebraucht, Kontext #41?).

**Sicherheits-Randnotiz (aufgeklärt, folgenlos):** Ein Subagenten-Report kam mit "SECURITY WARNING: Blocked by classifier" — bei Nachfrage: nur die harmlose "kein langes sleep"-Bremse des Bash-Tools, kein echter Sicherheitsvorfall. Kein DELETE wurde je versucht.

**Nicht behandelt:** #41 (Bozena-Stick, wartet auf Rubens Entscheidung — hängt jetzt auch an der #32-Auflage 8 oben), #29/#37/#39/#40/#42.

**Nächster Schritt:** Sobald der Fremdscan auf der NAS durch ist (Status prüfen: `ScheduledTasks`, Task `7738148f...`): Phantom-Verschwinden + Nachmessung der 2 Pilot-Filme (Name/ProviderIds/UserData) nachholen, dann Vollrollout-Entscheidung. Parallel: Rubens Antwort zu Auflage 8 einholen.
