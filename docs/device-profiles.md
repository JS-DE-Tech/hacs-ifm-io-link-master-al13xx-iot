# Geräteprofile

## Eigene digitale Geräte für DI und DO

In **Gerätebibliothek → Eigenes Gerät** den Gerätetyp **Digitales Gerät (DI / DO)** wählen, einen Namen eintragen und über **Bild hochladen** ein PNG-, JPEG- oder WebP-Bild ergänzen. Hersteller, Modell, Beschreibung und Hinweise sind optional. JSON oder eine IODD werden dafür nicht benötigt.

Die Profil-ID entsteht bei neuen Geräten automatisch aus dem Gerätenamen, beispielsweise `custom_druckluftverteiler`. Bereits belegte IDs bekommen eine Nummer. Beim Umbenennen gespeicherter Geräte bleibt ihre ID erhalten; eine manuell eingegebene ID wird ebenfalls nicht automatisch geändert.

An einem Port im Modus DI oder DO steht anschließend die Auswahl **Digitales Gerät** bereit. Gerät auswählen und **Portzuweisung speichern** anklicken. Alternativ öffnet **Digitales Gerät anlegen** am Port direkt den passenden Editor. Ein Gerätetyp kann mehreren Ports zugeordnet werden; Bezeichnung, Standort und Zweck bleiben je Port individuell.

Die Zuordnung ergänzt Darstellung und Geräteinformationen. Eingangszustände und Ausgangsrückmeldung kommen weiterhin vom Master. Sie ändert weder Portmodus noch Ausgangszustand und erzeugt keine zusätzlichen Prozesswert-Entitäten. Bestehende Geräte- und Entitäts-IDs bleiben erhalten. Die IO-Link-Profilzuordnung wird separat aufbewahrt und beim Wechsel zurück zu IO-Link wieder verwendet.

## IO-Link-Profile

Ein Profil ist eine JSON-Datenbeschreibung. Es wird weder mit `eval` noch als Python oder JavaScript ausgeführt. Geräteinformationen und Übersetzung gelten für den Gerätetyp; Standort, Bezeichnung und Zweck lassen sich je angeschlossenem Port überschreiben.

```json
{
  "id": "custom_drucksensor",
  "name": "Mein Drucksensor",
  "manufacturer": "Hersteller",
  "model": "Modell",
  "description": "Geräteinformationen",
  "purpose": "Filterüberwachung",
  "image": "/local/mein-sensor.png",
  "notes": "Skalierung anhand der Herstellerdatei prüfen",
  "length": 4,
  "match": [{"vendorid": 310, "deviceid": 602}],
  "fields": [
    {"key": "pressure", "name": "Druck", "type": "int", "offset": 0,
     "length": 2, "scale": 0.0001, "unit": "bar", "device_class": "pressure",
     "state_class": "measurement", "precision": 4,
     "invalid_values": [-32760, 32760, 32764]},
    {"key": "out1", "name": "OUT1", "type": "bool", "offset": 3,
     "length": 1, "shift": 0, "bits": 1}
  ]
}
```

- `length`: exakte erwartete PDIN-Länge, 1–32 Byte. Eine abweichende Länge führt zu „nicht verfügbar“ statt zu einer geratenen Interpretation.
- `offset`: Byteposition ab Anfang des vom Master gelieferten Hex-Strings, ab 0.
- `type`: `uint`, `int`, `float32`, `float64` oder `bool`; `endian` ist standardmäßig `big`.
- Ganzzahlen: zuerst nach rechts um `shift` verschieben, dann `bits` auswählen. `int` interpretiert das Vorzeichen innerhalb dieser Bitbreite.
- Messwert = Rohwert × `scale` + `add`. `precision` begrenzt die Nachkommastellen. Float-Werte müssen vollständige Bytes belegen.
- `invalid_values`: numerische Sonderwerte, die nicht als Messung ausgegeben werden. `invalid_when: {"offset": 21, "mask": 4}` sperrt das Feld, wenn das angegebene Statusbit gesetzt ist.
- Für binäre Sammelmeldungen kann `mask` mehrere Bits verknüpfen. Beispiel: `mask: 2031` entspricht dem bestehenden BADU-Node-RED-ODER der Bits 0–3 und 5–10.
- `match`: optionaler Schutz gegen falsche Gerätekennungen. Leere Liste erlaubt manuelle generische Profile. Ein Import übernimmt nur die primäre aktive Device-ID; Kompatibilitäts-IDs gelten nicht automatisch für dasselbe Layout.
- `conditions`: optionale Liste aus `{"index": 64, "value": 0}`. Der Index wird über IO-Link nur gelesen; ein abweichender Wert sperrt die Dekodierung.
- `parameters`: optionale herstellerspezifische Parameterliste mit Index, Name, Beschreibung und bei unterstützten Typen einem eigenen Decoder. Werte werden im Panel gezielt einzeln gelesen; komplexe Records bleiben als Rohwert zugänglich.

Im ZIP enthaltene PNG/JPEG-Bilder werden als lokale Daten-URL gespeichert. Alternativ: HTTPS-URL, `/local/`-Pfad oder PNG/JPEG/WebP-Upload. Eigene Profil-IDs beginnen mit `custom_`. Mitgelieferte Profile werden im Editor als eigene Kopie geöffnet.

## Unbekanntes Gerät

Im Port „Unbekannt“ auswählen und speichern oder **Debug-Datei** klicken. Der Export enthält Gerätekennungen, bis zu 30 zeitgestempelte PDIN-Proben, Antwortcodes und eine Profilvorlage. Netzwerkadresse, Zugangsdaten, Seriennummern und Standorttexte aus der Konfiguration werden nicht ausgegeben. Frei eingegebene Texte in eigenen Profilen sollten vor Weitergabe zusätzlich geprüft werden.

Die Datei kann zusammen mit der IODD einem Assistenten zur Profilentwicklung gegeben werden. Eine Bitfolge allein belegt weder Einheit noch Skalierung. Ein erzeugtes JSON-Profil im Editor einfügen, mit Rohwerten testen und speichern.

## Grenzen des automatischen Imports

Die IODD beschreibt mögliche Formate und Gerätevarianten. Manche Geräte wählen Format, Einheiten oder Wertebedeutungen über Laufzeitparameter. Solche Bedingungen müssen berücksichtigt werden; gleiche Paketlänge bedeutet nicht gleiches Format. Der Import priorisiert direkte, layoutspezifische Prozessdatendefinitionen. Bei dynamischen Menüs wird keine beliebige Einheit aus der ersten gefundenen Darstellung übernommen. Fehlende Einheiten und nicht unterstützte Felder werden in der Vorschau angezeigt.

Der Import führt keine Fremdskripte aus, extrahiert keine ZIP-Pfade auf das Dateisystem und akzeptiert keine DTD-/Entity-Deklarationen. Es gelten Größen-, Feld- und Dateianzahlgrenzen.
