
(function(){
"use strict";
const RACES = {
  senate:{ leader:"Schumer", challenger:"Van Hollen",
    labels:{2:"Declared for Schumer",1:"Leaning Schumer",0:"Undecided","-1":"Leaning against Schumer","-2":"Opposed to Schumer"},
    key:[["Vote","Secret ballot, 1 Dec"],["Needed","28 of 55 (29 if Peltola is seated)"]], needed:28, total:55 },
  house:{ leader:"Jeffries", challenger:null,
    labels:{2:"Declared for Jeffries",1:"Leaning Jeffries",0:"Undecided","-1":"Leaning against Jeffries","-2":"Opposed to Jeffries"},
    key:[["Caucus vote","Wed 18 Nov"],["Floor vote","3 Jan, majority of those voting"]], needed:null, total:null }
};
const ORDER = [-2,-1,0,null,1,2];
const COLVAR = {"2":"--s2","1":"--s1","0":"--s0","-1":"--sm1","-2":"--sm2","null":"--snone"};
const LIGHT = {"1":true,"0":true,"-1":true,"null":true};
const PCT = {"2":100,"1":75,"0":50,"-1":25,"-2":0};
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const col = s => css(COLVAR[String(s)]);
const esc = s => String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtDate = d => { if(!d) return ""; const t=new Date(d+"T12:00:00Z"); return isNaN(t)?d:t.toLocaleDateString("en-GB",{day:"numeric",month:"short",year: d.slice(0,4)==="2026"?undefined:"numeric"}); };
const stanceLabel = (m) => m.stance==null ? "No public position" : RACES[m.chamber].labels[String(m.stance)];

const ROOT = document.documentElement.dataset.root || "./";
const PRESET = document.body.dataset.race || "";
let race = PRESET || ((location.hash==="#house") ? "house" : "senate");
let members = [], feed = [], pending = [], meta = null;
let db = null, canEdit = false, writeLocked = false;
let sortKey = "stance", sortDir = "desc", openId = null, filterStance = "";

/* ---------- tabs ---------- */
document.querySelectorAll(".tab").forEach(b=>b.addEventListener("click",()=>{ race=b.dataset.race; try{history.replaceState(null,"","#"+race);}catch(e){} filterStance=""; openId=null; renderAll(); }));
if(!PRESET) window.addEventListener("hashchange",()=>{ const r=location.hash==="#house"?"house":"senate"; if(r!==race){race=r;renderAll();} });

/* ---------- summary ---------- */
function renderSummary(ms){
  const R = RACES[race];
  document.querySelectorAll(".tab").forEach(b=>b.setAttribute("aria-selected", String(b.dataset.race===race)));
  const km = document.getElementById("keymeta");
  const forLeader = ms.filter(m=>m.stance>=1 && m.status!=="Race not called").length;
  const declared = ms.filter(m=>m.stance===2 && m.status!=="Race not called").length;
  let html = R.key.map(([k,v])=>`<span>${esc(k)}: <b>${esc(v)}</b></span>`).join("");
  html += `<span>${esc(R.leader)} side: <b>${declared} declared, ${forLeader} incl. leaning</b></span>`;
  if(race==="senate"){ const vh = ms.filter(m=>m.backing==="Van Hollen").length; html += `<span>Named Van Hollen: <b>${vh}</b></span>`; }
  km.innerHTML = html;
  const bar = document.getElementById("bar"); const n = ms.length || 1;
  bar.innerHTML = ORDER.map(s=>{
    const c = ms.filter(m=>m.stance===s).length; if(!c) return "";
    const lab = s==null?"No public position":R.labels[String(s)];
    return `<button class="seg ${LIGHT[String(s)]?"light":""}" style="width:${(c/n*100).toFixed(2)}%;background:${col(s)}" title="${esc(lab)}: ${c}" data-s="${s}" aria-label="${esc(lab)}: ${c}. Filter the table">${c/n>0.035?c:""}</button>`;
  }).join("");
  if(R.needed){ const x = 100 - R.needed/n*100; bar.insertAdjacentHTML("beforeend",`<div class="thresh" style="left:${x}%"><span>${R.needed} needed</span></div>`); }
  bar.querySelectorAll(".seg").forEach(b=>b.addEventListener("click",()=>{ filterStance = b.dataset.s; document.getElementById("fStance").value = filterStance; renderGrid(); document.getElementById("gridtitle").scrollIntoView({behavior:"smooth"}); }));
  document.getElementById("legend").innerHTML = [2,1,0,-1,-2,null].map(s=>{
    const lab = s==null?"No public position":R.labels[String(s)];
    const p = s==null?"":` · ${PCT[String(s)]}%`;
    return `<span><i class="sw" style="background:${col(s)}"></i>${esc(lab)}${p}</span>`;
  }).join("") + `<span class="note">% = sway towards ${esc(R.leader)}</span>`;
}

/* ---------- hemicycle ---------- */
function seatLayout(N, rows){
  const r0 = rows<=4 ? 0.46 : 0.38, radii=[]; for(let i=0;i<rows;i++) radii.push(r0 + (1-r0)*i/(rows-1||1));
  const sum = radii.reduce((a,b)=>a+b,0); let counts = radii.map(r=>Math.floor(N*r/sum)); let left = N - counts.reduce((a,b)=>a+b,0);
  for(let i=rows-1; left>0; i=(i-1+rows)%rows){counts[i]++;left--;}
  const seats=[]; radii.forEach((r,i)=>{ const k=counts[i]; for(let j=0;j<k;j++){ const a = k===1?Math.PI/2:Math.PI*(1 - j/(k-1)); seats.push({r,a}); } });
  seats.sort((p,q)=> q.a-p.a || p.r-q.r);
  return seats;
}
function renderHemi(ms){
  const svg = document.getElementById("hemi");
  const W=800,H=430,cx=400,cy=405,R=380;
  const N=ms.length; const rows = race==="senate"?4:10; const dot = race==="senate"?15:9.2;
  const sorted = ms.slice().sort((a,b)=> rank(a)-rank(b) || (a.candidate?-1:0)-(b.candidate?-1:0) || (a.state+a.district).localeCompare(b.state+b.district));
  const seats = seatLayout(N, rows);
  let out = "";
  const brass = css("--brass"), line = css("--line");
  for(let i=0;i<=rows;i++){ const rr = R*((rows<=4?0.46:0.38) - 0.05 + (1.1-(rows<=4?0.46:0.38))*i/rows);
    out += `<path d="M${(cx-rr).toFixed(1)} ${cy} A${rr.toFixed(1)} ${rr.toFixed(1)} 0 0 1 ${(cx+rr).toFixed(1)} ${cy}" fill="none" stroke="${i===rows?brass:line}" stroke-width="${i===rows?1.5:1}" opacity="${i===rows?0.7:0.9}"></path>`; }
  out += `<rect x="${cx-70}" y="${cy+6}" width="140" height="12" rx="2" fill="${css("--navy2")}"></rect><rect x="${cx-70}" y="${cy+6}" width="140" height="2" fill="${brass}"></rect>`;
  sorted.forEach((m,i)=>{ const s=seats[i]; const x=cx + R*s.r*Math.cos(s.a), y=cy - R*s.r*Math.sin(s.a);
    const named = race==="senate" && m.backing==="Van Hollen";
    const fill = col(m.stance);
    out += `<circle data-id="${esc(m.id)}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${dot}" fill="${fill}" tabindex="0" aria-label="${esc(m.name)}, ${esc(stanceLabel(m))}" class="${openId===m.id?"sel":""} ${filterStance!=="" && String(m.stance)!==filterStance?"dim":""}"></circle>`;
    if(named) out += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(dot*0.36).toFixed(1)}" fill="${css("--surface")}" pointer-events="none"></circle>`;
  });
  const R2 = RACES[race]; const n = ms.filter(m=>m.status!=="Race not called").length;
  const lead = ms.filter(m=>m.stance>=1 && m.status!=="Race not called").length;
  out += `<text x="${cx}" y="${cy-62}" text-anchor="middle" font-family="${css("--font-display")}" font-size="40" font-weight="700" fill="${css("--ink")}">${lead}${R2.needed?` / ${R2.needed}`:""}</text>`;
  out += `<text x="${cx}" y="${cy-34}" text-anchor="middle" font-size="13" fill="${css("--muted")}">${R2.needed?`for ${esc(R2.leader)} of ${R2.needed} needed`:`for ${esc(R2.leader)} so far, of ${n} seats called`}</text>`;
  out += `<text x="${cx}" y="${cy-14}" text-anchor="middle" font-size="12" fill="${css("--muted")}">Declared + leaning, public statements only</text>`;
  svg.innerHTML = out;
  svg.querySelectorAll("circle[data-id]").forEach(c=>{
    c.addEventListener("mouseenter",e=>showTip(e,c.dataset.id)); c.addEventListener("mousemove",moveTip); c.addEventListener("mouseleave",hideTip);
    c.addEventListener("click",()=>openRow(c.dataset.id)); c.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();openRow(c.dataset.id);}});
  });
}
function rank(m){ return ORDER.indexOf(m.stance==null?null:m.stance); }
const tip = document.getElementById("tip");
function showTip(e,id){ const m=members.find(x=>x.id===id); if(!m) return;
  tip.innerHTML = `<b>${esc(m.name)}</b><span style="color:var(--muted)">${esc(where(m))} · ${esc(m.status)}</span><div style="margin-top:4px"><i class="sw" style="background:${col(m.stance)};vertical-align:-1px"></i> ${esc(stanceLabel(m))}${m.backing?` · ${esc(m.backing)}`:""}</div><div style="margin-top:4px">${esc(m.summary)}</div>${m.date?`<div style="color:var(--muted);margin-top:4px">${esc(m.source)} · ${esc(fmtDate(m.date))}</div>`:""}`;
  tip.style.display="block"; moveTip(e); }
