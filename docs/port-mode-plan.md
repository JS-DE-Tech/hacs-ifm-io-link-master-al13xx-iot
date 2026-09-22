# Pin 2 als Digitaleingang + Portmodus-Umschaltung (Pin 4)

Arbeitsnotiz/Plan, nicht Teil der Nutzer-Doku. Teil 1 ist umgesetzt (ab Version 0.4.0, Bugfix in 0.4.2). Teil 2 ist ab 0.5.0 vollständig umgesetzt (Backend, Websocket-Commands, Panel-Vorschau/Bestätigung, `switch`-Plattform für den DO-Ausgangszustand), siehe Abschnitt "Stand nach 0.5.0" unten. Teil 3 (Pin 4 als Digitaleingang, 2× DI, volle 4-Wege-Moduswahl) ist ab 0.7.0 umgesetzt und am realen Zwei-Ausgänge-Sensor vollständig verifiziert – siehe "Teil 3" unten. Damit ist der gesamte Plan abgeschlossen.

## Context

Der AL1350/AL1352 hat laut ifm-Datenblatt an jedem M12-Port zwei nutzbare Signale zusätzlich zur Sensorversorgung:

- **Pin 2** ist hardwareseitig **immer** ein digitaler Eingang (11–30 V high / 0–5 V low, kurzschlussfest) – unabhängig davon, ob der Port sonst als IO-Link läuft oder nicht.
- **Pin 4 (C/Q)** ist umschaltbar: entweder IO-Link-Kommunikation (heutiger, einziger unterstützter Zustand) oder digitaler Ausgang (max. 300 mA, kurzschlussfest).

Ziel: Pin 2 als reinen `binary_sensor` je Port sichtbar machen (**erledigt**), und eine **Umschalt-Logik** für den Portmodus von Pin 4 ergänzen (IO-Link ⇄ Digitalausgang, **offen**), analog zum bestehenden Parameter-Restore-Flow abgesichert – weil ein Moduswechsel den ggf. angeschlossenen IO-Link-Sensor vom Port trennt.

Klärung mit Elias: Pin-2-Sensor entsteht an **allen** Ports (unabhängig vom zugewiesenen Profil). Der Portmodus-Wechsel läuft **ausschließlich im Command-Center-Panel mit Vorschau+Bestätigung** (kein direktes HA-`select`/`switch` zum Umschalten des Modus, da das eine Automation versehentlich einen Sensor-Port kappen könnte). Sobald ein Port im DO-Modus ist, wird der reine Ausgangszustand (an/aus) als normales `switch`-Entity exponiert – das ist ungefährlich und automatisierbar.

**API verifiziert (2026-09-15, gegen echten AL1352 unter 192.168.1.22, Testmaster ohne Produktivbetrieb):**

| Zweck | Pfad | Format |
|---|---|---|
| Pin-2-Eingang lesen | `/iolinkmaster/port[X]/pin2in` | nur `getdata`, Integer 0/1. **Liegt direkt unter `port[X]`, nicht unter `iolinkdevice`** – `port_path()` (in `const.py`) darf hier NICHT verwendet werden, die Funktion hängt immer `/iolinkdevice/` an. Siehe Bugfix-Hinweis unten. |
| Portmodus lesen/schreiben | `/iolinkmaster/port[X]/mode` | Enum `0=Disabled, 1=DI, 2=DO, 3=IO-Link`, `getdata`+`setdata` |
| Portmodus schreiben | `POST /` mit `{"code":"request","cid":1,"adr":"/iolinkmaster/port[X]/mode/setdata","data":{"newvalue":<int>}}` | Antwort `{"code":200}` ohne `data` – passt zu `empty_response=True` wie bei `write_parameter` |
| DO-Ausgangswert (nicht live gegen ein DO getestet, nur Struktur bestätigt) | `/iolinkmaster/port[X]/iolinkdevice/pdout` | Hex-String, `getdata`+`setdata`, gleicher Knoten wie IO-Link-Ausgangsprozessdaten |

Live-Test: Port 3 (unbenutzt, `status=0`) per `setdata` von IO-Link (3) auf DI (1) und zurück auf IO-Link (3) geschaltet, beide Male per `getdata` zurückgelesen und bestätigt – Payload-Form `{"newvalue": <int>}` funktioniert wie bei der ifm-IoT-Core-Standardkonvention erwartet. Der Modus-Pfad ist einfacher als ursprünglich angenommen (`mode` direkt, kein verschachteltes `mode/portmode_device`; Integer-Enum statt String-Enum wie `IOL_AUTOSTART`/`DI_C/Q`/`DO_C/Q`).

