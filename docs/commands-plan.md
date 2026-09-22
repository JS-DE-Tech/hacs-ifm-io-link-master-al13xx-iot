# Herstellerspezifische Kommandos im Geräteprofil

Arbeitsnotiz/Plan, nicht Teil der Nutzer-Doku. Umgesetzt ab Version 0.8.0, Bugfix in 0.8.1. Nutzerdoku dazu in `docs/device-profiles.md`.

## Bugfix in 0.8.1: Eindeutigkeit fälschlich auf Index statt auf Index+Wert geprüft

**Gemeldet von Elias (2026-09-22)** anhand eines realen Profils (ifm KQ1000, kapazitiver Füllstandssensor): Der System-Command-Parameter des Sensors liegt auf einem einzigen Index (2), verschiedene Werte lösen aber unterschiedliche Aktionen aus (`208` = leeren Tank abgleichen, `209` = vollen Tank abgleichen) – ein bei IO-Link-„System Command“-Parametern verbreitetes Muster. Die ursprüngliche Validierung in `decoder.py` verlangte einen **innerhalb des Profils eindeutigen Index**, was genau diesen (eigentlich korrekten) Fall ablehnte. Zusätzlich hätten der `send_command`-Websocket-Handler und der Panel-Button dasselbe Problem gehabt: beide identifizierten ein Kommando bisher nur über `index`, hätten bei zwei Kommandos am selben Index also immer das erste gefunden/gesendet, unabhängig davon, welcher Button geklickt wurde.

**Fix:** Eindeutig sein muss die Kombination aus `index` **und** `value`, nicht der Index allein.

- `decoder.py`: `validate_profile` prüft jetzt `(index, value)`-Tupel statt nur `index`.
- `websocket.py`: `send_command` erwartet jetzt zusätzlich `value` in der Nachricht und sucht das Kommando über `index` **und** `value`.
- `panel.js`: Button trägt zusätzlich `data-command-value`, das Ausgabe-Element bekommt die ID `command-${index}-${value}` statt nur `command-${index}`; der Klick-Handler schickt beide Werte mit.
- Tests ergänzt: zwei Kommandos am selben Index mit unterschiedlichem Wert werden jetzt akzeptiert; ein Test sendet gezielt das zweite von zwei Kommandos am selben Index und prüft den korrekt kodierten Wert; ein Test prüft, dass ein bekannter Index mit falschem Wert abgelehnt wird.

Kein Schaden entstanden, da das Feature zum Meldezeitpunkt gerade erst released war (0.8.0) und noch nicht produktiv mit einem solchen Profil genutzt wurde.

## Context

Manche IO-Link-Sensoren benötigen zur Einrichtung oder Kalibrierung spezielle
Schreibkommandos (Index/Subindex + fester Integerwert), die nicht Teil der
IODD-Beschreibung sind und daher nicht automatisch aus dem Profil übernommen
werden können (z. B. „Kalibrierung starten“, „Werksreset“). Aktuell lässt sich
in der Gerätebibliothek nur eine `parameters`-Liste pflegen, die für
lesbare/skalierte Werte gedacht ist (Decoder, Entity-Anbindung als
Sensor/Number/Select). Für einen reinen, festen Schreibbefehl ist das
überdimensioniert.

Ziel: pro Geräteprofil eine neue, einfache `commands`-Liste (Index + fester
Integerwert 0–255, Subindex ist auf allen bisher verwendeten Sensoren 0 und
bleibt fest codiert), die auf der Portübersicht als eigener Bereich
„Kommandos anzeigen“ erscheint (neben der bestehenden „Parameterliste
anzeigen“) und dort per Klick direkt gesendet werden kann — ohne
Bestätigungsdialog, analog zu den bestehenden „Lesen“-Buttons.

Klärung mit Elias: Subindex bleibt fest auf 0 codiert (alle bisher
verwendeten Sensoren nutzen nur Subindex 0), Wertetyp ist immer uint8
(0–255). Beim Senden gibt es bewusst keinen Bestätigungsdialog wie beim
Portmodus-Wechsel — der Wert steht ja fest im Profil, ein Klick auf „Senden“
genügt, analog zu den bestehenden „Lesen“-Buttons in der Parameterliste.
Kommandos werden **nicht** als eigene Home-Assistant-Entity (z. B. `button`)
exponiert, bleiben reines Panel-Feature — Automatisierbarkeit war explizit
kein Ziel dieser Runde.

