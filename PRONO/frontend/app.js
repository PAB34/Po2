/* Ligue 1 PRONO — frontend (auth JWT + tableau de probas + actu) */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const TOKEN_KEY = "prono_token";
const API = ""; // même origine ; Caddy route /api -> backend
const token = () => localStorage.getItem(TOKEN_KEY) || "";
const authHeaders = () => ({ "Authorization": "Bearer " + token() });

async function api(path, opts = {}) {
  const r = await fetch(API + path, { ...opts, headers: { ...(opts.headers || {}), ...authHeaders() } });
  if (r.status === 401) { logout(); throw new Error("Session expirée"); }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Erreur");
  return r.json();
}

/* ---------- Auth ---------- */
async function doLogin() {
  const msg = $("#loginMsg"), btn = $("#loginBtn");
  msg.className = "loginmsg"; btn.disabled = true;
  try {
    const r = await fetch(API + "/api/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: $("#email").value.trim(), password: $("#password").value }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Connexion refusée");
    localStorage.setItem(TOKEN_KEY, d.access_token);
    showApp();
  } catch (e) {
    msg.textContent = e.message; msg.className = "loginmsg err show";
  }
  btn.disabled = false;
}
function logout() {
  localStorage.removeItem(TOKEN_KEY);
  $("#app").classList.add("hidden"); $("#login").classList.remove("hidden");
}
function showApp() {
  $("#login").classList.add("hidden"); $("#app").classList.remove("hidden");
  loadJournee(false);
}
$("#password") && $("#password").addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });

/* ---------- Rendu ---------- */
function confClass(c){const l=(c||"").toLowerCase();return l.includes("fort")?"fort":l.includes("moyen")?"moyen":"faible";}
function trendClass(l){return /↑|hausse/i.test(l)?"up":/↓|baisse|repli/i.test(l)?"down":"flat";}
function formPills(f){return [...(f||"")].map(c=>`<span class="pill ${c}">${c}</span>`).join("");}

function probBar(m){
  const seg=(cls,val,on)=>`<div class="seg ${cls} ${on?"win":""}" style="flex:${Math.max(val||0,1)} 1 0">${(val||0)>=9?val+"%":""}</div>`;
  return `<div class="probbar">${seg("h",m.p_home,m.pick_outcome==="H")}${seg("d",m.p_draw,m.pick_outcome==="D")}${seg("a",m.p_away,m.pick_outcome==="A")}</div>
    <div class="problbl"><span>1 ${esc(m.home)}</span><span>Nul</span><span>${esc(m.away)} 2</span></div>`;
}
function teamBadges(b){
  const o=[]; if(b.injuries_count>0)o.push(`<span class="bdg inj">🩼 ${b.injuries_count}</span>`);
  const t=trendClass(b.label); if(t==="up")o.push(`<span class="bdg up">▲ forme</span>`); if(t==="down")o.push(`<span class="bdg down">▼ baisse</span>`);
  return o.join("");
}
function injuryList(b){
  if(!b.injuries||!b.injuries.length)return `<div class="dyn" style="color:#15803d">Aucun blessé connu ✓</div>`;
  return `<ul class="injlist">`+b.injuries.map(i=>{
    const ko=/ligament|fracture|rupture/i.test(i.injury)?"ko":"";
    const ret=i.return&&i.return!=="non précisé"?` · retour ${esc(i.return)}`:"";
    return `<li><span class="${ko}">${esc(i.player)}</span> <span style="color:#64748b">(${esc(i.position)})</span> — ${esc(i.injury)}${ret}</li>`;
  }).join("")+`</ul>`;
}
function teamCard(b){
  return `<div class="dcard"><h4>${esc(b.team)}</h4>
    <span class="tag ${trendClass(b.label)}">${esc(b.label)}</span>
    <div class="dyn">${esc(b.summary)}</div>
    <div style="margin-top:9px;font-size:11px;font-weight:900;color:#475569;text-transform:uppercase;letter-spacing:.05em">Blessés</div>
    ${injuryList(b)}
    <button class="btn sm newsbtn" onclick="loadNews(this,'${esc(b.team)}')" style="background:#eef6f1;color:#0c241b;border:1px solid #d6e2db">📰 Actu ${esc(b.team)}</button>
    <div class="newslist"></div></div>`;
}
function matchCard(m,i){
  const dt=new Date(m.kickoff);
  const when=isNaN(dt)?"":dt.toLocaleDateString("fr-FR",{weekday:"short",day:"2-digit",month:"short"})+" · "+dt.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"});
  return `<div class="match" id="m${i}">
    <div class="mtop"><span class="when">${esc(when)}</span><span class="conf ${confClass(m.confidence)}">${esc(m.confidence)}</span></div>
    <div class="teams">
      <div class="team home"><span class="tname">${esc(m.home)}</span><div class="formpills">${formPills(m.home_block.forme)}</div><div class="badges">${teamBadges(m.home_block)}</div></div>
      <span class="vs">VS</span>
      <div class="team away"><span class="tname">${esc(m.away)}</span><div class="formpills">${formPills(m.away_block.forme)}</div><div class="badges">${teamBadges(m.away_block)}</div></div>
    </div>
    ${probBar(m)}
    <div class="pickline"><div><span class="lab">Le marché penche pour</span><br><span class="val">${esc(m.pick)} · ${m.pick_proba}%</span></div>
      <button class="expandbtn" onclick="toggle(${i})">Détails ▾</button></div>
    <div class="detail hidden" id="d${i}"><div class="dcols">${teamCard(m.home_block)}${teamCard(m.away_block)}</div></div>
  </div>`;
}
function toggle(i){const d=$("#d"+i);d.classList.toggle("hidden");const b=$("#m"+i+" .expandbtn");b.textContent=d.classList.contains("hidden")?"Détails ▾":"Masquer ▴";}

