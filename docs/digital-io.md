# Digitalausgänge und Kanalstatus

Lokaler Entwicklungsstand, noch nicht veröffentlicht oder auf Home Assistant installiert.
Ausgehend von 100prznts Digitalausgangsfunktion wurde der Schreibpfad neu abgesichert.

## Bedienung

Jeder Port erhält eine HA-Schalterentität „Digitalausgang (Pin 4)“. Sie ist nur
im vom Master gemeldeten DO-Modus verfügbar. Die ID folgt dem Fork-Schema
`<Master-Seriennummer>_port_<Port>_pin4_do`; bestehende Messwert-IDs bleiben gleich.
Im Command Center erscheinen bei DO die Tasten „Ausgang EIN“ und „Ausgang AUS“.
Die Verfügbarkeit hängt vom gelesenen Hardwaremodus ab, nicht von einer gespeicherten
Profilzuordnung. Bei unbekanntem Ausgangswert bleibt der Zustand unbekannt;
ein expliziter EIN/AUS-Befehl ist bei bestätigtem DO-Modus weiterhin möglich.

Oberhalb des Geräteprofils lässt sich „Portmodus (Pin 4)“ auf DO, IO-LINK, DI
oder Disabled stellen. „Portmodus ändern …“ verlangt eine Bestätigung mit Master
und Port. Erst dann wird geschrieben und zurückgelesen. Ein DO-Moduswechsel
schreibt anschließend AUS und prüft Modus und Ausgang. Ein impulsfreier Übergang
ist durch diese getrennten API-Aufrufe nicht garantiert. Bei Teilfehlern den
aktuellen Zustand prüfen; die Integration wiederholt Schreibzugriffe nicht.
Profilzuordnungen werden nicht gelöscht. Das Profilfeld ist außerhalb IO-Link gesperrt.
Jeder Port hat außerdem einen Binärsensor „Digitaleingang (Pin 4)“ mit stabiler ID
`<Master-Seriennummer>_port_<Port>_pin4_di`. DO und DI sind nur im passenden Modus
verfügbar; bestehende Entitäten werden beim Moduswechsel wiederverwendet.

Neben der Portnummer stehen kompakte Farbfelder im Stil des X01/X02-Feldes:
`X04 | IO-Link | DI2`, `X04 | DI1 | DI2` oder `X04 | DO | DI2`.
Nur IO-Link ist wegen der Beschriftung breiter. Grün bedeutet verbunden/An,
Rot bedeutet nicht verbunden/Aus, Grau unbekannt/nicht erreichbar/deaktiviert.
Tooltips und zugängliche Beschriftungen ergänzen Pin und Zustand.
Nur DO ist anklickbar; während des Schreibens ist das Feld gesperrt.

DI2 (Pin 2) wird auch im IO-Link- und DO-Modus als eigene HA-Binärsensorentität
angeboten (`<Master-Seriennummer>_port_<Port>_pin2_di`). DI1 (Pin 4) ist nur im
DI-Modus verfügbar. Unbekannte Eingangsdaten werden nicht als AUS interpretiert.

Start, Reload und Polling senden keine Ausgangswerte. Nach Modusänderungen am Master
aktualisieren sich Anzeige und Verfügbarkeit beim nächsten Poll.

## Anzeigen je Port

| Anzeige | Bedeutung |
|---|---|
| DI2 gelb / EIN | Pin 2 meldet aktiv |
| DI2 grau / AUS | Pin 2 meldet inaktiv |
| Pin 4 gelb / EIN bzw. grau / AUS | DI-Modus: Eingang; DO-Modus: gelesener Ausgangswert |
| Pin 4 grün / IO-Link verbunden | IO-Link-Modus und bestehende Verbindung |
| Pin 4 deaktiviert | Hardwaremodus 0 |
| Unbekannt oder nicht erreichbar | Fehlende/ungültige Daten oder verlorene Verbindung |

Dies sind **abgeleitete Kanalzustände**, kein direkter Abruf der physischen LED-Lampen.
Blinkfrequenzen, PREOPERATE und rote Fehler-LED-Codes werden nicht nachgebildet.
Der zurückgelesene DO-Wert bestätigt das Prozessdatenregister; er ist keine Messung
der tatsächlichen Ausgangsspannung oder der Reaktion eines angeschlossenen Aktors.

## Schreibprüfung

