# Master ersetzen oder erweitern

Verfügbar ab v0.1.5. Ein AL1350→AL1352-Austausch wurde am 16.10.2026 an der realen Garage-Installation mit Home Assistant 2026.9.4 durchgeführt und anschließend nachgeprüft.

Im Command Center unter **Master verwalten → Master ersetzen / erweitern** kann ein vorhandener AL1350 durch einen AL1350 oder AL1352 ersetzt werden. Ein Ersatzgerät mit weniger Ports wird abgewiesen.

## Automatischer Ablauf

Nach Sichern/Pausieren und physischem Austausch den Ersatzmaster suchen, prüfen und die gemeinsame Bestätigung setzen. **Austausch automatisch durchführen** startet anschließend einen Hintergrundauftrag in Home Assistant:

1. Gesicherte Quelle, ausgewählten Ersatzmaster und vollständige Portkonfiguration prüfen.
2. Netzwerk übertragen, falls erforderlich genau einen Neustart auslösen.
3. Bis zu 90 Sekunden auf die Ziel-IP warten und Seriennummer, Modell und Netzwerkwerte prüfen.
4. Gesicherte Portmodi und unterstützte Zusatzparameter übertragen, jeden Schritt zurücklesen. DO-Ports bleiben zunächst Disabled.
5. Alle übertragenen Werte erneut prüfen, bestehenden Config Entry übernehmen und HA-Reload/Verbindung bis zu 30 Sekunden prüfen.
6. Erst danach Erfolg melden. Der Abschluss wird dauerhaft gespeichert, damit eine Wiederaufnahme keine Hardwarezugriffe wiederholt.

Das Browserfenster darf geschlossen werden. Wiederöffnen zeigt den Fortschritt; nach einem HA-Neustart setzt **Austausch fortsetzen** den gespeicherten Ablauf nach erneuter Prüfung fort. Es startet nach einem HA-Neustart nicht selbstständig ohne Benutzeraktion. Bei falscher Identität, abweichender Konfiguration oder unklaren Schreibresultaten wird angehalten. Die Hardware muss dann gegebenenfalls vor Ort geprüft werden; solche Fälle sind bewusst keine garantierte automatische Wiederherstellung.

## Vorbereitung und verfügbare Einzelschritte

1. Solange der bisherige Master erreichbar ist, **Sichern und Austausch vorbereiten** wählen. Die Integration speichert ihre Konfiguration sowie lesbare Netzwerkwerte, Portmodi, Application Tag und LR-Agent-Einstellungen. Danach pausiert die Verarbeitung. Vorhandene Sensor-Parametersicherungen bleiben erhalten; es wird keine neue Vollsicherung aller Sensorparameter erzeugt.
2. Alten Master trennen. Ersatzmaster anschließen und über seine zunächst eigene, erreichbare IoT-Adresse suchen. Die Suche prüft ein angegebenes privates IPv4-Netz mit höchstens 1024 Adressen. Sie konfiguriert keine Netzwerkadapter; Geräte in einem nicht erreichbaren Werksnetz benötigen zunächst eine erreichbare Adresse. Die automatische Suche nutzt HTTP ohne Anmeldung; HTTPS-Geräte können direkt angegeben werden. Der Ersatzmaster muss mit den hinterlegten Zugangsdaten erreichbar sein.
3. **Ersatzgerät prüfen** zeigt Modell, Seriennummer, Ports und Zuordnungen. Aktive oder nicht eindeutig lesbare Digitalausgänge verhindern die Übernahme. Nicht passende Sensorprofile werden angezeigt.
4. Optional die gesicherten Netzwerkwerte anzeigen und **Netzwerk übernehmen** bestätigen. Voraussetzung ist eine vollständig gelesene statische IPv4-Konfiguration. DHCP-Adressen müssen separat eingerichtet werden. Der bisherige Master muss getrennt und die Ziel-IP frei sein. Ein offener TCP-Port an der Zieladresse blockiert die Übertragung; ein ausbleibender TCP-Verbindungsaufbau beweist allerdings nicht, dass kein anderes Gerät die IP verwendet.
5. Der automatische Auftrag (oder der entsprechende Einzelschritt) schreibt die vier Netzwerkwerte gemeinsam per `iotsetup/network/setblock`. Antwort 233 bedeutet ein automatisches Neuladen der Netzwerkschnittstelle; bei Antwort 230 wird nach erneuter Identitätsprüfung `firmware/reboot` ausgelöst. Bei Antwort 200 wird zunächst ebenfalls an der Ziel-IP geprüft. Es erfolgt kein Werksreset. Der automatische Auftrag wartet begrenzt auf die Wiederverbindung. Bei manueller Durchführung **Ziel-IP erneut prüfen** verwenden. Unklare Schreibresultate werden nicht automatisch wiederholt.
6. Erst nach Übereinstimmung von Seriennummer, Modell und Netzwerkwerten an der Ziel-IP **Konfiguration zurücksichern** wählen. Übertragen werden die gesicherten Portmodi und lesbaren, unterstützten Zusatzwerte (Application Tag, LR-Agent-IP/-Port/-Intervall). Gesicherte DO-Ports werden zunächst auf **Disabled** gesetzt und müssen später bewusst aktiviert werden. Zusätzliche Ports des AL1352 bleiben unverändert. Fehlende Zusatzwerte werden angezeigt und ausgelassen. MAC-Adresse, Security Mode, Kennwörter, Validierungs-/DataStorage-Konfiguration und sonstige nicht aufgeführte Masterparameter werden nicht geklont.
7. Ersatzgerät erneut prüfen und **Master ersetzen** bestätigen. Die bestehende Integration wird mit neuer Hardwareidentität und Adresse weiterverwendet. Bei Bedarf anschließend Sensorparameter über **Sensortausch & Sicherung** je Port mit der vorhandenen Vorschau zurückspielen. Beim bloßen Mastertausch behalten die weiterverwendeten Sensoren ihre eigene Parametrierung.

