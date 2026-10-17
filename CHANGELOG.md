# Changelog

## v0.1.6 – Anschlusshilfe für DI und DO (2026-10-17)

Reguläres Release. Die DO-Anschlusshilfe wurde in einer laufenden HA-2026.9.4-Installation am AL1352 sichtbar geprüft und vom Nutzer bestätigt. Die DI-Hilfe wurde lokal einschließlich Mobilansicht getestet und ebenfalls installiert; kein produktiver Port wurde dafür umgeschaltet.

- Fragezeichen an DI-/DO-Portkarten von AL1350/AL1352 öffnet ein modales Anschlussbeispiel mit Grafik und Anschlusstabelle. IO-Link- und deaktivierte Ports erhalten keine Schütz-Anschlusshilfe.
- DO: Schneider LC1D18BD mit Spulenanschlüssen und separatem DI2-Hilfskontakt. DI: zwei unabhängige potentialfreie Kontakte mit gemeinsamer L+-Abzweigung. Kabelbeispiel Phoenix Contact 1504615.
- Fachliche Vorbehalte bleiben sichtbar: Farb-Pin-Zuordnung durch Durchgang prüfen; elektrische Eignung des DO-Beispiels noch offen. Die Hilfe sendet keine Hardwarebefehle.
- Native Dialogbedienung mit Escape, Fokus-Rückgabe und scrollbar lesbarer Grafik auf kleinen Displays.
- Neue Ladeadresse bei der Panel-Registrierung verhindert, dass unter der unveränderten Integrationsversion noch die vorherige JavaScript-Datei verwendet wird. Die Registrierung wird beim HA-Core-Start erneuert.

## v0.1.5 – Masteraustausch, AL1352 und eigene digitale Geräte (2026-10-16)

Reguläres Release. Der AL1350→AL1352-Austausch wurde an realer Hardware unter HA 2026.9.4 abgeschlossen und nachgeprüft. Alle bisherigen 69 Entitätsidentitäten und 10 Geräteidentitäten blieben erhalten; zusätzliche Ports erweiterten den Bestand auf 85 Entitäten und 14 Geräte.

### Eigene digitale Geräte

- Profil-IDs neuer Geräte werden automatisch aus dem Gerätenamen erzeugt, einschließlich Umlauten und eindeutigen Nummern bei gleichen Namen. Gespeicherte und manuell festgelegte IDs bleiben beim Umbenennen erhalten.
- Gerätebibliothek um „Digitales Gerät (DI / DO)“ mit Name, Hersteller, Modell, Beschreibung und Bild-Upload erweitert; keine JSON- oder IODD-Eingabe nötig.
- Separate digitale Gerätezuordnung für DI-/DO-Ports. Bestehende IO-Link-Profile bleiben bei Moduswechseln gespeichert; Schalt-/Eingangszustände kommen unverändert vom Master.
- Vorhandene digitale Entitäts- und Geräte-IDs bleiben erhalten. Zugewiesene digitale Geräte können bearbeitet, aber nicht versehentlich aus der Bibliothek gelöscht werden.

### Masteraustausch

- Nachprüfung: durchgängiger Hintergrundauftrag nach einer Bestätigung, begrenztes Wiederverbinden, Rücksicherung und abschließende HA-Verbindungsprüfung; Browser kann geschlossen werden.
- Wiederanlauf mit gespeichertem Neustartzustand, kein Überspringen der Rücksicherung, Schutz vor konkurrierender Übernahme und Verlust der ursprünglichen Sicherung.
- 423 Python-Tests plus Frontend-Ablauftests; Austauschdialog bleibt bei laufenden Aktualisierungen erhalten.

- Austauschassistent unter „Master verwalten“: AL1350 durch AL1350/AL1352 ersetzen, ohne vorhandene Geräte-/Entitäts-IDs, Profilzuordnungen oder Parametersicherungen neu anzulegen.
- Netzwerksuche, Sicherung lesbarer Masterwerte, statische IP-Übernahme mit dokumentiertem Neustartverhalten und Identitätsprüfung an der Ziel-IP.
- Geprüfte Rücksicherung von Portmodi, Application Tag und lesbaren LR-Agent-Einstellungen; DO-Ports zunächst deaktiviert. Keine automatische Sensorparameter-Wiederherstellung.
- Persistentes Fortschrittsprotokoll, keine automatische Wiederholung unklarer Schreibzugriffe; Verwaltung auch bei offline befindlichem bisherigen Master.
- Umfang, Ablauf und Verifikationsgrenzen: [Masteraustausch](docs/master-replacement.md). Bei der realen Übernahme bestätigte Antwort 233 das Neuladen der Netzwerkschnittstelle; der separate Reboot-Pfad und Wiederanlauf nach Fehlern sind automatisiert simuliert. Kein elektrischer Lasttest und kein DI-High-Test.
- Deutsche und englische README aktualisiert, mit neuen Screenshots des AL1352, digitaler Portzuordnung, Gerätebibliothek und Masterverwaltung.

## v0.1.4 – Portmodi, digitale Ein-/Ausgänge und HA-Kompatibilität

