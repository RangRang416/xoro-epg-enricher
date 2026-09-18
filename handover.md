# Handover — xoro-epg-enricher (2026-09-18, Session-Ende)

**#43 (Jellyfin-Nutzer "Komo") erledigt:** Vorsession war abgebrochen, hatte bereits `/volume1/komo/{Filme,Fotos,Gifs}` befüllt + Jellyfin-Nutzer "Komo" ohne Bibliothekszugriff angelegt. In dieser Session: 3 neue `:ro`-Mounts in `docker-compose.yml` (NAS), Container neu gestartet, 3 Jellyfin-Bibliotheken angelegt, Nutzer "Komo" per API darauf beschränkt (`EnableAllFolders: false`), Passwort neu gesetzt (Ruben hat es im Chat erhalten). Login+Berechtigung verifiziert. Nur LAN-Zugriff (Android-App/Google TV im Heimnetz), kein Fernzugriff/Tailscale eingerichtet. Details: CHANGELOG.md.

**Nicht behandelt:** #41 (Bozena-Stick, wartet auf Rubens Entscheidung), #32 (WI-3-Plan wartet auf Freigabe), #29/#37/#39/#40/#42 unbearbeitet.

**Nächster Schritt:** Rubens Bestätigung, dass Komo-Zugriff in der Praxis (App/Google TV) funktioniert. Sonst: #41-Entscheidung oder #32-Freigabe abwarten.