**Wichtige Ergänzung nach Plan-Review (Elias, 2026-09-22):** Da `send_command`
anders als `read_parameter` tatsächlich auf das Gerät schreibt, und dabei
bewusst ohne Bestätigungsdialog auskommt, muss vor dem Schreiben die
Gerätekennung (vendorid/deviceid) frisch geprüft und gegen `profile["match"]`
abgeglichen werden — analog zu `parameters.py:collect_parameters` und dem
Restore-Flow. `coordinator.data[port]["connected"]` allein reicht nicht: das
Feld bedeutet nur „irgendein Gerät antwortet am Port“, ein
Identitäts-Mismatch landet nur im separaten `item["error"]`-Text (siehe
`coordinator.py` Zeilen 74-82), ohne `connected` zu beeinflussen. Ohne
zusätzliche Prüfung würde `send_command` bei einem Sensortausch ohne
Profil-Anpassung den festen Byte-Wert klaglos auf einen andersartigen Sensor
schreiben. Das damit verwandte, aber eigenständige Thema „DO-Schreibpfad
(`switch.py`) sollte den live gemeldeten Portmodus vor jedem `pdout`-Write
frisch prüfen“ ist **nicht** Teil dieses Plans, sondern als offener Punkt in
`docs/port-mode-plan.md` ergänzt.

## Bestehende Bausteine, die wiederverwendet werden

- `decoder.py:validate_profile` — Validierung von Profilen inkl. `parameters`
  (Zeilen ~208-229); wird um einen `commands`-Block erweitert.
- `api.py:IfmClient.write_parameter(port, index, raw_hex)` — schreibt bereits
  mit fest codiertem `subindex=0`; **keine Änderung nötig**, passt exakt.
- `websocket.py:read_parameter` (Zeile 177-200) — Muster für den neuen
  `send_command`-Handler: Coordinator holen, Port-Verbindung prüfen, Profil
  vom zugewiesenen Port laden, Eintrag per Index suchen.
- `panel.js` Zeile 83 (`profile.parameters?.length? ... : ...`) — Vorbild für
  den neuen `commands`-Abschnitt; `.parameter`-CSS-Klasse (panel.css) wird
  für die Zeilen wiederverwendet, keine neue CSS nötig.
- `panel.js` Zeilen 137-141 (`[data-read]`-Click-Handler) und
  `this.parameterBusy` — Vorbild für den neuen `[data-command]`-Handler
  (gleiches Busy-Set, gleiches `portKey()`).

## Geplante Änderungen

### 1. `decoder.py`
- `"commands"` zu `PROFILE_KEYS` hinzufügen.
- Neuer Validierungsblock nach der bestehenden `parameters`-Schleife:
  - `commands` optional, Liste, max. 64 Einträge.
  - Je Eintrag erlaubte Felder: `index`, `value`, `name`, `description`.
  - `index`: Ganzzahl 0–65535, **muss innerhalb des Profils eindeutig sein**
    (Subindex ist immer 0, also identifiziert `index` allein den Befehl).
  - `value`: Ganzzahl 0–255 (uint8).
  - `name`, `description`: String, ≤4000 Zeichen (gleiche Grenze wie bei
    `parameters`).
- Neue kleine Hilfsfunktion `encode_command(command) -> str`, die den festen
  `value` als ein Hex-Byte kodiert (`value.to_bytes(1, "big").hex().upper()`).
  Eigene Funktion statt Inline-Code im Websocket-Handler, damit sie isoliert
  testbar ist (analog zu `encode_parameter`).

### 2. `websocket.py`
- Neuer Handler `send_command`, registriert in `register_commands`. Anders
  als im ersten Entwurf reicht `port["connected"]` **nicht** als Schutz —
  vor dem Schreiben wird die Gerätekennung frisch gelesen und gegen
  `profile["match"]` geprüft, analog zu `read_identity` +
  `collect_parameters` in `parameters.py`:
  ```python
  @websocket_api.websocket_command({
      vol.Required("type"): "ifm_iolink/send_command",
      vol.Required("entry_id"): str,
      vol.Required("port"): int,
      vol.Required("index"): int,
  })
  @websocket_api.require_admin
  @websocket_api.async_response
  async def send_command(hass, connection, message):
      try:
          coordinator = coordinator_for(hass, message)
          port_state = coordinator.data[str(message["port"])]
          if not port_state["connected"]:
              raise ValueError("Port nicht verbunden")
          profile = coordinator.library.all.get(port_state["profile"], {})
          command = next((c for c in profile.get("commands", []) if c["index"] == message["index"]), None)
          if not command:
              raise ValueError("Kommando nicht im zugewiesenen Profil")
          identity = await read_identity(coordinator, message["port"])
          matches = profile.get("match", [])
          if matches and all(
              identity.get("vendorid") != m["vendorid"] or identity.get("deviceid") != m["deviceid"]
              for m in matches
          ):
              raise ValueError("Gerätekennung passt nicht zum zugewiesenen Profil")
          raw = encode_command(command)
          await coordinator.client.write_parameter(message["port"], command["index"], raw)
          connection.send_result(message["id"], {"sent": True})
      except (ValueError, IfmError) as err:
          connection.send_error(message["id"], "command_failed", str(err))
  ```
- Import `encode_command` zusätzlich zu `decode, validate_profile` aus
  `.decoder`, sowie `read_identity` aus `.parameters` (bereits vorhandene
  Funktion, liest `vendorid`/`deviceid`/`serial`/`status` frisch und wirft
  `ValueError`, falls kein Gerät verbunden ist — deckt den
  `connected`-Check danach im Grunde doppelt ab, der explizite
  `port["connected"]`-Check vorher bleibt aber als billiger Fast-Fail ohne
  Netzwerk-Roundtrip erhalten).
