# Prüfung und teilweise Übernahme von 100prznt

Stand: 2026-10-01. Diese Änderungen sind lokal und unveröffentlicht.

## Geprüfter Stand

- Quelle: [100prznt/Fork](https://github.com/100prznt/hacs-ifm-io-link-master-al13xx-iot).
- Fester Prüfstand: `54ae9723230292917e482c21717a3a9427f4d2b8`, Manifest 0.8.2.
- Vergleich gegen unseren Commit `15d7ee6580e1c5904530cedd56d13d0995bc6b70`:
  37 geänderte Dateien. Die lokale, noch nicht veröffentlichte HA-Registry-Korrektur
  ist zusätzlich erhalten geblieben.
- Die 249 vorhandenen Fork-Tests bestehen. Vier zusätzliche Prüfungen von
  Sicherheitsanforderungen schlagen fehl. Erfolgreiche Bestandstests sind damit
  kein Freigabenachweis für sämtliche neuen Funktionen.

## Lokal übernommen

| Teil | Herkunft und Anpassung |
|---|---|
| Erste Metadatenabfrage nach Host-Neustart | `100prznt/dff25a6`: Zeitstempel beginnt mit `None`, damit eine kleine monotone Uhr die Erstabfrage nicht verhindert. Invalidierung nach Restore ebenfalls auf `None` umgestellt; Regressionstest ergänzt. |
| Manifest-Version für Oberfläche | Versionshelfer und Anzeige aus dem Fork; angepasst, damit nicht bei jeder WebSocket-Abfrage synchron eine Datei gelesen wird. |
| Browser-Cache für JS/CSS | Manifest-Version für Panel-JavaScript und Stylesheet verwenden. Versionsausgabe wird im HTML weiterhin escaped. Kein Versionssprung auf die Fork-Version. |
| AL1352-Verbindungslinien | `100prznt/ad82999`: getrennte Knickpositionen für innere und äußere Portreihen. Kein Einfluss auf Gerätekommunikation. |
| SV4200-Prozessdaten | Aus `ifm_sv4200_0.json` abgeleitet, Skalierung korrigiert; Gerätekennung 310/484, vier Byte, Durchfluss, Temperatur und zwei Schaltzustände. Keine unbestätigten Herstellerparameter oder neuen Schreibfunktionen aktiviert. |

Die übernommenen Ideen und Profilbestandteile stammen von **100prznt**; die
selektive Übernahme ist kein vollständiger Merge seines Branches. Die genannten
Commits bleiben im Quellrepository nachvollziehbar. Bestehende Profile und IDs
werden nicht umbenannt; das neue mitgelieferte SV4200-Teilprofil verwendet `sv4200`.
Bereits importierte eigene Profile bleiben separat und werden nicht automatisch
ersetzt oder Ports neu zugewiesen.

## Befunde, die eine vollständige Übernahme verhindern

1. **Parameter-Schreibzugriff** (`entity.py:163–171` im Fork): kein erneuter
   Abgleich der Gerätekennung vor dem Schreiben, keine gemeinsame Portsperre mit
   Restore/Moduswechsel. Rücklesen aktualisiert die Anzeige, vergleicht aber den
   Istwert nicht mit dem geschriebenen Sollwert. Ein Lesefehler wird intern
   abgefangen. Ergebnis: Ein Schreibaufruf kann trotz fehlender Bestätigung als
   erfolgreich zurückkehren. Nicht übernommen.
2. **Digitalausgang** (`switch.py:_write`): schreibt `pdout` ohne frische
   Modusabfrage. Verfügbarkeit folgt der gespeicherten Zuordnung; unbekannte
   Ausgangsdaten werden als AUS interpretiert. Nicht übernommen.
3. **Moduswechsel** (`port_mode.py:execute_mode_change`): prüft vor dem Schreiben
   nur zwischengespeicherte Daten. Reproduktion: Vorschau für 3→2, tatsächlichen
   Modus auf 1 ändern, bestätigen: es wird trotzdem 2 geschrieben. Eine teilweise
   erfolgreiche Umschaltung mit fehlgeschlagener AUS-Initialisierung ist ebenfalls
   nicht abschließend behandelt. Nicht übernommen.
4. **Zahlenkodierung** (`decoder.py:encode_parameter`): ein `invalid_values`-
   Sonderwert wird akzeptiert; ein benutzerdefinierter Zahlenparameter an Index 2
   kann Systemkommandos übertragen. Beide Fälle separat reproduziert. Weitere
   offene Punkte sind Skalierung null und das Zusammenziehen getrennter
   IODD-Wertebereiche zu einem durchgehenden Minimum/Maximum. Nicht übernommen.
5. **Neue Kommandos** (`websocket.py:send_command`, `panel.js`): die frische
   Vendor-/Device-ID-Prüfung ist eine sinnvolle Verbesserung. Es fehlen aber
   gemeinsame serverseitige Schreibkoordination und eine Bestätigung für
   destruktive Aktionen wie Werksreset. Ein Busy-Set im Browser schützt nicht
   vor parallelen Clients oder Restore. Nicht übernommen.
6. **Fehlende Zustände**: Bei fehlenden DI-Daten ergibt der Coordinator `False`
   statt unbekannt (reproduziert). Das Panel zeigt bei fehlendem Masterstatus
   „Status ok“ (Codeprüfung). Masterdiagnose und DI-Anzeige deshalb nicht als
   Gesamtpaket übernommen.
7. **Release-Workflow**: veröffentlicht neue Manifest-Versionen nach einem
   erfolgreichen Tests-Workflow automatisch. Kein Bestandteil dieser Übernahme;
   keine Veröffentlichung und keine CI-Änderung durchgeführt.
8. **HA-API**: Der Fork enthält weiterhin `via_device`. Die zuvor lokal
   implementierte Registry-ID-Lösung wurde nicht durch Fork-Code ersetzt.

## Geräteprofile

| Profil | Ergebnis |
|---|---|
| SV4200 | Fehler bestätigt: Durchflussfaktor fehlt im Fork. Laut Hersteller Rohwert × 0,1 l/min. Korrigiertes Prozessdaten-Teilprofil übernommen. Drei Referenzvektoren einschließlich negativer Temperatur und vier Fehlerwertkombinationen geprüft. Keine echte Sensorprüfung. |
| KQ1000 | Geräteprofil und sechs Kommandos vorhanden, darunter Werksreset und Tankabgleich. Neue Schreibfunktion nicht freigegeben. Prozessdaten inklusive Exponent müssen noch vollständig abgeglichen werden; kein Profil aktiviert. |
| LDH292 | Feste Temperatur-/Feuchteskalierung trotz Hinweisen auf unvollständigen Import; `conditions` leer. Vollständiger Abgleich mit passender IODD und Gerätekonfiguration fehlt. Nicht als sicher falsch bezeichnet, aber nicht freigegeben. |
| PG1406 | Druck fest skaliert, Exponent separat ausgelesen; seine Bedeutung für die feste Skalierung muss bestätigt werden. Nicht freigegeben. |
| SM9000 | Feste Einheiten trotz Importhinweisen auf konfigurationsabhängige Einheiten, keine Bedingungen. Einheiteneinstellungen und Zählersemantik noch zu verifizieren. Nicht freigegeben. |

Alle neuen Fork-Profile verwenden `custom_...`-IDs, obwohl sie mitgeliefert werden.
Unsere Oberfläche behandelt dieses Präfix als benutzereigen. Eine pauschale
Übernahme oder Umbenennung kann daher auch Profilverwaltung und bestehende
Zuordnungen betreffen. Das isolierte SV4200-Profil umgeht dies ohne Migration
vorhandener Nutzerprofile. Die weiteren vier Profile sind nicht automatisch
installiert oder im produktiven Profilkatalog vorhanden.

Herstellerquelle für SV4200:
[ifm-0001E4-20231005-IODD1.1, Seiten 2–4](https://media.ifm.com/dam/f2c53e2b-34ef-4c85-a004-5571aa597de6/Original/ifm-0001E4-20231005-IODD11-en.pdf).
Sie bestätigt Gerätekennung, Big-Endian-Format, 16-Bit-Durchfluss mit Faktor 0,1,
14-Bit-Temperatur mit Faktor 0,1, OUT1/OUT2 und die geprüften Sonderwerte.
Das im Quellprofil enthaltene Herstellerbild bleibt unter den Rechten des Herstellers.

## Reproduzierbarkeit und Grenzen

Die vier zusätzlichen Prüfungen liegen in
[`reviews/100prznt_safety_checks.py`](reviews/100prznt_safety_checks.py).
Für die Reproduktion ausschließlich in einer separaten Kopie des oben genannten
Fork-Commits nach `tests/test_review_safety.py` kopieren und dort
`python -m pytest tests/test_review_safety.py -q` ausführen. Erwartetes Ergebnis
des unveränderten Prüfstands: vier echte Fehlschläge, kein `xfail`.
Diese Prüfungen sind kein Bestandteil unserer normalen Testsuite und schreiben
nicht auf reale Geräte.

Lokaler Übernahmestand: **173 Tests bestanden**, Ruff erfolgreich, Python- und
JavaScript-Syntax geprüft. Darin enthalten sind die acht Registry-Lifecycle-Tests
der vorigen Änderung und die neue Prüfung sämtlicher mitgelieferter Profile.
Keine vollständige HA-Laufzeitprüfung, kein visueller Browsertest der neuen
Linienführung und keine Referenzmessungen an den fünf neuen Sensormodellen.
Es wurden weder Gerätekommandos gesendet noch Geräteparameter verändert.
Keine Veröffentlichung, kein Push, keine Installation auf DEV oder Produktion.

Eine spätere vollständige Übernahme erfordert zuerst die genannten Korrekturen,
danach HA-Lifecycle-Tests und gezielte Referenzmessungen. Der aktuelle Stand
gibt ausdrücklich nur die oben aufgeführten lokalen Teiländerungen frei.
