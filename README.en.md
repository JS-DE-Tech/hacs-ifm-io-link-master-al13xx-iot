# ifm IO-Link Command Center for Home Assistant

[Deutsch](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/blob/main/README.md) | **English**

<p align="center">
  <img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/custom_components/ifm_iolink/brand/icon.png" alt="ifm IO-Link project logo" width="100">
</p>

<p align="center"><strong>Industrial sensors for your smart home.<br>Pool, heating and compressed air – connected locally, monitored together.</strong></p>

[![Version](https://img.shields.io/badge/version-0.8.2-blue)](https://github.com/100prznt/hacs-ifm-io-link-master-al13xx-iot/blob/main/custom_components/ifm_iolink/manifest.json)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5?logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Repository-41BDF5)](https://www.hacs.xyz/)
[![Tests](https://github.com/100prznt/hacs-ifm-io-link-master-al13xx-iot/actions/workflows/tests.yml/badge.svg)](https://github.com/100prznt/hacs-ifm-io-link-master-al13xx-iot/actions/workflows/tests.yml)
[![Local](https://img.shields.io/badge/Connection-Local-success)](#features)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/blob/main/LICENSE)
[![Support via PayPal](https://img.shields.io/badge/Support%20via-PayPal-0070BA?logo=paypal&logoColor=white)](https://paypal.me/JensSaffrich)

> 🔀 **This is a fork.** This repository is a fork of [JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot), maintained by [100prznt](https://github.com/100prznt). It includes additional changes made in this fork on top of the original – see [Changes in this fork](#changes-in-this-fork).

The **ifm IO-Link Command Center** connects **AL1350 and AL1352 IO-Link masters with IoT Core** directly to Home Assistant. Pressure, flow, temperature and device status become useful entities for dashboards, history and your own automations – without a cloud service, MQTT broker or Node-RED in between.

The graphical Command Center places the master at the centre, with connections to its devices. Each device shows its image, name, location, purpose and live readings. A shared device library, IODD import and parameter backups help you manage the entire installation in one place.

**A project by [JS-DE-Tech](https://github.com/JS-DE-Tech), developed for a real pool, heating and compressed-air installation.**

<p align="center">
  <img src="docs/images/screenshots/portuebersicht_v0_7.png" alt="Command Center showing an AL1352 with connected sensors, live readings, port assignment and DIO status" width="1100">
</p>

<p align="center"><a href="#features">Features</a> · <a href="#my-real-world-project">My project</a> · <a href="#installation">Installation</a> · <a href="#parameter-backup-and-sensor-replacement">Parameter backups</a> · <a href="#custom-devices-and-iodd-import">Custom devices</a></p>

## Changes in this fork

Compared to the original project by JS-DE-Tech, this fork so far adds:

- **Parameters as Home Assistant entities (from 0.2.0):** manufacturer parameters can be opted into per port in the parameter list, each becoming its own entity – a `sensor` (read-only) or, for writable integer parameters, a `number` (free numeric range) or `select` (fixed set of values, e.g. percentage steps) entity, both settable from Home Assistant too. All three read independently of the fast process-data poll: on startup, after every change, and hourly. See [Parameters as a Home Assistant entity](docs/device-profiles.md#parameter-als-home-assistant-entity) for details.
- **Master diagnostics as entities (from 0.3.0):** supply voltage, power consumption (derived from voltage × current, since the master itself reports no direct power value), temperature and supervision status of the master (the AL1350/AL1352 itself, not the connected sensors) are each exposed as a `sensor` or `binary_sensor` entity, and shown as a summary on the port overview page too.
- **Pin 2 digital input as an entity (from 0.4.0):** pin 2 of every IO-Link port is always a digital input at the hardware level, regardless of the port's mode or any assigned device profile. Now exposed as its own `binary_sensor` entity per port, and shown in the Command Center too.
- **Port-mode switching for pin 4 (from 0.5.0):** pin 4 (C/Q) of every port can be switched in the Command Center between IO-Link communication and a digital output – with a checked preview and confirmation, mirroring the parameter restore flow, since switching disconnects any connected IO-Link sensor from that port. A port in DO mode additionally gets its own `switch` entity for the raw output state (on/off) – automatable like any other Home Assistant entity.
- **Version display (from 0.6.0):** the port overview's footer shows the installed version. Update notifications themselves are deliberately not duplicated here – HACS already provides its own `update` entity for that (visible under Settings → Devices & Services or the Updates overview) once this repository has releases.
- **Pin 2/Pin 4 status directly on the port card (from 0.6.1):** next to the connector name (X01, X02, …) a small badge shows the live state of the digital input (pin 2); if a port is configured as a digital output, a second badge for its switching state appears too, and the card centre shows "Digital output (pin 4) · 24 V, max. 300 mA" instead of "Select a device".
- **Pin 4 as a digital input too, full mode selection (from 0.7.0):** pin 4 (C/Q) can now be switched between IO-Link, digital output, digital input and disabled (previously only IO-Link/digital output) – via a proper selector instead of a single toggle button, still with preview and confirmation. In digital-input mode, pin 4 gets its own `binary_sensor` entity, and the port card shows a matching short description and badges (`DI2`/`DI4`/`DO`) for all three non-IO-Link modes.
- **Manufacturer commands (from 0.8.0):** device profiles can now define their own fixed write commands not covered by the IODD – a fixed index and integer value, e.g. to start a calibration or trigger a factory reset. They show up in the Command Center under **Show commands**, right next to the parameter list; a click sends the fixed value immediately. Before sending, the connected device's identity is checked fresh against the profile, so a sensor swapped in the meantime doesn't accidentally receive the same command. See [Device profile format and examples](docs/device-profiles.md) for details.

## Features

| Feature | What it offers |
|---|---|
| **Direct local connection** | Process data goes directly from the IoT Core to Home Assistant. The default polling interval is two seconds and can be configured per master. |
| **Master discovery and setup** | DHCP discovery, scanning a specified private IPv4 network or entering the IoT address manually. Model and serial number are checked. |
| **Graphical port overview** | Master image, connecting lines, device cards and current readings in the dedicated **ifm IO-Link** Home Assistant sidebar panel. |
| **Multiple masters** | Switch between installations, rename masters and remove them from Home Assistant when needed. |
| **Shared device library** | Create a profile once and reuse it on several ports. Device name, location and purpose remain individual to each connection. |
| **Manufacturer file import** | Read IODD ZIP/XML files, select variants and import supported process data, parameters and images. |
| **Custom devices** | Edit descriptions, images and JSON decoding profiles, then test the decoding against a raw value. |
| **Unknown device diagnostics** | Download a debug file containing raw values and device identification to help create a profile, including with assistance from ChatGPT. |
| **Read device parameters** | Read individual values or all manufacturer parameters defined in the profile at the click of a button. |
| **Backup and restore** | Store parameter backups per port, export/import JSON, review a restore preview and download the restore report. |
| **Home Assistant entities** | Sensors and binary sensors for measurements and status, ready for your own charts, notifications and automations. |
| **Parameters as entities** | Pick individual manufacturer parameters per port in the parameter list; each becomes its own `sensor` (read-only) or, for writable integer parameters, a `number` or `select` entity you can also set from Home Assistant. |
| **Master diagnostics as entities** | Supply voltage, power consumption, temperature and supervision status of the master itself as a `sensor` or `binary_sensor` entity, and as a summary on the port overview. |
| **Pin 2 digital input as an entity** | Pin 2 of every IO-Link port is always a digital input at the hardware level, regardless of port mode or assigned profile – available as its own `binary_sensor` entity per port. |
| **Port-mode switching (pin 4)** | Switch between IO-Link, digital output, digital input and disabled in the Command Center – with preview and confirmation, since switching disconnects a connected sensor from the port. A DO-mode port exposes the output state as a `switch` entity, a DI-mode port the input state as a `binary_sensor` entity. |
| **Version display** | The installed version is visible directly on the port overview. HACS shows updates themselves via its own `update` entity. |
| **Manufacturer commands** | Fixed write commands (index + integer value) defined in the profile, for actions the IODD doesn't cover, e.g. starting a calibration – sent directly from the Command Center. |

Routine measurement polling reads the devices. Manufacturer parameters selected as entities are read on startup, after every change and once an hour. **Writes otherwise only happen during an explicitly confirmed parameter restore, or when you set a parameter's `number` entity.** The integration does not configure master network settings; the IO-Link port operating mode (IO-Link/digital output/digital input/disabled) can only be changed via the checked preview in the Command Center since 0.5.0, never automatically or through an automation.

## A look inside the Command Center

**Your installation at a glance:** The port overview above shows the AL1350 at the centre, its connected sensors and their current readings. Clicking a port opens device assignment, location and purpose on the right, together with process values, manufacturer parameters and backup functions. The screenshot comes from my running installation.

**Create once, reuse across ports:** The device library contains both bundled and custom profiles. Import manufacturer IODDs or use the profile editor to add device information, images and raw-data decoding, and test the result. The same profile can then be selected on multiple ports.

<p align="center">
  <img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/screenshots/geraetebibliothek.png" alt="Device library with BADU and ifm profiles, IODD import and a custom device editor" width="1100">
</p>

## My real-world project

I wanted to do more than read values on the devices themselves: I wanted to spot changes in my home systems early in Home Assistant. Working Node-RED decoders were the starting point. They became a standalone integration with a shared interface for the connected IO-Link sensors.

<p align="center">
  <img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/pool.jpeg" alt="Pool equipment with filter, flow measurement and an ifm IO-Link master" width="900">
</p>

### Pool filter: knowing when cleaning is needed

An **ifm PN7096** measures pressure at the pool filter. Its history helps me assess when the filter is becoming dirty and cleaning or backwashing may be needed. The useful reference is a clean filter at comparable pump output and valve positions. A single pressure reading is not a direct measurement of the degree of fouling.

### Flow and temperature: monitoring water circulation

The **Speck BADU FlowSonic Plus** provides flow, water temperature, totalizers and status information. I use these readings to monitor **active pool winter operation**, keeping the water circulating during winter, and to identify unusual circulation conditions early: low flow while the pump is running, an unsuitable valve position or interrupted circulation.

Looking at pressure and flow together is particularly helpful. A notification can draw attention to a problem; its specific cause still needs to be checked. The integration supplies the readings, while installation-specific thresholds and winter automations are configured in Home Assistant.

### Heating circuit: spotting pressure loss early

Another **PN7096** monitors heating-circuit pressure. History and custom notifications help identify when the circuit needs checking and, where appropriate, when heating water needs topping up. The integration does not refill the system itself.

### Compressed air: keeping an eye on control pressure

**PN7094 sensors** measure pressure at the compressor, distribution manifold and receiver. This lets me identify pressure drops and differences between measurement points, and monitor whether the required pneumatic control pressure is available. The existing installation remains responsible for pressure regulation.

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/poolfilter.jpeg" alt="PN7096 mounted on the pool filter"><br><strong>Pool filter pressure</strong></td>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/flowsonic-plus.jpeg" alt="BADU FlowSonic Plus in the water circuit"><br><strong>Flow and water temperature</strong></td>
</tr>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/heizung.jpeg" alt="PN7096 monitoring heating-circuit pressure"><br><strong>Heating-circuit monitoring</strong></td>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/druckluft.jpeg" alt="PN7094 and AL1350 in the compressed-air installation"><br><strong>Compressed air and control pressure</strong></td>
</tr>
</table>

### Power supplied through a PoE splitter

In my installation, a **PoE splitter/converter** powers the AL1350 and its connected sensors from a PoE feed. The splitter separates networking and power: Ethernet goes to the IoT port, and the appropriate DC output goes to the master's power input. This allows the sensors to be powered centrally through the network infrastructure.

The pictured splitter is labelled **POE-SP02BT-POE** and offers several output voltages according to its label. The AL1350 needs a suitable **24 V DC supply**; its specified operating range is 20–30 V DC. Output voltage, pin assignment and the available power budget must suit the master and all connected sensors together. Power reaches the AL1350 through its power connector; the external splitter performs the PoE conversion. [ifm datasheet](https://media.ifm.com/dam/aaf256ab-5a44-4254-9ac9-f84f55bfc80b/Original/AL1350-00_EN-GB.pdf)

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/pool2.jpeg" alt="AL1350 with an external PoE splitter"><br><strong>Master and PoE splitter</strong></td>
<td width="50%"><img src="https://raw.githubusercontent.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/main/docs/images/project/pool_poe.jpeg" alt="Detail of the PoE splitter behind the IO-Link master"><br><strong>Power supply and sensor connections</strong></td>
</tr>
</table>

## Supported devices

| Device | Scope | Validation |
|---|---|---|
| **ifm AL1350** | IoT master with four IO-Link ports | Tested on two physical masters |
| **ifm AL1352** | IoT master with eight IO-Link ports | Implemented; physical hardware testing pending |
| **ifm PN7094** | Pressure, device status, OUT1/OUT2; Default and Status B profiles | Status B checked on physical sensors |
| **ifm PN7096** | Pressure, device status, OUT1/OUT2; Default and Status B profiles | Status B checked on physical sensors |
| **ifm LDH292** | Humidity, temperature, device status | Implemented; physical hardware testing pending |
| **ifm PG1406** | Pressure (-0.124…2.5 bar), device status | Implemented; physical hardware testing pending |
| **ifm SM9000** | Flow (5…300 l/min), totalizer, temperature, OUT1/OUT2 | Implemented; physical hardware testing pending |
| **ifm SV4200** | Flow (1.0…20.0 l/min), temperature, OUT1/OUT2 | Implemented; physical hardware testing pending |
| **ifm KQ1000** | Fill level (distance), device status, OUT1/OUT2/OUT3; tank calibration commands (empty/full), factory reset, blink | Implemented; physical hardware testing pending |
| **Speck BADU FlowSonic Plus** | Flow, temperature, two totalizers and status flags | Real readings and Node-RED mapping checked |
| **Other IO-Link devices** | IODD import or a custom JSON profile | Depends on the device format and supported data types |

The daily value **“Filtered water volume today”** can be derived from a totalizer using a Home Assistant Utility Meter. It is not a separate IO-Link process value supplied by the device.

## Installation

### Through HACS

1. Open **Custom repositories** in HACS.
2. Add `https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot` with the category **Integration**.
3. Download **ifm IO-Link Master AL13xx IoT**.
4. Restart Home Assistant.

This is a custom HACS repository; it is not automatically included in the default HACS catalogue. [HACS documentation](https://www.hacs.xyz/docs/faq/custom_repositories/)

### Manual installation

Copy the `custom_components/ifm_iolink` folder from this repository or the release ZIP to `/config/custom_components/ifm_iolink`, then restart Home Assistant.

### Setting up masters and sensors

1. Open **Settings → Devices & services → Add integration → ifm IO-Link Master AL13xx IoT**.
2. Scan the private network or enter the master's IoT address.
3. Open **ifm IO-Link** in the Home Assistant sidebar.
4. Select a port and assign a suitable device profile. Matching vendor/device identifiers are highlighted in the dropdown.
5. Enter and save the device name, location and purpose.
6. Use the resulting entities in your dashboards and automations.

**Requirements:** Home Assistant 2025.7 is the minimum target version, with a reachable IoT Core and correctly configured IO-Link ports. Testing used Home Assistant 2026.8.3. Local integration logos are supported from HA 2026.3. Command Center management requires administrator permissions. Network scanning operates within reachable private IPv4 networks; a manual address can be used across VLANs. Password-based access to a master requires HTTPS.

## Parameter backup and sensor replacement

Use **Parameterliste anzeigen → Alle Gerätedaten lesen → Lesen** (“Show parameter list → Read all device data → Read”) to fetch all profile parameters. Individual parameters also have their own **Lesen** (“Read”) button.

The **Sensortausch & Sicherung** (“Sensor replacement & backup”) section offers these actions in order. The German labels below match the current interface:

| Interface action | Meaning |
|---|---|
| **Parametersicherung erstellen** | Create a parameter backup: read the current profile parameters and save the complete backup for this port in HA. |
| **Parametersicherung wiederherstellen** | Restore the stored port backup to the connected sensor after validation, preview and confirmation. |
| **Sicherung als JSON herunterladen** | Download the stored backup as a JSON file to your computer. |
| **JSON-Sicherung wiederherstellen** | Select an existing JSON backup and restore it through the same validation and confirmation process. |
| **Protokoll herunterladen** | Download the report showing original values, confirmed changes and errors from the last restore attempt. |

When replacing a sensor, its device identification and profile must match; the replacement's serial number may differ. Supported writable parameters are transferred individually and read back. Unchanged values, read-only values and system commands are skipped. The process stops on an error, leaving any values already written in place. The report records the result; there is no automatic rollback.

The backup covers **the parameters defined in the profile**, not a complete device image. The BADU profile currently contains three verified format/unit parameters. The master's automatic IO-Link Data Storage function is separate and is not enabled by this integration. Details and limitations: [Technical notes (German)](docs/technical-notes.md).

## Custom devices and IODD import

In the **Gerätebibliothek** (“Device library”), import a manufacturer's IODD as ZIP or XML, select the appropriate variant and review the preview. Device images included in a ZIP are imported; a standalone XML file does not contain external image files.

The importer supports integers, booleans, IEEE-754 floats, simple records, bit positions and static scaling, among other features. Unsupported or ambiguous definitions are reported as notes. Depending on the sensor, the profile may need further adjustments.

Without a suitable IODD, assign the device as **Unbekannt** (“Unknown”) and export a debug file. This can help you create a custom JSON decoding profile, test it directly in the Command Center, add an image and description, and assign it to several ports. Profiles describe data decoding; they do not contain executable Python or JavaScript code. [Profile format and examples (German)](docs/device-profiles.md)

### Defining a custom command

A command writes a fixed integer value to index/subindex 0 of the sensor – meant for manufacturer commands not covered by the IODD, e.g. "start calibration". In the profile editor this is a top-level `commands` array, next to `parameters`:

```json
{
  "commands": [
    {
      "index": 2,
      "value": 208,
      "name": "Calibrate empty tank",
      "description": "Calibrates the sensor against the empty tank"
    },
    {
      "index": 2,
      "value": 209,
      "name": "Calibrate full tank",
      "description": "Calibrates the sensor against the full tank"
    }
  ]
}
```

- `index`: the parameter index (0–65535). Several commands may share the same index, as shown here – typical for a "system command" parameter where different values trigger different actions. What must be unique is the combination of `index` **and** `value`.
- `value`: the value to write, a single byte (0–255). Subindex is always 0.
- `name`, `description`: label and help text for the "Send" button in the Command Center.

The command shows up in the Command Center under **Show commands**, next to the parameter list; clicking **Send** writes the value immediately, with no further confirmation dialog. Before every send, the connected device's identity is checked fresh against `match`, so a sensor swapped in the meantime doesn't accidentally receive the same command.

## Development, testing and feedback

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check custom_components tests scripts
python -m compileall -q custom_components
node --check custom_components/ifm_iolink/frontend/panel.js
```

Run `python scripts/preview.py` to start a local interface demo at `http://127.0.0.1:8765/`. It uses sample values only. Build the installation archive with `python scripts/package.py`.

**249 automated tests** cover decoding, IODD import, API errors and restore validation, among other areas. A restore without value changes has been checked on a physical PN7094; actual changes and failure scenarios have so far been simulated. [Validation scope (German)](docs/validation.md)

Bug reports, AL1352 hardware experiences and new sensor profiles are welcome through [GitHub Issues](https://github.com/JS-DE-Tech/hacs-ifm-io-link-master-al13xx-iot/issues). Please include the model, firmware, integration version and observed problem. Before uploading debug files or backups publicly, check them for private names, serial numbers and other installation-specific information.

## Support development

Enjoying the integration and want to support its continued development? Voluntary contributions via PayPal are much appreciated:

[Support development via PayPal](https://paypal.me/JensSaffrich)

## Licence and project

The project's own source code is licensed under the [MIT licence](LICENSE). Manufacturer images, IODD excerpts, logos and product names retain their respective rights. The installation photos were supplied by JS-DE-Tech. [Image credits and sources (German)](docs/assets.md)

This is an independent community integration by **JS-DE-Tech**, not an official product of ifm, Speck or JUMO.