- Kein Preview/Token-Flow (der Wert steht fest im Profil, Nutzer hat sich für
  „direkt senden“ entschieden) — kein `busy`-Lock nötig, da `read_parameter`
  ebenfalls keinen hat. Die Identitätsprüfung ersetzt hier bewusst den
  Bestätigungsdialog: sie verhindert das falsche Ziel, nicht den falschen
  Zeitpunkt.

### 3. `panel.js`
- Neuer Abschnitt direkt nach dem bestehenden `profile.parameters?.length`-
  Block (Zeile 83), unabhängig davon sichtbar (auch wenn ein Profil nur
  `commands`, aber keine `parameters` hat):
  ```
  ${profile.commands?.length?`<details><summary>Kommandos anzeigen</summary>
    <p class="field-help">Sendet einen festen, nicht in der IODD beschriebenen
    Wert an Index/Subindex 0 des Sensors, z. B. zum Starten einer Kalibrierung
    oder eines Werksresets.</p>
    ${profile.commands.map(c=>`<div class="parameter"><div><b>${esc(c.name)}</b>
      <small>Index ${c.index} · Wert ${c.value} · ${esc(c.description)}</small>
      <output id="command-${c.index}"></output></div>
      <button data-command="${c.index}" title="Kommando ${esc(c.name)} senden">Senden</button></div>`).join('')}
    </details>`:''}
  ```
- In `bindOverview()`, analog zu `[data-read]`:
  ```js
  this.shadowRoot.querySelectorAll('[data-command]').forEach(b=>b.onclick=async()=>{
    const key=this.portKey(),index=b.dataset.command,entry_id=this.masterId,port=this.port;
    if(this.parameterBusy.has(key))return;this.parameterBusy.add(key);this.paintParameters();
    const output=this.shadowRoot.querySelector(`#command-${index}`);
    try{await this.call('send_command',{entry_id,port,index:Number(index)});if(output)output.textContent='Gesendet.';}
    catch(e){if(output)output.textContent=`Fehler: ${e.message || e}`;}
    finally{this.parameterBusy.delete(key);this.paintParameters();}
  });
  ```
- `paintParameters()`: `[data-command]` mit in die Busy-Disable-Selektorliste
  aufnehmen (Zeile 171), damit Kommando-Buttons während einer laufenden
  Parameteraktion am selben Port gesperrt sind (und umgekehrt).

Kein neuer Editor auf der Gerätebibliotheks-Seite nötig: eigene Profile
werden dort bereits als freies JSON im Textfeld „Übersetzungsprofil“
bearbeitet (`panel.js` Zeile 111), ein `commands`-Array lässt sich dort genau
wie `parameters` von Hand eintragen.

### 4. Tests
- `tests/test_decoder.py`: `validate_profile` mit gültigem/ungültigem
  `commands`-Block (Feldgrenzen, doppelter Index, `value` außerhalb 0–255,
  unbekannte Felder) sowie `encode_command`.
- `tests/test_websocket.py`:
  - `"send_command"` zur parametrisierten Namensliste in
    `test_commands_reject_non_admin_before_scheduling` hinzufügen (Zeile
    90-111).
  - Neuer Test analog zum bisherigen Umgang mit `read_parameter`-artigen
    Handlern: Erfolgsfall (schreibt korrektes Hex-Byte über
    `client.write_parameter`), Fehlerfälle (Port nicht verbunden, Index nicht
    im Profil, `IfmError` beim Schreiben), **und explizit: Gerätekennung
    passt nicht zu `profile["match"]` → `write_parameter` wird NICHT
    aufgerufen** (Kernverhalten der neuen Härtung, analog zu den bestehenden
    Mismatch-Tests in `tests/test_restore.py`).
- `tests/test_api.py` und `test_parameters.py`: keine Änderung nötig, da
  `write_parameter` unverändert bleibt.

### 5. Dokumentation
- `docs/device-profiles.md`: kurzer neuer Abschnitt neben der bestehenden
  `parameters`-Beschreibung (Zeile 37), der das `commands`-Schema
  (Index/Wert/Name/Beschreibung, fester Subindex 0, uint8) und das
  „Kommandos anzeigen“-UI-Verhalten beschreibt.

## Verifikation

1. `pytest tests/test_decoder.py tests/test_websocket.py -q` — neue und
   bestehende Tests grün.
2. Manuell: Home Assistant mit dieser Integration starten, ein eigenes
   Testprofil in der Gerätebibliothek um einen `commands`-Eintrag ergänzen,
   speichern, Port zuweisen, auf der Portübersicht „Kommandos anzeigen“
   öffnen, „Senden“ klicken und per Debug-Datei / Sensor-Reaktion
   verifizieren, dass exakt das erwartete Byte auf Index/Subindex 0
   ankommt.
3. Versionsbump in `manifest.json` (neues Feature → Minor-Version) gemäß dem
   etablierten Release-Vorgehen (Tag + GitHub Release), letzter Schritt vor
   dem Release.