function moveTip(e){ const pad=14; let x=e.clientX+pad, y=e.clientY+pad; const r=tip.getBoundingClientRect(); if(x+r.width>innerWidth-8) x=e.clientX-r.width-pad; if(y+r.height>innerHeight-8) y=e.clientY-r.height-pad; tip.style.left=x+"px"; tip.style.top=y+"px"; }
function hideTip(){ tip.style.display="none"; }
const where = m => m.chamber==="senate" ? m.state : m.district;

/* ---------- feed ---------- */
function renderFeed(){
  const el = document.getElementById("feed");
  const items = feed.filter(e=>e.chamber===race).slice(0,80);
  if(!items.length){ el.innerHTML = `<div class="empty">No activity yet for this race.</div>`; return; }
  el.innerHTML = items.map(e=>`<div class="ev"><span class="dot" style="background:${col(e.stance==null?null:e.stance)}"></span><div>
    <div class="when">${esc(fmtDate(e.date))}${e.kind==="change"?" · changed":""}</div>
    <div><span class="who" data-id="${esc(e.memberId)}" tabindex="0" role="button">${esc(e.name)} (${esc(e.where)})</span>: ${esc(e.head)}</div>
    <div style="color:var(--muted)">${esc(e.text)} ${e.url?`<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.source||"Source")}</a>`:esc(e.source)}</div></div></div>`).join("");
  el.querySelectorAll(".who").forEach(w=>{ w.addEventListener("click",()=>openRow(w.dataset.id)); w.addEventListener("keydown",ev=>{if(ev.key==="Enter")openRow(w.dataset.id);}); });
}