## Teil 1 – Pin 2 als `binary_sensor` (erledigt, ab 0.4.0)

Umgesetzt in `coordinator.py`, `entity.py`, `binary_sensor.py`, `__init__.py`, `frontend/panel.js`.

**Bugfix in 0.4.2:** Der erste Versuch nutzte `port_path(port, "pin2in")`, was fälschlich `/iolinkmaster/port[X]/iolinkdevice/pin2in` erzeugte (die Hilfsfunktion hängt immer `/iolinkdevice/` an – richtig für `pdin`/`status`/`vendorid` etc., aber falsch für `pin2in`, das direkt unter dem Port liegt). Das führte dazu, dass der Wert immer `None`/`unbekannt` war, obwohl Pin 2 korrekt verdrahtet war. Fix: Pfad direkt als `f"/iolinkmaster/port[{port}]/pin2in"` bauen, ohne `port_path()`.

Falls für Teil 2 weitere direkt-unter-Port-liegende Knoten gebraucht werden (z. B. `mode`), gilt dieselbe Falle: **nicht** `port_path()` verwenden, sondern den Pfad explizit bauen.

## Teil 2 – Portmodus-Umschaltung (Pin 4) — offen

Folgt strukturell exakt dem bestehenden Parameter-Restore-Flow (`restore.py` + `websocket.py:preview_restore`/`restore_parameters`), der genau für "seltene, risikobehaftete, bestätigungspflichtige Schreibaktion" gebaut ist.

**`custom_components/ifm_iolink/api.py`**
- `request()`-Whitelist um den Lesepfad für den aktuellen Portmodus erweitern (`adr.endswith("/mode")`), damit `client.multi()` ihn wie `pdin`/`pin2in` batchen kann.
- Neue eigenständige Methode `write_port_mode(self, port, mode)`, analog zu `write_parameter()`: eigene strikte Validierung (`port` int 1–8, `mode` int aus `{0, 1, 2, 3}` – Disabled/DI/DO/IO-Link, **nicht** aus `request()`-Whitelist erreichbar), ruft `self._request(f"/iolinkmaster/port[{port}]/mode/setdata", {"newvalue": mode}, empty_response=True)`. Payload-Form live verifiziert.

**`custom_components/ifm_iolink/coordinator.py`**
- Portmodus ändert sich selten – wie `PORT_PROPERTIES` nur alle 60 s im `refresh_metadata`-Zweig mitlesen und im Item-Dict als `item["mode"]` ablegen, damit Panel und Websocket-Snapshot den aktuellen Modus ohne Extra-Request anzeigen können. **Pfad direkt bauen** (`f"/iolinkmaster/port[{port}]/mode"`), nicht über `port_path()`.

**Neues Modul `custom_components/ifm_iolink/port_mode.py`** (Geschwistermodul zu `restore.py`)
- `prepare_mode_change(coordinator, port, target_mode)`: liest aktuellen Modus + Portidentität, warnt falls aktuell ein IO-Link-Gerät verbunden ist (`connected`), baut ein reines Vorschau-Dict `{port, current_mode, target_mode, device_connected, assignment_name, profile_id}`. Keine Schreibzugriffe – Vorbild: `prepare_restore` in `restore.py`.
- `execute_mode_change(coordinator, port, plan, record, still_current)`: prüft `still_current()` + unveränderten Zustand seit Vorschau erneut, ruft `coordinator.client.write_port_mode(...)`, liest zurück zur Bestätigung, invalidiert `coordinator.metadata_at = 0` (erzwingt sofortigen Metadaten-Refresh) und räumt `coordinator.condition_values` für den Port auf. Vorbild: `execute_restore` in `restore.py`.

**`custom_components/ifm_iolink/websocket.py`**
- Zwei neue Commands, registriert in `register_commands()`: `ifm_iolink/preview_port_mode` und `ifm_iolink/set_port_mode`.
- Beide nutzen **denselben** `hass.data[DOMAIN]["parameter_backups"].busy`-Set und dieselbe `backups.plans`-Token-Struktur wie `preview_restore`/`restore_parameters` – 1:1 dasselbe Muster (Token via `secrets.token_urlsafe(24)`, 300 s TTL, an `connection.user.id` + `(entry_id, port)` + Coordinator-Objektidentität gebunden, Single-Use-Pop vor Ausführung). Dadurch blockieren sich Parameter-Restore und Moduswechsel am selben Port automatisch gegenseitig.
- `assign` prüft bereits `busy` vor einer Profilzuweisung – das greift unverändert auch während eines laufenden Moduswechsels.
- Nach erfolgreichem `set_port_mode`: `hass.config_entries.async_update_entry(...)` schreibt `entry.options["ports"][port]["mode"]` (neuer Schlüssel neben `profile`/`name`/`location`/`purpose`/`entities`, Default beim Fehlen: `3` = IO-Link). Wechselt ein Port in den DO-Modus (`2`), sollte `profile` dabei auf `"unknown"` zurückgesetzt werden (ein IO-Link-Profil kann keine DO-Prozessdaten decodieren).

