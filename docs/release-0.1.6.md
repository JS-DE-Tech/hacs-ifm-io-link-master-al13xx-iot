# v0.1.6 – Anschlusshilfe für DI und DO

**Reguläres Release / regular release**

## Deutsch

An DI-/DO-Portkarten von AL1350 und AL1352 öffnet ein Fragezeichen jetzt ein passendes Anschlussbeispiel direkt im Command Center:

- **DO:** Schneider LC1D18BD mit Spulenanschlüssen und separater Rückmeldung über den DI2-Hilfskontakt. Master-Rückmeldung und mechanische Rückmeldung werden unterschieden.
- **DI:** Zwei unabhängige potentialfreie Kontakte an DI1 und DI2 mit gemeinsamer L+-Versorgung.
- **Grafik und Tabelle:** Phoenix Contact 1504615 als Kabelbeispiel, farbige Leitungen und Anschlusstabelle. Auf kleinen Displays lässt sich die Grafik horizontal scrollen. Escape schließt den Dialog und gibt den Fokus zurück.
- **Zuverlässiges Laden:** Eine neue Frontend-Ladeadresse verhindert die weitere Nutzung der vorherigen JavaScript-Datei unter unveränderter Entwicklungsversionsnummer.

Die Hilfe sendet keine Hardwarebefehle. Die Beispiele bleiben Anschlussentwürfe: Farb-Pin-Zuordnung durch Durchgang prüfen; DO-Spulenverträglichkeit und DI2-Kontaktstrom sind vor Anschluss zu klären. Eine DO-Rückmeldung vom Master ist kein Nachweis des Laststroms.

**Prüfung:** 423 Python-Tests, drei JavaScript-Prüfprogramme, Ruff sowie Syntax-/Kompilierungsprüfungen. DO-Fragezeichen und Popup wurden im laufenden HA 2026.9.4 am AL1352 sichtbar geprüft und vom Nutzer bestätigt. DI wurde lokal einschließlich Mobilansicht geprüft und auf HA installiert; kein produktiver DI-Port wurde zum Test umgeschaltet. Keine elektrischen Lasttests.

**Update:** In HACS v0.1.6 installieren, HA neu starten und das Command Center neu laden. Die Mindestversion bleibt HA 2025.7.0. Bestehende Geräte-, Entitäts- und Profil-IDs werden nicht geändert; eine Neueinrichtung ist nicht erforderlich. Das beigefügte ZIP enthält `custom_components/ifm_iolink` und die Dokumentation.

## English

Question-mark buttons on AL1350/AL1352 DI/DO port cards now open mode-specific wiring examples:

- **DO:** Schneider LC1D18BD coil wiring and separate DI2 auxiliary-contact feedback, distinguished from master output read-back.
- **DI:** Two independent dry contacts for DI1 and DI2 sharing L+.
- **Diagram and table:** Phoenix Contact 1504615 cable example, coloured wires, connection table, scrollable mobile diagrams and Escape/focus handling.
- **Loading fix:** A revised frontend URL avoids loading the previous JavaScript file from the unchanged development-version address.

The help sends no hardware commands. Wiring proposals retain their caveats: verify wire-to-pin continuity, coil compatibility and DI2 contact current before wiring. Master output read-back does not prove load current.

Validation: 423 Python tests, three JavaScript check programs, lint and syntax/compilation checks. DO UI verified live on an AL1352 with HA 2026.9.4 and confirmed by the user. DI tested locally, including mobile layout, and installed on HA; no live DI-mode test or electrical load test. Install v0.1.6 through HACS, restart HA and reload the panel. Minimum HA version remains 2025.7.0; existing IDs are preserved.

## Screenshots

DO: aus dem laufenden Home Assistant / from the live Home Assistant installation. Captured before the release version bump.

![DO wiring help in HA](https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/v0.1.6/docs/images/screenshots/wiring-help-do-live.png)

DI: lokale Vorschau des freigegebenen Anschlussbeispiels / local preview of the approved wiring example, not a live hardware test.

![DI wiring example preview](https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/v0.1.6/docs/images/screenshots/wiring-help-di-preview.png)
