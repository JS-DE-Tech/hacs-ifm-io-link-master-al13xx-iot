const BASE = '/ifm_iolink_static';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const initialProfile = () => ({id:'custom_mein_sensor',name:'Mein Sensor',manufacturer:'',model:'',description:'',purpose:'',image:'',notes:'',length:2,fields:[{key:'value',name:'Messwert',type:'int',offset:0,length:2,scale:0.01,precision:2}]});
const formatValue = (value, field) => value == null ? '—' : typeof value === 'boolean' ? (value ? 'Aktiv' : 'Inaktiv') : `${new Intl.NumberFormat('de-DE',{maximumFractionDigits:field.precision ?? 3}).format(value)}${field.unit ? ' '+field.unit : ''}`;
const MODE_NAMES = {0:'Deaktiviert',1:'Digitaleingang (DI)',2:'Digitalausgang (DO)',3:'IO-Link'};
const PIN4_MODE_CARD = {
  0:{icon:'—',title:'Port deaktiviert',detail:'Pin 4 ist ausgeschaltet'},
  1:{icon:'DI',title:'Digitaleingang (Pin 4)',detail:'11–30 V high / 0–5 V low'},
  2:{icon:'DO',title:'Digitalausgang (Pin 4)',detail:'24 V · max. 300 mA'},
};