**Neues `custom_components/ifm_iolink/switch.py`** (neue Plattform)
- `const.py` – `PLATFORMS` um `"switch"` erweitern.
- Eine Entity **nur für Ports, deren `mode == 2`** (DO, aus `entry.options["ports"][port]["mode"]`): `IfmPin4Switch(IfmEntity, SwitchEntity)`, liest/schreibt den reinen Ausgangszustand über `/iolinkmaster/port[X]/iolinkdevice/pdout` (Hex-String – Struktur bestätigt, exakte Bit-/Byte-Kodierung für den DO-Fall vor der Implementierung noch an einem Port mit `mode=DO` gegenlesen). Das ist die einzige Stelle, an der eine normale, automatisierbare HA-Entity entsteht – der Moduswechsel selbst bleibt Panel-only.
- `__init__.py`s erwartete-`unique_id`-Menge um `prefix + "pin4_do"` erweitern, aber **nur** wenn `mode == 2`, sonst greift die Aufräumlogik korrekt und entfernt das Switch-Entity, sobald ein Port zurück auf IO-Link umgeschaltet wird.

**Frontend (`custom_components/ifm_iolink/frontend/panel.js`)**
- Im Inspector (Bereich analog zu „Sensortausch & Sicherung“) ein neues `<details>` „Portmodus“ mit: aktuellem Modus, einer Auswahl (IO-Link / Digitalausgang), einem Hinweistext bei aktuell verbundenem Sensor, und demselben Vorschau→Bestätigen-Dialogmuster wie `previewRestore()` – neue Methode `previewPortMode()` ruft `preview_port_mode`, öffnet einen `<dialog>` mit Warnung + Checkbox-Bestätigung, ruft bei Bestätigung `set_port_mode`.

## Stand nach 0.5.0

Umgesetzt gegenüber dem ursprünglichen Plan oben, mit zwei bewussten Abweichungen:

- **Kein Whitelist-Eintrag für einen einzelnen `mode`-Lesepfad in `api.py`.** Sowohl der 60-Sekunden-Metadaten-Read im Coordinator als auch der frische Kontroll-Read direkt vor/nach dem Schreiben in `port_mode.py` laufen über `client.multi([...])` (genau wie `read_identity` in `parameters.py`), nicht über einen einzelnen `request()`-Aufruf. `client.multi()` ruft intern `/getdatamulti` auf, das schon in der Whitelist steht; die Pfade *innerhalb* von `datatosend` werden von `request()` gar nicht geprüft. Eine Erweiterung der Whitelist wäre also wirkungslos gewesen. `write_port_mode()` bleibt wie geplant komplett außerhalb von `request()` (eigene Methode, wie `write_parameter()`).
- **Kein separates `record`-Argument bei `execute_mode_change()`.** Anders als `execute_restore` (viele Einzelschritte, die bei einem Absturz mitten im Vorgang einen Fortschrittsbericht brauchen) ist ein Moduswechsel ein einziger atomarer Schreib+Rücklese-Schritt. Es gibt daher keinen Zwischenzustand, der persistiert werden müsste, und keinen `get_port_mode_report`-Websocket-Command.

Token-Kollisionen zwischen Restore- und Portmodus-Vorschauen (beide nutzen denselben `backups.plans`-Dict) werden dadurch verhindert, dass Restore-Pläne unter dem Schlüssel `"plan"` und Portmodus-Pläne unter `"mode_plan"` abgelegt werden; `restore_parameters`/`set_port_mode` prüfen jeweils, dass der passende Schlüssel im gefundenen Token-Eintrag existiert, bevor sie ihn verwenden.

Ausgewählte Ziel-Modi sind im Backend (`port_mode.SWITCHABLE_MODES`) und im Panel bewusst auf `{2, 3}` (Digitalausgang/IO-Link) beschränkt – Disabled/DI sind zwar über `write_port_mode()` technisch erreichbar (API-Validierung erlaubt `{0,1,2,3}`), aber nicht Teil des hier abgedeckten Anwendungsfalls.

