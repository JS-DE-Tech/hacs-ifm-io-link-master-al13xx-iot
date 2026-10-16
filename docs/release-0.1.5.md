# v0.1.5 – AL1352, Masteraustausch und digitale Geräte

**Reguläres Release / regular release**

## Deutsch

Die Integration verbindet nun auch in der erprobten Praxis den achtkanaligen AL1352 mit Home Assistant. IO-Link-Sensoren, digitale Eingänge und schaltbare Ausgänge erscheinen gemeinsam im Command Center.

- **Master ersetzen / erweitern:** Unter „Master verwalten“ den bisherigen Master sichern und pausieren, Ersatzgerät im erreichbaren Netzwerk suchen und prüfen, anschließend die unterstützten statischen Netzwerkwerte und Konfiguration nach Bestätigung übertragen. Der Auftrag läuft in HA weiter, auch wenn das Fenster geschlossen wird; nach einem HA-Neustart kann er bewusst fortgesetzt werden.
- **IDs bleiben erhalten:** Bestehende Geräte- und Entitäts-IDs, Portzuordnungen, Namen und Parametersicherungen werden weiterverwendet. Neue AL1352-Ports ergänzen die Anlage. Gesicherte DO-Ports bleiben nach der Übertragung zunächst deaktiviert; Sensorparameter werden separat mit Vorschau wiederhergestellt.
- **Eigene DI-/DO-Geräte mit Bild:** Namen, Hersteller, Modell, Beschreibung und Bild direkt in der Gerätebibliothek pflegen, ohne JSON oder IODD. Ein Gerätetyp lässt sich mehreren Ports mit individuellen Bezeichnungen zuweisen. IO-Link-Zuordnungen bleiben separat gespeichert.
- **Automatische Profil-ID:** Neue IDs entstehen aus dem Gerätenamen, mit Umlautumwandlung und Nummern bei Namenskollisionen. Gespeicherte IDs bleiben beim Umbenennen stabil.
- **Dokumentation und Screenshots:** Deutsche und englische README mit realem AL1352, digitalen Portzuordnungen, Geräteeditor und Masterverwaltung aktualisiert.

### Prüfung und Update

423 Python-Tests, drei JavaScript-Prüfprogramme, Ruff und Syntax-/Kompilierungsprüfungen. Der reale AL1350→AL1352-Austausch unter HA 2026.9.4 erhielt alle bisherigen 69 Entitätsidentitäten und 10 Geräteidentitäten; neue Ports erweiterten den Bestand auf 85/14. Auch das anschließende Update mit digitalen Geräteprofilen erhielt diese IDs und Einstellungen.

Beim realen IP-Wechsel wurde Antwort 233 mit Neuladen der Netzwerkschnittstelle bestätigt. Der separate Reboot-Pfad sowie Fehler-/Wiederanlauffälle sind simuliert geprüft. Kein elektrischer Lasttest, kein DI-High-Test und keine vollständige Prüfung aller aktiven HA-Entitätszustände. HA ab 2025.7 bleibt Mindestzielversion; ältere Registry-APIs werden mit Testdoubles geprüft.

Vor dem Update eine HA-Sicherung anlegen. Über HACS **v0.1.5** herunterladen oder das beigefügte ZIP verwenden, anschließend HA neu starten und das Command Center neu laden. Eine Neueinrichtung der Integration ist nicht erforderlich. Das ZIP enthält den Integrationsordner unter `custom_components/ifm_iolink` sowie die Dokumentation.

## English

This regular release brings a physically verified eight-port AL1352 installation, a guided master replacement workflow and custom digital device profiles.

- **Replace or expand a master:** Back up and pause the existing master, discover and validate its replacement, then transfer supported static network settings and configuration after confirmation. The job continues in HA when the browser closes; after an HA restart, it can be explicitly resumed.
- **Preserve identity:** Existing device/entity IDs, port assignments, names and parameter backups are retained. Additional AL1352 ports extend the installation. Saved DO ports initially remain disabled after transfer; sensor parameters are restored separately after preview.
- **Digital devices without JSON or IODD:** Add names, descriptions and images through the device library and assign them to DI/DO ports. IO-Link assignments are preserved separately.
- **Automatic profile IDs:** Names generate IDs with normalized characters and numeric suffixes for duplicates. Saved IDs remain unchanged when a device is renamed.
- **Updated documentation:** German and English READMEs include screenshots from the live AL1352 installation.

Validation: 423 Python tests, three JavaScript check programs, linting and syntax/compilation checks. Real replacement on HA 2026.9.4 preserved all 69 original entity identities and 10 device identities; new ports expanded the totals to 85/14. The subsequent update preserved these IDs and settings. Network response 233 was observed on hardware; the separate reboot path and failure/resume cases were simulated. No electrical load test, DI-high test or exhaustive validation of all active HA entity states. HA 2025.7 remains the minimum target, with compatibility checks using test doubles.

Back up HA, install **v0.1.5** through HACS or the attached ZIP, restart HA and reload the Command Center. Re-creating the integration is not required.

## Screenshots

Captured from the running installation during development; the footer still shows the development build. / Während der Entwicklung an der laufenden Anlage aufgenommen; die Fußzeile zeigt noch den Entwicklungsstand.

### AL1352: acht Ports / eight ports

![AL1352 overview](https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/v0.1.5/docs/images/screenshots/al1352-overview.png)

### Digitale Geräte mit Bild / digital devices with images

![Digital device editor](https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/v0.1.5/docs/images/screenshots/digital-device-editor.png)

<details>
<summary>Portzuordnung und Masterverwaltung / port assignment and master management</summary>

![Digital port assignment](https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/v0.1.5/docs/images/screenshots/digital-port-device.png)

![Master replacement entry point](https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/v0.1.5/docs/images/screenshots/master-replacement.png)

</details>
