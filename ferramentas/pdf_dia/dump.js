// uso: node dump.js <dia> <saida.json>  — lê a programação gerada (programacao.html) e exporta as atividades do dia, sem pôsteres
const {chromium}=require('playwright');(async()=>{const dia=+process.argv[2];const b=await chromium.launch();const p=await b.newPage();
await p.route(/^https?:/,r=>r.abort());
await p.goto('file:///home/claude/cnc/programacao.html');await p.waitForTimeout(800);
const r=await p.evaluate(dia=>({ev:EV.filter(e=>e.d===dia&&e.type!=='V').map(e=>({s:e.s,e:e.e,room:e.room,rn:(ROOMS[e.room]||{}).n||e.room,code:e.code,type:e.type,tl:TYPES[e.type],title:e.title,people:e.people,flags:e.flags,tag:tagHTML(e)})),order:ROOM_ORDER}),dia);
require('fs').writeFileSync(process.argv[3],JSON.stringify(r));await b.close();})();