Im Panel gibt es dafür keine Dropdown-Auswahl (wie ursprünglich skizziert), sondern einen einzelnen Umschalt-Button, der immer auf den jeweils *anderen* der beiden Modi zeigt („Zu IO-Link wechseln …“ bzw. „Zu Digitalausgang wechseln …“) – einfacher als eine Auswahl, aus der man auch den bereits aktiven Modus wählen könnte.

**`pdout`-Byteformat verifiziert (2026-09-15, gegen echten AL1352 unter 192.168.1.22, Port 7/X07, unbenutzt/`status=0`, mit Zustimmung des Nutzers testweise auf DO geschaltet und danach zurück auf IO-Link):**

- Pfad ist ganz normal unter `iolinkdevice`, anders als `pin2in`/`mode`: `port_path(port, "pdout")` liefert korrekt `/iolinkmaster/port[X]/iolinkdevice/pdout` – **hier darf/muss `port_path()` verwendet werden.**
- Solange der Port nicht im DO-Modus ist, liefert `getdata` auf `pdout` einen Fehlercode (503); direkt nach dem Wechsel auf DO, aber vor dem ersten Schreiben, einen anderen Fehlercode (530, vermutlich „noch kein Wert gesetzt“).
- `setdata` mit `{"newvalue": "01"}` bzw. `{"newvalue": "00"}` funktioniert wie erwartet und wird per `getdata` unverändert zurückgelesen (1-Byte-Hex-String, gleiche Konvention wie `write_parameter`).
- Der Master validiert den Wert nicht als striktes Boolean: `"FF"` wird ebenso akzeptiert und unverändert zurückgelesen; ein zu langer Wert (`"0001"`) wird ohne Fehler auf das erste Byte gekürzt (Rücklesewert `"00"`). Die Implementierung schreibt daher ausschließlich `"01"`/`"00"` und liest beim Anzeigen defensiv „ein/aus“ als `raw != "00"`, statt strikt auf `"01"` zu vergleichen.
- Die physische Ausgangswirkung (tatsächlicher Pegel an Pin 4) wurde nicht mit einem Multimeter nachgemessen, nur die IoT-Core-Registerebene. Sollte ein Nutzer eine Abweichung zwischen `switch`-Zustand und realem Pegel melden, hier zuerst nachsehen.

**Bugfix in 0.5.1:** Die erste `switch.py`-Fassung machte `available` von einem erfolgreichen `pdout`-Read abhängig – aber genau der ist laut obiger Verifikation direkt nach einem Moduswechsel (vor dem ersten Schreiben) ein Fehlercode, nicht `"00"`/`"01"`. Ergebnis: Die Entity blieb dauerhaft "nicht verfügbar" und der Toggle ließ sich nicht bedienen, weil ein erster Schreibzugriff nötig gewesen wäre, den man über eine nicht verfügbare Entity gerade nicht auslösen kann (bestätigt an Port 7 des Testmasters). Fix: `available` hängt jetzt nur noch an `assignment.mode == 2` (der gespeicherten Portzuweisung, dieselbe Quelle, die auch den `pdout`-Read im Coordinator gattet), nicht mehr am `pdout`-Wert selbst; ein nicht gelesener/fehlerhafter `pdout`-Wert gilt als "aus". Zusätzlich schreibt `execute_mode_change()` beim Wechsel auf DO direkt einen Default von `"00"` (aus), damit `pdout` möglichst schnell einen echten Wert hat statt dauerhaft im Fehlerzustand zu bleiben.

Umgesetzt: `IfmClient.write_port_output()` in `api.py`, `pdout`-Read im Coordinator (nur für Ports mit gespeichertem `mode == 2`, um den sonst garantierten Fehlercode für IO-Link-Ports zu vermeiden), `switch.py` mit `IfmPin4Switch`, `PLATFORMS` in `const.py` um `"switch"` erweitert, erwartete-`unique_id`-Menge in `__init__.py` um `prefix + "pin4_do"` (nur bei `mode == 2`).

## Verifikation (Teil 1 + 2)