/* ---------- grid ---------- */
const COLS = [
  {k:"name",t:"Member"},{k:"stance",t:"Where they stand"},{k:"backing",t:"Backing"},{k:"confidence",t:"Confidence"},
  {k:"summary",t:"Latest evidence",nosort:true},{k:"date",t:"Source and date"},{k:"timing",t:"Timing"},{k:"changed",t:"Changed?"},
  {k:"faction",t:"Faction"},{k:"since",t:"In Congress since"},{k:"leaderPick",t:"Leader's primary pick",senateOnly:true}
];
function cols(){ return COLS.filter(c=>!(c.senateOnly && race!=="senate")); }
function renderHead(){
  document.getElementById("thead").innerHTML = cols().map(c=>`<th scope="col" data-k="${c.k}" ${c.nosort?"":`tabindex="0"`} aria-sort="${sortKey===c.k?(sortDir==="asc"?"ascending":"descending"):"none"}">${esc(c.t)}</th>`).join("");
  document.querySelectorAll("#thead th").forEach(th=>{ const c=COLS.find(x=>x.k===th.dataset.k); if(c.nosort) return;
    const go=()=>{ if(sortKey===c.k) sortDir = sortDir==="asc"?"desc":"asc"; else {sortKey=c.k; sortDir = (c.k==="stance"||c.k==="date"||c.k==="confidence")?"desc":"asc";} renderGrid(); };
    th.addEventListener("click",go); th.addEventListener("keydown",e=>{if(e.key==="Enter")go();}); });
  const fs = document.getElementById("fStance"); const R=RACES[race];
  fs.innerHTML = `<option value="">All stances</option>` + [2,1,0,-1,-2,null].map(s=>`<option value="${s}">${esc(s==null?"No public position":R.labels[String(s)])}</option>`).join("");
  fs.value = filterStance;
  const ff = document.getElementById("fFaction"); const fv = ff.value;
  const facs = [...new Set(members.filter(m=>m.chamber===race && m.faction).map(m=>m.faction))].sort();
  ff.innerHTML = `<option value="">All factions</option>` + facs.map(f=>`<option>${esc(f)}</option>`).join(""); ff.value = facs.includes(fv)?fv:"";
}
const CONFN = {high:3,medium:2,low:1,"":0};
function sortVal(m,k){
  if(k==="stance") return m.stance==null? -0.5 : m.stance;
  if(k==="confidence") return CONFN[m.confidence||""];
  if(k==="since") return m.since||9999;
  if(k==="name") return m.name.split(" ").slice(-1)[0];
  return (m[k]||"").toString().toLowerCase();
}
function filtered(){
  const q = document.getElementById("q").value.trim().toLowerCase();
  const st = document.getElementById("fStatus").value, cf = document.getElementById("fConf").value, fa = document.getElementById("fFaction").value;
  return members.filter(m=> m.chamber===race
    && (!q || (m.name+" "+m.state+" "+m.district+" "+m.backing).toLowerCase().includes(q))
    && (filterStance==="" || String(m.stance)===filterStance)
    && (!st || m.status===st) && (!cf || m.confidence===cf) && (!fa || m.faction===fa));
}
function stancePill(m){
  const s=m.stance; const p = s==null?"–":PCT[String(s)]+"%";
  return `<span class="stance"><span class="pct ${LIGHT[String(s)]?"light":""}" style="background:${col(s)}">${p}</span>${esc(stanceLabel(m))}</span>`;
}
function confDots(c){ const n=CONFN[c||""]; if(!n) return `<span class="note">–</span>`; return `<span class="conf" title="${esc(c)} confidence">${[1,2,3].map(i=>`<i class="${i<=n?"on":""}"></i>`).join("")}<span class="note" style="margin-left:4px">${esc(c)}</span></span>`; }
function renderGrid(){
  renderHead();
  const list = filtered();
  const dir = sortDir==="asc"?1:-1;
  list.sort((a,b)=>{ const x=sortVal(a,sortKey), y=sortVal(b,sortKey); if(x<y) return -dir; if(x>y) return dir; return a.name.localeCompare(b.name); });
  document.getElementById("count").textContent = `${list.length} of ${members.filter(m=>m.chamber===race).length} members`;
  const tb = document.getElementById("tbody"); const nc = cols().length;
  if(!list.length){ tb.innerHTML = `<tr><td class="empty" colspan="${nc}">No members match these filters.</td></tr>`; return; }
  tb.innerHTML = list.map(m=>{
    const cells = cols().map(c=>{
      switch(c.k){
        case "name": return `<td class="who"><b><a class="mlink" href="${ROOT}members/${esc(m.id)}/" onclick="event.stopPropagation()">${esc(m.name)}</a>${m.candidate?' <span class="chip">Candidate</span>':""}</b><small>${esc(where(m))} · </small><span class="chip ${m.status!=="Incumbent"?"new":""} ${m.status==="Race not called"||m.status==="Leaving"?"warn":""}">${esc(m.status)}</span></td>`;
        case "stance": return `<td>${stancePill(m)}</td>`;
        case "backing": return `<td>${esc(m.backing)||'<span class="note">–</span>'}</td>`;
        case "confidence": return `<td>${confDots(m.confidence)}</td>`;
        case "summary": return `<td class="ev-sum">${esc(m.summary)}${m.quote?`<q>${esc(m.quote)}</q>`:""}</td>`;
        case "date": return `<td class="src">${m.sourceUrl?`<a href="${esc(m.sourceUrl)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${esc(m.source||"Source")}</a>`:esc(m.source)||'<span class="note">–</span>'}${m.date?`<br><small class="note">${esc(fmtDate(m.date))}${m.via?` · via ${esc(m.via)}`:""}</small>`:""}</td>`;
        case "timing": return `<td>${esc(m.timing)||'<span class="note">–</span>'}</td>`;
        case "changed": return `<td>${m.changed||(m.history&&m.history.length)?`<span class="chip warn" title="${esc(m.changed)}">&#8644; ${esc(m.changed||"Changed")}</span>`:'<span class="note">No</span>'}</td>`;
        case "faction": return `<td>${esc(m.faction)||'<span class="note">–</span>'}</td>`;
        case "since": return `<td class="num">${m.since?esc(m.since):'<span class="note">New</span>'}</td>`;
        case "leaderPick": return `<td>${esc(m.leaderPick)||'<span class="note">–</span>'}</td>`;
        case "notes": return `<td class="note" style="max-width:24ch">${esc((m.notes||"").slice(0,80))}${(m.notes||"").length>80?"…":""}</td>`;
      }}).join("");
    let row = `<tr data-id="${esc(m.id)}" class="${openId===m.id?"sel":""}" tabindex="0">${cells}</tr>`;
    if(openId===m.id) row += detailRow(m,nc);
    return row;
  }).join("");
  tb.querySelectorAll("tr[data-id]").forEach(tr=>{ const id=tr.dataset.id;
    tr.addEventListener("click",()=>{ openId = openId===id?null:id; renderGrid(); renderHemi(members.filter(m=>m.chamber===race)); });
    tr.addEventListener("keydown",e=>{ if(e.key==="Enter"){ openId = openId===id?null:id; renderGrid(); renderHemi(members.filter(m=>m.chamber===race)); } }); });
  const save = document.getElementById("saveNote");
  if(save) save.addEventListener("click",saveNote);
}
function detailRow(m,nc){
  const hist = (m.history||[]).slice().reverse();
  return `<tr class="detail"><td colspan="${nc}"><div class="dgrid">
    <div><h4>Latest evidence</h4><div>${esc(m.summary)}</div>${m.quote?`<q style="display:block;margin-top:4px;color:var(--muted)">${esc(m.quote)}</q>`:""}
      <div class="note" style="margin-top:6px">${m.sourceUrl?`<a href="${esc(m.sourceUrl)}" target="_blank" rel="noopener">${esc(m.source||"Source")}</a>`:esc(m.source)} ${m.date?"· "+esc(fmtDate(m.date)):""} ${m.via?"· via "+esc(m.via):""}</div></div>
    <div><h4>Stance history</h4>${hist.length?`<ol class="hist">${hist.map(h=>`<li><b>${esc(fmtDate(h.date))}</b>: ${esc(h.fromLabel)} to ${esc(h.toLabel)}. ${esc(h.summary||"")} ${h.url?`<a href="${esc(h.url)}" target="_blank" rel="noopener">${esc(h.source||"Source")}</a>`:""}</li>`).join("")}</ol>`:`<div class="note">${m.changed?esc(m.changed)+". ":""}No approved changes since tracking began.</div>`}</div>
    <div><h4>More</h4><a href="${ROOT}members/${esc(m.id)}/">Full profile and stance history for ${esc(m.name)}</a></div>
    </div></td></tr>`;
}
function openRow(id){
  const m = members.find(x=>x.id===id); if(!m) return;
  if(m.chamber!==race){ race=m.chamber; }
  filterStance=""; document.getElementById("q").value=""; document.getElementById("fStatus").value=""; document.getElementById("fConf").value=""; document.getElementById("fFaction").value="";
  openId = id; renderAll();
  const tr = document.querySelector(`tr[data-id="${CSS.escape(id)}"]`); if(tr){ tr.scrollIntoView({behavior:"smooth",block:"center"}); tr.focus({preventScroll:true}); }
}
["q","fStatus","fConf","fFaction"].forEach(id=>document.getElementById(id).addEventListener("input",()=>renderGrid()));
document.getElementById("fStance").addEventListener("change",e=>{ filterStance=e.target.value; renderGrid(); renderHemi(members.filter(m=>m.chamber===race)); });

