const BASE = '/ifm_iolink_static';
const FRONTEND_REVISION = 'wiring-help-20261017';
// Static, read-only examples. No device commands are exposed by these dialogs.
const WIRING_HELP = {
  2: `<div class="cable"><strong>Vorgegebenes Kabel: Phoenix Contact 1504615</strong><span>SAC-4P-M12MS/4,0-PUR/M12FS · 4 m</span></div>
<div class="wiring-diagram-scroll" tabindex="0" role="region" aria-label="Anschlussgrafik, auf kleinen Displays horizontal scrollbar"><img class="diagram" src="${BASE}/images/wiring-do.svg" alt="Schütz LC1D18BD: Pin 4 an A1, Pin 3 an A2, Pin 1 an 13 und Pin 2 an 14."></div>

<table class="wiring"><thead><tr><th>Anschluss</th><th>Funktion</th><th>Kabelbelegung Phoenix Contact*</th></tr></thead><tbody>
<tr><td>A1 (+)</td><td>Spule · geschaltete +24 V DC</td><td><i class="swatch black"></i>Schwarz · Pin 4 · DO</td></tr>
<tr><td>A2 (−)</td><td>Spule · 0 V</td><td><i class="swatch blue"></i>Blau · Pin 3 · L−</td></tr>
<tr><td>13</td><td>Hilfsschließer · Versorgung</td><td><i class="swatch brown"></i>Braun · Pin 1 · L+</td></tr>
<tr><td>14</td><td>Hilfsschließer · Rückmeldung</td><td><i class="swatch white"></i>Weiß · Pin 2 · DI2</td></tr>
<tr><td>21 / 22</td><td>Hilfsöffner</td><td class="unused">Unbenutzt in diesem Beispiel</td></tr>
</tbody></table><p class="adapter">Das vorgegebene Kabel hat M12-Stecker und M12-Buchse. Für Schraubklemmen ist ein geeigneter Klemmenübergang nötig.</p><div class="footnote"><strong>* Aderfarben: Durchgang prüfen.</strong> Farben ↔ Pins sind für dieses Kabel noch nicht herstellerbestätigt.<br><strong>Anschlussentwurf – elektrische Freigabe offen:</strong> DO-Spulenverträglichkeit und DI2-Kontaktstrom prüfen.</div>
<div class="feedback"><div><strong>DO → Spule ansteuern</strong>Die Master-Rückmeldung zeigt den Ausgangszustand.</div><div><strong>DI2 ← Hilfskontakt 13–14</strong>Kontakt geschlossen = Rückmeldung EIN. Kein Laststromnachweis.</div></div>
<p class="tech">Spule: 5,4 W ≈ 225 mA bei 24 V / 20 °C; AL1352-Ausgang max. 300 mA. Daraus allein folgt keine Schaltfreigabe.<br>LC1D18BD-Hilfskontakt: mindestens 5 mA / 17 V laut Hersteller. LAD4TBDL bleibt eingebaut: bidirektionale Begrenzung.</p>
<div class="sources"><span>Herstellerquellen:</span><a href="https://www.phoenixcontact.com/en-us/products/sensoractuator-cable-sac-4p-m12ms-40-purm12fs-1504615?type=pdf" target="_blank" rel="noopener noreferrer">Phoenix Contact 1504615</a><a href="https://media.ifm.com/dam/07d8440a-39b5-4487-af9d-dd96e0cb8bb7/Original/AL1352-00_EN-GB.pdf" target="_blank" rel="noopener noreferrer">ifm AL1352</a><a href="https://www.se.com/us/en/faqs/FA112430/" target="_blank" rel="noopener noreferrer">Schneider Electric</a></div>
`,
  1: `<div class="cable"><strong>Vorgegebenes Kabel: Phoenix Contact 1504615</strong><span>SAC-4P-M12MS/4,0-PUR/M12FS · 4 m</span></div><div class="wiring-diagram-scroll" tabindex="0" role="region" aria-label="Anschlussgrafik, auf kleinen Displays horizontal scrollbar"><img class="diagram" src="${BASE}/images/wiring-di.svg" alt="Zwei unabhängige Schaltkontakte: Pin 1 gemeinsam, Kontakt 1 an Pin 4 DI1, Kontakt 2 an Pin 2 DI2. Pin 3 isoliert."></div>
<table class="wiring"><thead><tr><th>Anschluss</th><th>Funktion</th><th>Kabelbelegung Phoenix Contact*</th></tr></thead><tbody>
<tr><td>Kontakt 1 + 2</td><td>Gemeinsame Versorgung · je eine Kontaktseite</td><td><i class="swatch brown"></i>Braun · Pin 1 · L+</td></tr>
<tr><td>Kontakt 1</td><td>Andere Kontaktseite · Signal an DI1</td><td><i class="swatch black"></i>Schwarz · Pin 4 · DI1</td></tr>
<tr><td>Kontakt 2</td><td>Andere Kontaktseite · Signal an DI2</td><td><i class="swatch white"></i>Weiß · Pin 2 · DI2</td></tr>
<tr><td>Kein Kontakt</td><td>Am Kontaktende unbenutzt · einzeln isolieren</td><td><i class="swatch blue"></i>Blau · Pin 3 · L−</td></tr></tbody></table>
<p class="adapter">Das Kabel hat M12-Stecker und M12-Buchse. Für die Kontakte und die gemeinsame Abzweigung ist ein geeigneter Klemmenübergang nötig.</p>
<div class="footnote"><strong>* Aderfarben: Durchgang prüfen.</strong> Die Zuordnung der Farben zu den Pins ist für dieses Kabel noch nicht herstellerbestätigt.<br><strong>Anschlussentwurf zur Abstimmung.</strong> Pinbelegung und Eignung der verwendeten Kontakte vor Anschluss prüfen.</div>
<div class="feedback"><div><strong>Kontakt 1 → DI1 · Pin 4</strong>Geschlossen: L+ liegt an DI1 an. Kontakt 2 bleibt unabhängig.</div><div><strong>Kontakt 2 → DI2 · Pin 2</strong>Geschlossen: L+ liegt an DI2 an. Kontakt 1 bleibt unabhängig.</div></div>
<p class="tech">Plus-schaltendes Funktionsschema, aus der ifm-Pinbelegung und den Eingangspegeln abgeleitet. HIGH: 11–30 V DC; LOW: 0–5 V DC. Pin 4 muss auf DI stehen.<br>Nur passive, potentialfreie Kontakte verwenden; keine Fremdspannung einspeisen. Die L−-Versorgung des Masters bleibt angeschlossen.</p>
<div class="sources"><span>Herstellerquellen:</span><a href="https://www.phoenixcontact.com/en-us/products/sensoractuator-cable-sac-4p-m12ms-40-purm12fs-1504615?type=pdf">Phoenix Contact 1504615</a><a href="https://media.ifm.com/dam/07d8440a-39b5-4487-af9d-dd96e0cb8bb7/Original/AL1352-00_EN-GB.pdf">ifm AL1352</a><a href="https://www.ifm.com/mounting/80284138UK.pdf">ifm Betriebsanleitung</a></div>`
};
const hasWiringHelp = (master, item) => ['AL1350','AL1352'].includes(master?.identity?.model) && [1,2].includes(item?.mode);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const initialProfile = () => ({id:'custom_mein_sensor',name:'Mein Sensor',manufacturer:'',model:'',description:'',purpose:'',image:'',notes:'',length:2,fields:[{key:'value',name:'Messwert',type:'int',offset:0,length:2,scale:0.01,precision:2}]});
const digitalProfile = () => ({id:'custom_mein_digitalgeraet',kind:'digital',name:'Mein digitales Gerät',manufacturer:'',model:'',description:'',purpose:'',image:'',notes:'',length:0,fields:[]});
const profileIdFromName = (name, profiles=[]) => {
  const slug=String(name).toLowerCase().replace(/ä/g,'ae').replace(/ö/g,'oe').replace(/ü/g,'ue').replace(/ß/g,'ss').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'') || 'geraet';
  const base=('custom_'+slug).slice(0,64).replace(/_+$/g,'');
  const used=new Set(profiles.map(p=>p.id));let id=base,n=2;
  while(used.has(id)){const suffix='_'+n++;id=base.slice(0,64-suffix.length)+suffix;}
  return id;
};
const isDigitalMode = item => [1,2].includes(item?.mode);
const displayProfileId = item => isDigitalMode(item)?item.assignment?.digital_profile:item.profile;
const formatValue = (value, field) => value == null ? '—' : typeof value === 'boolean' ? (value ? 'Aktiv' : 'Inaktiv') : `${new Intl.NumberFormat('de-DE',{maximumFractionDigits:field.precision ?? 3}).format(value)}${field.unit ? ' '+field.unit : ''}`;
const channelState = (item, pin, online) => {
  if(!online)return {tone:'unknown',text:'Nicht erreichbar'};
  if(pin==='pin4' && item?.mode===3)return item.connected?{tone:'iol',text:'IO-Link verbunden'}:{tone:'unknown',text:'IO-Link nicht verbunden'};
  if(pin==='pin4' && item?.mode===0)return {tone:'off',text:'Deaktiviert'};
  const value=item?.[pin];
  return value===true?{tone:'on',text:'EIN'}:value===false?{tone:'off',text:'AUS'}:{tone:'unknown',text:'Unbekannt'};
};