1. `python -m pytest -q` (bestehende Suite darf nicht brechen – v. a. `tests/test_coordinator.py`, `tests/test_websocket.py`, `tests/test_api.py`, die um Tests für `write_port_mode`, `preview_port_mode`/`set_port_mode` und die `switch`-Plattform zu ergänzen sind).
2. `node --check custom_components/ifm_iolink/frontend/panel.js` nach jeder Panel-Änderung.
3. `python -m ruff check custom_components tests scripts` und `python -m compileall -q custom_components`.
4. Vor der `switch.py`-Implementierung noch das exakte `pdout`-Byteformat für den DO-Fall an einem Port mit `mode=DO` gegenlesen (z. B. Ausgang manuell schalten und `pdout` per `getdata` beobachten).
5. Manueller Test im Command Center (`scripts/preview.py` für UI-Layout, echter Master für Funktionstest): Portmodus-Wechsel eines Test-Ports zu DO, Ausgang per neuem `switch`-Entity schalten, zurück zu IO-Link wechseln und prüfen, dass der ursprüngliche Sensor wieder erkannt wird.

## Teil 3 – Vollständige Portmodus-Auswahl (Deaktiviert/DI/DO/IO-Link) + Pin 4 als Digitaleingang — umgesetzt (ab 0.7.0)

Alle unten geplanten Änderungen sind umgesetzt: `SWITCHABLE_MODES` deckt `{0,1,2,3}` ab, `item["pin4"]` im Coordinator, `IfmPin4DiSensor` in `binary_sensor.py`, Cleanup in `__init__.py`, verallgemeinerter Profil-Reset (`!= 3`) in `websocket.py`, sowie im Panel die 4-Wege-Auswahl (`<select>` statt Toggle-Button) und die einheitliche Portkarten-Darstellung für DO/DI/Deaktiviert inkl. `DI2`/`DI4`/`DO`-Badges mit DIN-EN-60947-5-2-Kontext im Tooltip.

**Physisch verifiziert (2026-09-15, Elias, mit dem echten Zwei-Ausgänge-Sensor am DI-geschalteten Port):** Beide Schaltzustände des Sensors durchgeschaltet – `pdin`/`item["pin4"]`/die `IfmPin4DiSensor`-Entity folgen dem realen Signal korrekt in beide Richtungen. Damit ist Teil 3 vollständig abgeschlossen, keine offenen Punkte mehr.

**Anlass:** Nutzer hat einen konkreten Sensor mit zwei separaten Schaltausgängen, der beide Signale (Pin 2 + Pin 4) gleichzeitig als Digitaleingänge braucht – nicht nur Vollständigkeit der Modus-Abdeckung.

**Klärung mit Elias (2026-09-15):**
- Moduswahl im Panel wird auf eine **echte 4-Wege-Auswahl** umgebaut (IO-Link / Digitalausgang / Digitaleingang / Deaktiviert), statt wie bisher ein Toggle-Button zwischen nur zwei Zielen. `SWITCHABLE_MODES` deckt damit den kompletten von `write_port_mode()` ohnehin schon zugelassenen Wertebereich `{0,1,2,3}` ab – die bisherige Beschränkung auf `{2,3}` entfällt komplett.
- Pin 4 im DI-Modus bekommt eine **eigene `binary_sensor`-Entity**, analog zu Pin 2 und zur bestehenden `IfmPin4Switch` – existiert nur solange `mode == 1`.
- Die Portkarte bekommt für **alle drei Nicht-IO-Link-Modi** (DO, DI, Deaktiviert) eine eigene, konsistente Darstellung in der Kartenmitte (statt „Gerät auswählen“/„Noch nicht zugewiesen“) – nicht nur für DO wie in 0.6.1 bereits umgesetzt. Pin 2 bleibt davon unberührt und zeigt sein `DI2`-Badge immer, unabhängig vom Portmodus (hardwareseitig fest, siehe Context oben).

**API verifiziert (2026-09-15, gegen echten AL1352 unter 192.168.1.22, Port 3, unbenutzt/`status=0`, testweise auf DI geschaltet und danach zurück auf IO-Link):**

| Zweck | Pfad | Format |
|---|---|---|
| Pin-4-DI-Wert lesen (Modus 1) | `/iolinkmaster/port[X]/iolinkdevice/pdin` | **Kein eigenes `pin4in`-Register** – der Pfad wurde vom Master beim Test komplett ignoriert (fehlte in der `getdatamulti`-Antwort, nicht mal ein Fehlercode). Stattdessen läuft der DI-Wert über denselben `pdin`-Knoten, der sonst die IO-Link-Prozessdaten liefert – **`port_path()` ist hier also richtig**, anders als bei `pin2in`/`mode`. |
| `iolinkdevice/status` im DI-Modus | – | Liefert 503 (wie im DO-Fall), da kein IO-Link-Gerät verbunden ist – `connected`-Logik im Coordinator bleibt unverändert korrekt (false), `decode()` läuft nicht an. |

