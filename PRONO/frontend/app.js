/* Ligue 1 PRONO — frontend (auth JWT + tableau de probas + actu) */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const TOKEN_KEY = "prono_token";
const token = () => localStorage.getItem(TOKEN_KEY) || "";

/* Identité visuelle : badge coloré + initiales (pas de vrai logo reproduit,
   juste une couleur d'identification — zéro question de droits/marques). */
const TEAM_BADGE = {
  "Paris SG":   { abbr: "PSG",  color: "#1a3a6b" },
  "Marseille":  { abbr: "OM",   color: "#1d8fce" },
  "Lyon":       { abbr: "OL",   color: "#1c2951" },
  "Monaco":     { abbr: "ASM",  color: "#c8102e" },
  "Lille":      { abbr: "LOSC", color: "#c8102e" },
  "Nice":       { abbr: "OGCN", color: "#a4231e" },
  "Lens":       { abbr: "RCL",  color: "#ffd200", dark: true },
  "Rennes":     { abbr: "SRFC", color: "#e2001a" },
  "Strasbourg": { abbr: "RCSA", color: "#0066b3" },
  "Brest":      { abbr: "SB29", color: "#c8102e" },
  "Nantes":     { abbr: "FCN",  color: "#fcd116", dark: true },
  "Toulouse":   { abbr: "TFC",  color: "#6e2585" },
  "Auxerre":    { abbr: "AJA",  color: "#1c2951" },
  "Le Havre":   { abbr: "HAC",  color: "#0066b3" },
  "Angers":     { abbr: "SCO",  color: "#1c2951" },
  "Metz":       { abbr: "FCM",  color: "#8b1538" },
  "Lorient":    { abbr: "FCL",  color: "#ff6600" },
  "Paris FC":   { abbr: "PFC",  color: "#1a3a6b" },
};
function crestBadge(team){
  const b = TEAM_BADGE[team];
  if(!b) return `<span class="crest" style="background:#64748b;color:#fff">${esc((team||"?").slice(0,3).toUpperCase())}</span>`;
  return `<span class="crest" style="background:${b.color};color:${b.dark?'#172800':'#fff'}">${esc(b.abbr)}</span>`;
}

async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { ...(opts.headers || {}), "Authorization": "Bearer " + token() } });
  if (r.status === 401) { logout(); throw new Error("Session expirée"); }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Erreur");
  return r.json();
}

/* ---------- PWA : installation ---------- */
let _deferredInstallPrompt = null;
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}
const _isStandalone = () => window.matchMedia("(display-mode: standalone)").matches
  || window.navigator.standalone === true;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  _deferredInstallPrompt = e;
  if (!_isStandalone()) $("#installBtn").classList.remove("hidden");
});
window.addEventListener("appinstalled", () => { $("#installBtn").classList.add("hidden"); });
async function installApp() {
  if (_deferredInstallPrompt) {
    _deferredInstallPrompt.prompt();
    const choice = await _deferredInstallPrompt.userChoice;
    _deferredInstallPrompt = null;
    if (choice && choice.outcome === "accepted") { $("#installBtn").classList.add("hidden"); return; }
  }
  showInstallInstructions();
}
function showInstallInstructions() {
  const ua = navigator.userAgent, iOS = /iphone|ipad|ipod/i.test(ua), android = /android/i.test(ua);
  let html = `<div class="installStep"><b>Installer Ligue 1 · Pronos</b>L'app s'ouvre alors en plein écran, comme une appli normale.</div>`;
  if (iOS) html += `<div class="installStep"><b>Sur iPhone (Safari)</b>Bouton Partager (carré avec flèche), puis « Sur l'écran d'accueil ».</div>`;
  else if (android) html += `<div class="installStep"><b>Sur Android (Chrome)</b>Menu ⋮ en haut à droite, puis « Ajouter à l'écran d'accueil » ou « Installer l'application ».</div>`;
  else html += `<div class="installStep"><b>Sur ordinateur</b>Utilise l'icône d'installation dans la barre d'adresse du navigateur (Chrome/Edge).</div>`;
  $("#installContent").innerHTML = html;
  $("#installModal").classList.remove("hidden");
}
function hideInstall() { $("#installModal").classList.add("hidden"); }
// Si déjà installée (standalone), pas la peine de montrer le bouton du tout.
if (_isStandalone()) document.addEventListener("DOMContentLoaded", () => $("#installBtn") && $("#installBtn").classList.add("hidden"));
// iOS ne déclenche jamais beforeinstallprompt : on propose quand même le bouton manuellement.
if (/iphone|ipad|ipod/i.test(navigator.userAgent) && !_isStandalone()) {
  document.addEventListener("DOMContentLoaded", () => $("#installBtn") && $("#installBtn").classList.remove("hidden"));
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

/* ---------- Mon compte ---------- */
async function showAccount() {
  $("#curPwd").value = ""; $("#newPwd").value = ""; $("#newPwd2").value = "";
  $("#accountMsg").className = "loginmsg";
  try { const me = await api("/api/auth/me"); $("#accEmail").value = me.email; } catch (e) {}
  $("#accountModal").classList.remove("hidden");
}
function hideAccount() { $("#accountModal").classList.add("hidden"); }
async function doChangePassword() {
  const msg = $("#accountMsg");
  const cur = $("#curPwd").value, n1 = $("#newPwd").value, n2 = $("#newPwd2").value;
  if (n1.length < 8) { msg.textContent = "Le nouveau mot de passe doit faire au moins 8 caractères."; msg.className = "loginmsg err show"; return; }
  if (n1 !== n2) { msg.textContent = "Les deux mots de passe ne correspondent pas."; msg.className = "loginmsg err show"; return; }
  try {
    await api("/api/auth/change-password", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: cur, new_password: n1 }),
    });
    msg.textContent = "Mot de passe modifié ✓"; msg.className = "loginmsg ok show";
    $("#curPwd").value = ""; $("#newPwd").value = ""; $("#newPwd2").value = "";
  } catch (e) { msg.textContent = e.message; msg.className = "loginmsg err show"; }
}