const channelLabel = (item, pin) => pin==='pin2'?'Pin 2 · Digitaleingang DI2':'Pin 4 · '+({0:'Deaktiviert',1:'Digitaleingang DI1',2:'Digitalausgang',3:'IO-Link'}[item?.mode] || 'Modus unbekannt');
const channelDescription = (item, pin, online) => {
  const label=channelLabel(item,pin);
  if(online && pin==='pin4' && item?.mode===0)return label;
  const status=online && pin==='pin4' && item?.mode===3?(item.connected?'Verbunden':'Nicht verbunden'):channelState(item,pin,online).text.replace('EIN','AN');
  return `${label} · ${status}`;
};

const modeLabel = mode => ({0:'Disabled',1:'DI',2:'DO',3:'IO-LINK'}[mode] || 'Unbekannt');
const modeStatus = (item, online) => {
  const label=({0:'Disabled',1:'DI1',2:'DO',3:'IO-Link'}[item?.mode] || '?');
  if(!online)return {label,text:channelDescription(item,'pin4',online),tone:'unknown',clickable:false};
  if(item?.mode===3)return {label,text:channelDescription(item,'pin4',online),tone:item.connected?'on':'off',clickable:false};
  if(item?.mode===0)return {label,text:'Pin 4 · Deaktiviert',tone:'unknown',clickable:false};
  const known=typeof item?.pin4==='boolean' && [1,2].includes(item?.mode);
  return {label,text:channelDescription(item,'pin4',online),tone:known?(item.pin4?'on':'off'):'unknown',clickable:item?.mode===2 && known};
};