Getestet mit `status=0`/unbeschaltetem Port: `pdin` lieferte `"00"` (Ruhewert). **Am realen Sensor verifiziert (2026-09-15):** Bit 0 wechselt korrekt zwischen `"00"`/`"01"`, wenn der Zwei-Ausgänge-Sensor tatsächlich schaltet – beide Zustände am Testport durchgeschaltet und bestätigt, dass `item["pin4"]`/die `IfmPin4DiSensor`-Entity dem realen Signal folgen.

**Praktischer Vorteil gegenüber Teil 2 (DO):** `pdin` wird vom Coordinator ohnehin **schon jeden Zyklus für jeden Port gelesen** (`paths.extend(port_path(port, name) for name in ("pdin", "status"))`, ungated). Für den DI-Fall ist also kein zusätzlicher, modus-gegateter Read nötig wie bei `pdout` – nur eine zusätzliche Interpretation des ohnehin vorhandenen `raw`-Werts. Damit entfällt auch die in 0.5.1 gefixte Verfügbarkeits-Falle (Register, das erst nach einem Schreibzugriff einen gültigen Wert hat) von vornherein – ein reines Lese-Register hat dieses Henne-Ei-Problem nicht.

**Geplante Änderungen:**

- **`port_mode.py`**: `SWITCHABLE_MODES` von `(2, 3)` auf `(0, 1, 2, 3)` erweitern (alle vier Modi wählbar); Fehlertext in `prepare_mode_change` entfällt weitgehend, da praktisch kein Modus mehr abgelehnt wird (nur noch "bereits in diesem Modus" bleibt als Ablehnungsgrund). Der DO-spezifische Default-Write (`write_port_output(port, False)`) bleibt nur an `actual == 2` gebunden – für DI (`1`) und Deaktiviert (`0`) gibt es nichts zu initialisieren/schreiben.
- **`coordinator.py`**: `item["pin4"]` ergänzen, analog zu `item["pin2"]`/`item["pdout"]` – Wert aus dem ohnehin gelesenen `raw` ableiten, nur wenn `assignment.get("mode") == 1`, sonst `None`: `item["pin4"] = (raw not in (None, "00")) if assignment.get("mode") == 1 else None`. Kein neuer Pfad in der `paths`-Liste nötig.
- **`binary_sensor.py`**: neue Entity `IfmPin4DiSensor` (oder generischer benannt), Vorbild `IfmPin2Sensor`, aber wie `IfmPin4Switch` nur erzeugt wenn `entry.options["ports"][port]["mode"] == 1`. `EntityCategory.DIAGNOSTIC` wie bei Pin 2 (reine Anzeige, kein Schreibzugriff).
- **`__init__.py`**: erwartete-`unique_id`-Menge um `prefix + "pin4_di"` erweitern, nur wenn `mode == 1` (Aufräumlogik entfernt die Entity automatisch beim Zurückschalten, wie schon bei `pin4_do`).
- **`websocket.py`** (`set_port_mode`): Profil-Reset-Bedingung von `if result["mode"] == 2:` auf `if result["mode"] != 3:` verallgemeinern – ein DI- oder deaktivierter Port kann genauso wenig IO-Link-Prozessdaten decodieren wie ein DO-Port, `profile`/`entities` müssen also in allen drei Fällen auf `"unknown"`/`[]` zurückgesetzt werden. Deckt Modus `0` automatisch mit ab, da `!= 3` alle drei Nicht-IO-Link-Ziele erfasst.
- **Frontend (`panel.js`) – Moduswahl**: `<details>`-Block „Portmodus“ von Einzel-Toggle-Button auf ein `<select>` mit vier Optionen (IO-Link / Digitalausgang / Digitaleingang (Pin 4) / Deaktiviert) umbauen; „Wechseln“-Button nur aktiv, wenn Auswahl ≠ aktueller Modus; `previewPortMode(targetMode)` bleibt inhaltlich unverändert (nimmt schon einen beliebigen `targetMode` entgegen). Hinweistext im Vorschau-Dialog dynamisch aus `MODE_NAMES`-Bezeichnungen aufbauen statt hart auf „Digitalausgang“ zu verweisen (Backend hat `MODE_NAMES` in `port_mode.py` bereits, Frontend müsste das analog nachbilden, z. B. als kleines JS-Objekt wie `MODE_NAMES` in `panel.js` bereits für die Badges existiert).
- **Frontend (`panel.js`) – Portkarte für alle drei Nicht-IO-Link-Modi**: Die in 0.6.1 eingeführte `isDo`-Verzweigung in `portCard()` auf alle drei Fälle verallgemeinern (z. B. über eine kleine Lookup-Tabelle `mode → {icon, title, detail}` statt eines einzelnen Booleans), damit device-row und `unknown-device`-Icon konsistent befüllt werden:
  - `mode===2` (DO, bereits umgesetzt): Icon-Box „DO“, Titel „Digitalausgang (Pin 4)“, Detail „24 V · max. 300 mA“.
  - `mode===1` (DI, neu): Icon-Box „DI“, Titel „Digitaleingang (Pin 4)“, Detail „11–30 V high / 0–5 V low“ (aus dem Datenblatt-Kontext oben im Dokument, gleiche Spezifikation wie Pin 2).
  - `mode===0` (Deaktiviert, neu): Icon-Box z. B. „—“, Titel „Port deaktiviert“, Detail z. B. „Pin 4 ist ausgeschaltet“.
  - `mode===3` (IO-Link): unverändert das bisherige profilbasierte Verhalten.
  - Pin-2-`DI2`-Badge bleibt in allen vier Fällen unverändert sichtbar (siehe Context: hardwareseitig unabhängig vom Portmodus).