class IfmIolinkPanel extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:'open'}); this.data={masters:[],profiles:[]}; this.page='overview'; this.port=1; this.draft=initialProfile(); this.parameterReads=new Map(); this.parameterBackups=new Map(); this.parameterBusy=new Set(); this.restoreReports=new Map();
  }
  set hass(value) { this._hass=value; if (this.isConnected && !this.started) this.start(); }
  connectedCallback() { if (this._hass) this.start(); }
  disconnectedCallback() { clearInterval(this.timer); this.resizeObserver?.disconnect(); this.started=false; }
  start() { if(this.started)return; this.started=true; this.render(); this.refresh(); this.timer=setInterval(()=>this.refresh(),2000); }
  async call(type, values={}) { return this._hass.callWS({type:`ifm_iolink/${type}`,...values}); }
  async refresh(force=false) {
    if(this.loading)return; this.loading=true;
    try {
      const next=await this.call('snapshot',{include_profiles:force || !this.profilesLoaded});
      if(next.profiles){this.profilesLoaded=true;this.profileRevision=next.profile_revision;}else{next.profiles=this.data.profiles;if(next.profile_revision!==this.profileRevision)this.profilesLoaded=false;}
      const signature=JSON.stringify([next.masters.map(m=>[m.entry_id,m.name]),next.profiles.map(p=>[p.id,p.name])]);
      this.data=next; if(!next.masters.some(m=>m.entry_id===this.masterId)) this.masterId=next.masters[0]?.entry_id;
      if(force || signature!==this.signature){this.signature=signature;this.render();}else this.paint();
    } catch(error) { this.notify(`Verbindung zu Home Assistant: ${error.message || error}`,true); }
    finally {this.loading=false;}
  }
  get master(){return this.data.masters.find(m=>m.entry_id===this.masterId);}
  get selected(){return this.master?.ports?.[this.port];}
  profile(id){return this.data.profiles.find(p=>p.id===id);}
  notify(message,error=false){const el=this.shadowRoot.querySelector('#notice');if(el){el.textContent=message;el.className=error?'notice error':'notice';}}
  render() {
    const master=this.master;
    this.shadowRoot.innerHTML=`<link rel="stylesheet" href="${BASE}/panel.css?v=${esc(this.data.version || '')}"><div class="app">
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
    return `<section class="section-heading"><div><span class="eyebrow">DEINE ANLAGE</span><h2>${esc(master.name)}</h2><p>${portCount} IO-Link-Ports · Aktualisierung alle ${master.interval} Sekunden</p></div><div class="master-tools"><span class="master-diagnostics" id="master-diagnostics" role="status"></span><span class="status" id="master-status"></span><button id="manage-master">Master verwalten</button></div></section>
    <div class="workspace"><section class="topology" aria-label="Master mit angeschlossenen Geräten"><div class="topology-grid" style="--rows:${rows}">
      <div class="master-device" style="grid-row:1 / ${rows+1}"><span class="master-model">${esc(master.identity.model)}</span><img src="${BASE}/images/${master.identity.model.toLowerCase()}.png" alt="ifm ${esc(master.identity.model)}"><span class="master-caption">IO-LINK MASTER</span></div>
      <svg class="wires" aria-hidden="true"></svg>${Array.from({length:portCount},(_,i)=>this.portCard(i+1)).join('')}</div><p class="topology-hint">Port auswählen, Gerät zuweisen, Messwerte ansehen.</p></section>
      <aside class="inspector">${this.inspector()}</aside></div>`;
  }
  portCard(number) {
    const item=this.master.ports[number] || {};const profile=this.profile(item.profile);const assignment=item.assignment || {};
    const side=number%2?'left':'right';
    const pin4=PIN4_MODE_CARD[item.mode];
    return `<button class="port-card ${side} ${number===this.port?'selected':''}" data-port="${number}" style="grid-row:${Math.ceil(number/2)};grid-column:${side==='left'?1:3}">
      <span class="port-line"></span><div class="port-card-top"><span class="port-label-group"><span class="port-label">X${String(number).padStart(2,'0')}</span><span class="port-label" data-pin2="${number}" title="Digitaleingang Pin 2 · Ausgang 2 nach DIN EN 60947-5-2 (oft NC/Antivalent, je nach Sensor auch Diagnose/Teach-In)">DI2</span>${item.mode===1?`<span class="port-label" data-pin4="${number}" title="Digitaleingang Pin 4/C-Q · Hauptschaltausgang (Ausgang 1, meist NO) nach DIN EN 60947-5-2">DI4</span>`:''}${item.mode===2?`<span class="port-label" data-pin4="${number}" title="Digitalausgang Pin 4/C-Q">DO</span>`:''}</span><span class="port-state" data-status="${number}"></span></div>
      <div class="device-row">${pin4?`<span class="unknown-device compact">${esc(pin4.icon)}</span><div><strong>${esc(pin4.title)}</strong><small>${esc(pin4.detail)}</small></div>`:`${profile?.image?`<img src="${esc(profile.image)}" alt="${esc(profile.model)}" referrerpolicy="no-referrer">`:'<span class="unknown-device">?</span>'}<div><strong>${esc(assignment.name || profile?.model || 'Gerät auswählen')}</strong><small>${esc(assignment.location || (item.identity?.productname ? 'Gerät erkannt' : 'Noch nicht zugewiesen'))}</small></div>`}</div>
      <div class="card-values">${(profile?.fields || []).filter(f=>f.type!=='bool').slice(0,2).map(f=>`<div><small>${esc(f.name)}</small><b data-value="${number}:${esc(f.key)}">—</b></div>`).join('') || `<small>${esc(item.identity?.productname || 'Unbekannt / kein Gerät')}</small>`}</div>
      ${assignment.purpose?`<div class="purpose">${esc(assignment.purpose)}</div>`:''}</button>`;
  }
  inspector(){
    const item=this.selected || {};const profile=this.profile(item.profile);const a=item.assignment || {};
    return `<div class="inspector-title"><div><span class="eyebrow">ANSCHLUSS X${String(this.port).padStart(2,'0')}</span><h3>Gerät & Messwerte</h3></div><span class="port-state" data-status="${this.port}"></span></div>
      <form id="assignment"><label>Geräteprofil<select name="profile"><option value="unknown">Unbekannt · Debug-Datei erzeugen</option>${this.data.profiles.map(p=>`<option value="${esc(p.id)}" ${p.id===item.profile?'selected':''}>${esc(p.name)}${item.suggested?.includes(p.id)?' · passend zur Kennung':''}</option>`).join('')}</select></label>
      ${item.suggested?.length && item.profile==='unknown'?`<p class="suggestion">Passendes Profil erkannt. Im Dropdown als „passend zur Kennung“ markiert.</p>`:''}
      <label>Gerätebezeichnung<input name="name" maxlength="500" value="${esc(a.name)}" placeholder="z. B. Druck am Poolfilter"></label>
      <label>Standort<input name="location" maxlength="500" value="${esc(a.location)}" placeholder="z. B. Heizungsraum"></label>
      <label>Verwendungszweck<input name="purpose" maxlength="500" value="${esc(a.purpose || profile?.purpose)}" placeholder="Was überwacht dieses Gerät?"></label>
      <button class="primary" type="submit">Portzuweisung speichern</button></form>
      <div class="action-row"><button id="debug">Debug-Datei</button><button id="new-device">Eigenes Gerät</button></div>
      <div class="decode-error" id="decode-error" role="status"></div>
      ${profile?`<section class="readings"><h4>Prozesswerte <span>${profile.fields.length}</span></h4>${profile.fields.map(f=>`<div class="reading"><span>${esc(f.name)}</span><strong data-value="${this.port}:${esc(f.key)}">—</strong></div>`).join('')}</section>
      <details><summary>Geräteinformationen & Hinweise</summary><p>${esc(profile.description)}</p><p>${esc(profile.notes)}</p><small>Quelle: ${esc(profile.source)}</small></details>
      ${profile.parameters?.length?`<details class="parameter-list"><summary>Parameterliste anzeigen</summary><div class="parameter parameter-read-all"><div><b>Alle Gerätedaten lesen</b></div><button id="read-all" title="Alle Gerätedaten lesen">Lesen</button></div><p id="parameter-status" role="status">Alle im Profil enthaltenen Parameter werden nacheinander gelesen.</p><p class="field-help">Als Entity markierte Parameter erscheinen in Home Assistant als Sensor- (nur lesbar), Number- (freier Zahlenbereich) oder Select-Entity (feste Werteliste, z. B. Prozentstufen). Der Wert wird beim Start, nach jeder Änderung und stündlich neu gelesen.</p>${profile.parameters.map(p=>{const kind=this.parameterKind(p);const checked=(a.entities||[]).includes(p.index);const kindLabel={number:'Number',select:'Select',sensor:'Sensor'}[kind];const kindTitle={number:'Number-Entity (freier Zahlenbereich)',select:'Select-Entity (feste Werteliste)',sensor:'Sensor-Entity (nur lesbar)'}[kind];return `<div class="parameter"><label class="parameter-entity-toggle" title="Als ${kindTitle} anlegen"><input type="checkbox" data-entity="${p.index}" ${checked?'checked':''}><small>${kindLabel}</small></label><div><b>${esc(p.name)}</b><small>Index ${p.index} · ${esc(p.datatype)} · ${esc(p.access || 'ro')} · ${esc(p.description)}</small><output id="parameter-${p.index}">Noch nicht gelesen</output></div><button data-read="${p.index}" title="Parameter ${esc(p.name)} lesen">Lesen</button></div>`;}).join('')}<div class="parameter-entity-save"><button id="save-parameter-entities">Auswahl als Entity speichern</button><p id="parameter-entity-status" role="status"></p></div></details><details><summary>Sensortausch & Sicherung</summary><div class="parameter-actions backup-actions"><div class="backup-action"><button id="backup-parameters" aria-describedby="backup-help">Parametersicherung erstellen</button><p id="backup-help">Liest die aktuellen Profilparameter des Sensors und speichert sie für diesen Port in Home Assistant. Nur eine vollständige Abfrage ersetzt die bisherige Sicherung.</p></div><div class="backup-action"><button id="restore-saved" aria-describedby="restore-saved-help" disabled>Parametersicherung wiederherstellen</button><p id="restore-saved-help">Verwendet die für diesen Port in Home Assistant gespeicherte Sicherung. Zeigt zuerst eine Vorschau; erst nach deiner Bestätigung werden passende Parameter auf den angeschlossenen Sensor übertragen.</p></div><div class="backup-action"><button id="download-parameters" aria-describedby="download-help" disabled>Sicherung als JSON herunterladen</button><p id="download-help">Lädt die in Home Assistant gespeicherte Port-Sicherung als JSON-Datei auf deinen Computer. Der Sensor wird dabei nicht erneut ausgelesen.</p></div><div class="backup-action"><label class="button upload">JSON-Sicherung wiederherstellen<input id="restore-upload" type="file" accept=".json,application/json" aria-label="JSON-Sicherung auswählen" aria-describedby="restore-file-help"></label><p id="restore-file-help">Wähle eine zuvor heruntergeladene JSON-Sicherung von deinem Computer. Die Datei und der Sensor werden geprüft; anschließend bestätigst du die Wiederherstellung in der Vorschau.</p></div><div class="backup-action"><button id="restore-report" aria-describedby="restore-report-help" disabled>Protokoll herunterladen</button><p id="restore-report-help">Lädt das Protokoll der letzten Wiederherstellung an diesem Port herunter: ursprüngliche Werte, bestätigte Änderungen und mögliche Fehler. Erst nach einem Wiederherstellungsversuch verfügbar.</p></div></div><p id="backup-status"></p><p id="restore-status" role="status"></p><p>Eine Wiederherstellung prüft Gerätekennung, Profil und aktuelle Werte. Nur unterstützte schreibbare Parameter werden nach Bestätigung übertragen und zurückgelesen. Unveränderte Werte werden ausgelassen. Bei Fehlern wird gestoppt; bereits geschriebene Werte bleiben bestehen. Das Protokoll enthält die ursprünglichen Werte. Es erfolgt kein automatischer Rollback. Für den automatischen Sensortausch kann im Master die IO-Link-Funktion „Backup + Restore“ mit einem kompatiblen Ersatzsensor eingerichtet werden.</p></details>`:''}`:'<div class="unknown-info"><h4>Ein neues Gerät?</h4><p>Importiere seine Hersteller-IODD in der Gerätebibliothek. Alternativ enthält die Debug-Datei Rohwerte und Gerätekennung für ein eigenes Übersetzungsprofil.</p></div>'}
      ${profile.commands?.length?`<details><summary>Kommandos anzeigen</summary><p class="field-help">Sendet einen festen, nicht in der IODD beschriebenen Wert an Index/Subindex 0 des Sensors, z. B. zum Starten einer Kalibrierung oder eines Werksresets.</p>${profile.commands.map(c=>`<div class="parameter"><div><b>${esc(c.name)}</b><small>Index ${c.index} · Wert ${c.value} · ${esc(c.description)}</small><output id="command-${c.index}-${c.value}"></output></div><button data-command="${c.index}" data-command-value="${c.value}" title="Kommando ${esc(c.name)} senden">Senden</button></div>`).join('')}</details>`:''}
      <details><summary>Verbindung & Rohdaten</summary><dl>${['productname','vendorid','deviceid','serial'].map(k=>`<dt>${esc(k)}</dt><dd>${esc(item.identity?.[k] ?? '—')}</dd>`).join('')}<dt>Digitaleingang (Pin 2)</dt><dd id="pin2">—</dd></dl><code id="raw"></code><small id="updated"></small></details>
      ${this.portModeDetails(item)}`;
  }
  portModeDetails(item){
    const mode=item.mode;
    if(mode==null)return `<details><summary>Portmodus</summary><p class="field-help">Portmodus wird geladen …</p></details>`;
    const options=[3,2,1,0].map(m=>`<option value="${m}" ${m===mode?'selected':''}>${esc(MODE_NAMES[m])}${m===mode?' (aktuell)':''}</option>`).join('');
    return `<details><summary>Portmodus</summary><p>Aktueller Modus (Pin 4): <b>${esc(MODE_NAMES[mode])}</b></p>
      <label>Zielmodus<select id="port-mode-target">${options}</select></label>
      <p class="field-help">Pin 4 (C/Q) kann zwischen IO-Link-Kommunikation, Digitalausgang, Digitaleingang und Deaktiviert umgeschaltet werden. Ein Wechsel trennt einen ggf. angeschlossenen IO-Link-Sensor von diesem Port und läuft nur nach Bestätigung in einer Vorschau.</p>
      <button id="preview-port-mode" disabled>Modus wechseln …</button>
      <p id="port-mode-status" role="status"></p></details>`;
  }
  paintPortModeButton(){
    const select=this.shadowRoot.querySelector('#port-mode-target'),btn=this.shadowRoot.querySelector('#preview-port-mode');
    if(!select || !btn)return;
    btn.disabled=this.parameterBusy.has(this.portKey()) || Number(select.value)===this.selected?.mode;
  }
  library(){
    return `<section class="section-heading"><div><span class="eyebrow">EINMAL ANLEGEN · MEHRFACH VERWENDEN</span><h2>Deine Gerätebibliothek</h2><p>Herstellerdatei importieren oder ein eigenes Übersetzungsprofil anlegen.</p></div><div class="action-row"><label class="button primary upload">IODD importieren<input id="iodd-upload" type="file" accept=".zip,.xml"></label><button id="blank-profile">+ Eigenes Gerät</button></div></section>
      <div class="library-layout"><section class="library-list">${this.data.profiles.map(p=>`<button class="library-card" data-edit="${esc(p.id)}">${p.image?`<img src="${esc(p.image)}" alt="${esc(p.model)}" referrerpolicy="no-referrer">`:'<span class="unknown-device">?</span>'}<div><span class="eyebrow">${p.id.startsWith('custom_')?'EIGENES GERÄT':'MITGELIEFERT'}</span><h3>${esc(p.name)}</h3><p>${esc(p.purpose || p.description)}</p><small>${p.fields.length} Prozesswerte · ${p.length} Byte${p.parameters?.length?` · ${p.parameters.length} Parameter`:''}</small></div><span>↗</span></button>`).join('')}</section>
      <section class="profile-editor"><span class="eyebrow">PROFILWERKSTATT</span><h3>${esc(this.draft.name || 'Eigenes Gerät')}</h3>
      <div id="import-candidates">${this.candidates?.length?`<label>IODD-Variante<select id="variant">${this.candidates.map((c,i)=>`<option value="${i}" ${i===this.candidateIndex?'selected':''}>${esc(c.profile.name)} · ${esc(c.layout)} · ID ${esc(c.profile.match?.[0]?.deviceid?.toString(16))}</option>`).join('')}</select></label><p class="suggestion">${esc(this.candidates[this.candidateIndex || 0].warnings.join(' · ') || 'Herstellerdaten importiert. Prüfe Vorschau und Gerätevariante, dann speichern.')}</p>`:''}</div>
      <form id="profile-form"><div class="two-col"><label>Profil-ID<input name="id" value="${esc(this.draft.id)}" required pattern="custom_[a-z0-9_]+"></label><label>Gerätename<input name="name" value="${esc(this.draft.name)}" required></label><label>Hersteller<input name="manufacturer" value="${esc(this.draft.manufacturer)}"></label><label>Modell<input name="model" value="${esc(this.draft.model)}"></label></div>
      <label>Informationen zum Gerät<textarea name="description" rows="2">${esc(this.draft.description)}</textarea></label><label>Verwendungszweck<input name="purpose" value="${esc(this.draft.purpose)}"></label>
      <label>Bild-URL oder /local/-Pfad<input name="image" value="${esc(this.draft.image?.startsWith('data:')?'':this.draft.image)}" placeholder="https://… oder /local/mein-sensor.png"></label><div class="image-upload">${this.draft.image?`<img src="${esc(this.draft.image)}" alt="Profilbild" referrerpolicy="no-referrer">`:''}<label class="button upload">Bild hochladen<input id="image-upload" type="file" accept="image/png,image/jpeg,image/webp"></label></div>
      <label>Hinweise<textarea name="notes" rows="2">${esc(this.draft.notes)}</textarea></label>
      <label>Übersetzungsprofil (JSON)<textarea id="profile-json" rows="12" spellcheck="false">${esc(this.profileJson())}</textarea></label><p class="field-help">Bytepositionen, Vorzeichen, Skalierung und Einheiten. Hersteller-IODDs füllen das Profil automatisch aus. Hier lässt sich auch ein erstelltes JSON-Profil einfügen.</p>
      <label>Test-Rohwert (Hex)<input id="test-raw" value="${esc(this.testRaw || '')}" placeholder="z. B. 08980101"></label><div class="action-row"><button id="test-profile" type="button">Übersetzung testen</button><button id="export-profile" type="button">JSON exportieren</button></div><pre id="test-output"></pre>
      <div class="action-row"><button class="primary" type="submit">Geräteprofil speichern</button>${this.draft.id?.startsWith('custom_')&&this.profile(this.draft.id)?'<button type="button" id="delete-profile">Löschen</button>':''}</div></form></section></div>`;
  }
  async downloadDebug() {
    const result=await this.call('debug',{entry_id:this.masterId,port:this.port});
    this.download(`iolink-port-${this.port}-debug.json`,result); return result;
  }
  download(name,value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  bindOverview(){
    this.shadowRoot.querySelectorAll('[data-port]').forEach(b=>b.onclick=()=>{this.port=Number(b.dataset.port);this.render();});
    this.shadowRoot.querySelector('#assignment')?.addEventListener('submit',async e=>{
      e.preventDefault();const button=e.submitter;button.disabled=true;
      try{const values=Object.fromEntries(new FormData(e.target));if(values.profile==='unknown') await this.downloadDebug();await this.call('assign',{entry_id:this.masterId,port:this.port,...values});this.notify('Portzuweisung gespeichert. Home Assistant lädt die Sensoren neu.');setTimeout(()=>this.refresh(true),1500);}catch(error){this.notify(error.message || String(error),true);}finally{button.disabled=false;}
    });
    this.shadowRoot.querySelector('#debug')?.addEventListener('click',()=>this.downloadDebug().catch(e=>this.notify(e.message,true)));
    this.shadowRoot.querySelector('#new-device')?.addEventListener('click',()=>{this.testRaw=this.selected?.raw || '';this.page='library';this.draft=initialProfile();this.draft.length=Math.max(1,this.testRaw.length/2);this.render();});
    this.shadowRoot.querySelector('#manage-master')?.addEventListener('click',()=>this.manageMaster());
    this.shadowRoot.querySelector('#restore-saved')?.addEventListener('click',()=>this.previewRestore());
    this.shadowRoot.querySelector('#port-mode-target')?.addEventListener('change',()=>this.paintPortModeButton());
    this.shadowRoot.querySelector('#preview-port-mode')?.addEventListener('click',()=>{const select=this.shadowRoot.querySelector('#port-mode-target');if(select)this.previewPortMode(Number(select.value));});
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
    this.shadowRoot.querySelectorAll('[data-command]').forEach(b=>b.onclick=async()=>{
      const key=this.portKey(),index=b.dataset.command,value=b.dataset.commandValue,entry_id=this.masterId,port=this.port;
      if(this.parameterBusy.has(key))return;this.parameterBusy.add(key);this.paintParameters();
      const output=this.shadowRoot.querySelector(`#command-${index}-${value}`);
      try{await this.call('send_command',{entry_id,port,index:Number(index),value:Number(value)});if(output)output.textContent='Gesendet.';}
      catch(e){if(output)output.textContent=`Fehler: ${e.message || e}`;}
      finally{this.parameterBusy.delete(key);this.paintParameters();}
    });
    if(this.selected){const key=this.portKey();this.call('get_parameter_backup',{entry_id:this.masterId,port:this.port}).then(result=>{this.parameterBackups.set(key,result.backup);this.paintParameters();}).catch(e=>this.notify(e.message,true));this.call('get_restore_report',{entry_id:this.masterId,port:this.port}).then(result=>{this.restoreReports.set(key,result.report);this.paintParameters();}).catch(e=>this.notify(e.message,true));}
    this.shadowRoot.querySelector('#save-parameter-entities')?.addEventListener('click',async()=>{
      const button=this.shadowRoot.querySelector('#save-parameter-entities'),status=this.shadowRoot.querySelector('#parameter-entity-status');
      const indices=[...this.shadowRoot.querySelectorAll('[data-entity]')].filter(i=>i.checked).map(i=>Number(i.dataset.entity));
      button.disabled=true;
      try{await this.call('set_parameter_entities',{entry_id:this.masterId,port:this.port,indices});if(status)status.textContent=`${indices.length} Parameter als Entity ausgewählt. Home Assistant lädt die Sensoren neu.`;setTimeout(()=>this.refresh(true),1500);}
      catch(error){if(status)status.textContent=error.message || String(error);}
      finally{button.disabled=false;}
    });
  }
  parameterKind(p){
    const field=p.decoder?.fields?.length===1?p.decoder.fields[0]:null;
    if(!field || p.access!=='rw' || !['uint','int'].includes(field.type))return 'sensor';
    const size=field.length ?? 1;
    const trivial=(field.offset ?? 0)===0 && (field.shift ?? 0)===0 && (field.bits ?? size*8)===size*8;
    if(!trivial)return 'sensor';
    return field.values?'select':'number';
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
    this.shadowRoot.querySelectorAll('[data-read],[data-command],#read-all,#backup-parameters,#restore-upload').forEach(b=>b.disabled=busy);
    this.paintPortModeButton();
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
  async previewPortMode(targetMode){
    const key=this.portKey(),entry_id=this.masterId,port=this.port,name=this.master?.name;
    if(this.parameterBusy.has(key))return;this.parameterBusy.add(key);this.paintParameters();this.notify('Aktueller Portmodus wird für die Vorschau geprüft …');
    let preview;
    try{preview=await this.call('preview_port_mode',{entry_id,port,target_mode:targetMode});}catch(error){this.notify(error.message || String(error),true);return;}finally{this.parameterBusy.delete(key);this.paintParameters();}
    const dialog=document.createElement('dialog');dialog.className='master-dialog restore-dialog';
    dialog.innerHTML=`<h3>Portmodus wechseln</h3><p><b>${esc(name)} · Port X${String(port).padStart(2,'0')}</b><br>Aktueller Modus: ${esc(MODE_NAMES[preview.current_mode] ?? preview.current_mode)}<br>Neuer Modus: ${esc(MODE_NAMES[preview.target_mode] ?? preview.target_mode)}</p>
      ${preview.device_connected?`<p class="suggestion">An diesem Port ist aktuell ein Gerät verbunden${preview.assignment_name?` (${esc(preview.assignment_name)})`:''}. Der Wechsel trennt dieses Gerät von Pin 4.</p>`:''}
      ${preview.target_mode!==3?'<p>Digitalausgang, Digitaleingang und Deaktiviert können keine IO-Link-Prozessdaten liefern; die Portzuweisung wird dabei auf „Unbekannt“ zurückgesetzt.</p>':''}
      <p>Die Vorschau gilt fünf Minuten.</p>
      <label class="restore-consent"><input type="checkbox" id="port-mode-consent"> Wechsel für diesen Port bestätigt</label>
      <div class="parameter-actions"><button id="confirm-port-mode" class="primary" disabled>Jetzt wechseln</button><button id="cancel-port-mode">Abbrechen</button></div>
      <p id="port-mode-progress" role="status"></p>`;
    this.shadowRoot.append(dialog);dialog.showModal();dialog.onclose=()=>dialog.remove();dialog.querySelector('#cancel-port-mode').onclick=()=>dialog.close();
    const submit=dialog.querySelector('#confirm-port-mode');dialog.querySelector('#port-mode-consent').onchange=e=>submit.disabled=!e.target.checked;
    submit.onclick=async()=>{submit.disabled=true;dialog.querySelector('#port-mode-consent').disabled=true;dialog.querySelector('#cancel-port-mode').disabled=true;dialog.oncancel=e=>e.preventDefault();dialog.querySelector('#port-mode-progress').textContent='Modus wird gewechselt …';this.parameterBusy.add(key);
      try{await this.call('set_port_mode',{entry_id,port,token:preview.token,confirm:true});dialog.querySelector('#port-mode-progress').textContent='Portmodus gewechselt. Home Assistant lädt die Sensoren neu.';dialog.querySelector('#cancel-port-mode').textContent='Schließen';setTimeout(()=>this.refresh(true),1500);}catch(error){dialog.querySelector('#port-mode-progress').textContent=`${error.message || error}. Vor erneutem Versuch den aktuellen Modus prüfen.`;}finally{this.parameterBusy.delete(key);dialog.querySelector('#cancel-port-mode').disabled=false;dialog.oncancel=null;this.paintParameters();}
    };
  }
  manageMaster(){
    const master=this.master;if(!master)return;
    const dialog=document.createElement('dialog');dialog.className='master-dialog';
    dialog.innerHTML=`<h3>Master verwalten</h3><form id="rename-master"><label>Mastername<input name="name" value="${esc(master.name)}" required maxlength="120"></label><button class="primary" type="submit">Namen speichern</button></form><hr><h4>Master löschen</h4><p>Entfernt „${esc(master.name)}“ mit Portzuweisungen, zugehörigen Entitäten und Parametersicherungen aus Home Assistant. Eigene Geräteprofile bleiben in der Bibliothek. Am physischen Master wird nichts zurückgesetzt.</p><form id="delete-master"><label>Zum Löschen Masternamen eingeben<input name="confirm_name" autocomplete="off" required placeholder="${esc(master.name)}"></label><button class="danger" type="submit" disabled>Master endgültig löschen</button></form><p id="master-dialog-status" role="status"></p><button id="close-master-dialog">Schließen</button>`;
    this.shadowRoot.append(dialog);dialog.showModal();
    dialog.querySelector('#close-master-dialog').onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();
    const deleteForm=dialog.querySelector('#delete-master');deleteForm.elements.confirm_name.oninput=()=>{deleteForm.querySelector('button').disabled=deleteForm.elements.confirm_name.value!==master.name;};
    const submit=async(e,type,values)=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const result=await this.call(type,{entry_id:master.entry_id,...values});dialog.close();await this.refresh(true);this.notify(type==='rename_master'?'Mastername gespeichert.':`Master entfernt.${result.require_restart?' Home Assistant muss neu gestartet werden.':''}`);}catch(error){dialog.querySelector('#master-dialog-status').textContent=error.message || String(error);button.disabled=false;}};
    dialog.querySelector('#rename-master').onsubmit=e=>submit(e,'rename_master',{name:e.target.elements.name.value});
    deleteForm.onsubmit=e=>submit(e,'delete_master',{confirm_name:e.target.elements.confirm_name.value});
  }
  bindLibrary(){
    this.shadowRoot.querySelector('#blank-profile')?.addEventListener('click',()=>{this.draft=initialProfile();this.candidates=null;this.render();});
    this.shadowRoot.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{this.draft=structuredClone(this.profile(b.dataset.edit));if(!this.draft.id.startsWith('custom_'))this.draft.id='custom_'+this.draft.id;this.candidates=null;this.render();});
    const form=this.shadowRoot.querySelector('#profile-form');if(!form)return;
    form.querySelectorAll('[name]').forEach(input=>input.addEventListener('input',()=>{this.draft[input.name]=input.value;this.syncJson();}));
    this.shadowRoot.querySelector('#profile-json').addEventListener('change',e=>{try{this.draft={image:this.draft.image,...JSON.parse(e.target.value)};form.querySelectorAll('[name]').forEach(input=>{input.value=input.name==='image'&&this.draft.image?.startsWith('data:')?'':this.draft[input.name] || '';});}catch(error){this.notify('Ungültiges JSON: '+error.message,true);}});
    this.shadowRoot.querySelector('#test-raw').addEventListener('input',e=>{this.testRaw=e.target.value;});
    this.shadowRoot.querySelector('#variant')?.addEventListener('change',e=>{this.candidateIndex=Number(e.target.value);this.draft=structuredClone(this.candidates[this.candidateIndex].profile);this.render();});
    this.shadowRoot.querySelector('#iodd-upload')?.addEventListener('change',async e=>{
      const file=e.target.files[0];if(!file)return;if(file.size>2_000_000)return this.notify('Die IODD darf höchstens 2 MB groß sein.',true);
      this.notify('Herstellerdatei wird gelesen …');
      try{const content=(await this.asDataUrl(file)).split(',')[1];this.candidates=await this.call('import_iodd',{content,filename:file.name});this.candidateIndex=0;this.draft=structuredClone(this.candidates[0].profile);this.render();this.notify(`${this.candidates.length} Gerätevariante(n) erkannt. Passende Variante auswählen und speichern.`);}catch(error){this.notify('IODD-Import: '+(error.message || error),true);}
    });
    this.shadowRoot.querySelector('#image-upload')?.addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;if(file.size>1_000_000)return this.notify('Bild darf höchstens 1 MB groß sein.',true);try{this.draft.image=await this.asDataUrl(file);this.render();}catch(error){this.notify(error.message,true);}});
    this.shadowRoot.querySelector('#test-profile')?.addEventListener('click',async()=>{try{const profile=this.readJson();const result=await this.call('test_profile',{profile,raw:this.testRaw || ''});this.shadowRoot.querySelector('#test-output').textContent=JSON.stringify(result,null,2);this.notify('Profiltest erfolgreich. Werte mit der Geräteanzeige vergleichen.');}catch(error){this.notify(error.message || String(error),true);}});
    this.shadowRoot.querySelector('#export-profile')?.addEventListener('click',()=>{try{const profile=this.readJson();this.download(`${profile.id}.json`,profile);}catch(error){this.notify(error.message,true);}});
    this.shadowRoot.querySelector('#delete-profile')?.addEventListener('click',async()=>{try{await this.call('delete_profile',{profile_id:this.draft.id});this.draft=initialProfile();await this.refresh(true);this.notify('Profil gelöscht.');}catch(error){this.notify(error.message,true);}});
    form.addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const profile=this.readJson();await this.call('save_profile',{profile});this.draft=profile;await this.refresh(true);this.notify('Geräteprofil gespeichert. Es steht jetzt an allen Ports im Dropdown bereit.');}catch(error){this.notify(error.message || String(error),true);}finally{button.disabled=false;}});
  }
  profileJson(){const value={...this.draft};if(value.image?.startsWith('data:'))delete value.image;return JSON.stringify(value,null,2);}
  syncJson(){const el=this.shadowRoot.querySelector('#profile-json');if(el)el.value=this.profileJson();}
  readJson(){return {image:this.draft.image || '',...JSON.parse(this.shadowRoot.querySelector('#profile-json').value)};}
  asDataUrl(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error('Datei konnte nicht gelesen werden'));reader.readAsDataURL(file);});}
  paint(){
    const master=this.master;if(!master)return;
    const el=this.shadowRoot.querySelector('#master-status');if(el){el.textContent=master.online?'● Master verbunden':'○ Master nicht erreichbar';el.classList.toggle('offline',!master.online);}
    const diag=this.shadowRoot.querySelector('#master-diagnostics');
    if(diag){
      const d=master.diagnostics || {};
      const problem=!!d.status;
      const parts=[];
      if(d.temperature!=null)parts.push(`${d.temperature} °C`);
      if(d.voltage!=null)parts.push(`${d.voltage.toFixed(1)} V`);
      if(d.power!=null)parts.push(`${d.power.toFixed(1)} W`);
      parts.push(problem?`⚠ Störung (Code ${d.status})`:'✓ Status ok');
      diag.textContent=master.online?parts.join(' · '):'';
      diag.classList.toggle('problem',master.online && problem);
      diag.hidden=!master.online;
    }
    this.shadowRoot.querySelectorAll('[data-value]').forEach(e=>{const [port,key]=e.dataset.value.split(':');const item=master.ports[port];const field=this.profile(item?.profile)?.fields.find(f=>f.key===key);if(field)e.textContent=formatValue(master.online&&item.connected&&!item.error?item.values[key]:null,field);});
    this.shadowRoot.querySelectorAll('[data-status]').forEach(e=>{const item=master.ports[e.dataset.status];const online=master.online&&item?.connected;e.textContent=online?'● Verbunden':'○ Offline';e.classList.toggle('offline',!online);});
    this.shadowRoot.querySelectorAll('[data-pin2]').forEach(e=>{const item=master.ports[e.dataset.pin2];e.classList.toggle('io-on',!!item?.pin2);});
    this.shadowRoot.querySelectorAll('[data-pin4]').forEach(e=>{
      const item=master.ports[e.dataset.pin4];
      const isDo=item?.mode===2;
      const on=isDo?(item?.pdout && item.pdout!=='00'):item?.mode===1?!!item?.pin4:false;
      e.classList.toggle('do-on',!!(isDo && on));
      e.classList.toggle('io-on',!!(!isDo && on));
    });
    const pin2=this.shadowRoot.querySelector('#pin2');if(pin2)pin2.textContent=this.selected?.pin2==null?'—':this.selected.pin2?'Aktiv':'Inaktiv';
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