async function loadNews(btn,team){
  const box=btn.nextElementSibling; btn.disabled=true; btn.textContent="Chargement…";
  try{
    const d=await api("/api/ligue1/news?team="+encodeURIComponent(team));
    box.innerHTML=(!d.items||!d.items.length)?`<div class="dyn">Aucune actu récente.</div>`:
      d.items.map(it=>{
        const tags=(it.tags||[]).map(t=>{const c=/BLESS/.test(t)?"bless":/RETOUR/.test(t)?"retour":"";return `<span class="ntag ${c}">${esc(t)}</span>`;}).join("");
        return `<div class="newsitem"><a href="${esc(it.link)}" target="_blank" rel="noopener">${esc(it.title)}</a><div class="meta"><span>${esc(it.date)}</span><span>${esc(it.source)}</span>${tags}</div></div>`;
      }).join("");
    btn.textContent="📰 Actu "+team;
  }catch(e){box.innerHTML=`<div class="dyn">Erreur de chargement.</div>`;btn.textContent="📰 Réessayer";}
  btn.disabled=false;
}

async function loadJournee(force){
  const list=$("#list"); list.innerHTML=`<div class="loading"><div class="spin"></div>Chargement…</div>`;
  $("#refreshBtn").disabled=true;
  try{
    const d=await api("/api/ligue1/journee"+(force?"?refresh=1":""));
    $("#heroTitle").textContent=d.matches.length?`${d.matches.length} matchs`:"Aucun match";
    $("#heroMeta").innerHTML=`<span>📅 <b>${esc(d.source)}</b></span><span>💹 Cotes : <b>${esc((d.odds_source||[]).join(", ")||"—")}</b></span><span>🕒 ${esc(d.updated)}</span>`;
    const ha=$("#healthAlert");
    if(d.health&&!d.health.ok){ha.classList.remove("hidden");ha.innerHTML=`<b>⚠ Alerte blessés (Transfermarkt)</b> — données possiblement périmées : `+esc((d.health.issues||[]).join(" ; "));}
    else ha.classList.add("hidden");
    list.innerHTML=d.matches.length?d.matches.map((m,i)=>matchCard(m,i)).join(""):`<div class="note">Aucun match à venir (intersaison).</div>`;
  }catch(e){ if(token()) list.innerHTML=`<div class="note">Erreur de chargement.</div>`; }
  $("#refreshBtn").disabled=false;
}

/* ---------- Boot ---------- */
if (token()) showApp(); else $("#login").classList.remove("hidden");