- **Badge-Namenskonvention geklärt (2026-09-15):** Kompakte Karten-Badges bleiben **pin-/funktionsbasiert**, nicht sensor-/normbasiert, weil der Master nur weiß, dass ein Pin elektrisch ein DI ist, nicht wofür der angeschlossene Sensor die Ader tatsächlich nutzt (nach DIN EN 60947-5-2 ist Pin 2/weiße Ader zwar häufig ein zweiter Schaltausgang (NC/Antivalent), bei manchen Sensoren aber auch Diagnose- oder Teach-In-Leitung – eine feste “Ausgang 2”/”Q2”-Beschriftung wäre also nicht für alle Profile korrekt). Deshalb:
  - Pin-2-Badge wird von `DI` auf **`DI2`** umbenannt (bisher `data-pin2`, Text `DI`).
  - Pin-4-DI-Badge heißt **`DI4`**.
  - Pin-4-DO-Badge bleibt `DO` (unverändert, da als einziges DO-Badge pro Port ohnehin eindeutig).
  - Die DIN-EN-60947-5-2-Begriffe (Hauptschaltausgang/Ausgang 1 für Pin 4, zweiter Schaltausgang/Ausgang 2 für Pin 2) wandern stattdessen in die `title`-Tooltips der Badges, z. B. `title=”Digitaleingang Pin 2 · Ausgang 2 nach DIN EN 60947-5-2 (oft NC/Antivalent, je nach Sensor auch Diagnose/Teach-In)”` bzw. für Pin 4 `title=”Digitaleingang Pin 4/C-Q · Hauptschaltausgang (Ausgang 1, meist NO) nach DIN EN 60947-5-2”` – dort ist Kontext ohne Fehlbehauptung möglich, weil es nur beim Hover als Zusatzinfo erscheint statt als feste Beschriftung.

**Verifikation (zusätzlich zu oben) — beide erledigt (2026-09-15):**
6. ✅ Sensor an einen DI-geschalteten Port angeschlossen: `pdin` bestätigt Bit 0 spiegelt den tatsächlichen Signalzustand wider (nicht nur den Ruhewert `"00"` bei offenem Eingang).
7. ✅ Test mit beiden Signalen gleichzeitig (Pin 2 über `pin2in`, Pin 4 über `pdin`) am konkreten Zwei-Ausgänge-Sensor durchgeführt – beide Zustände korrekt geschaltet. Teil 3 ist damit vollständig abgeschlossen.

## Nachtrag: aktives DO-Badge blieb farblos (behoben in 0.7.2/0.7.3)

**Meldung (2026-09-16, Elias, am echten AL1352 im Labor, Port 3 auf DO):** Nach der Farbumstellung des DO-Badges (gelbgrün → tomatenrot, 0.7.1) blieb das Badge bei aktivem Ausgang grau statt eingefärbt, obwohl die `switch`-Entity "Digitalausgang (Pin 4)" korrekt "An" zeigte – zwei unabhängige Ursachen, beide behoben:

