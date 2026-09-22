# ifm IO-Link Command Center for Home Assistant

**Deutsch** | [English](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/blob/main/README.en.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/custom_components/ifm_iolink/brand/icon.png" alt="ifm IO-Link Projektlogo" width="100">
</p>

<p align="center"><strong>Industriesensorik für dein Smart Home.<br>Pool, Heizung und Druckluft – lokal verbunden und gemeinsam im Blick.</strong></p>

[![Version](https://img.shields.io/badge/version-0.8.2-blue)](https://github.com/100prznt/hacs-ifm-io-link-master-al13xx-iot/blob/main/custom_components/ifm_iolink/manifest.json)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5?logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Repository-41BDF5)](https://www.hacs.xyz/)
[![Tests](https://github.com/100prznt/hacs-ifm-io-link-master-al13xx-iot/actions/workflows/tests.yml/badge.svg)](https://github.com/100prznt/hacs-ifm-io-link-master-al13xx-iot/actions/workflows/tests.yml)
[![Local](https://img.shields.io/badge/Verbindung-Lokal-success)](#funktionen)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/blob/main/LICENSE)
[![Unterstützen via PayPal](https://img.shields.io/badge/Support%20via-PayPal-0070BA?logo=paypal&logoColor=white)](https://paypal.me/JensSaffrich)

> 🔀 **Dies ist ein Fork.** Dieses Repository ist ein Fork von [JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot), weiterentwickelt von [100prznt](https://github.com/100prznt). Er enthält zusätzliche, hier entstandene Änderungen gegenüber dem Original – siehe [Änderungen in diesem Fork](#änderungen-in-diesem-fork).

Das **ifm IO-Link Command Center** verbindet die IO-Link-Master **AL1350 und AL1352 mit IoT Core** direkt mit Home Assistant. Druck, Durchfluss, Temperatur und Gerätezustände werden zu nutzbaren Entitäten für Dashboards, Verläufe und eigene Automationen – ohne Cloud, MQTT-Broker oder Node-RED als Zwischenstation.

Im grafischen Command Center steht der Master in der Mitte. Seine Ports führen zu den angeschlossenen Geräten mit Bild, Bezeichnung, Standort, Verwendungszweck und Live-Messwerten. Eine gemeinsame Gerätebibliothek, IODD-Import und Parametersicherungen machen aus einzelnen Sensoren eine übersichtliche Anlage.

**Ein Projekt von [JS-DE-Tech](https://github.com/JS-DE-Tech), entstanden aus einer realen Pool-, Heizungs- und Druckluftinstallation.**

<p align="center">
  <img src="docs/images/screenshots/portuebersicht_v0_7.png" alt="Command Center: AL1352 mit verbundenen Sensoren, Live-Messwerten, Portzuweisung und DIO-Anzeige" width="1100">
</p>

<p align="center"><a href="#funktionen">Funktionen</a> · <a href="#mein-praxisprojekt">Praxisprojekt</a> · <a href="#installation">Installation</a> · <a href="#parametersicherung--sensortausch">Parametersicherung</a> · <a href="#eigene-ger%C3%A4te--iodd-import">Eigene Geräte</a></p>


## Änderungen in diesem Fork

Gegenüber dem Original-Projekt von JS-DE-Tech ergänzt dieser Fork bisher:

- **Parameter als Home-Assistant-Entity (ab 0.2.0):** Herstellerparameter lassen sich in der Parameterliste je Port gezielt auswählen und als eigene Entity anlegen – als `sensor` (nur lesend) oder, bei schreibbaren Ganzzahlparametern, als `number` (freier Wertebereich) oder `select` (feste Werteliste, z. B. Prozentstufen), jeweils auch aus Home Assistant heraus setzbar. Alle drei werden unabhängig vom schnellen Prozessdaten-Poll gelesen: beim Hinzufügen, nach jeder Änderung und stündlich. Details unter [Parameter als Home-Assistant-Entity](docs/device-profiles.md#parameter-als-home-assistant-entity).
- **Master-Diagnose als Entity (ab 0.3.0):** Versorgungsspannung, Leistungsaufnahme (aus Spannung × Strom berechnet, da der Master selbst keinen Leistungswert liefert), Temperatur und Supervision-Status des Masters (AL1350/AL1352 selbst, nicht der angeschlossenen Sensoren) stehen als eigene `sensor`- bzw. `binary_sensor`-Entität zur Verfügung und werden zusätzlich als Kennzahl auf der Portübersicht angezeigt.
- **Digitaleingang Pin 2 als Entity (ab 0.4.0):** Pin 2 jedes IO-Link-Ports ist hardwareseitig immer ein digitaler Eingang, unabhängig vom Portmodus oder einem zugewiesenen Geräteprofil. Steht ab sofort als eigene `binary_sensor`-Entität je Port zur Verfügung und wird zusätzlich im Command Center angezeigt.
- **Portmodus-Umschaltung für Pin 4 (ab 0.5.0):** Pin 4 (C/Q) jedes Ports lässt sich im Command Center zwischen IO-Link-Kommunikation und Digitalausgang umschalten – mit geprüfter Vorschau und Bestätigung, analog zur Parameter-Wiederherstellung, da ein Wechsel einen ggf. angeschlossenen IO-Link-Sensor vom Port trennt. Ein Port im DO-Modus bekommt zusätzlich eine eigene `switch`-Entität für den reinen Ausgangszustand (an/aus) – automatisierbar wie jede andere Home-Assistant-Entity.
- **Versionsanzeige (ab 0.6.0):** Der Footer der Portübersicht zeigt die installierte Version. Für Update-Benachrichtigungen selbst ist bewusst kein eigener Mechanismus eingebaut – das übernimmt HACS bereits über seine eigene `update`-Entity (sichtbar unter Einstellungen → Geräte & Dienste bzw. der Updates-Übersicht), sobald für dieses Repository Releases gepflegt werden.
- **Pin-2/Pin-4-Status direkt auf der Portkarte (ab 0.6.1):** Neben dem Steckernamen (X01, X02, …) zeigt ein kleines Badge live den Zustand des Digitaleingangs (Pin 2); ist ein Port als Digitalausgang konfiguriert, kommt ein zweites Badge für dessen Schaltzustand dazu, und die Kartenmitte zeigt statt „Gerät auswählen“ direkt „Digitalausgang (Pin 4) · 24 V, max. 300 mA“.
- **Pin 4 auch als Digitaleingang, volle Modusauswahl (ab 0.7.0):** Pin 4 (C/Q) lässt sich jetzt zwischen IO-Link, Digitalausgang, Digitaleingang und Deaktiviert umschalten (vorher nur IO-Link/Digitalausgang) – über eine echte Auswahl statt eines einzelnen Umschalt-Buttons, weiterhin mit Vorschau und Bestätigung. Im Digitaleingang-Modus bekommt Pin 4 eine eigene `binary_sensor`-Entity, und die Portkarte zeigt für alle drei Nicht-IO-Link-Modi eine passende Kurzbeschreibung samt Badges (`DI2`/`DI4`/`DO`).
- **Herstellerspezifische Kommandos (ab 0.8.0):** Geräteprofile können jetzt eigene, nicht in der IODD beschriebene Schreibkommandos definieren – fester Index und Ganzzahlwert, z. B. um eine Kalibrierung zu starten oder einen Werksreset auszulösen. Im Command Center erscheinen sie unter **Kommandos anzeigen** direkt neben der Parameterliste; ein Klick sendet den festen Wert sofort. Vor dem Senden wird die Gerätekennung frisch gegen das Profil geprüft, damit ein zwischenzeitlich getauschter Sensor nicht versehentlich denselben Befehl erhält. Details unter [Profilformat und Beispiele](docs/device-profiles.md).

## Funktionen

| Funktion | Dein Nutzen |
|---|---|
| **Direkte lokale Verbindung** | Der IoT Core liefert Prozessdaten direkt an Home Assistant. Standardmäßig alle zwei Sekunden, je Master einstellbar. |
| **Master finden und einrichten** | DHCP-Erkennung, Suche in einem angegebenen privaten IPv4-Netz oder manuelle IoT-Adresse. Modell und Seriennummer werden geprüft. |
| **Grafische Portübersicht** | Masterabbildung, Verbindungslinien, Gerätekarten und aktuelle Werte in einem eigenen HA-Seitenleisteneintrag **ifm IO-Link**. |
| **Mehrere Master verwalten** | Zwischen Anlagen wechseln, Master umbenennen und bei Bedarf aus Home Assistant entfernen. |
| **Gerätebibliothek für alle Ports** | Ein Geräteprofil einmal anlegen und an mehreren Ports verwenden. Bezeichnung, Standort und Zweck bleiben je Anschluss individuell. |
| **Herstellerdateien importieren** | IODD-ZIP/XML auswerten, Varianten auswählen und unterstützte Prozessdaten, Parameter und Bilder übernehmen. |
| **Eigene Geräte ergänzen** | Beschreibungen, Bilder und JSON-Übersetzungsprofile bearbeiten und die Übersetzung an einem Rohwert testen. |
| **Unbekannte Geräte untersuchen** | Debug-Datei mit Rohwerten und Gerätekennung herunterladen – als Grundlage für die Profilerstellung, auch mit Unterstützung durch ChatGPT. |
| **Parameter gezielt lesen** | Einzelne Werte oder alle im Profil hinterlegten Herstellerparameter auf Knopfdruck abfragen. |
| **Sichern und wiederherstellen** | Parametersicherung am Port, JSON-Export/-Import, geprüfte Vorschau und Protokoll des Wiederherstellungsversuchs. |
| **Home-Assistant-Entitäten** | Sensoren und binäre Sensoren für Messwerte und Zustände; damit eigene Diagramme, Meldungen und Automationen erstellen. |
| **Parameter als Entity** | In der Parameterliste je Port gezielt Herstellerparameter auswählen; daraus entsteht eine eigene `sensor`-Entity (nur lesend) oder – bei schreibbaren Ganzzahlparametern – eine `number`- oder `select`-Entity, die sich auch aus Home Assistant heraus setzen lässt. |
| **Master-Diagnose als Entity** | Versorgungsspannung, Leistungsaufnahme, Temperatur und Supervision-Status des Masters selbst als `sensor`- bzw. `binary_sensor`-Entität sowie als Kennzahl auf der Portübersicht. |
| **Digitaleingang Pin 2 als Entity** | Pin 2 jedes IO-Link-Ports ist hardwareseitig immer ein digitaler Eingang, unabhängig von Portmodus oder zugewiesenem Profil – als eigene `binary_sensor`-Entität je Port verfügbar. |
| **Portmodus-Umschaltung (Pin 4)** | Im Command Center zwischen IO-Link, Digitalausgang, Digitaleingang und Deaktiviert wechseln – mit Vorschau und Bestätigung, da ein Wechsel einen angeschlossenen Sensor vom Port trennt. Im DO-Modus steht der Ausgangszustand als `switch`-Entität, im DI-Modus der Eingangszustand als `binary_sensor`-Entität zur Verfügung. |
| **Versionsanzeige** | Installierte Version direkt auf der Portübersicht sichtbar. Updates selbst zeigt HACS über seine eigene `update`-Entity an. |
| **Herstellerspezifische Kommandos** | Im Profil hinterlegte, feste Schreibkommandos (Index + Ganzzahlwert) für Aktionen, die nicht in der IODD stehen, z. B. eine Kalibrierung starten – direkt aus dem Command Center senden. |

Die laufende Messwerterfassung liest die Geräte. Als Entity ausgewählte Herstellerparameter werden beim Start, nach jeder Änderung und stündlich gelesen. **Darüber hinaus erfolgen Schreibzugriffe nur bei einer ausdrücklich bestätigten Parameterwiederherstellung oder beim Setzen einer Parameter-`number`-Entity.** Master-Netzwerkeinstellungen werden durch diese Integration nicht eingerichtet; die IO-Link-Portbetriebsart (IO-Link/Digitalausgang/Digitaleingang/Deaktiviert) lässt sich seit 0.5.0 ausschließlich über die geprüfte Vorschau im Command Center ändern, nie automatisch oder per Automation.

## Ein Blick ins Command Center

**Die Anlage auf einen Blick:** Die Portübersicht oben zeigt den AL1350 im Mittelpunkt, die angeschlossenen Sensoren und ihre aktuellen Messwerte. Ein Klick auf einen Port öffnet rechts die Gerätezuweisung, Standort und Verwendungszweck sowie Prozesswerte, Herstellerparameter und Sicherungsfunktionen. Der Screenshot stammt aus meiner laufenden Installation.

**Einmal anlegen, mehrfach verwenden:** In der Gerätebibliothek stehen mitgelieferte und eigene Profile gemeinsam bereit. Hersteller-IODDs lassen sich importieren; im Profileditor können Geräteinformationen, Bilder und die Übersetzung der Rohdaten ergänzt und getestet werden. Anschließend lässt sich dasselbe Profil an mehreren Ports auswählen.

<p align="center">
  <img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/screenshots/geraetebibliothek.png" alt="Gerätebibliothek mit BADU- und ifm-Profilen, IODD-Import und Editor für eigene Geräte" width="1100">
</p>

## Mein Praxisprojekt

Ich wollte meine Haustechnik nicht nur am Gerät ablesen, sondern Veränderungen rechtzeitig in Home Assistant erkennen. Ausgangspunkt waren bereits funktionierende Node-RED-Auswertungen. Daraus entstand eine eigenständige Integration mit einer gemeinsamen Oberfläche für die angeschlossenen IO-Link-Sensoren.

<p align="center">
  <img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/pool.jpeg" alt="Pooltechnik mit Filter, Durchflussmessung und ifm IO-Link-Master" width="900">
</p>

### Poolfilter: Reinigung nach Bedarf erkennen

Ein **ifm PN7096** erfasst den Druck am Poolfilter. Der Verlauf hilft mir einzuschätzen, wann der Filter stärker verschmutzt und eine Reinigung beziehungsweise Rückspülung sinnvoll wird. Entscheidend ist der Vergleich mit dem sauberen Filter bei vergleichbarer Pumpenleistung und Ventilstellung. Ein einzelner Druckwert ist noch kein direkt gemessener Verschmutzungsgrad.

### Durchfluss und Temperatur: den Wasserkreislauf überwachen

Der **Speck BADU FlowSonic Plus** liefert Durchfluss, Wassertemperatur, Summenzähler und Zustandsinformationen. Ich nutze diese Daten als Grundlage für die Überwachung der **aktiven Poolüberwinterung** und um Auffälligkeiten im Wasserkreislauf früh zu erkennen: etwa zu wenig Durchfluss bei laufender Pumpe, eine ungünstige Ventilstellung oder eine Unterbrechung der Zirkulation.

Druck und Durchfluss gemeinsam zu betrachten ist dabei besonders hilfreich. Eine Meldung kann auf eine Störung aufmerksam machen; die konkrete Ursache muss anschließend geprüft werden. Die Integration liefert die Messwerte, die anlagenspezifischen Alarmgrenzen und Winterautomationen werden in Home Assistant eingerichtet.

### Heizkreis: Druckverlust früh bemerken

Ein weiterer **PN7096** überwacht den Heizungsdruck. Über Verlauf und eigene Benachrichtigungen lässt sich erkennen, wann eine Kontrolle des Heizkreises und gegebenenfalls das Nachfüllen von Heizungswasser erforderlich ist. Die Integration füllt selbst kein Wasser nach.

### Druckluft: den Steuerdruck im Blick behalten

**PN7094-Sensoren** erfassen den Druck an Kompressor, Verteiler und Speicher. So kann ich Druckabfälle und Abweichungen zwischen den Messstellen erkennen und überwachen, ob der benötigte Steuerdruck bereitsteht. Die eigentliche Druckregelung bleibt Aufgabe der vorhandenen Anlage.

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/poolfilter.jpeg" alt="PN7096 am Poolfilter"><br><strong>Poolfilterdruck</strong></td>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/flowsonic-plus.jpeg" alt="BADU FlowSonic Plus im Wasserkreislauf"><br><strong>Durchfluss und Wassertemperatur</strong></td>
</tr>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/heizung.jpeg" alt="PN7096 zur Heizkreis-Drucküberwachung"><br><strong>Heizkreis überwachen</strong></td>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/druckluft.jpeg" alt="PN7094 und AL1350 in der Druckluftinstallation"><br><strong>Druckluft und Steuerdruck</strong></td>
</tr>
</table>

### Stromversorgung über einen PoE-Splitter

In meiner Installation versorgt ein **PoE-Splitter/Wandler** den AL1350 und die daran angeschlossenen Sensoren über die PoE-Zuleitung. Der Splitter trennt Netzwerk und Versorgung: Ethernet geht zum IoT-Port, der passende DC-Ausgang zum Stromanschluss des Masters. Damit lässt sich die Sensorik zentral über die Netzwerkinfrastruktur versorgen.

Der abgebildete Splitter trägt die Modellbezeichnung **POE-SP02BT-POE** und bietet laut Typenschild mehrere Ausgangsspannungen. Für den AL1350 wird eine passende **24-V-DC-Versorgung** benötigt; sein spezifizierter Bereich liegt bei 20–30 V DC. Ausgangsspannung, Anschlussbelegung und das verfügbare Leistungsbudget müssen für Master und alle angeschlossenen Sensoren zusammen passen. Der AL1350 wird über seinen Stromanschluss versorgt; der externe Splitter übernimmt die PoE-Wandlung. [ifm-Datenblatt](https://media.ifm.com/dam/aaf256ab-5a44-4254-9ac9-f84f55bfc80b/Original/AL1350-00_EN-GB.pdf)

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/pool2.jpeg" alt="AL1350 mit externem PoE-Splitter"><br><strong>Master und PoE-Splitter</strong></td>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/pool_poe.jpeg" alt="Detail des PoE-Splitters hinter dem IO-Link-Master"><br><strong>Versorgung und Sensoranschlüsse</strong></td>
</tr>
</table>

## Unterstützte Geräte

| Gerät | Umfang | Erprobung |
|---|---|---|
| **ifm AL1350** | IoT-Master mit vier IO-Link-Ports | Zwei reale Master getestet |
| **ifm AL1352** | IoT-Master mit acht IO-Link-Ports | Implementiert; Hardwaretest ausstehend |
| **ifm PN7094** | Druck, Gerätestatus, OUT1/OUT2; Profile für Default und Status B | Status B an realen Sensoren geprüft |
| **ifm PN7096** | Druck, Gerätestatus, OUT1/OUT2; Profile für Default und Status B | Status B an realen Sensoren geprüft |
| **ifm LDH292** | Luftfeuchte, Temperatur, Gerätestatus | Implementiert; Hardwaretest ausstehend |
| **ifm PG1406** | Druck (-0,124…2,5 bar), Gerätestatus | Implementiert; Hardwaretest ausstehend |
| **ifm SM9000** | Durchfluss (5…300 l/min), Totalisator, Temperatur, OUT1/OUT2 | Implementiert; Hardwaretest ausstehend |
| **ifm SV4200** | Durchfluss (1,0…20,0 l/min), Temperatur, OUT1/OUT2 | Implementiert; Hardwaretest ausstehend |
| **ifm KQ1000** | Füllstand (Distanz), Gerätestatus, OUT1/OUT2/OUT3; Tankabgleich-Kommandos (leer/voll), Werksreset, Blinken | Implementiert; Hardwaretest ausstehend |
| **Speck BADU FlowSonic Plus** | Durchfluss, Temperatur, zwei Summenzähler und Zustandsflags | Reale Messwerte und Node-RED-Zuordnung geprüft |
| **Weitere IO-Link-Geräte** | IODD-Import oder eigenes JSON-Profil | Abhängig von Geräteformat und unterstützten Datentypen |

Der Tageswert **„Gefiltertes Wasservolumen heute“** kann aus einem Summenzähler mit einem Home-Assistant-Verbrauchszähler abgeleitet werden. Er ist kein separat gelieferter IO-Link-Prozesswert.

## Installation

### Über HACS

1. In HACS **Benutzerdefinierte Repositories** öffnen.
2. `https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot` als Kategorie **Integration** hinzufügen.
3. **ifm IO-Link Master AL13xx IoT** herunterladen.
4. Home Assistant neu starten.

Das Repository wird als benutzerdefiniertes HACS-Repository verwendet; es ist nicht automatisch Bestandteil des HACS-Standardkatalogs. [HACS-Dokumentation](https://www.hacs.xyz/docs/faq/custom_repositories/)

### Manuell

Den Ordner `custom_components/ifm_iolink` aus diesem Repository oder dem Release-ZIP nach `/config/custom_components/ifm_iolink` kopieren und Home Assistant neu starten.

### Master und Sensoren einrichten

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → ifm IO-Link Master AL13xx IoT** öffnen.
2. Das private Netzwerk durchsuchen oder die IoT-Adresse des Masters eingeben.
3. In der HA-Seitenleiste **ifm IO-Link** öffnen.
4. Einen Port auswählen und ein passendes Geräteprofil zuweisen. Übereinstimmende Hersteller-/Gerätekennungen werden im Dropdown markiert.
5. Gerätebezeichnung, Standort und Verwendungszweck eintragen und speichern.
6. Die erzeugten Entitäten für eigene Dashboards und Automationen verwenden.

**Voraussetzungen:** Home Assistant ab 2025.7 als Mindestzielversion, erreichbarer IoT Core und passend konfigurierte IO-Link-Ports. Getestet wurde mit Home Assistant 2026.8.3. Lokale Integrationslogos werden ab HA 2026.3 unterstützt. Verwaltung im Command Center benötigt Administratorrechte. Netzsuche arbeitet innerhalb erreichbarer privater IPv4-Netze; bei VLANs kann die manuelle Adresse genutzt werden. Passwortzugriffe auf den Master erfordern HTTPS.

## Parametersicherung & Sensortausch

Unter **Parameterliste anzeigen → Alle Gerätedaten lesen → Lesen** werden alle Profilparameter abgefragt. Einzelne Parameter besitzen einen eigenen Lesen-Button.

Unter **Sensortausch & Sicherung** stehen die Aktionen in dieser Reihenfolge:

| Aktion | Bedeutung |
|---|---|
| **Parametersicherung erstellen** | Aktuelle Profilparameter lesen und eine vollständige Sicherung für diesen Port in HA speichern. |
| **Parametersicherung wiederherstellen** | Die gespeicherte Port-Sicherung prüfen und nach Vorschau und Bestätigung auf den angeschlossenen Sensor übertragen. |
| **Sicherung als JSON herunterladen** | Die gespeicherte Sicherung auf dem eigenen Computer ablegen. |
| **JSON-Sicherung wiederherstellen** | Eine vorhandene JSON-Datei auswählen und mit demselben Prüf- und Bestätigungsablauf verwenden. |
| **Protokoll herunterladen** | Ursprüngliche Werte, bestätigte Änderungen und Fehler des letzten Wiederherstellungsversuchs nachvollziehen. |

Beim Sensortausch müssen Gerätekennung und Profil passen; die Seriennummer des Ersatzgeräts darf von der ursprünglichen abweichen. Unterstützte schreibbare Parameter werden einzeln übertragen und zurückgelesen. Unveränderte Werte, reine Lesewerte und Systembefehle werden ausgelassen. Bei einem Fehler stoppt der Vorgang; bereits übertragene Werte bleiben bestehen. Das Protokoll dokumentiert den erreichten Stand, es gibt keinen automatischen Rollback.

Gesichert wird der **im Profil enthaltene Parameterumfang**, kein vollständiges Geräteabbild. Beim BADU sind derzeit drei verifizierte Format-/Einheitenparameter hinterlegt. Die automatische IO-Link-Data-Storage-Funktion des Masters ist davon unabhängig und wird hier nicht aktiviert. Details und Grenzen: [Technische Hinweise](docs/technical-notes.md).

## Eigene Geräte & IODD-Import

In der **Gerätebibliothek** eine Hersteller-IODD als ZIP oder XML importieren, die passende Variante auswählen und die Vorschau prüfen. Enthaltene Gerätebilder werden aus dem ZIP übernommen; eine einzelne XML-Datei liefert keine externen Bilddateien mit.

Der Import unterstützt unter anderem Ganzzahlen, Boolesche Werte, IEEE-754-Floats, einfache Records, Bitpositionen und statische Skalierungen. Nicht unterstützte oder uneindeutige Angaben werden als Hinweise angezeigt. Je nach Sensor kann eine Ergänzung des Profils erforderlich sein.

Ohne passende IODD lässt sich ein Gerät als **Unbekannt** zuweisen und eine Debug-Datei exportieren. Daraus kann ein eigenes JSON-Übersetzungsprofil entstehen, das sich direkt im Command Center testen, mit Bild und Beschreibung versehen und anschließend mehreren Ports zuweisen lässt. Profile beschreiben die Datenübersetzung; sie enthalten keinen ausführbaren Python- oder JavaScript-Code. [Profilformat und Beispiele](docs/device-profiles.md)

### Eigene Kommandos definieren

Ein Kommando schreibt einen festen Ganzzahlwert auf Index/Subindex 0 des Sensors – gedacht für Herstellerbefehle, die nicht in der IODD stehen, z. B. „Kalibrierung starten“. Im Profileditor gehört dazu ein `commands`-Array auf oberster Ebene, neben `parameters`:

```json
{
  "commands": [
    {
      "index": 2,
      "value": 208,
      "name": "Leeren Tank abgleichen",
      "description": "Kalibriert den Sensor auf den leeren Tank"
    },
    {
      "index": 2,
      "value": 209,
      "name": "Vollen Tank abgleichen",
      "description": "Kalibriert den Sensor auf den vollen Tank"
    }
  ]
}
```

- `index`: Parameterindex (0–65535). Mehrere Kommandos dürfen sich denselben Index teilen, wie hier – typisch für einen „System Command“-Parameter, bei dem verschiedene Werte verschiedene Befehle auslösen. Eindeutig sein muss die Kombination aus `index` **und** `value`.
- `value`: der zu schreibende Wert, ein einzelnes Byte (0–255). Subindex ist immer 0.
- `name`, `description`: Beschriftung und Hilfetext für den „Senden“-Button im Command Center.

Im Command Center erscheint das Kommando unter **Kommandos anzeigen** neben der Parameterliste; ein Klick auf **Senden** schreibt den Wert sofort, ohne weiteren Bestätigungsdialog. Vor jedem Senden wird die Gerätekennung frisch gegen `match` geprüft, damit ein zwischenzeitlich getauschter, andersartiger Sensor nicht versehentlich denselben Befehl bekommt.

## Entwicklung, Tests und Rückmeldungen

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check custom_components tests scripts
python -m compileall -q custom_components
node --check custom_components/ifm_iolink/frontend/panel.js
```

Mit `python scripts/preview.py` startet eine lokale Oberflächen-Demo unter `http://127.0.0.1:8765/`. Sie arbeitet ausschließlich mit Beispielwerten. Das Installationspaket erstellt `python scripts/package.py`.

**249 automatisierte Tests** decken unter anderem Dekodierung, IODD-Import, API-Fehler und Wiederherstellungsprüfungen ab. Eine Wiederherstellung ohne Wertänderungen wurde an einem realen PN7094 geprüft; tatsächliche Änderungen und Fehlerfälle wurden bislang simuliert. [Prüfumfang](docs/validation.md)

Fehler, Erfahrungen mit dem AL1352 und neue Sensorprofile sind als [GitHub-Issue](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/issues) willkommen. Bitte Modell, Firmware, Integrationsversion und den beobachteten Fehler nennen. Debug-Dateien und Sicherungen vor dem öffentlichen Hochladen auf private Bezeichnungen, Seriennummern und sonstige anlagenspezifische Angaben prüfen.

## Entwicklung unterstützen

Dir gefällt die Integration und du möchtest ihre Weiterentwicklung unterstützen? Über eine freiwillige Unterstützung via PayPal freue ich mich:

[Entwicklung über PayPal unterstützen](https://paypal.me/JensSaffrich)

## Lizenz und Projekt

Der selbst erstellte Programmcode steht unter der [MIT-Lizenz](LICENSE). Herstellerbilder, IODD-Auszüge, Logos und Produktnamen behalten ihre jeweiligen Rechte. Die Praxisfotos stammen von JS-DE-Tech. [Bild- und Quellenhinweise](docs/assets.md)

Dies ist eine unabhängige Community-Integration von **JS-DE-Tech**, kein offizielles Produkt von ifm, Speck oder JUMO.