1. Gültigen Port, booleschen Zielwert und aktiven Coordinator prüfen.
2. Gemeinsame Portsperre mit Parametersicherung und Restore belegen.
3. Master-Modell und Seriennummer frisch lesen und vergleichen.
4. Tatsächlichen Portmodus unmittelbar vor dem Schreiben lesen: nur 2 / DO zulassen.
5. Genau einmal ein Byte `00` oder `01` schreiben.
6. Modus und Ausgang erneut lesen; nur übereinstimmende Werte bestätigen.
7. Bei Fehler/Timeout den zwischengespeicherten Ausgang unbekannt setzen,
   Sperre auch bei Abbruch freigeben; keine automatische Wiederholung.

Panelzugriffe benötigen Administratorrechte. HA-Schalter verwenden die regulären
Home-Assistant-Berechtigungen. Beide Wege verwenden dieselbe serverseitige Prüfung.
Eine Sperre innerhalb dieser Integration kann keine fremde Software am Master sperren:
Ein externer Moduswechsel zwischen Prüfung und Schreiben bleibt technisch möglich,
da die API keinen atomaren Vergleich-und-Schreibvorgang anbietet. Master daher nicht
gleichzeitig von mehreren Konfigurationsprogrammen umstellen. Fail-safe-Einstellungen
bei Verbindungsverlust bleiben Sache des Masters und werden hier nicht verändert.

## Quellen und Verifikation

- ifm-Originalbetriebsanleitung AL1350, Kapitel 7.2.3 und 9.2.11,
  [PDF-Spiegel der Herstelleranleitung](https://www.quicktimeonline.com/assets/images/pdf/IFM%20Electronic/operating-instruction-AL1350.pdf):
  Pin 2 unter `/iolinkmaster/port[n]/pin2in`, Prozessdaten unter
  `/iolinkmaster/port[n]/iolinkdevice/pdin` bzw. `pdout`, DO-Ausgang als ein Hex-Byte.
- [Offizielles AL1350-Datenblatt](https://media.ifm.com/dam/aaf256ab-5a44-4254-9ac9-f84f55bfc80b/Original/AL1350-00_EN-GB.pdf).

Automatisierte Tests prüfen Setup/Reload mit simuliertem HA-Rand, API-Payloads,
frische Identität/Modi, Portsperren, Rücklesefehler und teilweise ausgeführte
Moduswechsel. JavaScript-Prüfungen testen Statusfarben und konkurrierende DO-Klicks.

Hardwaretest am 16.10.2026: Garage AL1350, Firmware AL1x5x_cn_it_v3.1.99,
freier Port 4, mit den tatsächlichen Integrationsfunktionen (ohne HA-Installation):

| Schritt | Rücklesewert |
|---|---|
| DI | Modus 1, pdin 00 |
| DO mit AUS-Initialisierung | Modus 2, pdout 00 |
| DO EIN | Modus 2, pdout 01 |
| DO AUS | Modus 2, pdout 00 |
| Disabled | Modus 0 |
| Wiederherstellung | Modus 3 (IO-Link), alle Portmodi wie vor dem Test |

Keine Last angeschlossen: Ausgangsspannung und reale Schützreaktion sind nicht
geprüft. DI-High, AL1352-Hardware, vollständige HA-Laufzeit und visuelle Browserprüfung
stehen aus. Keine Installation auf dem produktiven Home Assistant, keine Veröffentlichung.


## Automatische Entitätsverwaltung

DO ist nur im Modus DO aktiv, DI1 nur im Modus DI. IO-Link-Prozesswerte
und die IO-Link-Verbindungsentität sind nur im IO-Link-Modus aktiv.
Die übrigen Entitäten werden deaktiviert, nicht gelöscht. DI2 bleibt unabhängig
vom Pin-4-Modus aktiv. Entity-IDs und Einstellungen bleiben bestehen.
Nur Deaktivierungen dieser Modusautomatik werden automatisch rückgängig gemacht;
manuelle, Geräte- und Config-Entry-Deaktivierungen haben Vorrang.
Bei unbekanntem Modus oder Verbindungsfehler erfolgt kein Registry-Umbau.
Nach Wiederaktivierung lädt HA den Config Entry verzögert neu (etwa 30 Sekunden).
Während dieser Zeit kann die Entität noch nicht verfügbar sein.

Geprüft mit Registry-Testdoubles: Moduswechsel, wiederholte Abfragen,
persistierte Einträge nach Reload, manuelle Deaktivierung und ID-Erhalt.
Verwendete Registry-APIs sind in HA 2025.7 vorhanden. Ein echter HA-Lauf
für diese Erweiterung wurde noch nicht durchgeführt.