1. **`coordinator.py` (0.7.2):** Das Panel färbt das Badge anhand des **live vom Gerät gelesenen** Modus (`item["mode"]`), ob `pdout` überhaupt abgefragt wurde, hing aber nur an der **gespeicherten Zuweisung** (`assignment.get("mode") == 2`) – zwei unterschiedliche Quellen für dasselbe Konzept, die kurz nach einem Moduswechsel oder beim allerersten Poll-Zyklus auseinanderlaufen konnten. Fix: `pdout`/`pin4` werden jetzt abgefragt/exponiert, sobald *entweder* die Zuweisung *oder* der zuletzt vom Gerät gelesene Modus DO/DI ist, inklusive unconditional auf jedem Metadaten-Refresh-Tick. Regressionstests: `test_pdout_is_read_when_device_reports_do_even_if_assignment_is_stale`, `test_pin4_di_value_is_read_when_device_reports_di_even_if_assignment_is_stale` in `tests/test_coordinator.py`.
2. **`panel.js` (0.7.3):** Die Stylesheet-`<link>`-Injektion für `panel.css` hatte anders als `panel.js` (das schon `?v=<version>` nutzt) **kein Cache-Busting**. Ein Browser konnte dadurch trotz Hard-Reload der Seite dauerhaft eine veraltete `panel.css` (ohne die `.do-on`-Regel aus 0.7.1) ausliefern, weil das Stylesheet erst beim Aufbau des Panel-Shadow-DOM nachgeladen wird, nicht beim initialen Seitenaufruf. Fix: `href="${BASE}/panel.css?v=${this.data.version}"`.

Am Nutzer bestätigt (2026-09-16, nach Update auf 0.7.3 + Neustart + Hard-Reload): Badge färbt sich jetzt korrekt tomatenrot bei aktivem Ausgang. Keine offenen Punkte mehr – der Plan bleibt abgeschlossen.

## Offener Punkt (2026-09-22): DO-Schreibpfad sollte live gemeldeten Modus vor jedem Write prüfen

Aufgefallen bei der Planung eines separaten Features (herstellerspezifische Kommandos, siehe `docs/commands-plan.md`), das denselben rohen Schreibpfad (`write_parameter`/`write_port_output`) nutzt und dafür eine Identitätsprüfung vor dem Schreiben bekommt. Dabei fiel auf: `switch.py:IfmPin4Switch._write()` schreibt aktuell **ungeprüft** auf `pdout`, sobald die Entity aufgerufen wird – `available` hängt nur an der **gespeicherten** Zuweisung (`assignment.get("mode") == 2`, siehe Bugfix in 0.5.1 oben), nicht am **live vom Master gemeldeten** Modus (`item["mode"]`/`identity.get("mode")`). Die beiden Werte laufen normalerweise synchron (ein Moduswechsel läuft über `set_port_mode` inkl. Options-Update und Reload), aber ein kurzes Zeitfenster zwischen einem Moduswechsel und dem nächsten Metadaten-Refresh ist nicht ausgeschlossen – dann würde ein Toggle-Klick `pdout` auf einen Port schreiben, der laut Gerät gerade gar nicht mehr im DO-Modus ist.

**Nicht kritisch wie der ursprüngliche 0.5.1-Bug** (der betraf `available`/Anzeige, das hier ist ein Randfall beim Schreiben), aber im Sinne derselben "vor jedem Schreibzugriff den aktuellen Zustand frisch verifizieren"-Sorgfalt wie beim Portmodus-Wechsel selbst (`still_current`-Prüfung in `port_mode.py`) oder wie sie jetzt für `send_command` eingeführt wird (Identitätsprüfung vor jedem Schreiben, siehe `docs/commands-plan.md`).

**Mögliche Umsetzung, noch nicht geplant/entschieden:** `_write()` in `switch.py` liest vor dem eigentlichen `write_port_output()`-Aufruf den aktuell vom Master gemeldeten Portmodus frisch (z. B. über denselben `/iolinkmaster/port[X]/mode`-Pfad wie im Coordinator-Metadaten-Refresh) und bricht mit einer verständlichen Fehlermeldung ab, falls dieser nicht (mehr) `2` (DO) ist, statt den Wert blind zu schreiben. Braucht wie alle Schreibpfade in diesem Repo eine Verifikation an echter Hardware vor dem Release (Port kurz nach einem Moduswechsel schalten, während `pdout` noch stale sein könnte).

Ausdrücklich als eigener, von den Commands nicht abhängiger Task behandeln – bewusste Entscheidung bei der Planung des Commands-Features (2026-09-22), um bereits ausgeliefertes Verhalten nicht nebenbei mitzuändern.