class IfmIolinkPanel extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:'open'}); this.data={masters:[],profiles:[]}; this.page='overview'; this.port=1; this.draft=initialProfile(); this.autoProfileId=true; this.parameterReads=new Map(); this.parameterBackups=new Map(); this.parameterBusy=new Set(); this.restoreReports=new Map();
  }
  set hass(value) { this._hass=value; if (this.isConnected && !this.started) this.start(); }
  connectedCallback() { if (this._hass) this.start(); }
  disconnectedCallback() { clearInterval(this.timer); this.stopReplacementPolling?.(); this.replacementDialog?.close(); this.wiringDialog?.close(); this.resizeObserver?.disconnect(); this.started=false; }
  start() { if(this.started)return; this.started=true; this.render(); this.refresh(); this.timer=setInterval(()=>this.refresh(),2000); }
  async call(type, values={}) { return this._hass.callWS({type:`ifm_iolink/${type}`,...values}); }
  async refresh(force=false) {
    if(this.loading)return; this.loading=true;
    try {
      const next=await this.call('snapshot',{include_profiles:force || !this.profilesLoaded});
      if(next.profiles){this.profilesLoaded=true;this.profileRevision=next.profile_revision;}else{next.profiles=this.data.profiles;if(next.profile_revision!==this.profileRevision)this.profilesLoaded=false;}
      const signature=JSON.stringify([next.masters.map(m=>[m.entry_id,m.name,m.replacement_paused,m.replacement_detected,Object.values(m.ports || {}).map(p=>[p.mode,p.assignment])]),next.profiles.map(p=>[p.id,p.name]),next.profile_revision]);
      this.data=next; if(!next.masters.some(m=>m.entry_id===this.masterId)) this.masterId=next.masters[0]?.entry_id;
      if(force || signature!==this.signature){this.signature=signature;this.render();}else this.paint();
    } catch(error) { this.data.masters.forEach(m=>m.online=false);this.paint();this.notify(`Verbindung zu Home Assistant: ${error.message || error}`,true); }
    finally {this.loading=false;}
  }
  get master(){return this.data.masters.find(m=>m.entry_id===this.masterId);}
  get selected(){return this.master?.ports?.[this.port];}
  profile(id){return this.data.profiles.find(p=>p.id===id);}
  notify(message,error=false){const el=this.shadowRoot.querySelector('#notice');if(el){el.textContent=message;el.className=error?'notice error':'notice';}}
  render() {
    // Live snapshots may change while the replacement job runs. Keep its dialog
    // and progress visible; closing it performs a full refresh of the overview.
    if(this.replacementDialog?.open)return;
    if(this.wiringDialog?.open){
      this.wiringNeedsRender=true;
      const context=this.wiringContext,master=this.data.masters.find(m=>m.entry_id===context.entryId);
      if(master?.ports?.[context.port]?.mode!==context.mode || !hasWiringHelp(master,master?.ports?.[context.port]))this.wiringDialog.close();
      return;
    }
    const master=this.master;
    this.shadowRoot.innerHTML=`<link rel="stylesheet" href="${BASE}/panel.css?v=${esc(this.data.version || '')}&ui=${FRONTEND_REVISION}"><div class="app">
      <header><div class="brand"><img class="brand-icon" src="${BASE}/images/integration-icon.png" alt="ifm IO-Link Logo"><div><span class="eyebrow">LOKAL VERBUNDEN</span><h1>ifm IO-Link Command Center</h1></div></div><div class="header-actions"><a href="/config/integrations/dashboard/add?domain=ifm_iolink">+ Master hinzufügen</a><span class="tag">AL1350 or AL1352 with IoT core</span></div></header>
      <div class="toolbar"><nav><button data-page="overview" class="${this.page==='overview'?'active':''}">Portübersicht</button><button data-page="library" class="${this.page==='library'?'active':''}">Gerätebibliothek <span>${this.data.profiles.length}</span></button></nav>
      ${master?`<label class="master-choice">Master <select id="master">${this.data.masters.map(m=>`<option value="${esc(m.entry_id)}" ${m===master?'selected':''}>${esc(m.name)}</option>`).join('')}</select></label>`:''}</div>
      <div id="notice" class="notice" role="status" aria-live="polite"></div>
      ${this.page==='overview'?this.overview():this.library()}
      <footer><span>ifm IO-Link · Direkte Verbindung zu Home Assistant</span><span>by JS-DE-Tech${this.data.version?` · v${esc(this.data.version)}`:''}</span></footer></div>`;
    this.shadowRoot.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{this.page=b.dataset.page;this.render();});
    this.shadowRoot.querySelector('#master')?.addEventListener('change',e=>{this.masterId=e.target.value;this.port=1;this.render();});
    this.bindOverview(); this.bindLibrary(); this.paint(); this.paintParameters();
    this.resizeObserver?.disconnect();const grid=this.shadowRoot.querySelector('.topology-grid');if(grid){this.resizeObserver=new ResizeObserver(()=>this.drawWires());this.resizeObserver.observe(grid);this.shadowRoot.querySelector('.master-device img').onload=()=>this.drawWires();}
  }
  overview() {
    const master=this.master;if(!master)return `<section class="empty"><h2>Dein erster IO-Link-Master</h2><p>Füge einen AL1350 oder AL1352 hinzu. Du kannst das lokale Netzwerk durchsuchen oder die IoT-Adresse direkt eintragen.</p><a class="primary button" href="/config/integrations/dashboard/add?domain=ifm_iolink">Master einrichten</a><p>Ein bereits eingerichteter Master erscheint hier, sobald er geladen ist.</p></section>`;
    const portCount=master.identity.ports;
    const rows=portCount/2;
    return `<section class="section-heading"><div><span class="eyebrow">DEINE ANLAGE</span><h2>${esc(master.name)}</h2><p>${portCount} IO-Link-Ports · Aktualisierung alle ${master.interval} Sekunden</p></div><div class="master-tools"><span class="status" id="master-status"></span><button id="manage-master">Master verwalten</button></div></section>${master.replacement_detected || master.replacement_paused?`<div class="notice">${master.replacement_detected?'Anderer Master erkannt – Austausch bestätigen':'Masteraustausch vorbereitet – Verarbeitung pausiert'} <button id="replacement-alert">Austausch prüfen</button></div>`:''}
    <div class="workspace"><section class="topology" aria-label="Master mit angeschlossenen Geräten"><div class="topology-grid" style="--rows:${rows}">
      <div class="master-device" style="grid-row:1 / ${rows+1}"><span class="master-model">${esc(master.identity.model)}</span><img src="${BASE}/images/${master.identity.model.toLowerCase()}.png" alt="ifm ${esc(master.identity.model)}"><span class="master-caption">IO-LINK MASTER</span></div>
      <svg class="wires" aria-hidden="true"></svg>${Array.from({length:portCount},(_,i)=>this.portCard(i+1)).join('')}</div><p class="topology-hint">Port auswählen, Gerät zuweisen, Messwerte ansehen.</p></section>
      <aside class="inspector">${this.inspector()}</aside></div>`;
  }
  portCard(number) {
    const item=this.master.ports[number] || {};const profile=this.profile(displayProfileId(item));const assignment=item.assignment || {};
    const side=number%2?'left':'right';
    return `<div role="button" tabindex="0" class="port-card ${side} ${number===this.port?'selected':''}" data-port="${number}" style="grid-row:${Math.ceil(number/2)};grid-column:${side==='left'?1:3}">
      <span class="port-line"></span><div class="port-card-top"><span class="port-label">X${String(number).padStart(2,'0')}</span><button class="signal-badge unknown" data-toggle="${number}" type="button" disabled></button><span class="signal-badge unknown" data-di2="${number}" role="img">DI2</span>${hasWiringHelp(this.master,item)?`<button class="wiring-help-button" data-wiring-help="${number}" type="button" aria-label="Anschlusshilfe ${modeLabel(item.mode)} für Port ${number} öffnen" aria-haspopup="dialog" title="Anschlussbeispiel anzeigen">?</button>`:''}</div>
      <div class="device-row">${profile?.image?`<img src="${esc(profile.image)}" alt="${esc(profile.model || profile.name)}" referrerpolicy="no-referrer">`:'<span class="unknown-device">?</span>'}<div><strong>${esc(assignment.name || profile?.name || profile?.model || 'Gerät auswählen')}</strong><small>${esc(assignment.location || (profile?.kind==='digital'?'Digitales Gerät':(item.identity?.productname ? 'Gerät erkannt' : 'Noch nicht zugewiesen')))}</small></div></div>
      <div class="card-values">${(item.mode===3?profile?.fields || []:[]).filter(f=>f.type!=='bool').slice(0,2).map(f=>`<div><small>${esc(f.name)}</small><b data-value="${number}:${esc(f.key)}">—</b></div>`).join('') || `<small>${esc(isDigitalMode(item)?(item.mode===2?'Digitalausgang · Rückmeldung vom Master':'Digitaleingänge · Status vom Master'):(item.identity?.productname || 'Unbekannt / kein Gerät'))}</small>`}</div>
      ${assignment.purpose?`<div class="purpose">${esc(assignment.purpose)}</div>`:''}</div>`;
  }
  inspector(){
    const item=this.selected || {};const profile=this.profile(displayProfileId(item));const a=item.assignment || {};
    return `<div class="inspector-title"><div><span class="eyebrow">ANSCHLUSS X${String(this.port).padStart(2,'0')}</span><h3>Gerät & Messwerte</h3></div><span class="port-state" data-status="${this.port}"></span></div>
      <label>Portmodus<select id="port-mode">${item.mode==null?'<option value="" selected>Unbekannt</option>':''}${[2,3,1,0].map(mode=>`<option value="${mode}" ${item.mode===mode?'selected':''}>${modeLabel(mode)}</option>`).join('')}</select></label><button id="apply-mode" type="button">Portmodus aktivieren</button>
      <p class="field-help">Modusänderungen werden vor dem Schreiben bestätigt. Die Profilzuordnung bleibt erhalten.</p>
      <form id="assignment"><label>${isDigitalMode(item)?'Digitales Gerät':'Geräteprofil'}<select name="${isDigitalMode(item)?'digital_profile':'profile'}" ${![1,2,3].includes(item.mode)?'disabled':''}><option value="unknown">${isDigitalMode(item)?'Kein digitales Gerät zugewiesen':'Unbekannt · Debug-Datei erzeugen'}</option>${this.data.profiles.filter(p=>(p.kind==='digital')===isDigitalMode(item)).map(p=>`<option value="${esc(p.id)}" ${p.id===displayProfileId(item)?'selected':''}>${esc(p.name)}${item.suggested?.includes(p.id)?' · passend zur Kennung':''}</option>`).join('')}</select></label>
      ${item.suggested?.length && item.profile==='unknown'?`<p class="suggestion">Passendes Profil erkannt. Im Dropdown als „passend zur Kennung“ markiert.</p>`:''}
      <label>Gerätebezeichnung<input name="name" maxlength="500" value="${esc(a.name)}" placeholder="${isDigitalMode(item)?'z. B. Schütz Kompressor':'z. B. Druck am Poolfilter'}"></label>
      <label>Standort<input name="location" maxlength="500" value="${esc(a.location)}" placeholder="z. B. Heizungsraum"></label>
      <label>Verwendungszweck<input name="purpose" maxlength="500" value="${esc(a.purpose || profile?.purpose)}" placeholder="Was überwacht dieses Gerät?"></label>
      <button class="primary" type="submit">Portzuweisung speichern</button></form>
      <div class="action-row">${!isDigitalMode(item)?'<button id="debug">Debug-Datei</button>':''}<button id="new-device">${isDigitalMode(item)?'Digitales Gerät anlegen':'Eigenes Gerät'}</button></div>
      <div class="decode-error" id="decode-error" role="status"></div>
      <section class="readings"><h4>Kanalstatus</h4><p class="field-help">Aus den gemeldeten Pin-Zuständen abgeleitet; keine exakte Wiedergabe der physischen LED-Blinkmuster.</p>
      ${['pin4','pin2'].map(pin=>`<div class="reading"><span>${channelLabel(item,pin)}</span><strong class="channel-led unknown" data-channel="${this.port}:${pin}">Unbekannt</strong></div>`).join('')}
      ${item.mode===2?'<div class="action-row"><button data-output="on">Ausgang EIN</button><button data-output="off">Ausgang AUS</button></div><p class="field-help">Schaltet Pin 4 nach frischer DO-Modus-Prüfung und bestätigt den Wert durch Rücklesen.</p>':'<p class="field-help">Zum Schalten oben den Portmodus DO wählen. DI zeigt den Eingangszustand.</p>'}</section>
      ${profile && item.mode===3?`<section class="readings"><h4>Prozesswerte <span>${profile.fields.length}</span></h4>${profile.fields.map(f=>`<div class="reading"><span>${esc(f.name)}</span><strong data-value="${this.port}:${esc(f.key)}">—</strong></div>`).join('')}</section>
      <details><summary>Geräteinformationen & Hinweise</summary><p>${esc(profile.description)}</p><p>${esc(profile.notes)}</p><small>Quelle: ${esc(profile.source)}</small></details>
      ${profile.parameters?.length?`<details class="parameter-list"><summary>Parameterliste anzeigen</summary><div class="parameter parameter-read-all"><div><b>Alle Gerätedaten lesen</b></div><button id="read-all" title="Alle Gerätedaten lesen">Lesen</button></div><p id="parameter-status" role="status">Alle im Profil enthaltenen Parameter werden nacheinander gelesen.</p>${profile.parameters.map(p=>`<div class="parameter"><div><b>${esc(p.name)}</b><small>Index ${p.index} · ${esc(p.datatype)} · ${esc(p.access || 'ro')} · ${esc(p.description)}</small><output id="parameter-${p.index}">Noch nicht gelesen</output></div><button data-read="${p.index}" title="Parameter ${esc(p.name)} lesen">Lesen</button></div>`).join('')}</details><details><summary>Sensortausch & Sicherung</summary><div class="parameter-actions backup-actions"><div class="backup-action"><button id="backup-parameters" aria-describedby="backup-help">Parametersicherung erstellen</button><p id="backup-help">Liest die aktuellen Profilparameter des Sensors und speichert sie für diesen Port in Home Assistant. Nur eine vollständige Abfrage ersetzt die bisherige Sicherung.</p></div><div class="backup-action"><button id="restore-saved" aria-describedby="restore-saved-help" disabled>Parametersicherung wiederherstellen</button><p id="restore-saved-help">Verwendet die für diesen Port in Home Assistant gespeicherte Sicherung. Zeigt zuerst eine Vorschau; erst nach deiner Bestätigung werden passende Parameter auf den angeschlossenen Sensor übertragen.</p></div><div class="backup-action"><button id="download-parameters" aria-describedby="download-help" disabled>Sicherung als JSON herunterladen</button><p id="download-help">Lädt die in Home Assistant gespeicherte Port-Sicherung als JSON-Datei auf deinen Computer. Der Sensor wird dabei nicht erneut ausgelesen.</p></div><div class="backup-action"><label class="button upload">JSON-Sicherung wiederherstellen<input id="restore-upload" type="file" accept=".json,application/json" aria-label="JSON-Sicherung auswählen" aria-describedby="restore-file-help"></label><p id="restore-file-help">Wähle eine zuvor heruntergeladene JSON-Sicherung von deinem Computer. Die Datei und der Sensor werden geprüft; anschließend bestätigst du die Wiederherstellung in der Vorschau.</p></div><div class="backup-action"><button id="restore-report" aria-describedby="restore-report-help" disabled>Protokoll herunterladen</button><p id="restore-report-help">Lädt das Protokoll der letzten Wiederherstellung an diesem Port herunter: ursprüngliche Werte, bestätigte Änderungen und mögliche Fehler. Erst nach einem Wiederherstellungsversuch verfügbar.</p></div></div><p id="backup-status"></p><p id="restore-status" role="status"></p><p>Eine Wiederherstellung prüft Gerätekennung, Profil und aktuelle Werte. Nur unterstützte schreibbare Parameter werden nach Bestätigung übertragen und zurückgelesen. Unveränderte Werte werden ausgelassen. Bei Fehlern wird gestoppt; bereits geschriebene Werte bleiben bestehen. Das Protokoll enthält die ursprünglichen Werte. Es erfolgt kein automatischer Rollback. Für den automatischen Sensortausch kann im Master die IO-Link-Funktion „Backup + Restore“ mit einem kompatiblen Ersatzsensor eingerichtet werden.</p></details>`:''}`:isDigitalMode(item)?`<details><summary>Geräteinformationen & Hinweise</summary><p>${esc(profile?.description || 'Eigenes digitales Gerät mit Bild in der Gerätebibliothek anlegen und hier auswählen.')}</p><p>${esc(profile?.notes)}</p></details>`:'<div class="unknown-info"><h4>Ein neues Gerät?</h4><p>Importiere seine Hersteller-IODD in der Gerätebibliothek. Alternativ enthält die Debug-Datei Rohwerte und Gerätekennung für ein eigenes Übersetzungsprofil.</p></div>'}
      <details><summary>Verbindung & Rohdaten</summary><dl>${['productname','vendorid','deviceid','serial'].map(k=>`<dt>${esc(k)}</dt><dd>${esc(item.identity?.[k] ?? '—')}</dd>`).join('')}</dl><code id="raw"></code><small id="updated"></small></details>`;
  }
  library(){
    if(this.autoProfileId)this.draft.id=profileIdFromName(this.draft.name,this.data.profiles);
    return `<section class="section-heading"><div><span class="eyebrow">EINMAL ANLEGEN · MEHRFACH VERWENDEN</span><h2>Deine Gerätebibliothek</h2><p>IO-Link-Profile importieren oder eigene digitale Geräte mit Bild anlegen.</p></div><div class="action-row"><label class="button primary upload">IODD importieren<input id="iodd-upload" type="file" accept=".zip,.xml"></label><button id="blank-profile">+ Eigenes Gerät</button></div></section>
      <div class="library-layout"><section class="library-list">${this.data.profiles.map(p=>`<button class="library-card" data-edit="${esc(p.id)}">${p.image?`<img src="${esc(p.image)}" alt="${esc(p.model)}" referrerpolicy="no-referrer">`:'<span class="unknown-device">?</span>'}<div><span class="eyebrow">${p.id.startsWith('custom_')?'EIGENES GERÄT':'MITGELIEFERT'}</span><h3>${esc(p.name)}</h3><p>${esc(p.purpose || p.description)}</p><small>${p.kind==='digital'?'Digitales Gerät · DI / DO':`${p.fields.length} Prozesswerte · ${p.length} Byte${p.parameters?.length?` · ${p.parameters.length} Parameter`:''}`}</small></div><span>↗</span></button>`).join('')}</section>
      <section class="profile-editor"><span class="eyebrow">PROFILWERKSTATT</span><h3>${esc(this.draft.name || 'Eigenes Gerät')}</h3>
      <div id="import-candidates">${this.candidates?.length?`<label>IODD-Variante<select id="variant">${this.candidates.map((c,i)=>`<option value="${i}" ${i===this.candidateIndex?'selected':''}>${esc(c.profile.name)} · ${esc(c.layout)} · ID ${esc(c.profile.match?.[0]?.deviceid?.toString(16))}</option>`).join('')}</select></label><p class="suggestion">${esc(this.candidates[this.candidateIndex || 0].warnings.join(' · ') || 'Herstellerdaten importiert. Prüfe Vorschau und Gerätevariante, dann speichern.')}</p>`:''}</div>
      <label>Gerätetyp<select id="profile-kind" ${this.profile(this.draft.id)?'disabled':''}><option value="iolink" ${this.draft.kind!=='digital'?'selected':''}>IO-Link-Gerät</option><option value="digital" ${this.draft.kind==='digital'?'selected':''}>Digitales Gerät (DI / DO)</option></select></label><form id="profile-form"><div class="two-col"><label>Profil-ID<input name="id" value="${esc(this.draft.id)}" required maxlength="64" pattern="custom_[a-z0-9_]+" title="Wird bei neuen Geräten automatisch aus dem Gerätenamen erstellt. Bestehende IDs bleiben beim Umbenennen erhalten."></label><label>Gerätename<input name="name" value="${esc(this.draft.name)}" required></label><label>Hersteller<input name="manufacturer" value="${esc(this.draft.manufacturer)}"></label><label>Modell<input name="model" value="${esc(this.draft.model)}"></label></div>
      <label>Informationen zum Gerät<textarea name="description" rows="2">${esc(this.draft.description)}</textarea></label><label>Verwendungszweck<input name="purpose" value="${esc(this.draft.purpose)}"></label>
      <label>Bild-URL oder /local/-Pfad<input name="image" value="${esc(this.draft.image?.startsWith('data:')?'':this.draft.image)}" placeholder="https://… oder /local/mein-sensor.png"></label><div class="image-upload">${this.draft.image?`<img src="${esc(this.draft.image)}" alt="Profilbild" referrerpolicy="no-referrer">`:''}<label class="button upload">Bild hochladen<input id="image-upload" type="file" accept="image/png,image/jpeg,image/webp"></label></div>
      <label>Hinweise<textarea name="notes" rows="2">${esc(this.draft.notes)}</textarea></label>
      ${this.draft.kind==='digital'?'<p>Name und Bild für DI- und DO-Ports. Die Zustände liefert der Master; ein Übersetzungsprofil ist nicht erforderlich.</p>':`<label>Übersetzungsprofil (JSON)<textarea id="profile-json" rows="12" spellcheck="false">${esc(this.profileJson())}</textarea></label><p class="field-help">Bytepositionen, Vorzeichen, Skalierung und Einheiten. Hersteller-IODDs füllen das Profil automatisch aus. Hier lässt sich auch ein erstelltes JSON-Profil einfügen.</p>
      <label>Test-Rohwert (Hex)<input id="test-raw" value="${esc(this.testRaw || '')}" placeholder="z. B. 08980101"></label><div class="action-row"><button id="test-profile" type="button">Übersetzung testen</button><button id="export-profile" type="button">JSON exportieren</button></div><pre id="test-output"></pre>`}
      <div class="action-row"><button class="primary" type="submit">Geräteprofil speichern</button>${this.draft.id?.startsWith('custom_')&&this.profile(this.draft.id)?'<button type="button" id="delete-profile">Löschen</button>':''}</div></form></section></div>`;
  }
  async downloadDebug() {
    const result=await this.call('debug',{entry_id:this.masterId,port:this.port});
    this.download(`iolink-port-${this.port}-debug.json`,result); return result;
  }
  download(name,value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  showWiringHelp(port, opener){
    const master=this.master,item=master?.ports?.[port];
    if(!hasWiringHelp(master,item) || this.wiringDialog?.open)return;
    const mode=item.mode,dialog=document.createElement('dialog');
    dialog.className='wiring-help';
    dialog.setAttribute('aria-labelledby','wiring-help-title');
    this.wiringContext={entryId:master.entry_id,port,mode};this.wiringNeedsRender=false;
    dialog.innerHTML=`<div class="pophead"><div><div class="eyebrow">${esc(master.name)} · X${String(port).padStart(2,'0')} · ${mode===2?'DIGITALAUSGANG MIT RÜCKMELDUNG':'DIGITALEINGÄNGE DI1 / DI2'}</div><h2 id="wiring-help-title">Anschlussbeispiel · ${mode===2?'Schütz mit Rückmeldung':'Zwei Schaltkontakte'}</h2><p>${mode===2?'Schneider Electric LC1D18BD als Anschlussbeispiel':'Potentialfreie Kontakte mit gemeinsamer Versorgung'}</p></div><button class="close" type="button" autofocus aria-label="Anschlusshilfe schließen">×</button></div><div class="body">${WIRING_HELP[mode]}</div>`;
    this.wiringDialog=dialog;
    dialog.onclose=()=>{
      dialog.remove();this.wiringDialog=null;this.wiringContext=null;
      if(this.isConnected!==false){if(this.wiringNeedsRender)this.render();this.wiringNeedsRender=false;const current=this.shadowRoot.querySelector(`[data-wiring-help="${port}"]`);(current || this.shadowRoot.querySelector(`[data-port="${port}"]`) || opener)?.focus();}
    };
    dialog.querySelector('.close').onclick=()=>dialog.close();
    dialog.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left || event.clientX>box.right || event.clientY<box.top || event.clientY>box.bottom)dialog.close();}});
    this.shadowRoot.append(dialog);dialog.showModal();
  }
  async toggleOutput(port){
    const master=this.master,item=master?.ports?.[port];
    if(!modeStatus(item,master?.online).clickable)return;
    const entry_id=master.entry_id,key=`${entry_id}:${port}:${item.profile}`;
    if(this.parameterBusy.has(key))return;
    this.parameterBusy.add(key);this.paint();
    try{await this.call('set_digital_output',{entry_id,port,on:!item.pin4});await this.refresh();this.notify('DO-Rückmeldung vom Master bestätigt.');}
    catch(error){item.pin4=null;this.notify(error.message || String(error),true);}
    finally{this.parameterBusy.delete(key);this.paint();}
  }
  async changeMode(){
    const entry_id=this.masterId,port=this.port,expected_mode=this.selected?.mode;
    const target_mode=Number(this.shadowRoot.querySelector('#port-mode').value),key=this.portKey();
    if(expected_mode==null || target_mode===expected_mode || this.parameterBusy.has(key))return;
    if(!window.confirm(`${this.master.name} · X${String(port).padStart(2,'0')}: ${modeLabel(expected_mode)} → ${modeLabel(target_mode)}?\nDie Funktion an Pin 4 wird geändert. Profilzuordnungen bleiben gespeichert.${target_mode===2?'\nNach der Umschaltung wird AUS geschrieben und geprüft. Während der Umschaltung ist kein unterbrechungs- oder impulsfreier Ausgang garantiert.':''}`))return;
    this.parameterBusy.add(key);this.paint();
    let failure;
    try{await this.call('set_port_mode',{entry_id,port,expected_mode,target_mode,confirm:true});}
    catch(error){failure=error.message || String(error);}
    finally{this.parameterBusy.delete(key);await this.refresh(true);}
    this.notify(failure || 'Portmodus durch Rücklesen bestätigt.',!!failure);
  }
  bindOverview(){
    this.shadowRoot.querySelectorAll('[data-wiring-help]').forEach(button=>button.onclick=event=>{event.stopPropagation();this.showWiringHelp(Number(button.dataset.wiringHelp),button);});
    this.shadowRoot.querySelector('#apply-mode')?.addEventListener('click',()=>this.changeMode());
    this.shadowRoot.querySelectorAll('[data-toggle]').forEach(b=>b.onclick=e=>{e.stopPropagation();this.toggleOutput(Number(b.dataset.toggle));});
    this.shadowRoot.querySelectorAll('[data-output]').forEach(b=>b.onclick=async()=>{
      const key=this.portKey(),entry_id=this.masterId,port=this.port;
      if(this.parameterBusy.has(key))return;
      this.parameterBusy.add(key);this.paint();
      try{await this.call('set_digital_output',{entry_id,port,on:b.dataset.output==='on'});await this.refresh();this.notify('Ausgang durch Rücklesen bestätigt.');}
      catch(e){const master=this.data.masters.find(m=>m.entry_id===entry_id);if(master?.ports?.[port])master.ports[port].pin4=null;this.notify(e.message || String(e),true);}
      finally{this.parameterBusy.delete(key);this.paint();}
    });
    this.shadowRoot.querySelectorAll('[data-port]').forEach(b=>{b.onclick=()=>{this.port=Number(b.dataset.port);this.render();};b.onkeydown=e=>{if(e.target===b && ['Enter',' '].includes(e.key)){e.preventDefault();b.click();}};});
    this.shadowRoot.querySelector('#assignment')?.addEventListener('submit',async e=>{
      e.preventDefault();const button=e.submitter;button.disabled=true;
      try{const values=Object.fromEntries(new FormData(e.target));if(!values.profile)values.profile=this.selected?.profile || 'unknown';if(values.profile==='unknown' && this.selected?.mode===3) await this.downloadDebug();await this.call('assign',{entry_id:this.masterId,port:this.port,...values});this.notify('Portzuweisung gespeichert. Home Assistant lädt die Sensoren neu.');setTimeout(()=>this.refresh(true),1500);}catch(error){this.notify(error.message || String(error),true);}finally{button.disabled=false;}
    });
    this.shadowRoot.querySelector('#debug')?.addEventListener('click',()=>this.downloadDebug().catch(e=>this.notify(e.message,true)));
    this.shadowRoot.querySelector('#new-device')?.addEventListener('click',()=>{this.testRaw=this.selected?.raw || '';this.page='library';this.autoProfileId=true;this.draft=isDigitalMode(this.selected)?digitalProfile():initialProfile();if(this.draft.kind!=='digital')this.draft.length=Math.max(1,this.testRaw.length/2);this.render();});
    this.shadowRoot.querySelector('#manage-master')?.addEventListener('click',()=>this.manageMaster());
    this.shadowRoot.querySelector('#replacement-alert')?.addEventListener('click',()=>this.replaceMaster());
    this.shadowRoot.querySelector('#restore-saved')?.addEventListener('click',()=>this.previewRestore());
    this.shadowRoot.querySelector('#restore-upload')?.addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>500000)throw Error('JSON-Sicherung darf höchstens 500 KB groß sein.');await this.previewRestore(JSON.parse(await file.text()));}catch(error){this.notify(error.message,true);}finally{e.target.value='';}});
    this.shadowRoot.querySelector('#restore-report')?.addEventListener('click',()=>{const report=this.restoreReports.get(this.portKey());if(report)this.download(`iolink-port-${this.port}-restore-report.json`,report);});
    this.shadowRoot.querySelector('#read-all')?.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();this.readAllParameters(false);});
    this.shadowRoot.querySelector('#backup-parameters')?.addEventListener('click',()=>this.readAllParameters(true));
    this.shadowRoot.querySelector('#download-parameters')?.addEventListener('click',()=>{const backup=this.parameterBackups.get(this.portKey());if(backup)this.download(`iolink-port-${this.port}-parameters.json`,backup);});
    this.shadowRoot.querySelectorAll('[data-read]').forEach(b=>b.onclick=async()=>{
      const key=this.portKey(),index=b.dataset.read,entry_id=this.masterId,port=this.port;
      if(this.parameterBusy.has(key))return;this.parameterBusy.add(key);this.paintParameters();
      try{const result=await this.call('read_parameter',{entry_id,port,index:Number(index)});const data=this.parameterReads.get(key) || {values:{},errors:{}};data.values[index]=result;delete data.errors[index];data.message='Parameter gelesen.';this.parameterReads.set(key,data);}catch(e){this.notify(e.message,true);}finally{this.parameterBusy.delete(key);this.paintParameters();}
    });
    if(this.selected){const key=this.portKey();this.call('get_parameter_backup',{entry_id:this.masterId,port:this.port}).then(result=>{this.parameterBackups.set(key,result.backup);this.paintParameters();}).catch(e=>this.notify(e.message,true));this.call('get_restore_report',{entry_id:this.masterId,port:this.port}).then(result=>{this.restoreReports.set(key,result.report);this.paintParameters();}).catch(e=>this.notify(e.message,true));}

  }
  portKey(){return `${this.masterId}:${this.port}:${this.selected?.profile}`;}
  async readAllParameters(save){
    const key=this.portKey(),entry_id=this.masterId,port=this.port;
    if(this.parameterBusy.has(key))return;this.parameterBusy.add(key);this.paintParameters();
    try{const result=await this.call('read_parameters',{entry_id,port,save});const failed=Object.keys(result.errors).length;
      result.message=`${Object.keys(result.values).length} Parameter gelesen${failed?`, ${failed} Fehler. Vorhandene Sicherung bleibt erhalten.`:'.'}${result.saved?' Am Port gespeichert.':''}`;
      this.parameterReads.set(key,result);if(result.saved)this.parameterBackups.set(key,result);
    }catch(e){this.parameterReads.set(key,{values:{},errors:{},message:e.message || String(e)});}finally{this.parameterBusy.delete(key);this.paintParameters();}
  }
  paintParameters(){
    const key=this.portKey(),data=this.parameterReads.get(key),backup=this.parameterBackups.get(key),busy=this.parameterBusy.has(key);
    this.shadowRoot.querySelectorAll('[data-read],#read-all,#backup-parameters,#restore-upload').forEach(b=>b.disabled=busy);
    const status=this.shadowRoot.querySelector('#parameter-status');if(status)status.textContent=busy?'Parameterabfrage oder Wiederherstellung läuft …':data?.message || 'Alle im Profil enthaltenen Parameter werden nacheinander gelesen.';
    for(const p of this.profile(this.selected?.profile)?.parameters || []){const el=this.shadowRoot.querySelector(`#parameter-${p.index}`),v=data?.values?.[p.index];if(el)el.textContent=data?.errors?.[p.index]?`Fehler: ${data.errors[p.index]}`:v?`${typeof v.value==='string'?v.value:formatValue(v.value,{unit:v.unit})} (Hex: ${v.raw})`:'Noch nicht gelesen';}
    const label=this.shadowRoot.querySelector('#backup-status');if(label)label.textContent=backup?`Sicherung vom ${new Date(backup.created_at).toLocaleString('de-DE')} · ${Object.keys(backup.values).length} Parameter · Profil ${backup.profile_id}`:'Noch keine Sicherung an diesem Port.';
    const download=this.shadowRoot.querySelector('#download-parameters');if(download)download.disabled=!backup;
    const restore=this.shadowRoot.querySelector('#restore-saved');if(restore)restore.disabled=!backup || busy;
    const report=this.restoreReports.get(key),reportButton=this.shadowRoot.querySelector('#restore-report');if(reportButton)reportButton.disabled=!report;
    const state=this.shadowRoot.querySelector('#restore-status');if(state && report)state.textContent=this.restoreText(report);
  }
  restoreText(report){return report.status==='completed'?`Wiederherstellung geprüft: ${report.verified.length} geänderte Parameter geschrieben und zurückgelesen.`:report.status==='running'?`Letzter Vorgang unvollständig. ${report.verified.length} Parameter waren bestätigt. Vor erneutem Restore Protokoll und Gerät prüfen.`:`Wiederherstellung gestoppt: ${report.error || 'Unbekannter Fehler'}. ${report.verified.length} Parameter bestätigt${report.in_flight!=null?`, Index ${report.in_flight} möglicherweise geschrieben`:''}. Protokoll herunterladen.`;}
  async previewRestore(backup){
    const key=this.portKey(),entry_id=this.masterId,port=this.port,name=this.master?.name;
    if(this.parameterBusy.has(key))return;this.parameterBusy.add(key);this.paintParameters();this.notify('Sicherung und aktueller Sensor werden für die Vorschau geprüft …');
    let preview;
    try{preview=await this.call('preview_restore',{entry_id,port,...(backup?{backup}:{})});}catch(error){this.notify(error.message || String(error),true);return;}finally{this.parameterBusy.delete(key);this.paintParameters();}
    const changed=preview.rows.filter(r=>r.changed),dialog=document.createElement('dialog');dialog.className='master-dialog restore-dialog';
    dialog.innerHTML=`<h3>Parametersicherung wiederherstellen</h3><p><b>${esc(name)} · Port X${String(port).padStart(2,'0')}</b><br>Sensor-Seriennummer: ${esc(preview.target.serial)}<br>Hersteller-/Gerätekennung: ${preview.target.vendorid} / ${preview.target.deviceid}<br>Sicherung vom ${esc(new Date(preview.source_created_at).toLocaleString('de-DE'))}</p><p>${changed.length} Änderungen · ${preview.rows.length-changed.length} unverändert · ${preview.skipped.length} ausgelassen</p><div class="restore-table"><table><thead><tr><th>Parameter</th><th>Aktuell (Hex)</th><th>Sicherung (Hex)</th></tr></thead><tbody>${preview.rows.map(r=>`<tr><td>${esc(r.name)} <small>${r.index}${r.changed?'':' · unverändert'}</small></td><td><code>${esc(r.before)}</code></td><td><code>${esc(r.after)}</code></td></tr>`).join('')}</tbody></table></div>${preview.skipped.length?`<details><summary>Ausgelassene Parameter (${preview.skipped.length})</summary>${preview.skipped.map(r=>`<p>${r.index} · ${esc(r.name)}: ${esc(r.reason)}</p>`).join('')}</details>`:''}<p>Änderungen wirken auf den angeschlossenen Sensor. Bei einem Fehler wird gestoppt; bereits geschriebene Werte bleiben bestehen. Die Vorschau gilt fünf Minuten.</p><label class="restore-consent"><input type="checkbox" id="restore-consent"> Werte für diesen Sensor und Port geprüft</label><div class="parameter-actions"><button id="confirm-restore" class="primary" disabled>${changed.length?'Jetzt zurückschreiben':'Unveränderte Werte überprüfen'}</button><button id="cancel-restore">Abbrechen</button></div><p id="restore-progress" role="status"></p>`;
    this.shadowRoot.append(dialog);dialog.showModal();dialog.onclose=()=>dialog.remove();dialog.querySelector('#cancel-restore').onclick=()=>dialog.close();
    const submit=dialog.querySelector('#confirm-restore');dialog.querySelector('#restore-consent').onchange=e=>submit.disabled=!e.target.checked;
    submit.onclick=async()=>{submit.disabled=true;dialog.querySelector('#restore-consent').disabled=true;dialog.querySelector('#cancel-restore').disabled=true;dialog.oncancel=e=>e.preventDefault();dialog.querySelector('#restore-progress').textContent='Gerät wird erneut geprüft. Wiederherstellung läuft …';this.parameterBusy.add(key);
      try{const report=await this.call('restore_parameters',{entry_id,port,token:preview.token,confirm:true});this.restoreReports.set(key,report);dialog.querySelector('#restore-progress').textContent=this.restoreText(report);dialog.querySelector('#cancel-restore').textContent='Schließen';this.parameterReads.delete(key);}catch(error){dialog.querySelector('#restore-progress').textContent=`${error.message || error}. Vor erneutem Versuch das letzte Restore-Protokoll prüfen.`;}finally{this.parameterBusy.delete(key);dialog.querySelector('#cancel-restore').disabled=false;dialog.oncancel=null;this.paintParameters();}
    };
  }
  manageMaster(){
    const master=this.master;if(!master)return;
    const dialog=document.createElement('dialog');dialog.className='master-dialog';
    dialog.innerHTML=`<h3>Master verwalten</h3><form id="rename-master"><label>Mastername<input name="name" value="${esc(master.name)}" required maxlength="120"></label><button class="primary" type="submit">Namen speichern</button></form><hr><h4>Master ersetzen / erweitern</h4><p>Bestehende Geräte- und Entitäts-IDs sowie Portzuordnungen bleiben erhalten.</p><button id="replace-master">Austausch vorbereiten / fortsetzen</button><hr><h4>Master löschen</h4><p>Entfernt „${esc(master.name)}“ mit Portzuweisungen, zugehörigen Entitäten und Parametersicherungen aus Home Assistant. Eigene Geräteprofile bleiben in der Bibliothek. Am physischen Master wird nichts zurückgesetzt.</p><form id="delete-master"><label>Zum Löschen Masternamen eingeben<input name="confirm_name" autocomplete="off" required placeholder="${esc(master.name)}"></label><button class="danger" type="submit" disabled>Master endgültig löschen</button></form><p id="master-dialog-status" role="status"></p><button id="close-master-dialog">Schließen</button>`;
    this.shadowRoot.append(dialog);dialog.showModal();
    dialog.querySelector('#close-master-dialog').onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();
    dialog.querySelector('#replace-master').onclick=()=>{dialog.close();this.replaceMaster();};
    const deleteForm=dialog.querySelector('#delete-master');deleteForm.elements.confirm_name.oninput=()=>{deleteForm.querySelector('button').disabled=deleteForm.elements.confirm_name.value!==master.name;};
    const submit=async(e,type,values)=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const result=await this.call(type,{entry_id:master.entry_id,...values});dialog.close();await this.refresh(true);this.notify(type==='rename_master'?'Mastername gespeichert.':`Master entfernt.${result.require_restart?' Home Assistant muss neu gestartet werden.':''}`);}catch(error){dialog.querySelector('#master-dialog-status').textContent=error.message || String(error);button.disabled=false;}};
    dialog.querySelector('#rename-master').onsubmit=e=>submit(e,'rename_master',{name:e.target.elements.name.value});
    deleteForm.onsubmit=e=>submit(e,'delete_master',{confirm_name:e.target.elements.confirm_name.value});
  }
  async replaceMaster(){
    const master=this.master;if(!master || this.replacementDialog?.open)return;
    const dialog=document.createElement('dialog');dialog.className='master-dialog';
    dialog.innerHTML=`<h3>Master ersetzen / erweitern</h3><p>${esc(master.name)} · ${esc(master.identity.model)}<br>Seriennummer: ${esc(master.identity.serial)}</p><p>1. Einstellungen sichern und Verarbeitung pausieren.<br>2. Alten Master trennen, Ersatzmaster anschließen und prüfen.<br>3. Austausch bestätigen: Netzwerk übernehmen, bei Bedarf neu starten, Ziel-IP prüfen, Konfiguration zurücksichern und Master übernehmen.</p><p>Geräte- und Entitäts-IDs, Profile und Parametersicherungen bleiben erhalten. DO-Ports bleiben zunächst deaktiviert. Sensorparameter können nach der Übernahme je Sensor geprüft zurückgespielt werden.</p><button id="prepare-replacement">Sichern und Austausch vorbereiten</button><label>Netzwerk durchsuchen (IPv4/CIDR)<input id="replacement-subnet" placeholder="z. B. 10.100.0.0/22"></label><button id="replacement-search">Ersatzmaster suchen</button><div id="replacement-found"></div><label>IoT-Adresse des Ersatzmasters<input id="replacement-url" value="${esc(master.url || '')}"></label><button id="preview-replacement">Ersatzgerät prüfen</button><div id="replacement-preview"></div><button id="replacement-backup">Gesicherte Werte anzeigen</button><pre id="replacement-network-values"></pre><label><input type="checkbox" id="replacement-disconnected"> Alter Master getrennt, Ziel-IP frei und Ersatzmaster sowie Zuordnungen geprüft. Netzwerk und gesicherte Konfiguration übertragen und den Ersatzmaster übernehmen; DO-Ports bleiben deaktiviert.</label><button class="primary" id="replacement-automatic" disabled>Austausch automatisch durchführen</button><p>Nach dem Start läuft der Auftrag in Home Assistant weiter, auch wenn dieses Fenster geschlossen wird. Bei einer Unterbrechung hier erneut öffnen und fortsetzen.</p><details><summary>Einzelschritte / manuelle Übernahme</summary><button id="replacement-network" disabled>Nur Netzwerk übernehmen</button><button id="replacement-verify">Ziel-IP erneut prüfen</button><p>Nach bestätigter Ziel-IP werden gesicherte Portmodi, Application Tag und lesbare LR-Agent-Einstellungen übertragen. DO-Ports werden deaktiviert, zusätzliche Ports bleiben unverändert. MAC-Adresse und Zugangsdaten werden nicht kopiert.</p><button id="replacement-modes" disabled>Nur Konfiguration zurücksichern</button><label><input type="checkbox" id="replacement-manual-consent"> Ersatzmaster und Zuordnungen geprüft; ohne weitere Übertragung mit den aktuellen Portmodi übernehmen.</label><button id="confirm-replacement" disabled>Master manuell übernehmen</button></details><p id="replacement-status" role="status" aria-live="polite"></p><button id="cancel-replacement">Austausch abbrechen / bisherigen Master verwenden</button><button id="close-replacement">Schließen</button>`;
    this.replacementDialog=dialog;this.shadowRoot.append(dialog);dialog.showModal();
    const el=id=>dialog.querySelector('#'+id);
    let paused=!!master.replacement_paused, replacementToken=null, verified=false;
    let busy=false, running=false, resumable=false, resumeKnown=false, completed=false, pollTimer=null, closed=false;
    const status=el('replacement-status');
    const run=(action,extra={})=>this.call('replacement',{entry_id:master.entry_id,action,...extra});
    const stopPolling=()=>{clearTimeout(pollTimer);pollTimer=null;};
    this.stopReplacementPolling=()=>{closed=true;stopPolling();};
    dialog.onclose=()=>{closed=true;stopPolling();dialog.remove();this.replacementDialog=null;this.stopReplacementPolling=null;if(this.isConnected!==false)void this.refresh(true);};
    el('close-replacement').onclick=()=>dialog.close();
    const update=()=>{
      const locked=busy || running || completed;
      dialog.querySelectorAll('button,input').forEach(node=>{node.disabled=locked;});
      el('close-replacement').disabled=false;
      el('prepare-replacement').disabled=locked || paused || resumable;
      el('preview-replacement').disabled=locked || !paused;
      el('replacement-search').disabled=locked || resumable;
      el('replacement-url').disabled=locked || resumable;
      el('replacement-subnet').disabled=locked || resumable;
      el('replacement-automatic').textContent=resumable?'Austausch fortsetzen':'Austausch automatisch durchführen';
      el('replacement-automatic').disabled=locked || !(resumable || (paused && replacementToken && el('replacement-disconnected').checked));
      el('replacement-network').disabled=locked || resumable || !(replacementToken && el('replacement-disconnected').checked);
      el('replacement-verify').disabled=locked || !paused;
      el('replacement-backup').disabled=locked || !paused;
      el('replacement-modes').disabled=locked || !verified;
      el('confirm-replacement').disabled=locked || !replacementToken || !el('replacement-manual-consent').checked;
      el('cancel-replacement').disabled=locked || (!paused && resumable);
    };
    const invalidatePreview=()=>{replacementToken=null;el('replacement-preview').innerHTML='';el('replacement-disconnected').checked=false;el('replacement-manual-consent').checked=false;update();};
    const operate=async work=>{
      if(busy || running || completed)return;
      busy=true;update();
      try{await work();}catch(e){status.textContent=e.message || String(e);}
      finally{busy=false;if(!closed)update();}
    };
    const showBackup=async()=>{
      const b=await run('status'),h=b.hardware || {},n=h.network || {},t=b.transfer;
      resumable=(!!t || resumeKnown) && paused;verified=t?.stage==='verified';
      el('replacement-network-values').textContent=[h.error || '',`Ziel-IP: ${n.ipaddress || 'nicht gesichert'}`,`Subnetzmaske: ${n.subnetmask || '—'}`,`Gateway: ${n.ipdefaultgateway || '—'}`,`Adressierung: ${n.dhcp===0?'statisch':n.dhcp===1?'DHCP (manuell einrichten)':'unbekannt'}`,`Application Tag: ${h.settings?.['/devicetag/applicationtag'] || '—'}`,`LR-Agent: ${h.settings?.['/iotsetup/smobip'] || '—'} · Port ${h.settings?.['/iotsetup/smobport'] ?? '—'} · Intervall ${h.settings?.['/iotsetup/smobinterval'] ?? '—'}`,h.skipped?.length?'Nicht alle Zusatzparameter lesbar; diese werden ausgelassen.':'',...Object.entries(h.modes || {}).map(([p,m])=>`Port ${p}: ${modeLabel(m)}${m===2?' → zunächst Disabled':''}`),t?`Übertragung: ${t.stage==='verified'?'Ziel-IP bestätigt':'Rückmeldung prüfen'} · ${t.url}`:'',...(t?.ports || []).map(p=>`Port ${p.port}: ${p.state==='verified'?'bestätigt':'Ergebnis unklar'}`),...(t?.settings || []).map(p=>`${p.path.split('/').pop()}: ${p.state==='verified'?'bestätigt':'Ergebnis unklar'}`)].filter(Boolean).join('\n');
      if(t?.url)el('replacement-url').value=t.url;
    };
    const finish=async()=>{
      completed=true;running=false;resumable=false;paused=false;replacementToken=null;stopPolling();
      status.textContent='Ersatzmaster übernommen. Netzwerk und Konfiguration wurden zurückgelesen und bestätigt. Home Assistant ist mit dem Ersatzmaster verbunden. Die bisherigen IDs bleiben erhalten; DO-Ports sind deaktiviert.';
      update();await this.refresh(true);
    };
    const poll=async()=>{
      if(closed)return;
      try{
        const job=await run('job_status');if(closed)return;
        const expectCompletion=paused || resumable || running;
        running=!!job?.running;resumeKnown=!!job?.resumable;resumable=resumeKnown;
        if(job?.result && expectCompletion){await finish();return;}
        if(job?.error && (paused || resumable)){status.textContent=job.error;if(paused)await showBackup();}
        else if(running){
          resumable=true;
          const progress=job.progress;
          status.textContent=typeof progress==='string'?progress:(progress?.message || progress?.stage || 'Austausch läuft in Home Assistant …');
        }else if(paused || resumable){if(paused)await showBackup();if(resumable)status.textContent=paused?'Gespeicherter Austausch vorhanden. Mit „Austausch fortsetzen“ wird der Stand am Ersatzmaster geprüft und fortgeführt.':'Master bereits übernommen. Mit „Austausch fortsetzen“ wird die Verbindung in Home Assistant abschließend geprüft.';}
      }catch(e){status.textContent=`Status derzeit nicht erreichbar: ${e.message || String(e)}. Der Auftrag kann in Home Assistant weiterlaufen; Status wird erneut geprüft.`;running=true;}
      if(!closed){update();if(running)pollTimer=setTimeout(poll,2000);}
    };
    el('replacement-backup').onclick=()=>operate(showBackup);
    el('replacement-search').onclick=()=>operate(async()=>{
      const r=await run('search',{network:el('replacement-subnet').value}),area=el('replacement-found');
      area.innerHTML=r.found.map((m,i)=>`<button data-found="${i}">${esc(m.model)} · ${esc(m.serial)} · ${esc(m.url)}</button>`).join('') || 'Keine erreichbaren Master gefunden. IoT-Adresse gegebenenfalls direkt eingeben.';
      area.querySelectorAll('[data-found]').forEach(button=>button.onclick=()=>{if(busy || running || resumable)return;el('replacement-url').value=r.found[Number(button.dataset.found)].url;invalidatePreview();});
    });
    el('replacement-url').oninput=invalidatePreview;
    el('replacement-disconnected').onchange=update;el('replacement-manual-consent').onchange=update;
    const networkResult=r=>{
      verified=!!r.verified;resumable=true;invalidatePreview();
      if(r.verified){el('replacement-url').value=r.url;status.textContent='Ersatzmaster und Netzwerkwerte an der Ziel-IP bestätigt. Austausch automatisch fortsetzen oder die nächsten Einzelschritte ausführen.';}else{status.textContent=r.message;}
    };
    el('replacement-network').onclick=()=>operate(async()=>{networkResult(await run('network',{token:replacementToken,confirm:true}));await showBackup();});
    el('replacement-verify').onclick=()=>operate(async()=>networkResult(await run('verify_network')));
    el('replacement-modes').onclick=()=>operate(async()=>{await run('restore_modes',{confirm:true});status.textContent='Konfiguration zurückgelesen und bestätigt. DO-Ports bleiben deaktiviert. Mit „Austausch fortsetzen“ abschließend prüfen und übernehmen.';await showBackup();});
    el('prepare-replacement').onclick=()=>operate(async()=>{await run('prepare',{confirm:true});paused=true;status.textContent='Konfiguration gesichert. Verarbeitung pausiert. Master kann jetzt getauscht werden.';await showBackup();});
    el('cancel-replacement').onclick=()=>operate(async()=>{await run('cancel',{confirm:true});dialog.close();});
    el('preview-replacement').onclick=()=>operate(async()=>{
      invalidatePreview();
      const p=await run('preview',{url:el('replacement-url').value});replacementToken=p.token;
      el('replacement-preview').innerHTML=`<h4>${esc(p.old_model)} → ${esc(p.target.model)}</h4><p>Neue Seriennummer: ${esc(p.target.serial)}</p>${p.rows.map(r=>`<p>X${String(r.port).padStart(2,'0')} · ${r.new?'Neuer Port':esc(r.name || 'Zuordnung beibehalten')} · ${modeLabel(r.mode)}${r.profile_matches?'':' · Sensor passt derzeit nicht zum Profil'}</p>`).join('')}`;
      status.textContent='Vorschau gilt fünf Minuten. Ersatzmaster und gesicherte Werte prüfen, dann den automatischen Austausch bestätigen.';
      await showBackup();
    });
    el('confirm-replacement').onclick=()=>operate(async()=>{await run('confirm',{token:replacementToken,confirm:true});completed=true;paused=false;status.textContent='Ersatzmaster manuell übernommen. Die bestehenden IDs bleiben erhalten.';await this.refresh(true);});
    el('replacement-automatic').onclick=async()=>{
      if(busy || running || completed || !(resumable || (replacementToken && el('replacement-disconnected').checked)))return;
      running=true;stopPolling();update();status.textContent='Automatischer Austausch wird gestartet …';
      try{await run('run',{confirm:true,...(!resumable?{token:replacementToken}:{})});resumable=true;replacementToken=null;}
      catch(e){running=false;status.textContent=e.message || String(e);try{await showBackup();}catch{}update();return;}
      await poll();
    };
    // Recover both a running server-side job and a persisted transfer after a
    // browser/HA restart before enabling actions in this dialog.
    busy=true;update();await poll();busy=false;if(!closed)update();
  }
  bindLibrary(){
    this.shadowRoot.querySelector('#blank-profile')?.addEventListener('click',()=>{this.autoProfileId=true;this.draft=initialProfile();this.candidates=null;this.render();});
    this.shadowRoot.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{this.draft=structuredClone(this.profile(b.dataset.edit));this.autoProfileId=!this.draft.id.startsWith('custom_');if(this.autoProfileId)this.draft.id=profileIdFromName(this.draft.name,this.data.profiles);this.candidates=null;this.render();});
    this.shadowRoot.querySelector('#profile-kind')?.addEventListener('change',e=>{const metadata=Object.fromEntries(['id','name','manufacturer','model','description','purpose','image','notes'].map(k=>[k,this.draft[k]]));this.draft={...(e.target.value==='digital'?digitalProfile():initialProfile()),...metadata};this.candidates=null;this.render();});
    const form=this.shadowRoot.querySelector('#profile-form');if(!form)return;
    form.querySelectorAll('[name]').forEach(input=>input.addEventListener('input',()=>{this.draft[input.name]=input.value;if(input.name==='id')this.autoProfileId=false;if(input.name==='name'&&this.autoProfileId){this.draft.id=profileIdFromName(input.value,this.data.profiles);form.querySelector('[name="id"]').value=this.draft.id;}this.syncJson();}));
    this.shadowRoot.querySelector('#profile-json')?.addEventListener('change',e=>{try{this.draft={image:this.draft.image,...JSON.parse(e.target.value)};this.autoProfileId=false;form.querySelectorAll('[name]').forEach(input=>{input.value=input.name==='image'&&this.draft.image?.startsWith('data:')?'':this.draft[input.name] || '';});}catch(error){this.notify('Ungültiges JSON: '+error.message,true);}});
    this.shadowRoot.querySelector('#test-raw')?.addEventListener('input',e=>{this.testRaw=e.target.value;});
    this.shadowRoot.querySelector('#variant')?.addEventListener('change',e=>{this.autoProfileId=false;this.candidateIndex=Number(e.target.value);this.draft=structuredClone(this.candidates[this.candidateIndex].profile);this.render();});
    this.shadowRoot.querySelector('#iodd-upload')?.addEventListener('change',async e=>{
      const file=e.target.files[0];if(!file)return;if(file.size>2_000_000)return this.notify('Die IODD darf höchstens 2 MB groß sein.',true);
      this.notify('Herstellerdatei wird gelesen …');
      try{const content=(await this.asDataUrl(file)).split(',')[1];this.candidates=await this.call('import_iodd',{content,filename:file.name});this.candidateIndex=0;this.autoProfileId=false;this.draft=structuredClone(this.candidates[0].profile);this.render();this.notify(`${this.candidates.length} Gerätevariante(n) erkannt. Passende Variante auswählen und speichern.`);}catch(error){this.notify('IODD-Import: '+(error.message || error),true);}
    });
    this.shadowRoot.querySelector('#image-upload')?.addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;if(file.size>1_000_000)return this.notify('Bild darf höchstens 1 MB groß sein.',true);try{this.draft.image=await this.asDataUrl(file);this.render();}catch(error){this.notify(error.message,true);}});
    this.shadowRoot.querySelector('#test-profile')?.addEventListener('click',async()=>{try{const profile=this.readJson();const result=await this.call('test_profile',{profile,raw:this.testRaw || ''});this.shadowRoot.querySelector('#test-output').textContent=JSON.stringify(result,null,2);this.notify('Profiltest erfolgreich. Werte mit der Geräteanzeige vergleichen.');}catch(error){this.notify(error.message || String(error),true);}});
    this.shadowRoot.querySelector('#export-profile')?.addEventListener('click',()=>{try{const profile=this.readJson();this.download(`${profile.id}.json`,profile);}catch(error){this.notify(error.message,true);}});
    this.shadowRoot.querySelector('#delete-profile')?.addEventListener('click',async()=>{try{await this.call('delete_profile',{profile_id:this.draft.id});this.autoProfileId=true;this.draft=initialProfile();await this.refresh(true);this.notify('Profil gelöscht.');}catch(error){this.notify(error.message,true);}});
    form.addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const profile=this.readJson();await this.call('save_profile',{profile});this.draft=profile;this.autoProfileId=false;await this.refresh(true);this.notify('Geräteprofil gespeichert. Es steht jetzt an passenden Ports im Dropdown bereit.');}catch(error){this.notify(error.message || String(error),true);}finally{button.disabled=false;}});
  }
  profileJson(){const value={...this.draft};if(value.image?.startsWith('data:'))delete value.image;return JSON.stringify(value,null,2);}
  syncJson(){const el=this.shadowRoot.querySelector('#profile-json');if(el)el.value=this.profileJson();}
  readJson(){if(this.draft.kind==='digital')return {...this.draft};return {image:this.draft.image || '',...JSON.parse(this.shadowRoot.querySelector('#profile-json').value)};}
  asDataUrl(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error('Datei konnte nicht gelesen werden'));reader.readAsDataURL(file);});}
  paint(){
    const master=this.master;if(!master)return;
    const el=this.shadowRoot.querySelector('#master-status');if(el){el.textContent=master.online?'● Master verbunden':'○ Master nicht erreichbar';el.classList.toggle('offline',!master.online);}
    this.shadowRoot.querySelectorAll('[data-value]').forEach(e=>{const [port,key]=e.dataset.value.split(':');const item=master.ports[port];const field=this.profile(item?.profile)?.fields.find(f=>f.key===key);if(field)e.textContent=formatValue(master.online&&item.connected&&!item.error?item.values[key]:null,field);});
    this.shadowRoot.querySelectorAll('[data-status]').forEach(e=>{const item=master.ports[e.dataset.status];const online=master.online&&item?.connected;const digital=master.online&&[1,2].includes(item?.mode);e.textContent=digital?(item.mode===2?'Digitalausgang':'Digitaleingang'):online?'● Verbunden':'○ Offline';e.classList.toggle('offline',!online&&!digital);});
    this.shadowRoot.querySelectorAll('[data-channel]').forEach(e=>{const [port,pin]=e.dataset.channel.split(':');const state=channelState(master.ports[port],pin,master.online);e.className=`channel-led ${state.tone}`;e.textContent=state.text.replace('IO-Link ','').replace('EIN','AN');e.title=channelDescription(master.ports[port],pin,master.online);});
    this.shadowRoot.querySelectorAll('[data-output]').forEach(b=>b.disabled=!master.online||this.selected?.mode!==2||this.parameterBusy.has(this.portKey()));
    this.shadowRoot.querySelectorAll('[data-toggle]').forEach(b=>{const item=master.ports[b.dataset.toggle],state=modeStatus(item,master.online);b.textContent=state.label;b.title=state.text;b.className=`signal-badge ${state.tone}`;b.disabled=!state.clickable||this.parameterBusy.has(`${master.entry_id}:${b.dataset.toggle}:${item?.profile}`);b.setAttribute('aria-label',`${state.text}, Port ${b.dataset.toggle}`);});
    this.shadowRoot.querySelectorAll('[data-di2]').forEach(e=>{const state=channelState(master.ports[e.dataset.di2],'pin2',master.online);e.className=`signal-badge ${state.tone}`;e.title=channelDescription(master.ports[e.dataset.di2],'pin2',master.online);e.setAttribute('aria-label',e.title);});
    const apply=this.shadowRoot.querySelector('#apply-mode');if(apply)apply.disabled=!master.online||this.selected?.mode==null||this.parameterBusy.has(this.portKey());
    const raw=this.shadowRoot.querySelector('#raw');if(raw)raw.textContent=this.selected?.raw || 'Keine Prozessdaten';
    const error=this.shadowRoot.querySelector('#decode-error');if(error)error.textContent=this.selected?.error || '';
    const updated=this.shadowRoot.querySelector('#updated');if(updated)updated.textContent=this.selected?.updated?'Letzte Antwort: '+new Date(this.selected.updated).toLocaleTimeString('de-DE'):'';
    this.drawWires();
  }
  drawWires(){
    const grid=this.shadowRoot.querySelector('.topology-grid');const svg=this.shadowRoot.querySelector('.wires');const picture=this.shadowRoot.querySelector('.master-device img');if(!grid||!svg||!picture)return;
    const box=grid.getBoundingClientRect(), img=picture.getBoundingClientRect();if(!img.height)return;
    const rows=this.master.identity.model==='AL1350'?[.66,.83]:[.477,.61,.744,.88];
    const lanes=rows.length===4?[0,1,1,0]:rows.map(()=>0);
    svg.setAttribute('viewBox',`0 0 ${box.width} ${box.height}`);svg.replaceChildren();
    this.shadowRoot.querySelectorAll('[data-port]').forEach(card=>{
      const port=Number(card.dataset.port),left=port%2===1,rect=card.getBoundingClientRect(),rowIndex=Math.floor((port-1)/2);
      const x=(left?rect.right:rect.left)-box.left,y=(rect.top+rect.height/2)-box.top;
      const endX=img.left-box.left+img.width*(left?.275:.73),endY=img.top-box.top+img.height*rows[rowIndex];
      const elbow=(left?img.left-9-lanes[rowIndex]*7:img.right+9+lanes[rowIndex]*7)-box.left,color=port===this.port?'#e58b40':'#a9becd';
      const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',`M ${x} ${y} H ${elbow} V ${endY} H ${endX}`);path.setAttribute('fill','none');path.setAttribute('stroke',color);path.setAttribute('stroke-width','1.5');svg.append(path);
      const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');dot.setAttribute('cx',endX);dot.setAttribute('cy',endY);dot.setAttribute('r','3');dot.setAttribute('fill',color);svg.append(dot);
    });
  }
}
customElements.define('ifm-iolink-panel',IfmIolinkPanel);