- Portmodus direkt im Command Center wählen: DO, IO-Link, DI oder Disabled; mit Bestätigung und Rücklesen vom Master. Beschriftung: „Portmodus“ / „Portmodus aktivieren“.
- DO als HA-Schalter und anklickbare Anzeige mit Master-Rückmeldung; DI1 an Pin 4 und DI2 an Pin 2 als Binärsensoren.
- Automatische Deaktivierung unpassender Entitäten je Portmodus, Wiederaktivierung mit denselben IDs. Manuelle Deaktivierungen bleiben erhalten; DI2 bleibt unabhängig vom Pin-4-Modus aktiv. HA kann zur Wiederaktivierung etwa 30 Sekunden benötigen.
- Aktuelle HA-Gerätezuordnung über via_device_id; Kompatibilität mit HA ab 2025.7 bleibt erhalten.
- Kompakte Statusfelder, einheitliche Pin-/Typ-/Status-Texte, gleich große Portkarten und feste Messwertspalten.
- AL1352-Verbindungslinien verbessert; geprüftes SV4200-Prozessdatenprofil ergänzt. Teilübernahmen aus dem Beitrag von 100prznt sind im Prüfbericht dokumentiert.

### Prüfung und Grenzen

297 Python-Tests; JavaScript-Status-/Klicktests, Ruff und Syntaxprüfungen.
AL1350 Port 4 wurde ohne Last mit DI, DO (AUS/AN/AUS), Disabled und IO-Link geprüft. Das bisherige Frontend und die Digitalfunktionen wurden auf HA 2026.9.4 geprüft.
Die neue automatische Entitätsverwaltung ist mit Registry-Testdoubles geprüft, noch nicht in einem laufenden HA. Kein AL1352-Hardwaretest, kein elektrischer Lasttest und kein DI-High-Test.

Vorabversion: Vor dem Update ein HA-Backup erstellen. Dieses Release installiert sich nicht automatisch auf deinem HA.

## Entwicklungsprotokoll

## Unveröffentlicht – 2026-10-16

- Kanalbeschriftungen und Tooltips vereinheitlicht: Pin, Typ und Status; im Kanalstatus steht der Status separat ohne doppelte Pin-/DI-Angabe.

### Kompakte Portanzeigen und zweiter Eingang


- Farbfelder neben der Portnummer: IO-Link/DI1/DO und DI2, ohne zusätzliche
  An/Aus-Texte. Gleiche Größe wie das Portfeld, IO-Link entsprechend breiter.
  Grün = verbunden/aktiv, Rot = nicht verbunden/inaktiv, Grau = unbekannt/offline.
  Tooltips nennen Pin und Zustand. Nur DO ist schaltbar.
- Separater DI2-Binärsensor an Pin 2, unabhängig vom Pin-4-Modus. DI1 bleibt an
  Pin 4 im DI-Modus; bestehende IDs bleiben erhalten. Setup/Reload erzeugt keine Duplikate.
- 281 Python-Tests sowie JavaScript-Status-/Klickprüfungen erfolgreich; Ruff und
  JS-Syntax erfolgreich. Kein neuer Hardware-High-Pegel-Test, keine HA-Installation.

### Portmodus und DO-Rückmeldung

- Auswahl „Portmodus (Pin 4)“ über dem Geräteprofil: DO, IO-LINK, DI, Disabled.
  Explizite Bestätigung, frische Master-/Modusprüfung und Rücklesekontrolle.
  Vorhandene Profilzuordnungen und Entity-IDs bleiben erhalten.
- Anklickbare DO-Anzeige neben X01…X08: Rot/Aus, Grün/An; während einer
  Anfrage gesperrt. DI nur lesend, IO-Link gelb, unbekannt/offline grau.
- DI-Binärsensor mit stabiler ID; DO-Schalter verwendet den gelesenen Masterwert.
  Beide Entitäten bleiben bei anderen Modi nicht verfügbar und werden wiederverwendet.
- DO-Moduswechsel schreibt anschließend AUS und prüft den Wert. Teilfehler werden
  nicht als Erfolg ausgegeben. Kein Schreiben beim Start, Polling oder Reload.
- Garage AL1350, freier Port 4, real getestet: DI=00; DO=00 â†’ 01 â†’ 00;
  Disabled=0; ursprünglicher IO-Link-Modus=3 wiederhergestellt. Keine Schreibzugriffe
  auf andere Ports. Keine HA-Installation und keine Veröffentlichung.
- Prüfung: 251 Python-Tests erfolgreich; JavaScript-Status-/Klickprüfungen, Ruff,
  Python-Kompilierung und JS-Syntax erfolgreich.
- Grenzen: keine elektrische Last/Spannungsmessung, kein DI-High-Test und kein
  AL1352-Hardwaretest; keine vollständige HA-Laufzeit-/Browserprüfung.

## Vorheriger lokaler Stand – 2026-10-01

### Digitalausgänge und Kanalstatus

- Pin-4-Digitalausgänge als HA-Schalter und als EIN/AUS-Tasten im Command Center.
  Ausschließlich für bereits am Master auf DO konfigurierte Ports. Die Integration
  ändert keinen Portmodus und sendet beim Start/Reload keine Ausgangswerte.