/* ---------- review queue ---------- */
function renderReview(){ return; }
function renderReviewUnused(){
  const card = document.getElementById("reviewcard"); const el = document.getElementById("review");
  const items = pending.filter(p=>p.chamber===race);
  if(!canEdit || !pending.length){ card.hidden = true; return; }
  card.hidden = false;
  if(!items.length){ el.innerHTML = `<div class="note">Nothing waiting for this race. ${pending.length} waiting in the other race.</div>`; return; }
  el.innerHTML = items.map(p=>{ const m = members.find(x=>x.id===p.memberId) || {name:p.name,chamber:p.chamber,stance:null};
    const fromL = stanceLabel(m), toL = p.proposedStance==null?"No public position":RACES[p.chamber].labels[String(p.proposedStance)];
    return `<div class="prop" style="border-left-color:${col(p.proposedStance)}">
      <div><b>${esc(p.name)}</b> <span class="note">${esc(p.where||"")}</span></div>
      <div>${esc(fromL)} &rarr; <b>${esc(toL)}</b>${p.proposedBacking?` · backing ${esc(p.proposedBacking)}`:""} · ${confDots(p.confidence)}</div>
      <div>${esc(p.summary)}${p.quote?` <q style="color:var(--muted)">${esc(p.quote)}</q>`:""}</div>
      <div class="note">${p.sourceUrl?`<a href="${esc(p.sourceUrl)}" target="_blank" rel="noopener">${esc(p.source||"Source")}</a>`:esc(p.source)} · ${esc(fmtDate(p.date))} · found ${esc((p.foundAt||"").slice(0,16).replace("T"," "))}</div>
      <div class="acts"><button class="btn primary" data-act="ok" data-id="${esc(p._id)}">Approve</button><button class="btn" data-act="no" data-id="${esc(p._id)}">Reject</button><span class="note" data-msg="${esc(p._id)}"></span></div></div>`; }).join("");
  el.querySelectorAll("button[data-act]").forEach(b=>b.addEventListener("click",()=> b.dataset.act==="ok"?approve(b.dataset.id,b):reject(b.dataset.id,b)));
}
function msg(id,t){ const s=document.querySelector(`[data-msg="${CSS.escape(id)}"]`); if(s) s.textContent=t; }
async function approve(pid,btn){
  const p = pending.find(x=>x._id===pid); if(!p||!db) return; btn.disabled=true; msg(pid,"Saving…");
  try{
    const m = members.find(x=>x.id===p.memberId);
    const R = RACES[p.chamber];
    const toS = p.proposedStance==null?null:Number(p.proposedStance);
    const fromLabel = m?stanceLabel(m):"Not tracked";
    const toLabel = toS==null?"No public position":R.labels[String(toS)];
    const today = new Date().toISOString().slice(0,10);
    const date = p.date || today;
    const histEntry = {date, from:m?m.stance:null, to:toS, fromLabel, toLabel, summary:p.summary||"", source:p.source||"", url:p.sourceUrl||""};
    const body = { stance:toS, pct: toS==null?null:PCT[String(toS)], backing:p.proposedBacking||"", confidence:p.confidence||"medium",
      summary:p.summary||"", quote:p.quote||"", source:p.source||"", sourceUrl:p.sourceUrl||"", date, via:"",
      timing: date>="2026-11-04"?"Post-election":"Pre-election", updated: today };
    if(m && m.stance!==toS) body.changed = `${fromLabel} to ${toLabel}`;
    body.history = (m&&m.history?m.history.slice():[]).concat([histEntry]).slice(-30);
    if(m){ await db.doc("members/"+m.id).update(body); }
    else { await db.doc("members/"+p.memberId).set(Object.assign({id:p.memberId,name:p.name,chamber:p.chamber,state:p.state||"",district:p.district||"",faction:"",status:p.status||"New",since:null,leaderPick:"",notes:"",candidate:false},body)); }
    const head = (p.proposedBacking==="Van Hollen")?"Backs Van Hollen":toLabel;
    const ev = {date, memberId:p.memberId, name:p.name, where:p.where||"", chamber:p.chamber, stance:toS, head, text:p.summary||"", source:p.source||"", url:p.sourceUrl||"", kind:(m&&m.stance!==toS)?"change":"update"};
    const next = [ev].concat(feed).sort((a,b)=>(b.date||"").localeCompare(a.date||"")).slice(0,300);
    await db.doc("feed/events").set({items:next});
    await db.doc("pending/"+pid).delete();
  }catch(e){ handleWriteError(e); msg(pid,"Couldn't save. "+(e&&e.message?e.message:"Try again.")); btn.disabled=false; }
}
async function reject(pid,btn){
  if(!db) return; btn.disabled=true;
  try{ await db.doc("pending/"+pid).delete(); }catch(e){ handleWriteError(e); msg(pid,"Couldn't remove it. Try again."); btn.disabled=false; }
}
async function saveNote(e){
  const id = e.target.dataset.id; const box = document.getElementById("noteBox"); const out = document.getElementById("noteMsg");
  const m = members.find(x=>x.id===id); if(!m||!db) return; if((m.notes||"")===box.value){ out.textContent="No changes."; return; }
  out.textContent="Saving…";
  try{ await db.doc("members/"+id).update({notes:box.value}); out.textContent="Saved."; }catch(err){ handleWriteError(err); out.textContent="Couldn't save the note."; }
}
function handleWriteError(e){ if(e && e.code==="invalid_argument"){ writeLocked = true; } }

