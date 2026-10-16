const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = vm.createContext({structuredClone,HTMLElement:class{},customElements:{define(){}}});
vm.runInContext(fs.readFileSync('custom_components/ifm_iolink/frontend/panel.js','utf8')+'\nthis.Panel=IfmIolinkPanel;this.digital=digitalProfile;',ctx);
const digital={...ctx.digital(),id:'custom_relay',name:'Relay',image:'/local/relay.png'};
const sensor={id:'sensor',name:'Pressure',fields:[],length:2};
const panel={draft:digital,data:{profiles:[sensor,digital]},profile:id=>[sensor,digital].find(p=>p.id===id),profileJson(){throw Error('Digital editor must not need JSON');}};
const html=ctx.Panel.prototype.library.call(panel);
assert.ok(html.includes('Digitales Gerät (DI / DO)'));
assert.ok(html.includes('Bild hochladen'));
assert.ok(!html.includes('id="profile-json"'));
assert.ok(!html.includes('id="test-raw"'));
assert.equal(ctx.Panel.prototype.readJson.call(panel).image,'/local/relay.png');
for(const mode of [1,2]){
 const item={mode,profile:'sensor',assignment:{profile:'sensor',digital_profile:'custom_relay'}};
 panel.master={ports:{1:item}};panel.selected=item;panel.port=1;
 const card=ctx.Panel.prototype.portCard.call(panel,1);
 assert.ok(card.includes('/local/relay.png'));assert.ok(card.includes('Relay'));
 const inspector=ctx.Panel.prototype.inspector.call(panel);
 assert.ok(inspector.includes('<select name="digital_profile" >'));
 assert.ok(inspector.includes('value="custom_relay" selected'));
 assert.ok(!inspector.includes('value="sensor"'));
 assert.ok(!inspector.includes('IODD'));
 assert.ok(!inspector.includes('Parameterliste anzeigen'));
}
panel.selected={mode:3,profile:'sensor',assignment:{digital_profile:'custom_relay'}};
const inspector=ctx.Panel.prototype.inspector.call(panel);
assert.ok(inspector.includes('value="sensor" selected'));
assert.ok(!inspector.includes('value="custom_relay"'));
console.log('Digital device editor, image and mode-specific assignment checks passed');

const makeId=vm.runInContext('profileIdFromName',ctx);
assert.equal(makeId('Druckluftverteiler'),'custom_druckluftverteiler');
assert.equal(makeId('Schütz – Öl & Größe'),'custom_schuetz_oel_groesse');
assert.equal(makeId('🔌'),'custom_geraet');
assert.equal(makeId('Ventil',[{id:'custom_ventil'},{id:'custom_ventil_2'}]),'custom_ventil_3');
const longId=makeId('A'.repeat(100));
assert.equal(longId.length,64);
assert.equal(makeId('A'.repeat(100),[{id:longId}]).length,64);
const inputs=['id','name'].map(name=>({name,value:'',addEventListener(type,fn){this[type]=fn;}}));
const form={querySelectorAll(){return inputs;},querySelector(){return inputs[0];},addEventListener(){}};
const editButton={dataset:{edit:'custom_saved'}};
const blankButton={addEventListener(type,fn){this[type]=fn;}};
const editor={draft:{...digital},autoProfileId:true,data:{profiles:[{id:'custom_ventil'}]},
 profile(){return {...digital,id:'custom_saved'};},syncJson(){},render(){},
 shadowRoot:{querySelector(s){return s==='#profile-form'?form:s==='#blank-profile'?blankButton:null;},querySelectorAll(){return [editButton];}}};
ctx.Panel.prototype.bindLibrary.call(editor);
inputs[1].value='Ventil';inputs[1].input();
assert.equal(editor.draft.id,'custom_ventil_2');
assert.equal(inputs[0].value,editor.draft.id);
editButton.onclick();inputs[1].value='Neuer Name';inputs[1].input();
assert.equal(editor.draft.id,'custom_saved','Renaming a saved profile must preserve assignments');
blankButton.click();inputs[1].value='Pumpe';inputs[1].input();
assert.equal(editor.draft.id,'custom_pumpe');
inputs[0].value='custom_manual';inputs[0].input();inputs[1].value='Anderer Name';inputs[1].input();
assert.equal(editor.draft.id,'custom_manual');
console.log('Automatic profile IDs, collisions, existing profiles and manual overrides passed');
