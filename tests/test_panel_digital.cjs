// Execute the actual panel's pure indicator function, without a browser or HA.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../custom_components/ifm_iolink/frontend/panel.js'), 'utf8');
const context = vm.createContext({HTMLElement: class {}, customElements: {define() {}}});
vm.runInContext(source + '\nthis.indicator = channelState;', context);
const state = context.indicator;
assert.equal(state({pin2:true}, 'pin2', true).tone, 'on');
assert.equal(state({pin2:false}, 'pin2', true).text, 'AUS');
assert.equal(state({pin2:null}, 'pin2', true).tone, 'unknown');
assert.equal(state({mode:2,pin4:null}, 'pin4', true).text, 'Unbekannt');
assert.equal(state({mode:2,pin4:true}, 'pin4', false).tone, 'unknown');
assert.equal(state({mode:3,connected:true}, 'pin4', true).tone, 'iol');
assert.equal(state({mode:3,connected:false}, 'pin4', true).tone, 'unknown');
assert.equal(state({mode:0}, 'pin4', true).text, 'Deaktiviert');
console.log('8 channel indicator checks passed');
vm.runInContext('this.badge = modeStatus; this.Panel = IfmIolinkPanel;', context);
assert.equal(context.badge({mode:3,connected:true},true).tone,'on');
assert.equal(context.badge({mode:3,connected:false},true).tone,'off');
assert.equal(context.badge({mode:3},true).label,'IO-Link');
assert.equal(context.badge({mode:1},true).label,'DI1');
assert.equal(context.badge({mode:2},true).label,'DO');
assert.equal(context.badge({mode:2,pin4:true},true).tone,'on');
assert.equal(context.badge({mode:2,pin4:false},true).tone,'off');
assert.equal(context.badge({mode:2,pin4:false},true).clickable,true);
assert.equal(context.badge({mode:1,pin4:true},true).clickable,false);
assert.equal(context.badge({mode:2,pin4:null},true).clickable,false);
assert.equal(context.badge({mode:2,pin4:true},false).clickable,false);
assert.equal(context.badge({mode:0},true).tone,'unknown');
(async()=>{
 const writes=[];let release;
 const item={mode:2,pin4:false,profile:'unknown'};
 const panel={master:{entry_id:'garage',online:true,ports:{4:item}},parameterBusy:new Set(),paint(){},notify(){},async refresh(){},call:async(type,args)=>{writes.push({type,...args});await new Promise(r=>release=r);}};
 const first=context.Panel.prototype.toggleOutput.call(panel,4);
 await context.Panel.prototype.toggleOutput.call(panel,4);
 assert.equal(writes.length,1);
 assert.equal(writes[0].entry_id,'garage');assert.equal(writes[0].port,4);assert.equal(writes[0].on,true);
 assert.equal(item.pin4,false); // no optimistic state
 release();await first;assert.equal(panel.parameterBusy.size,0);
 console.log('Mode badge and concurrent DO click checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
// Card header has only Xnn, Pin-4 mode signal and DI2; no duplicated status row.
const card = context.Panel.prototype.portCard.call({master:{ports:{4:{mode:1,assignment:{}}}},profile(){},port:4},4);
assert.ok(card.includes('data-toggle="4"'));
assert.ok(card.includes('data-di2="4"'));
assert.ok(!card.includes('channel-indicators'));
assert.ok(!card.includes('data-status="4"'));