/* ---------- Onglets ---------- */
let _actuLoaded = false;
let _testsLoaded = false;
function switchTab(tab) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  $("#view-matchs").classList.toggle("hidden", tab !== "matchs");
  $("#view-actu").classList.toggle("hidden", tab !== "actu");
  $("#view-tests").classList.toggle("hidden", tab !== "tests");
  if (tab === "actu" && !_actuLoaded) loadActu();
  if (tab === "tests" && !_testsLoaded) loadDiagnostics(false);
}
function refreshAll() {
  _actuLoaded = false;
  loadJournee(true);
  if (!$("#view-actu").classList.contains("hidden")) loadActu();
  if (!$("#view-tests").classList.contains("hidden")) loadDiagnostics(true);
}

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
  return `<div class="dcard"><h4>${crestBadge(b.team)} ${esc(b.team)}</h4>
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
function ctxClass(level){const l=(level||"").toLowerCase();return l.includes("volatil")?"ctx-volatil":l.includes("nuancer")?"ctx-nuancer":"ctx-standard";}
function contextBlock(ctx){
  if(!ctx) return "";
  const cls=ctxClass(ctx.level);
  const list=(ctx.factors&&ctx.factors.length)
    ? `<ul class="ctxlist">${ctx.factors.map(f=>`<li>${esc(f)}</li>`).join("")}</ul>`
    : `<div class="ctxlist empty">Aucun facteur particulier identifié.</div>`;
  return `<div class="ctxblock ${cls}">
    <div class="ctxhead">🔎 Niveau de lecture : <b>${esc(ctx.level)}</b> (${ctx.count} facteur${ctx.count>1?"s":""})</div>
    ${list}
    <div class="ctxfoot">Ce contexte n'influence pas la probabilité affichée (issue du marché) — il aide à nuancer la lecture, pas à recommander un pari.</div>
  </div>`;
}
function matchRow(m,i){
  const dt=new Date(m.kickoff);
  const when=isNaN(dt)?"":dt.toLocaleDateString("fr-FR",{weekday:"short",day:"2-digit",month:"2-digit"})+" "+dt.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"});
  const inj=(m.home_block.injuries_count||0)+(m.away_block.injuries_count||0);
  const injBadge=inj>0?`<span class="rowbadge inj">🩼 ${inj}</span>`:"";
  const ctx=m.context;
  const ctxBadge=(ctx&&ctx.level!=="Standard")
    ? `<span class="rowbadge ${ctxClass(ctx.level)}">${ctx.level==="Volatil"?"🌪":"⚠️"} ${esc(ctx.level)}</span>` : "";
  return `<tr class="prow" onclick="toggleDetail(${i})">
      <td class="mcell">
        <div class="mteams"><span class="mh">${esc(m.home)}</span><span class="msep">–</span><span class="ma">${esc(m.away)}</span></div>
        <div class="msub"><span class="cdot ${confClass(m.confidence)}"></span>${esc(when)} ${injBadge} ${ctxBadge}</div>
      </td>
      ${probCell(m.p_home,"h",m.pick_outcome==="H")}
      ${probCell(m.p_draw,"d",m.pick_outcome==="D")}
      ${probCell(m.p_away,"a",m.pick_outcome==="A")}
      <td class="acell"><button class="actubtn" onclick="event.stopPropagation();toggleDetail(${i})">Actu</button></td>
    </tr>
    <tr class="detailrow hidden" id="d${i}"><td colspan="5">
      ${contextBlock(ctx)}
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