## Erhaltene Identität

Config-Entry-ID, Geräte-Registry-IDs, Entitäts-IDs, bisherige Unique-IDs, Namen, Bereiche, Profilzuordnungen und vorhandene Parametersicherungen bleiben erhalten. Dafür bleibt die ursprüngliche Seriennummer als interner `registry_serial`-Namensraum erhalten. Die tatsächliche Seriennummer des Ersatzmasters wird separat zur Kommunikation und Identitätsprüfung verwendet. Neue Ports erhalten zusätzliche Geräte und Entitäten. Das alte Gerät kann nicht als zweite Integration mit demselben reservierten Namensraum hinzugefügt werden.

Die Messwerterfassung prüft auch nach dem Austausch die Masteridentität. Ein anderes Gerät an derselben IP wird nicht stillschweigend übernommen. Bei offline befindlichem oder abweichendem Master bleibt die Verwaltung erreichbar, soweit eine vollständige bisherige Identität gespeichert ist.

## Unterbrechung und Rückkehr

Der Austausch speichert Sicherung und Fortschritt privat in Home Assistants `.storage/ifm_iolink.replacement.<entry_id>`. Schreibversuche werden vor dem Hardwarezugriff protokolliert. Nach einem HA-Neustart kann die Ziel-IP erneut geprüft werden. Bereits versuchte Konfigurationsschritte werden beim Fortsetzen nur zurückgelesen; noch nicht versuchte Schritte können ausgeführt werden. Stimmt ein unklarer Schreibversuch nicht mit dem gewünschten Wert überein, muss die Einstellung vor Ort geklärt werden. Es gibt keinen automatischen Rollback der Hardware.

**Austausch abbrechen / bisherigen Master verwenden** beendet die Pause nur, solange noch keine Hardwareübertragung begonnen hat. Danach bleibt die Sicherung erhalten und der Ablauf muss fortgesetzt bzw. der Fehler geklärt werden. Es gibt keinen automatischen Hardware-Rollback. Austauschaktionen sind installationsübergreifend serialisiert; ein Ersatzmaster kann nicht zugleich von zwei Austauschvorgängen beansprucht werden.

## Prüfung und Grenzen

423 Python-Tests sowie JavaScript-Status-, Klick-, Geräteeditor- und Austauschdialogtests bestanden. Ruff und JavaScript-Syntaxprüfung fehlerfrei. Die zusätzlichen Ablaufprüfungen führen den echten Orchestrator gegen einen simulierten Master aus, einschließlich verzögertem Neustart, verlorenen Antworten, Hintergrundausführung, Zeitüberschreitung und Wiederaufnahme nach Übernahme. Automatisierte Tests decken wiederholten AL1350-/AL1352-Austausch, ID-Erhalt, Offline-/Reload-Fälle, Vorschauänderungen, Identitätskonflikte, Netzwerkvalidierung, dokumentierte Antwortcodes, verlorene Antworten, belegte Zieladressen, Speicherfehler, Wiederanlauf und Rücklesen ab. Der Geräte-Registry-Testdouble berücksichtigt globale Kennungen und den Cleanup vorhandener Entitäten. Registry-/Lifecycle-Tests verwenden HA-2025.7- und HA-2026.9-Testdoubles; sie ersetzen keinen Test mit einem vollständigen laufenden HA.

Reale Übernahme am 16.10.2026: Der AL1352 mit Firmware AL1x5x_cn_it_v2.3.23 übernahm die statische Ziel-IP. Das Austauschjournal bestätigte den Abschluss, geprüfte Netzwerkwerte sowie vier Portmodi und vier Zusatzwerte. Antwort 233 führte zum Neuladen der Netzwerkschnittstelle; in diesem Lauf war kein separater Firmware-Reboot nötig. Alle bisherigen 69 Entitätsidentitäten und 10 Geräteidentitäten samt Hierarchie blieben erhalten. Die zusätzlichen Ports erweiterten den Bestand auf 85 Entitäten und 14 Geräte. Beide Master lieferten anschließend Messwerte, X05–X08 meldeten DO/AUS. Ein späteres Update auf den Stand mit digitalen Geräteprofilen erhielt alle 85/14 Identitäten sowie Daten und Optionen.

Der separate Reboot-Pfad (Antwort 230), Unterbrechungen und Wiederanlauf sind simuliert geprüft, nicht in diesem realen Austausch erzwungen. Kein elektrischer Lasttest, keine unabhängige Messwertkalibrierung und keine vollständige Prüfung sämtlicher Entitätszustände. Die erfolgreichen Registry-Vergleiche, UI-Prüfungen und direkten Masterabfragen belegen keinen universellen Test aller Firmwarestände.

Grundlage: ifm-Betriebsanleitungen [AL1350](https://www.quicktimeonline.com/assets/images/pdf/IFM%20Electronic/operating-instruction-AL1350.pdf) (S. 37, 43, 101–103) und [AL1352](https://www.quicktimeonline.com/assets/images/pdf/IFM%20Electronic/operating-instruction-AL1352.pdf) (S. 40, 46, 104–106). Die Dokumente beschreiben Firmware 3.1.x; das Verhalten anderer Firmwarestände ist vor einem realen Austausch zu verifizieren.
