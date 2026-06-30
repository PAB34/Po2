/* Ligue 1 PRONO — frontend (auth JWT + tableau de probas + actu) */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const TOKEN_KEY = "prono_token";
const token = () => localStorage.getItem(TOKEN_KEY) || "";

async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { ...(opts.headers || {}), "Authorization": "Bearer " + token() } });
  if (r.status === 401) { logout(); throw new Error("Session expirée"); }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Erreur");
  return r.json();
}

/* ---------- Auth ---------- */
async function doLogin() {
  const msg = $("#loginMsg"), btn = $("#loginBtn");
  msg.className = "loginmsg"; btn.disabled = true;
  try {
    const r = await fetch("/api/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: $("#email").value.trim(), password: $("#password").value }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Connexion refusée");
    localStorage.setItem(TOKEN_KEY, d.access_token);
    showApp();
  } catch (e) { msg.textContent = e.message; msg.className = "loginmsg err show"; }
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

/* ---------- Onglets ---------- */
let _actuLoaded = false;
function switchTab(tab) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  $("#view-matchs").classList.toggle("hidden", tab !== "matchs");
  $("#view-actu").classList.toggle("hidden", tab !== "actu");
  if (tab === "actu" && !_actuLoaded) loadActu();
}
function refreshAll() { _actuLoaded = false; loadJournee(true); if (!$("#view-actu").classList.contains("hidden")) loadActu(); }

/* ---------- Helpers rendu ---------- */
function confClass(c){const l=(c||"").toLowerCase();return l.includes("fort")?"fort":l.includes("moyen")?"moyen":"faible";}
function trendClass(l){return /↑|hausse/i.test(l)?"up":/↓|baisse|repli/i.test(l)?"down":"flat";}
function stakesClass(level){const l=(level||"").toLowerCase();return l==="fort"?"stk-fort":l==="moyen"?"stk-moyen":"stk-faible";}
function formPills(f){return [...(f||"")].map(c=>`<span class="pill ${c}">${c}</span>`).join("");}
function newsItems(items){
  if(!items||!items.length) return `<div class="dyn">Aucune actu récente.</div>`;
  return items.map(it=>{
    const tags=(it.tags||[]).map(t=>{const c=/BLESS/.test(t)?"bless":/RETOUR/.test(t)?"retour":"";return `<span class="ntag ${c}">${esc(t)}</span>`;}).join("");
    return `<div class="newsitem"><a href="${esc(it.link)}" target="_blank" rel="noopener">${esc(it.title)}</a>
      <div class="meta"><span>${esc(it.date)}</span><span>${esc(it.source)}</span>${tags}</div></div>`;
  }).join("");
}

/* ---------- Tableau des matchs ---------- */
function injuryList(b){
  if(!b.injuries||!b.injuries.length)return `<div class="dyn" style="color:#15803d">Aucun blessé connu ✓</div>`;
  return `<ul class="injlist">`+b.injuries.map(i=>{
    const ko=/ligament|fracture|rupture/i.test(i.injury)?"ko":"";
    const ret=i.return&&i.return!=="non précisé"?` · retour ${esc(i.return)}`:"";
    return `<li><span class="${ko}">${esc(i.player)}</span> <span style="color:#64748b">(${esc(i.position)})</span> — ${esc(i.injury)}${ret}</li>`;
  }).join("")+`</ul>`;
}
function stakesBlock(st){
  if(!st || st.rank==null) return "";
  return `<div class="dlbl">Enjeu</div>
    <div class="stkrow">
      <span class="stkrank">${st.rank}<sup>e</sup>/${st.n_teams} · ${st.points} pts${st.games_remaining?` · ${st.games_remaining} matchs restants`:""}</span>
      <span class="stkpill ${stakesClass(st.level)}">${esc(st.enjeu_label)}</span>
    </div>`;
}
function teamCard(b){
  return `<div class="dcard"><h4>${esc(b.team)}</h4>
    <span class="tag ${trendClass(b.label)}">${esc(b.label)}</span>
    <div class="formpills" style="margin:6px 0">${formPills(b.forme)}</div>
    <div class="dyn">${esc(b.summary)}</div>
    ${stakesBlock(b.stakes)}
    <div class="dlbl">Blessés</div>${injuryList(b)}
    <button class="btn sm newsbtn" onclick="loadTeamNews(this,'${esc(b.team)}')">📰 Actu ${esc(b.team)}</button>
    <div class="newslist"></div></div>`;
}
function probCell(val,cls,win){
  return `<td class="pc ${cls} ${win?"win":""}">${val==null?"—":val+"%"}</td>`;
}
function matchRow(m,i){
  const dt=new Date(m.kickoff);
  const when=isNaN(dt)?"":dt.toLocaleDateString("fr-FR",{weekday:"short",day:"2-digit",month:"2-digit"})+" "+dt.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"});
  const inj=(m.home_block.injuries_count||0)+(m.away_block.injuries_count||0);
  const injBadge=inj>0?`<span class="rowbadge inj">🩼 ${inj}</span>`:"";
  const hotStakes=[m.home_block.stakes,m.away_block.stakes].some(s=>s&&s.level==="Fort");
  const stakesBadge=hotStakes?`<span class="rowbadge hot">🔥 enjeu</span>`:"";
  const noteRow=m.stakes_note?`<div class="stknote">⚖️ ${esc(m.stakes_note)}</div>`:"";
  return `<tr class="prow" onclick="toggleDetail(${i})">
      <td class="mcell">
        <div class="mteams"><span class="mh">${esc(m.home)}</span><span class="msep">–</span><span class="ma">${esc(m.away)}</span></div>
        <div class="msub"><span class="cdot ${confClass(m.confidence)}"></span>${esc(when)} ${injBadge} ${stakesBadge}</div>
      </td>
      ${probCell(m.p_home,"h",m.pick_outcome==="H")}
      ${probCell(m.p_draw,"d",m.pick_outcome==="D")}
      ${probCell(m.p_away,"a",m.pick_outcome==="A")}
      <td class="acell"><button class="actubtn" onclick="event.stopPropagation();toggleDetail(${i})">Actu</button></td>
    </tr>
    <tr class="detailrow hidden" id="d${i}"><td colspan="5">
      ${noteRow}
      <div class="dcols">${teamCard(m.home_block)}${teamCard(m.away_block)}</div>
    </td></tr>`;
}
function toggleDetail(i){ $("#d"+i).classList.toggle("hidden"); }

async function loadTeamNews(btn,team){
  const box=btn.nextElementSibling; btn.disabled=true; btn.textContent="Chargement…";
  try{ const d=await api("/api/ligue1/news?team="+encodeURIComponent(team)); box.innerHTML=newsItems(d.items); btn.textContent="📰 Actu "+team; }
  catch(e){ box.innerHTML=`<div class="dyn">Erreur.</div>`; btn.textContent="📰 Réessayer"; }
  btn.disabled=false;
}

async function loadJournee(force){
  const list=$("#list"); list.innerHTML=`<div class="loading"><div class="spin"></div>Chargement…</div>`;
  $("#refreshBtn").disabled=true;
  try{
    const d=await api("/api/ligue1/journee"+(force?"?refresh=1":""));
    $("#heroMeta").innerHTML=`<span>📅 <b>${esc(d.source)}</b></span><span>💹 <b>${esc((d.odds_source||[]).join(", ")||"—")}</b></span><span>🕒 ${esc(d.updated)}</span>`;
    const ha=$("#healthAlert");
    if(d.health&&!d.health.ok){ha.classList.remove("hidden");ha.innerHTML=`<b>⚠ Alerte blessés</b> — données possiblement périmées : `+esc((d.health.issues||[]).join(" ; "));}
    else ha.classList.add("hidden");
    list.innerHTML=d.matches.length
      ? `<table class="ptable"><thead><tr><th>Match</th><th>1</th><th>N</th><th>2</th><th></th></tr></thead>
         <tbody>${d.matches.map((m,i)=>matchRow(m,i)).join("")}</tbody></table>`
      : `<div class="note">Aucun match à venir (intersaison).</div>`;
  }catch(e){ if(token()) list.innerHTML=`<div class="note">Erreur de chargement.</div>`; }
  $("#refreshBtn").disabled=false;
}

async function loadActu(){
  const box=$("#actuList"); box.innerHTML=`<div class="loading"><div class="spin"></div>Chargement de l'actu…</div>`;
  try{
    const d=await api("/api/ligue1/actu");
    box.innerHTML=`<div class="newslist big">${newsItems(d.items)}</div>`;
    _actuLoaded=true;
  }catch(e){ box.innerHTML=`<div class="note">Erreur de chargement de l'actu.</div>`; }
}

/* ---------- Boot ---------- */
if (token()) showApp(); else $("#login").classList.remove("hidden");