/* ---------- status + render ---------- */
function renderStatus(){
  const el = document.getElementById("status");
  let t = "";
  if(meta && meta.lastRun){ t += `Last checked ${new Date(meta.lastRun).toLocaleString("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}`;
    if(meta.itemsScanned!=null) t += `, checked ${meta.itemsScanned} items`;
    if(meta.applied!=null) t += `, applied ${meta.applied} update${meta.applied===1?"":"s"}`;
    if(meta.skipped) t += ` and skipped ${meta.skipped} it judged not accurate enough`;
    t += ". Updated hourly from dated, named news sources. ";
  } else t += "The hourly news trawl hasn't reported yet. ";
  t += "Stances come from public statements and news reports; the leadership votes are secret ballots, so treat this as public positioning, not a vote count.";
  el.textContent = t;
}
function renderAll(){
  const ms = members.filter(m=>m.chamber===race);
  renderSummary(ms); renderHemi(ms); renderFeed(); renderReview(); renderGrid(); renderStatus();
}
function banner(t){ const b=document.getElementById("banner"); if(!t){b.hidden=true;return;} b.textContent=t; b.hidden=false; }

/* ---------- data ---------- */
(async function init(){
  renderAll();
  try{
    const r = await fetch(ROOT+"data.json",{cache:"no-store"});
    if(!r.ok) throw new Error(r.status);
    const d = await r.json();
    const DEF = {name:"",chamber:"",state:"",district:"",faction:"",status:"Incumbent",since:null,stance:null,backing:"",confidence:"",summary:"",quote:"",source:"",sourceUrl:"",date:"",via:"",leaderPick:"",changed:"",candidate:false,timing:"",history:[]};
    members = (d.members||[]).map(x=>Object.assign({},DEF,x));
    feed = d.feed||[]; meta = d.meta||null;
    banner(""); renderAll();
  }catch(e){ banner("The live data couldn't be loaded. Reload the page to try again."); }
})();
})();
