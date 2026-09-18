# Handover — xoro-epg-enricher (2026-09-18, Zwischenstand — Session läuft noch)

**#43 (Jellyfin-Nutzer "Komo") erledigt.** 3 Bibliotheken + Nutzer "Komo" eingerichtet, Login verifiziert. Trickplay-Extraktion für "Komo Filme"/"Komo Gifs" aktiviert, Scan angestoßen — Status am Sessionende nicht final geprüft (ob GIFs tatsächlich Thumbnails bekommen, war noch offen). `EnableInternetProviders` war überall schon `false`. Details: CHANGELOG.md, Issue-#43-Kommentar.

**#32 WI-3.1 abgeschlossen, committed (`ba9c16e`).** Alle 4 Spike-Fragen beantwortet (siehe Issue-#32-Kommentare). `scripts/provider_coverage.py` neu, Baseline auf 401/1310 (2026-09-18) neu verankert. Kritischer Fund für WI-3.3: Jellyfin-Update-Endpoint überschreibt `ProviderIds` unbedingt → Read-Modify-Write Pflicht. Offen, nicht blockierend: `windows-e`-Delta (-9 Items) ungeklärt, 40 weitere URIInfo.bin unter `/usb-pvr` außerhalb Scope, möglicher Widerspruch zu WI-2 (`EnableInternetProviders`).

**#32 WI-3.2 — Pilot ausgeführt, NOCH NICHT COMMITTED, Review läuft.** 2 Ordner (`Die Schnecke und der Buckelwal`, `Mein Vater, die Wurst`) — `URIInfo.bin` → `URIInfo.bin.xoro-hidden` umbenannt (NICHT gelöscht: Advisor deckte auf, dass `DELETE /Items/{id}` bei Einzelfilm-Ordnern den ganzen Ordner inkl. echtem Film von der Platte löschen würde — DELETE als Mechanismus für den Plan verworfen). Von mir unabhängig verifiziert: beide echte Filme unverändert (ProviderIds+Watch-Status intakt), Rename tatsächlich passiert. **Phantom-Items sind in der Jellyfin-DB noch nicht verschwunden** — ein fremder, nicht selbst ausgelöster Library-Scan lief parallel (zuletzt 88,8%, sehr langsam wegen TVDb-Rate-Limits) und hat den gezielten Refresh-Effekt bisher blockiert. Kein Fehlschlag, nur noch nicht verifizierbar.

**Opus-Review für WI-3.2 läuft im Hintergrund** (Sicherheitsbewertung Rename-Mechanismus + Freigabe-Empfehlung für Vollrollout auf die übrigen 168 URIInfo.bin-Items). Bei Session-Abbruch vor Abschluss: Ergebnis ist dann verloren (Subagent-Prozess weg), aber NAS-Zustand ist unverändert nutzbar — `git status` im Repo prüfen (Skript-Änderungen? keine erwartet, Review schreibt nichts), dann Opus-Review-Schritt aus `wi3-plan-metadaten-luecke.md` (Abschnitt WI-3.2) manuell neu anstoßen.

**Sicherheits-Randnotiz (aufgeklärt):** Ein Subagenten-Report kam mit "SECURITY WARNING: Blocked by classifier" — bei Nachfrage stellte sich heraus, das war nur die harmlose "kein langes sleep"-Bremse des Bash-Tools (Anti-Polling), kein echter Sicherheits-Klassifikator-Vorfall. Kein DELETE wurde je versucht, keine Umgehung.

**NAS-Zustand:** Zwei parallele Scans liefen am Sessionende auf der Synology (Komo-Trickplay + der fremde Library-Scan bei 88,8%) — unabhängig vom PC, laufen weiter.

**Nicht behandelt:** #41 (Bozena-Stick, wartet auf Rubens Entscheidung), #29/#37/#39/#40/#42.

**Nächster Schritt:** Opus-Review-Ergebnis abwarten → bei Freigabe: WI-3.2 committen, Issue-#32-Kommentar mit Review-Ergebnis + Vollrollout-Entscheidung. Danach: Komo-Gifs-Trickplay-Status nachprüfen (offene Zusage), `windows-e`-Delta-Frage aus WI-3.1 falls gewünscht klären.
