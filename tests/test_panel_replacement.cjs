// Exercise the real replacement-dialog controller with a small DOM and WS fake.
// No device writes, Home Assistant instance or third-party DOM package required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../custom_components/ifm_iolink/frontend/panel.js'), 'utf8');

class Element {
  constructor(tag='div') { this.tag=tag;this.nodes=new Map();this.disabled=false;this.checked=false;this.value='';this.textContent=''; }
  set innerHTML(value) {
    this.html=value;this.nodes.clear();
    for(const [,tag,attrs,id,tail] of value.matchAll(/<(\w+)\s+([^>]*?)id="([^"]+)"([^>]*)>/g)) {
      const node=new Element(tag);node.disabled=(attrs+tail).includes('disabled');
      node.value=(attrs+tail).match(/value="([^"]*)"/)?.[1] || '';
      this.nodes.set('#'+id,node);
    }
  }
  get innerHTML(){return this.html;}
  querySelector(selector){return this.nodes.get(selector) || null;}
  querySelectorAll(selector){return selector==='button,input'?[...this.nodes.values()].filter(n=>['button','input'].includes(n.tag)):[];}
  showModal(){this.open=true;}
  close(){this.open=false;this.onclose?.();}
  remove(){this.removed=true;}
}

function fixture({paused=true,transfer=null,jobs=[{}]}={}) {
  const requests=[],timers=new Map();let timerId=0,dialog,jobIndex=0;
  const context=vm.createContext({HTMLElement:class {},customElements:{define(){}},document:{createElement(){dialog=new Element('dialog');return dialog;}},
    setTimeout(fn,ms){assert.equal(ms,2000);timers.set(++timerId,fn);return timerId;},clearTimeout(id){timers.delete(id);}});
  vm.runInContext(source+'\nthis.Panel=IfmIolinkPanel;',context);
  const panel={master:{entry_id:'garage',name:'Garage',identity:{model:'AL1350',serial:'OLD'},url:'http://old',replacement_paused:paused},
    shadowRoot:{append(){}},refreshes:0,async refresh(){this.refreshes++;},
    async call(type,args){
      assert.equal(type,'replacement');assert.equal(args.entry_id,'garage');requests.push({...args});
      if(args.action==='job_status'){const job=jobs[Math.min(jobIndex++,jobs.length-1)];if(job instanceof Error)throw job;return job;}
      if(args.action==='status')return {hardware:{network:{ipaddress:'10.0.0.2',dhcp:0},modes:{1:3,2:2}},transfer};
      if(args.action==='preview')return {token:'REVIEWED',old_model:'AL1350',target:{model:'AL1352',serial:'NEW'},rows:[]};
      if(args.action==='run')return {running:true};
      return {};
    }};
  return {panel,requests,timers,context,get dialog(){return dialog;},el(id){return dialog.querySelector('#'+id);},
    async open(){await context.Panel.prototype.replaceMaster.call(panel);},
    async tick(){const [id,fn]=timers.entries().next().value || [];assert.ok(fn,'expected status polling');timers.delete(id);await fn();}};
}