- Frische Master-Identitäts- und DO-Modusprüfung, gemeinsame Sperre mit Sicherung/
  Restore, anschließende Prüfung von Modus und Ausgang durch Rücklesen.
  Keine automatischen Schreibwiederholungen; unbekannte Werte werden nicht als AUS ausgegeben.
- Zwei Statusanzeigen pro Port für Pin 2 und Pin 4/IO-Link, aus gemeldeten Daten
  abgeleitet. Keine simulierten Hardware-Blinkcodes. Nichterreichbarkeit und fehlende
  Daten werden kenntlich gemacht. Der Modus wird bei jedem Poll erneut abgefragt.
- 215 Python-Tests und acht JavaScript-Prüfungen der Anzeige erfolgreich;
  Ruff und Syntaxprüfungen erfolgreich. Keine Hardware-Schaltung und keine
  HA-Installation vorgenommen. Grenzen und Bedienung: [Digital-I/O](docs/digital-io.md).

### Geprüfte Teilübernahme von 100prznt

- Metadaten werden auch direkt nach einem Host-Neustart zuverlässig abgefragt;
  Invalidierung nach Restore angepasst.
- Manifest-Version für Panelanzeige und JS-/CSS-Cache-Aktualisierung verwendet.
- Getrennte Verbindungslinien für innere und äußere AL1352-Portreihen.
- SV4200-Prozessdatenprofil mit gegenüber dem Fork korrigiertem Faktor 0,1 l/min,
  ohne unbestätigte Herstellerparameter oder neue Schreibfunktionen.
- 173 Tests erfolgreich. Vier zusätzliche Sicherheitsprüfungen scheitern im
  unveränderten Fork; die betroffenen Funktionen wurden nicht übernommen.
- Quelle, Urheberschaft, offene Geräteprüfungen und Grenzen stehen im
  [Prüfbericht](docs/review-100prznt.md). Keine automatische Veröffentlichung.

### Home-Assistant-Gerätezuordnung

- Die gemeinsame Basisklasse von `sensor.py` und `binary_sensor.py` verwendet
  auf aktuellen Home-Assistant-Versionen `DeviceInfo.via_device_id` statt des
  veralteten `via_device`. Damit entfällt die entsprechende API-Warnung.
- Die ID kommt direkt vom Rückgabewert der Master-Registrierung mit dem
  jeweiligen `config_entry_id`. Der Master wird vor dem Start der
  Sensorplattformen registriert; beim Reload wird die ID erneut ermittelt.
  Es wird weder das bisherige Identifier-Tupel als ID verwendet noch global
  nach einem möglicherweise zu einem anderen Config Entry gehörenden Gerät gesucht.
- Bestehende Geräte-Identifier und Entity-Unique-IDs bleiben unverändert.
  Keine Datenmigration, keine neue Einrichtung und keine Änderung an
  Portzuweisungen, Einstellungen oder Sicherungsformaten erforderlich.
- Die Mindestversion HA 2025.7 bleibt erhalten: Nur wenn `DeviceInfo` das neue
  Feld noch nicht unterstützt, wird die dort gültige Identifier-Variante benutzt.
  Auf der aktuellen API wird kein `via_device` mehr übergeben.

### Prüfung und Grenzen

- Offiziellen Quellcode von HA 2025.7.0 und 2026.9.4 verglichen. In 2025.7
  akzeptiert `async_get_or_create` noch kein `via_device_id`; das gleichnamige
  interne Registry-Feld allein bedeutet keine Unterstützung in `DeviceInfo`.
- Acht neue Regressionstests führen die tatsächlichen Integrations-Setup-,
  Sensor- und Binary-Sensor-Setupfunktionen mit simulierten HA-Schnittstellen aus:
  Erstinstallation, vorhandene Geräte mit Benutzeranpassungen, Unload/Reload,
  Registry-IDs pro Config Entry und Ablehnung einer falschen Master-Seriennummer.
  Beide API-Varianten werden geprüft. Der aktuelle Testvertrag lehnt den
  veralteten Parameter ausdrücklich ab; der alte lehnt das neue Feld ab.
- Gesamte lokale Testsuite: 158 Tests erfolgreich; Ruff und Python-Kompilierung
  erfolgreich. Keine vollständigen HA-Laufzeit- oder echten Registry-Migrationstests.
  Die Erhaltung der Zuordnungen ist mit simulierten Registries getestet;
  ein Upgrade-Test auf einer isolierten HA-Instanz bleibt ergänzend sinnvoll.
- Keine Veröffentlichung, kein Versionswechsel und keine Installation oder
  Änderung auf einer produktiven oder DEV-Home-Assistant-Instanz.

Quellen:

- [Offizielle HA-API-Änderungen und Ablösung bis 2027.8](https://developers.home-assistant.io/blog/2026/08/24/device-registry-follow-up-changes/)
- [Device Registry in HA 2026.9.4](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/helpers/device_registry.py)
- [Device Registry in HA 2025.7.0](https://github.com/home-assistant/core/blob/2025.7.0/homeassistant/helpers/device_registry.py)
