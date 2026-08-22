# Handover — xoro-epg-enricher (2026-08-22, Nachtrag)

**#33/#34/#35 geschlossen** (Rubens Freigabe).

**Neuer Fund + Fix (#36, offen, wartet auf Verifikation über mehrere Tage):** Docker-Bind-Mounts übernehmen einen CIFS-Mount NICHT, wenn er erst nach dem Jellyfin-Container-Start entsteht (rprivate-Propagation, Inode-Vergleich bestätigt zwei unterschiedliche Sichten). Akuter Auslöser: windows-e (E:, Windows-PC) wurde heute erst um 15:30 gemountet, Jellyfin lief aber schon seit 07:53 — Container sah leeres Verzeichnis. Sofort-Fix: `docker restart jellyfin` manuell. Dauerhaft-Fix deployed: `mount-cifs.sh` (NAS-only) restartet Jellyfin jetzt automatisch, wenn ein Mount frisch dazukommt UND Jellyfin bereits lief (vorheriger Script-Kommentar "kein Restart nötig" war falsch, korrigiert). Backup der Vorversion: `mount-cifs.sh.bak-2026-08-22`.

**Jellyfin-Bibliotheken ergänzt (mit Rubens Freigabe):** 5 bisher fehlende E:-Ordner (Film, Fernsehfilm, Fernsehen, Film & Serie in Einsfestival → Filme; Doku-Reihe → Dokumentationen) hinzugefügt, roh (kryptische DVB-Rohdateinamen, keine Metadaten-Bereinigung — passt zu #32). Z:/Filme existiert nicht als Ordner (0-Byte-Datei von 2015). Voller Library-Scan angestoßen (Rubens Freigabe), lief bei Sessionende bei ~52%.

**Neu (#37, Backlog):** F:-Laufwerk vom Windows-PC ist noch nicht freigegeben/gemountet/in Jellyfin — zurückgestellt, nicht dringend.

**Unverändert offen:** #22 (Upstream-Jellyfin-Bug), #29 (TVDb-Spike-Plan unbearbeitet seit 25.06.), #32 (Metadaten-Lücke, eigene Projektphase).

Nächster sinnvoller Schritt: #36 nach ein paar Tagen Logs verifizieren (analog zum #35-Vorgehen); Scan-Ergebnis mit Ruben prüfen (kamen die 5 neuen Ordner sauber/erkennbar an, oder viel "Nicht erkannt"?); dann Richtung #29 oder #32 entscheiden.
