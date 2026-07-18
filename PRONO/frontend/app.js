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
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw-20260718-wide.js", { updateViaCache: "none" }).catch(() => {}));
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
  let html = `<div class="installStep"><b>Installer Ligue 1 - Pronos</b>L'app s'ouvre alors en plein écran, comme une appli normale.</div>`;
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
let _tennisLoaded = false;
let _tennisData = null;
let _tennisBrackets = null;
let _tennisMode = "matches";
let _selectedBracket = 0;
let _bracketTourFilter = "all";
let _tennisSort = { key: "kickoff", dir: "asc" };
function switchTab(tab) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  $("#app").classList.toggle("tennis-wide", tab === "tennis");
  $("#view-matchs").classList.toggle("hidden", tab !== "matchs");
  $("#view-actu").classList.toggle("hidden", tab !== "actu");
  $("#view-tests").classList.toggle("hidden", tab !== "tests");
  $("#view-tennis").classList.toggle("hidden", tab !== "tennis");
  if (tab === "actu" && !_actuLoaded) loadActu();
  if (tab === "tests" && !_testsLoaded) loadDiagnostics(false);
  if (tab === "tennis" && !_tennisLoaded) loadTennis(false);
}
function refreshAll() {
  _actuLoaded = false;
  loadJournee(true);
  if (!$("#view-actu").classList.contains("hidden")) loadActu();
  if (!$("#view-tests").classList.contains("hidden")) loadDiagnostics(true);
  if (!$("#view-tennis").classList.contains("hidden")) loadTennis(true);
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
    const ret=i.return&&i.return!=="non précisé"?` - retour ${esc(i.return)}`:"";
    return `<li><span class="${ko}">${esc(i.player)}</span> <span style="color:#64748b">(${esc(i.position)})</span> — ${esc(i.injury)}${ret}</li>`;
  }).join("")+`</ul>`;
}
function stakesBlock(st){
  if(!st || st.rank==null) return "";
  return `<div class="dlbl">Enjeu</div>
    <div class="stkrow">
      <span class="stkrank">${st.rank}<sup>e</sup>/${st.n_teams} - ${st.points} pts${st.games_remaining?` - ${st.games_remaining} matchs restants`:""}</span>
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
  sl.innerHTML=chips.map(c=>`<span>${esc(c)}</span>`).join(" - ");
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


/* ---------- Tennis ---------- */
function pctTennis(value) {
  if (value === null || value === undefined || value === "") return "-";
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(n) + "%" : "-";
}
function numTennis(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "-";
}
function signedTennis(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}`;
}
function tennisSignals(row) {
  const chips = [
    `${esc(row.joueur1 || "J1")}: charge ${esc(row.fatigue1 || "inconnue")}`,
    `${esc(row.joueur2 || "J2")}: charge ${esc(row.fatigue2 || "inconnue")}`,
    `H2H ${esc(row.h2h || "0-0")}`,
    row.match_source ? `Source ${esc(row.match_source)}` : "",
    row.odds_status && row.odds_status !== "ok" ? "Cotes indisponibles" : "",
  ].filter(Boolean).map(t => `<span>${t}</span>`).join("");
  const alert = row.alerte ? `<div class="talert">${esc(row.alerte)}</div>` : "";
  const proofs = row.preuves ? `<div class="tproof">${esc(row.preuves)}</div>` : "";
  return `<div class="tchips">${chips}</div>${alert}${proofs}`;
}
function tennisMarkets(markets) {
  if (!markets || !markets.length) return `<div class="tmarkets empty">-</div>`;
  return `<div class="tmarkets">${markets.map(m => `<span class="mkt ${esc(m.force || "info")}" title="${esc([m.detail, m.source ? "Source: " + m.source : "", m.confidence ? "Confiance: " + m.confidence : ""].filter(Boolean).join(" | "))}"><b>${esc(m.label || "Marche")}</b>${esc(m.pick || "-")}${m.prob == null ? "" : `<em>${esc(m.prob)}%</em>`}</span>`).join("")}</div>`;
}
const TENNIS_SORT_COLUMNS = [
  ["tour", "Circuit"], ["kickoff", "Heure"], ["tournoi", "Tournoi"], ["match", "Match"],
  ["forme", "Forme"], ["decision", "Lecture"], ["proba_marche", "Marche", "n"], ["proba_elo", "Elo surface", "n"],
  ["ecart_elo", "Ecart", "n"], ["impact_contexte", "Contexte"], ["cote", "Cote", "n"],
  ["markets", "Stats marches"], ["p20", "Fav 2-0", "n"], ["p21", "Fav 2-1", "n"], ["p3", "3 sets", "n"],
];
function tennisSortIcon(key) {
  if (_tennisSort.key !== key) return "";
  return _tennisSort.dir === "asc" ? " ^" : " v";
}
function tennisHeader(key, label, cls = "") {
  return `<th class="${cls}"><button class="sorthead" onclick="setTennisSort('${key}')" aria-label="Trier par ${esc(label)}">${esc(label)}${tennisSortIcon(key)}</button></th>`;
}
function setTennisSort(key) {
  _tennisSort = _tennisSort.key === key ? { key, dir: _tennisSort.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "kickoff" ? "asc" : "desc" };
  renderTennis();
}
function tennisSortValue(row, key) {
  if (key === "kickoff") return row.kickoff || row.heure || "9999";
  if (key === "markets") return Math.max(...(row.markets || []).map(m => Number(m.prob || 0)), 0);
  if (key === "forme") return `${row.cycle1 || ""} ${row.cycle2 || ""}`.toLowerCase();
  if (["proba_marche", "proba_elo", "ecart_elo", "cote", "p20", "p21", "p3"].includes(key)) return Number(row[key] ?? -9999);
  const decisionOrder = { strong: 4, watch: 3, insufficient: 2, favorable: 1, neutral: 0 };
  if (key === "decision") return decisionOrder[row.decision_level] ?? -1;
  return String(row[key] || "").toLowerCase();
}
function sortedTennisRows(rows) {
  const dir = _tennisSort.dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = tennisSortValue(a, _tennisSort.key), bv = tennisSortValue(b, _tennisSort.key);
    if (av < bv) return -dir;
    if (av > bv) return dir;
    return String(a.match || "").localeCompare(String(b.match || ""));
  });
}
function tennisDecision(row) {
  const range = row.fourchette_min == null || row.fourchette_max == null ? "-" : `${row.fourchette_min}-${row.fourchette_max}%`;
  return `<div class="tdecision ${esc(row.decision_level || "neutral")}">
    <span>${esc(row.decision || "Neutre")}</span>
    <b>${esc(row.favori || "-")}</b>
    <small>Fourchette ${esc(range)} | fiabilite ${esc(row.qualite || "faible")}</small>
  </div>`;
}
function tennisContext(row) {
  const contextClass = row.impact_contexte === "avantage relatif" ? "favorable" : row.impact_contexte === "desavantage relatif" ? "defavorable" : "neutre";
  return `<div class="tcontext ${contextClass}">
    <b>${esc(row.impact_contexte || "neutre")}</b>
    <span>${esc(row.decision_detail || "aucun facteur discriminant")}</span>
  </div>`;
}
function tennisForm(row) {
  return `<div class="tform">
    <span><b>${esc(row.joueur1 || "J1")}</b>${esc(row.cycle1 || "inconnue")}</span>
    <span><b>${esc(row.joueur2 || "J2")}</b>${esc(row.cycle2 || "inconnue")}</span>
  </div>`;
}
function tennisElo(row) {
  if (row.proba_elo != null) return pctTennis(row.proba_elo);
  return `<span class="tmissing" title="${esc(row.elo_detail || "Historique de surface insuffisant pour au moins un joueur")}">Indispo</span>`;
}
function tennisTable(rows) {
  if (!rows || !rows.length) return `<div class="note">Aucun match a venir pour le moment.</div>`;
  const header = TENNIS_SORT_COLUMNS.map(([key, label, cls]) => tennisHeader(key, label, cls || "")).join("");
  return `<div class="tenwrap"><table class="tentable"><thead><tr>${header}</tr></thead><tbody>${sortedTennisRows(rows).map(row => {
    const gap = Number(row.ecart_elo);
    const gapCls = !Number.isFinite(gap) ? "flat" : gap <= -5 ? "neg" : gap >= 5 ? "pos" : "flat";
    return `<tr>
      <td><span class="tourpill ${esc(row.tour || "")}">${esc(row.tour || "-")}</span></td>
      <td><b>${esc(row.heure || "-")}</b><div class="tsub">${esc(row.surface || "")}</div></td>
      <td><b>${esc(row.tournoi)}</b></td>
      <td><div class="tmatch">${esc(row.match)}</div>${tennisSignals(row)}</td>
      <td>${tennisForm(row)}</td>
      <td>${tennisDecision(row)}</td>
      <td class="n probten">${pctTennis(row.proba_marche)}<span style="width:${Math.max(8, Number(row.proba_marche || 0) * 0.46)}px"></span></td>
      <td class="n">${tennisElo(row)}</td>
      <td class="n tadj ${gapCls}">${row.ecart_elo == null ? "-" : signedTennis(row.ecart_elo)}</td>
      <td>${tennisContext(row)}</td>
      <td class="n">${numTennis(row.cote)}</td>
      <td>${tennisMarkets(row.markets)}</td>
      <td class="n">${pctTennis(row.p20)}</td>
      <td class="n">${pctTennis(row.p21)}</td>
      <td class="n">${pctTennis(row.p3)}</td>
    </tr>`;
  }).join("")}</tbody></table></div>`;
}
function tennisModeBar() {
  return `<div class="tenmode">
    <button class="${_tennisMode === "matches" ? "active" : ""}" onclick="setTennisMode('matches')">Lecture matchs</button>
    <button class="${_tennisMode === "brackets" ? "active" : ""}" onclick="setTennisMode('brackets')">Tableaux</button>
  </div>`;
}
function setTennisMode(mode) {
  _tennisMode = mode;
  renderTennis();
  if (mode === "brackets" && !_tennisBrackets) loadTennisBrackets(false);
}
function renderTennis() {
  const box = $("#tennisContent");
  if (!_tennisData) return;
  const body = _tennisMode === "brackets" ? renderTennisBrackets() : renderTennisMatches();
  box.innerHTML = tennisModeBar() + body;
}
function renderTennisMatches() {
  const data = _tennisData || {};
  const rows = [...(data.atp || []).map(r => ({ ...r, tour: "ATP" })), ...(data.wta || []).map(r => ({ ...r, tour: "WTA" }))];
  return `<div class="tensection"><h3>Lecture des matchs <span>${rows.length} matchs - ${(data.atp || []).length} ATP / ${(data.wta || []).length} WTA</span></h3>${tennisTable(rows)}</div>`;
}
function playerSlot(p) {
  const seed = p && p.seed ? `<span class="bseed">${esc(p.seed)}</span>` : "";
  const score = p && p.score && p.score.length ? `<span class="bscore">${p.score.map(esc).join(" ")}</span>` : "";
  const cls = p && p.winner ? " winner" : "";
  return `<div class="bplayer${cls}">${seed}<span class="bname" title="${esc((p && p.name) || "TBD")}">${esc((p && p.name) || "TBD")}</span>${score}</div>`;
}
function bracketMatch(m) {
  return `<div class="bmatch">
    <div class="bstatus" title="${esc(m.status || "")}">${esc(m.status || "")}</div>
    ${playerSlot(m.player1)}${playerSlot(m.player2)}
  </div>`;
}
function bracketState(t) {
  const done = Number(t.completed_matches || 0), total = Number(t.total_matches || 0);
  if (!total) return "Indisponible";
  if (done <= 0) return "A venir";
  if (done >= total) return "Termine";
  return "En cours";
}
function bracketErrors(errors) {
  if (!errors || !errors.length) return "";
  const items = errors.map(e => `<li><b>${esc(e.tour || "")}</b> ${esc(e.name || "Tournoi")} <span>${esc(e.source || "source")}</span> - ${esc(e.error || "Erreur")}</li>`).join("");
  return `<details class="berrors"><summary>${errors.length} source${errors.length > 1 ? "s" : ""} en erreur</summary><ul>${items}</ul></details>`;
}
function bracketFilters(tournaments) {
  const count = tour => tour === "all" ? tournaments.length : tournaments.filter(t => t.tour === tour).length;
  return `<div class="bracketFilters">
    ${["all", "ATP", "WTA"].map(tour => `<button class="bfilter ${_bracketTourFilter === tour ? "active" : ""}" aria-pressed="${_bracketTourFilter === tour}" onclick="setBracketTourFilter('${tour}')">${tour === "all" ? "Tous" : tour}<span>${count(tour)}</span></button>`).join("")}
  </div>`;
}
function setBracketTourFilter(tour) {
  _bracketTourFilter = tour;
  _selectedBracket = 0;
  renderTennis();
}
function selectBracket(i) {
  _selectedBracket = i;
  renderTennis();
}
function renderTennisBrackets() {
  if (!_tennisBrackets) return `<div class="loading"><div class="spin"></div>Chargement des tableaux...</div>`;
  const tournaments = _tennisBrackets.tournaments || [];
  const errors = _tennisBrackets.errors || [];
  const filtered = _bracketTourFilter === "all" ? tournaments : tournaments.filter(t => t.tour === _bracketTourFilter);
  const meta = `<div class="bracketMeta"><span>${esc(tournaments.length)} tableau${tournaments.length > 1 ? "x" : ""}</span><span>Mis a jour ${esc(_tennisBrackets.updated || "-")}</span><span>${esc(_tennisBrackets.source || "Sources tennis")}</span></div>`;
  const top = `<div class="bracketTop">${meta}${bracketFilters(tournaments)}</div>`;
  const diagnostics = bracketErrors(errors);
  if (!tournaments.length) return `${top}<div class="note">Aucun tableau complet trouve pour les tournois en cours.</div>${diagnostics}`;
  if (!filtered.length) return `${top}<div class="note">Aucun tableau ${esc(_bracketTourFilter)} disponible pour le moment.</div>${diagnostics}`;
  if (_selectedBracket >= filtered.length) _selectedBracket = 0;
  const chips = filtered.map((t, i) => `<button class="bchip ${i === _selectedBracket ? "active" : ""}" aria-pressed="${i === _selectedBracket}" title="${esc(t.name)}" onclick="selectBracket(${i})">
    <b>${esc(t.tour)}</b><span class="bchipName">${esc(t.name)}</span><span class="bchipCount">${esc(t.completed_matches)}/${esc(t.total_matches)} joues</span>
  </button>`).join("");
  const t = filtered[_selectedBracket];
  const rounds = (t.rounds || []).map(r => `<div class="bround"><div class="broundh">${esc(r.name)}</div>${(r.matches || []).map(bracketMatch).join("")}</div>`).join("");
  const sourceLabel = t.source ? `source ${t.source}` : "source";
  const sourceLink = t.source_url ? `<a href="${esc(t.source_url)}" target="_blank" rel="noopener">${esc(sourceLabel)}</a>` : `<span class="bsource">${esc(sourceLabel)}</span>`;
  return `${top}<div class="bracketToolbar">${chips}</div>
    <div class="bracketPanel">
      <div class="bracketTitle"><div><b title="${esc(t.name)}">${esc(t.name)}</b><span>${esc(t.location || "")}${t.location ? " - " : ""}${esc(bracketState(t))} - ${esc(t.completed_matches)}/${esc(t.total_matches)} joues</span></div>${sourceLink}</div>
      <div class="bracketRounds">${rounds}</div>
    </div>${diagnostics}`;
}
async function loadTennisBrackets(force) {
  const main = $("#tennisContent");
  if (!_tennisBrackets) main.innerHTML = tennisModeBar() + `<div class="loading"><div class="spin"></div>Chargement des tableaux...</div>`;
  try {
    _tennisBrackets = await api("/api/tennis/brackets" + (force ? "?refresh=1" : ""));
    renderTennis();
  } catch (e) {
    main.innerHTML = tennisModeBar() + `<div class="note">Erreur de chargement des tableaux : ${esc(e.message || "source indisponible")}</div>`;
  }
}
async function loadTennis(force) {
  const box = $("#tennisContent");
  box.innerHTML = `<div class="loading"><div class="spin"></div>${force ? "Actualisation" : "Chargement"} des matchs...</div>`;
  $("#refreshBtn").disabled = true;
  try {
    _tennisData = await api("/api/tennis/matches" + (force ? "?refresh=1" : ""));
    if (force) _tennisBrackets = null;
    const masked = Number(_tennisData.filtered_past || 0);
    const age = Number(_tennisData.feed_age_hours);
    const usesSportScore = (_tennisData.external_sources || []).includes("SportScore");
    const sportScoreCredit = usesSportScore ? `<span><a href="https://sportscore.com/" rel="dofollow">Powered by SportScore</a></span>` : "";
    const scoreboard = _tennisData.scoreboard_source ? `<span>Confrontations : ${esc(_tennisData.scoreboard_source)}${_tennisData.scoreboard_count ? ` (${esc(_tennisData.scoreboard_count)})` : ""}</span>` : "";
    $("#tennisMeta").innerHTML = `<span>Mis a jour : <b>${esc(_tennisData.updated || "-")}</b></span>${scoreboard}${_tennisData.feed_updated ? `<span>Flux cotes : ${esc(_tennisData.feed_updated)}</span>` : ""}${Number.isFinite(age) ? `<span>Age cotes : ${esc(age)}h</span>` : ""}${masked ? `<span>${esc(masked)} passes masques</span>` : ""}${sportScoreCredit}`;
    renderTennis();
    _tennisLoaded = true;
    if (_tennisMode === "brackets") loadTennisBrackets(force);
  } catch (e) {
    box.innerHTML = `<div class="note">Erreur de chargement Tennis : ${esc(e.message || "flux indisponible")}</div>`;
  }
  $("#refreshBtn").disabled = false;
}
/* ---------- Boot ---------- */
if (token()) showApp(); else $("#login").classList.remove("hidden");