(async()=>{
  // Fresh preparation is possible; absence of a backup does not lock the UI.
  const fresh=fixture({paused:false});await fresh.open();
  assert.equal(fresh.el('prepare-replacement').disabled,false);
  assert.equal(fresh.requests.filter(r=>r.action==='status').length,0);
  await fresh.el('prepare-replacement').onclick();
  assert.equal(fresh.el('preview-replacement').disabled,false);

  // A single explicitly confirmed run owns the whole migration; polling only
  // reads server-side status, even while the panel would normally rerender.
  const f=fixture({jobs:[{}, {running:true,progress:'Netzwerk prüfen'}, {running:true,progress:'Konfiguration prüfen'}, {running:false,result:{saved:true}}]});
  await f.open();assert.equal(f.el('replacement-automatic').disabled,true);
  await f.el('preview-replacement').onclick();assert.equal(f.el('replacement-automatic').disabled,true);
  f.el('replacement-disconnected').checked=true;f.el('replacement-disconnected').onchange();
  assert.equal(f.el('replacement-automatic').disabled,false);
  await f.el('replacement-automatic').onclick();
  assert.equal(f.requests.find(r=>r.action==='run').token,'REVIEWED');
  assert.equal(f.requests.find(r=>r.action==='run').confirm,true);
  assert.equal(f.el('replacement-status').textContent,'Netzwerk prüfen');
  assert.equal(f.el('replacement-network').disabled,true);
  assert.equal(f.el('cancel-replacement').disabled,true);
  await f.el('replacement-automatic').onclick(); // queued double click
  assert.equal(f.requests.filter(r=>r.action==='run').length,1);
  f.context.Panel.prototype.render.call(f.panel);assert.equal(f.dialog.open,true);
  await f.tick();await f.tick();
  assert.equal(f.panel.refreshes,1);assert.equal(f.timers.size,0);
  assert.equal(f.el('replacement-automatic').disabled,true);
  assert.equal(f.requests.some(r=>['network','restore_modes','confirm'].includes(r.action)),false);

  // Closing a running dialog stops browser polling, never cancels the HA job.
  const closing=fixture({jobs:[{running:true,progress:'Neustart prüfen'}]});await closing.open();
  closing.el('close-replacement').onclick();
  assert.equal(closing.timers.size,0);assert.equal(closing.panel.replacementDialog,null);
  assert.equal(closing.requests.some(r=>r.action==='cancel'),false);

  // After HA restart, persisted state makes the resume control available with
  // no stale preview token and without changing target/network in the browser.
  const resume=fixture({transfer:{stage:'verified',url:'http://10.0.0.2'},jobs:[{}, {running:true}]});
  await resume.open();assert.equal(resume.el('replacement-automatic').textContent,'Austausch fortsetzen');
  assert.equal(resume.el('replacement-automatic').disabled,false);
  assert.equal(resume.el('replacement-url').disabled,true);
  await resume.el('replacement-automatic').onclick();
  assert.equal('token' in resume.requests.find(r=>r.action==='run'),false);

  // Automation identity may already be journaled before the network transfer
  // exists; the backend can resume this case without another preview token.
  const beforeWrite=fixture({jobs:[{resumable:true}, {running:true,resumable:true}]});
  await beforeWrite.open();assert.equal(beforeWrite.el('replacement-automatic').disabled,false);
  await beforeWrite.el('replacement-automatic').onclick();
  assert.equal('token' in beforeWrite.requests.find(r=>r.action==='run'),false);

  // Errors stay visible and are never automatically retried as mutations.
  const fail=fixture({transfer:{stage:'network_attempted',url:'http://10.0.0.2'},jobs:[{running:false,error:'Andere Seriennummer an der Ziel-IP'}]});
  await fail.open();assert.equal(fail.el('replacement-status').textContent,'Andere Seriennummer an der Ziel-IP');
  assert.equal(fail.el('replacement-automatic').disabled,false);assert.equal(fail.timers.size,0);
  assert.equal(fail.requests.some(r=>r.action==='run'),false);

  const preflight=fixture({jobs:[{error:'Vorschau abgelaufen',resumable:false}]});await preflight.open();
  assert.equal(preflight.el('replacement-automatic').disabled,true);
  assert.equal(preflight.el('preview-replacement').disabled,false);
  const completed=fixture({paused:false,jobs:[{result:{saved:true}}]});await completed.open();
  assert.equal(completed.el('prepare-replacement').disabled,false);

  // Adoption may already have cleared the pause flag before HA reload/health
  // failed. Resume then completes the read-only health check, not a new swap.
  const adopted=fixture({paused:false,jobs:[{error:'HA-Verbindung noch nicht bestätigt',resumable:true},{result:{saved:true},resumable:false}]});
  await adopted.open();
  assert.equal(adopted.el('replacement-status').textContent,'HA-Verbindung noch nicht bestätigt');
  assert.equal(adopted.el('replacement-automatic').disabled,false);
  assert.equal(adopted.el('prepare-replacement').disabled,true);
  assert.equal(adopted.el('cancel-replacement').disabled,true);
  assert.equal(adopted.requests.some(r=>r.action==='status'),false);
  await adopted.el('replacement-automatic').onclick();
  assert.equal('token' in adopted.requests.find(r=>r.action==='run'),false);
  assert.match(adopted.el('replacement-status').textContent,/Home Assistant ist mit dem Ersatzmaster verbunden/);
  assert.equal(adopted.panel.refreshes,1);

  // A transient WS failure cannot expose manual writes beside an unknown job.
  const reconnect=fixture({jobs:[new Error('WS getrennt'),{running:true}]});await reconnect.open();
  assert.equal(reconnect.el('cancel-replacement').disabled,true);
  await reconnect.tick();assert.equal(reconnect.requests.some(r=>r.action==='run'),false);
  reconnect.panel.isConnected=false;
  reconnect.context.clearInterval=()=>{};
  reconnect.context.Panel.prototype.disconnectedCallback.call(reconnect.panel);
  assert.equal(reconnect.timers.size,0);assert.equal(reconnect.panel.replacementDialog,null);
  assert.equal(reconnect.panel.refreshes,0);
  console.log('Replacement automation, consent, polling, restart/resume and dialog-lifecycle checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
