# Quellen und Bilder

Die Quellen wurden vom Nutzer für dieses Projekt bereitgestellt. Herstellerbilder und Marken bleiben Eigentum der jeweiligen Rechteinhaber.

| Verwendung | Quelle |
|---|---|
| SV4200-Profilbild und Ausgangsprofil | 100prznt-Fork, Commit `54ae972`; Prozessdatenkorrektur nach ifm-0001E4-20231005-IODD1.1; siehe `review-100prznt.md` |
| AL1350/AL1352-Abbildung | vom Nutzer bereitgestellte PNG-Bilder |
| PN7094/PN7096 Status B, Originalbilder und Parameter | ifm IODD `000259` / `00025A`, Stand 2019-03-07 |
| PN7094 Default | ifm IODD `000193`, Stand 2017-11-22 |
| PN7096 Default | ifm IODD `000194`, Stand 2014-09-09 |
| BADU FlowSonic Plus im mitgelieferten Profil | vom Nutzer bereitgestelltes Originalbild des BADU FlowSonic Plus |
| JUMO-Produktfamilienbild für importierte JUMO-Varianten | `JUMO-flowTRANS_US-20220908-IODD1.1.zip` |
| BADU-Betriebsinformationen | `BTA_BADU FlowSonic, FlowSonic-_DE-EN_03-2025.pdf`, Inhalt DE 01/2025 |
| BADU-Messwerte und Statuszuordnung | bereitgestellter und vom Nutzer bestätigter Node-RED-Flow |

Die JUMO-Datei enthält 25 Geräte-IDs mit je zwei Prozessdatenformaten. `0x186831` ist nicht darunter. Die Testdaten für die JUMO-Importlogik beschreiben ausdrücklich `0x186031` und werden nicht als exakte BADU-IODD ausgegeben.

`tests/fixtures` enthält relevante Auszüge der bereitgestellten ifm-IODDs sowie eine JUMO-Variante zum Prüfen des Imports. Die ursprünglichen privaten Flow-Dateien, IP-Adressen und Seriennummern werden nicht mit dem Installationspaket verteilt.

- Integrationsicon und Panel-Logo: von JS-DE-Tech bereitgestellte PNG in `custom_components/ifm_iolink/brand/icon.png` und `frontend/images/integration-icon.png`.
- Die beiden Screenshots unter `docs/images/screenshots/` wurden von JS-DE-Tech bereitgestellt und zeigen die Portübersicht und Gerätebibliothek der Integration.
- Die sieben Praxisfotos unter `docs/images/project/` wurden von JS-DE-Tech für die Projektbeschreibung bereitgestellt. Die JPEG-Bilddaten bleiben unverändert; EXIF/XMP/IPTC-Metadaten wurden bis auf die für die korrekte Darstellung benötigte Ausrichtung entfernt.
- Die MIT-Lizenz gilt für den selbst erstellten Programmcode. Herstellerbilder, IODD-Auszüge, Logos und Praxisfotos werden dadurch nicht unter MIT neu lizenziert. Für eine Weiterverwendung gelten die Rechte der jeweiligen Urheber.