function renderSummaryLine(matches){
  const sl=$("#summaryLine");
  if(!matches||!matches.length){ sl.classList.add("hidden"); return; }
  const nb=matches.length;
  const derbies=matches.filter(m=>m.derby).length;
  const volatils=matches.filter(m=>m.context&&m.context.level==="Volatil").length;
  const nuances=matches.filter(m=>m.context&&m.context.level==="À nuancer").length;
  const chips=[`${nb} match${nb>1?"s":""}`];
  if(volatils) chips.push(`🌪 ${volatils} volatil${volatils>1?"s":""}`);
  if(nuances) chips.push(`⚠️ ${nuances} à nuancer`);
  if(derbies) chips.push(`⚔️ ${derbies} derby${derbies>1?"s":""}`);
  sl.classList.remove("hidden");
  sl.innerHTML=chips.map(c=>`<span>${esc(c)}</span>`).join(" · ");
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
    const bn=$("#breakNote");
    if(d.break&&d.break.detected){
      const icon=d.break.kind==="hivernale"?"❄️":d.break.kind==="internationale"?"🌍":"⏸️";
      bn.classList.remove("hidden");
      bn.innerHTML=`${icon} <b>${esc(d.break.label)}</b> — ${esc(d.break.note)}`;
    } else bn.classList.add("hidden");
    renderSummaryLine(d.matches);
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


/* ---------- Tests PRONO value ---------- */
const VALUE_CHECKS = {
  scenarios: { label: "Scenarios", method: "GET", path: "/api/value/scenarios/ligue1/journee?refresh=1" },
  tickets: { label: "Tickets candidats", method: "GET", path: "/api/value/ticket-families/ligue1" },
  backtest: { label: "Backtest scenarios", method: "GET", path: "/api/value/backtests/ligue1/scenarios" },
  coverage: { label: "Couverture cotes", method: "GET", path: "/api/value/coverage/odds" },
};
function setTestsStatus(text, kind="info") {
  const box = $("#testsStatus");
  if (!box) return;
  box.textContent = text;
  box.className = "note teststatus " + kind;
}
function renderJsonDetails(data) {
  return `<details class="jsonbox"><summary>Details JSON</summary><pre>${esc(JSON.stringify(data, null, 2))}</pre></details>`;
}
function testCard(title, status, body, data) {
  const cls = status === "ok" ? "ok" : status === "error" ? "error" : "degraded";
  return `<article class="testcard ${cls}"><div class="testhead"><b>${esc(title)}</b><span>${esc(status)}</span></div>${body}${renderJsonDetails(data)}</article>`;
}
function renderDiagnostics(data) {
  const checks = data.checks || [];
  const cards = checks.map(c => testCard(
    c.name || "check",
    c.status || (c.ok ? "ok" : "error"),
    `<p>${esc(c.message || "")}</p><div class="testmeta">${c.count != null ? `Count: ${esc(c.count)}` : ""}${c.source ? ` � Source: ${esc(c.source)}` : ""}</div>`,
    c
  )).join("");
  const summary = data.summary || {};
  $("#testsPanel").innerHTML = `<div class="testsummary">
    <span>Scenarios: <b>${summary.can_build_scenarios ? "OK" : "KO"}</b></span>
    <span>Fixtures futures: <b>${summary.has_upcoming_fixtures ? "OK" : "degrade"}</b></span>
    <span>Cotes: <b>${summary.has_odds_snapshots ? "OK" : "a brancher"}</b></span>
  </div>${cards}`;
  setTestsStatus(`Diagnostic termine : ${data.status || "ok"}.`, data.status || "ok");
  _testsLoaded = true;
}
async function loadDiagnostics(refresh) {
  setTestsStatus("Diagnostic en cours...");
  $("#testsPanel").innerHTML = `<div class="loading"><div class="spin"></div>Diagnostic...</div>`;
  try {
    const data = await api("/api/value/diagnostics" + (refresh ? "?refresh=1" : ""));
    renderDiagnostics(data);
  } catch (e) {
    setTestsStatus(e.message, "error");
    $("#testsPanel").innerHTML = "";
  }
}
function renderValueResult(kind, data) {
  if (kind === "scenarios") {
    return testCard("Scenarios Ligue 1", "ok", `<p>${esc(data.count || 0)} match(s) scenario.</p>`, data);
  }
  if (kind === "tickets") {
    return testCard("Tickets candidats", data.n_candidates ? "ok" : "degraded", `<p>${esc(data.n_candidates || 0)} candidat(s) depuis ${esc(data.n_predictions || 0)} prediction(s).</p>`, data);
  }
  if (kind === "backtest") {
    return testCard("Backtest scenarios", data.n_signals ? "ok" : "degraded", `<p>${esc(data.n_signals || 0)} signal(aux), ${esc(data.n_matched || 0)} prediction(s) matchee(s).</p>`, data);
  }
  if (kind === "coverage") {
    return testCard("Couverture cotes", data.event_count ? "ok" : "degraded", `<p>${esc(data.event_count || 0)} evenement(s), ${esc(data.snapshot_count || 0)} snapshot(s).</p>`, data);
  }
  return testCard("Resultat", "ok", "", data);
}
async function runValueCheck(kind) {
  const conf = VALUE_CHECKS[kind];
  if (!conf) return;
  setTestsStatus(`${conf.label} en cours...`);
  try {
    const data = await api(conf.path, { method: conf.method });
    $("#testsPanel").innerHTML = renderValueResult(kind, data);
    setTestsStatus(`${conf.label} termine.`, "ok");
    _testsLoaded = true;
  } catch (e) {
    setTestsStatus(e.message, "error");
  }
}

/* ---------- Boot ---------- */
if (token()) showApp(); else $("#login").classList.remove("hidden");

