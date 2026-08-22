# Handover — xoro-epg-enricher (2026-08-22)

**#35 verifiziert:** Health-Check-Fix vom 07.08. funktioniert zuverlässig — Log-Auswertung (`mount-cifs.log`) zeigt 8 automatische Neustarts an den Boot-Tagen 08.-17.08., je innerhalb 2 Min. nach dem 08:00-Boot. Ruben merkt den morgendlichen Aussetzer seither vermutlich gar nicht mehr. Ein unerklärter Zusatzstart am 21.08. 20:40 Uhr (nicht Boot-bedingt) — nicht weiter untersucht, einmalig, selbstheilend abgefangen. Root Cause (Boot-Race) bleibt bestehen, Symptom ist gelöst. Kommentar auf #35 gepostet, Vorschlag zum Schließen als "won't-fix-root-cause" — **wartet auf Rubens Freigabe**.

**#33/#34:** Dokumentations-Lücke gefunden und geschlossen — Fixes waren seit 26.06. committed (`e1bcf98`, `d112728`, `d87187f`), aber nie auf den Issues kommentiert. Nachgetragen. **Warten seit 7 Wochen auf Freigabe zum Schließen.**

**#22:** unverändert, Upstream-Bug bei Jellyfin-Android-TV, kein eigener Fix möglich, weiter offen.

**#29:** PM-Plan (TVDb-v4-API-Spike) steht seit 25.06. unbearbeitet im letzten Kommentar — nicht angefasst diese Session.

**#32:** als eigene Projektphase ("Bestandsarchiv-Anreicherung") eingeordnet (PM-Kommentar 05.07.), #33/#34 hingen daran und sind jetzt erledigt — #32 selbst noch offen, größerer Scope, nicht ohne Rubens Entscheidung angefasst.

**Nebenbefund:** SSH-Alias `synology` fehlte in dieser Session in `~/.ssh/config` (nur `hetzner` vorhanden) — nachgetragen, funktioniert wieder.

Nächster sinnvoller Schritt: Ruben entscheiden lassen, ob #33/#34/#35 geschlossen werden, und ob #29 (TVDb-Spike) oder #32 (neue Projektphase) als nächstes angegangen werden soll.
