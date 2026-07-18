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
let _tennisQuery = "";
let _expandedTennisMatch = null;
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
    `${esc(row.joueur1 || "J1")}: ${esc(row.fatigue1 || "charge inconnue")}`,
    `${esc(row.joueur2 || "J2")}: ${esc(row.fatigue2 || "charge inconnue")}`,
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
  ["forme", "Forme"], ["decision", "Lecture"], ["concordance", "Concordance"], ["proba_marche", "Marche", "n"],
  ["proba_elo_surface", "Elo surface", "n"], ["proba_elo_global", "Elo global", "n"],
  ["ecart_elo", "Lecture Elo"], ["impact_contexte", "Contexte"], ["cote", "Cote", "n"],
  ["markets", "Stats marches"], ["p20", "Fav 2-0", "n"], ["p21", "Fav 2-1", "n"], ["p3", "3 sets", "n"],
];
const TENNIS_HEADER_HELP = {
  forme: "Signal descriptif: activite, serie, momentum, victoires recentes et charge du tournoi.",
  proba_elo_surface: "Probabilite Elo calculee uniquement avec les matchs sur la surface du jour.",
  proba_elo_global: "Probabilite Elo calculee sur l'ensemble des surfaces.",
  ecart_elo: "Difference entre l'Elo de reference et le consensus du marche pour le favori.",
  concordance: "Accord qualitatif entre marche, Elo, forme recente et qualite des donnees. Ce signal ne modifie aucune probabilite.",
};
function tennisSortIcon(key) {
  if (_tennisSort.key !== key) return "";
  return _tennisSort.dir === "asc" ? " ^" : " v";
}
function tennisHeader(key, label, cls = "") {
  const help = TENNIS_HEADER_HELP[key] ? ` title="${esc(TENNIS_HEADER_HELP[key])}"` : "";
  return `<th class="${cls}"><button class="sorthead" onclick="setTennisSort('${key}')" aria-label="Trier par ${esc(label)}"${help}>${esc(label)}${tennisSortIcon(key)}</button></th>`;
}
function setTennisSort(key) {
  _tennisSort = _tennisSort.key === key ? { key, dir: _tennisSort.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "kickoff" ? "asc" : "desc" };
  renderTennis();
}
function tennisSortValue(row, key) {
  if (key === "kickoff") return row.kickoff || row.heure || "9999";
  if (key === "markets") return Math.max(...(row.markets || []).map(m => Number(m.prob || 0)), 0);
  if (key === "forme") return `${row.cycle1 || ""} ${row.cycle2 || ""}`.toLowerCase();
  if (key === "ecart_elo") return row.ecart_elo == null ? -9999 : Math.abs(Number(row.ecart_elo));
  if (["proba_marche", "proba_elo_surface", "proba_elo_global", "cote", "p20", "p21", "p3"].includes(key)) return Number(row[key] ?? -9999);
  const decisionOrder = { strong: 4, watch: 3, insufficient: 2, favorable: 1, neutral: 0 };
  if (key === "decision") return decisionOrder[row.decision_level] ?? -1;
  if (key === "concordance") return ({ aligned: 5, strong: 4, mixed: 3, watch: 2, partial: 1, conflict: 0, insufficient: -1 })[row.concordance_level] ?? -1;
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
function tennisElo(row, key) {
  if (row[key] != null) return pctTennis(row[key]);
  const fallback = key === "proba_elo_surface" ? row.elo_detail : "Historique global insuffisant pour au moins un joueur";
  return `<span class="tmissing" title="${esc(fallback || "Historique insuffisant")}">Indispo</span>`;
}
function tennisGap(row) {
  if (row.ecart_elo == null) return `<span class="tmissing">Indispo</span>`;
  const gap = Number(row.ecart_elo);
  const abs = Math.abs(gap);
  const source = row.elo_reference === "global" ? "Global" : "Surface";
  const state = abs < 3 ? "aligned" : gap < 0 ? "prudent" : "optimistic";
  const label = state === "aligned" ? "Aligne" : state === "prudent" ? "Elo plus prudent" : "Elo plus optimiste";
  const position = Math.max(4, Math.min(96, 50 + gap * 2.5));
  return `<div class="tgap ${state}" title="${esc(source)}: ${signedTennis(gap)} points par rapport au marche">
    <b>${label}</b><span>${source} ${signedTennis(gap)} pts</span><i><em style="left:${position}%"></em></i>
  </div>`;
}
function tennisConcordance(row) {
  const level = row.concordance_level || "insufficient";
  return `<div class="tconcord ${esc(level)}" title="${esc(row.concordance_detail || "Donnees insuffisantes")}">
    <b>${esc(row.concordance || "Donnees faibles")}</b>
    <span>${esc(row.concordance_detail || "Accord non mesurable")}</span>
  </div>`;
}
function tennisRowKey(row) {
  const value = `${row.tour || ""}|${row.kickoff || row.heure || ""}|${row.match || ""}`;
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) hash = ((hash << 5) - hash + value.charCodeAt(i)) | 0;
  return `tp${Math.abs(hash)}`;
}
function toggleTennisProps(key) {
  const previous = _expandedTennisMatch;
  if (previous && previous !== key) {
    const previousRow = document.getElementById(`props-${previous}`);
    const previousButton = document.getElementById(`props-btn-${previous}`);
    if (previousRow) previousRow.classList.add("hidden");
    if (previousButton) { previousButton.setAttribute("aria-expanded", "false"); previousButton.querySelector("span").textContent = "+"; }
  }
  const detail = document.getElementById(`props-${key}`);
  const button = document.getElementById(`props-btn-${key}`);
  if (!detail || !button) return;
  const opening = detail.classList.contains("hidden");
  detail.classList.toggle("hidden", !opening);
  button.setAttribute("aria-expanded", String(opening));
  button.querySelector("span").textContent = opening ? "-" : "+";
  _expandedTennisMatch = opening ? key : null;
}
function tennisThresholds(items) {
  if (!items || !items.length) return `<span class="tmissing">Indispo</span>`;
  return `<div class="prop-thresholds">${items.map(item => `<span>Plus de ${esc(item.line)} <b>${pctTennis(item.over)}</b></span>`).join("")}</div>`;
}
function tennisPropMetric(label, value, suffix = "", note = "") {
  return `<div class="prop-metric"><span>${esc(label)}</span><b>${value == null ? "-" : esc(value) + suffix}</b>${note ? `<small>${esc(note)}</small>` : ""}</div>`;
}
function tennisPropsPlayer(player) {
  if (!player) return `<section class="tprop-player unavailable"><h5>Profil indisponible</h5></section>`;
  const aceRange = player.aces_interval || [];
  const dfRange = player.double_faults_interval || [];
  return `<section class="tprop-player">
    <div class="prop-player-head"><h5>${esc(player.player || "Joueur")}</h5><span>${esc(player.confidence || "faible")} | ${esc(player.sample_surface || 0)} surface, ${esc(player.sample_total || 0)} total</span></div>
    <div class="prop-metrics">
      ${tennisPropMetric("Aces attendus", numTennis(player.aces_expected, 1), "", aceRange.length ? `Intervalle 80%: ${aceRange[0]}-${aceRange[1]}` : "")}
      ${tennisPropMetric("Doubles fautes", numTennis(player.double_faults_expected, 1), "", dfRange.length ? `Intervalle 80%: ${dfRange[0]}-${dfRange[1]}` : "")}
      ${tennisPropMetric("Tenue de service", pctTennis(player.hold_probability))}
      ${tennisPropMetric("Risque d'etre breake", pctTennis(player.broken_probability))}
      ${tennisPropMetric("Breaks attendus", numTennis(player.breaks_expected, 1), "", `Au moins un: ${pctTennis(player.break_probability)}`)}
    </div>
    <div class="prop-lines"><div><b>Aces</b>${tennisThresholds(player.aces_thresholds)}</div><div><b>Doubles fautes</b>${tennisThresholds(player.double_faults_thresholds)}</div></div>
  </section>`;
}
function tennisValidation(props) {
  const labels = {
    aces_reference: "Aces", double_faults_3_plus: "Doubles fautes",
    broken: "Service breake", break_1_plus: "Break realise", tiebreak: "Tie-break",
  };
  const entries = Object.entries((props && props.validation) || {});
  if (!entries.length) return "";
  return `<div class="prop-validation"><b>Validation hors echantillon 2025</b>${entries.map(([key, item]) => `<span class="${item.validated ? "ok" : "ko"}" title="Brier ${esc(item.brier)} contre reference ${esc(item.baseline_brier)}">${esc(labels[key] || key)}: ${item.validated ? "valide" : "non valide"} | n=${esc(item.sample)}</span>`).join("")}</div>`;
}
function tennisPropsPanel(row) {
  const props = row.props;
  if (!props || !props.players || !props.players.length) return `<div class="tprop-panel unavailable"><b>Statistiques joueurs indisponibles</b><span>L'historique est insuffisant pour construire ce profil.</span></div>`;
  return `<div class="tprop-panel">
    <div class="prop-panel-head"><div><b>Profil service et retour</b><span>${esc(row.surface || props.surface || "Surface inconnue")} | modele joueur + adversaire + surface</span></div><div><b>${pctTennis(props.tiebreak_probability)}</b><span>Au moins un tie-break</span></div></div>
    <div class="prop-players">${props.players.map(tennisPropsPlayer).join("")}</div>
    ${tennisValidation(props)}
    <p>Seuils statistiques issus de l'historique match par match. Ils ne representent pas les lignes actuellement proposees par un bookmaker.</p>
  </div>`;
}function tennisTable(rows) {
  if (!rows || !rows.length) return `<div class="note">${_tennisQuery ? "Aucun match ne correspond a la recherche." : "Aucun match a venir pour le moment."}</div>`;
  const header = TENNIS_SORT_COLUMNS.map(([key, label, cls]) => tennisHeader(key, label, cls || "")).join("");
  return `<div class="tenwrap"><table class="tentable"><thead><tr>${header}</tr></thead><tbody>${sortedTennisRows(rows).map(row => {
    const key = tennisRowKey(row);
    const expanded = _expandedTennisMatch === key;
    return `<tr>
      <td><span class="tourpill ${esc(row.tour || "")}">${esc(row.tour || "-")}</span></td>
      <td><b>${esc(row.heure || "-")}</b>${row.live ? `<span class="livepill">Live</span>` : ""}<div class="tsub">${esc(row.surface || "")}${row.round ? ` | ${esc(row.round)}` : ""}</div></td>
      <td><b>${esc(row.tournoi)}</b></td>
      <td><div class="tmatch">${esc(row.match)}</div><button id="props-btn-${key}" class="prop-toggle" onclick="toggleTennisProps('${key}')" aria-expanded="${expanded}" aria-controls="props-${key}" title="Afficher les statistiques detaillees"><span aria-hidden="true">${expanded ? "-" : "+"}</span><b>Stats</b></button>${tennisSignals(row)}</td>
      <td>${tennisForm(row)}</td>
      <td>${tennisDecision(row)}</td>
      <td>${tennisConcordance(row)}</td>
      <td class="n probten">${pctTennis(row.proba_marche)}<span style="width:${Math.max(8, Number(row.proba_marche || 0) * 0.46)}px"></span></td>
      <td class="n">${tennisElo(row, "proba_elo_surface")}</td>
      <td class="n">${tennisElo(row, "proba_elo_global")}</td>
      <td>${tennisGap(row)}</td>
      <td>${tennisContext(row)}</td>
      <td class="n">${numTennis(row.cote)}</td>
      <td>${tennisMarkets(row.markets)}</td>
      <td class="n">${pctTennis(row.p20)}</td>
      <td class="n">${pctTennis(row.p21)}</td>
      <td class="n">${pctTennis(row.p3)}</td>
    </tr><tr id="props-${key}" class="tprop-row ${expanded ? "" : "hidden"}"><td colspan="17">${tennisPropsPanel(row)}</td></tr>`;
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
function tennisAllRows() {
  const data = _tennisData || {};
  return [...(data.atp || []).map(r => ({ ...r, tour: "ATP" })), ...(data.wta || []).map(r => ({ ...r, tour: "WTA" }))];
}
function tennisSearchText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}
function filteredTennisRows(rows) {
  const words = tennisSearchText(_tennisQuery).split(/\s+/).filter(Boolean);
  if (!words.length) return rows;
  return rows.filter(row => {
    const haystack = tennisSearchText([
      row.tour, row.tournoi, row.match, row.joueur1, row.joueur2, row.favori,
      row.surface, row.cycle1, row.cycle2, row.decision, row.impact_contexte, row.concordance, row.concordance_detail,
    ].join(" "));
    return words.every(word => haystack.includes(word));
  });
}
function tennisPendingFinals(rows) {
  const pending = filteredTennisRows(rows || []);
  if (!pending.length) return "";
  return `<section class="pending-finals"><h3>Finales confirmees - cotes en attente <span>${pending.length}</span></h3>
    <div class="pending-note">Ces confrontations sont confirmees par ESPN. Elles rejoindront automatiquement le tableau decisionnel des que les cotes correspondantes seront publiees.</div>
    <div class="pending-wrap"><table class="pending-table"><thead><tr><th>Circuit</th><th>Heure</th><th>Tournoi</th><th>Match</th><th>Statut</th></tr></thead><tbody>${pending.map(row => {
      const key = tennisRowKey(row);
      const expanded = _expandedTennisMatch === key;
      return `<tr><td><span class="tourpill ${esc(row.tour || "")}">${esc(row.tour || "-")}</span></td>
        <td><b>${esc(row.heure || "-")}</b><div class="tsub">${esc(row.surface || "")}</div></td>
        <td><b>${esc(row.tournoi || "-")}</b><div class="tsub">${esc(row.round || "Final")}</div></td>
        <td><div class="tmatch">${esc(row.match || "-")}</div><button id="props-btn-${key}" class="prop-toggle" onclick="toggleTennisProps('${key}')" aria-expanded="${expanded}" aria-controls="props-${key}" title="Afficher les statistiques detaillees"><span aria-hidden="true">${expanded ? "-" : "+"}</span><b>Stats</b></button></td>
        <td><span class="pending-pill">En attente de cote</span><small>Probabilites marche non calculees</small></td></tr>
        <tr id="props-${key}" class="tprop-row ${expanded ? "" : "hidden"}"><td colspan="5">${tennisPropsPanel(row)}</td></tr>`;
    }).join("")}</tbody></table></div></section>`;
}
function tennisMatchesResults(allRows) {
  const rows = filteredTennisRows(allRows);
  const count = rows.length === allRows.length ? `${rows.length} matchs` : `${rows.length} sur ${allRows.length} matchs`;
  return `<h3>Lecture des matchs <span>${count}</span></h3>${tennisTable(rows)}${tennisPendingFinals((_tennisData || {}).pending_odds || [])}`;
}
function setTennisSearch(value) {
  _tennisQuery = value;
  const results = $("#tennisMatchesResults");
  if (results) results.innerHTML = tennisMatchesResults(tennisAllRows());
  const clear = $("#tennisSearchClear");
  if (clear) clear.classList.toggle("hidden", !_tennisQuery);
}
function clearTennisSearch() {
  _tennisQuery = "";
  renderTennis();
  const input = $("#tennisSearch");
  if (input) input.focus();
}
function renderTennisMatches() {
  const rows = tennisAllRows();
  return `<div class="tensection">
    <div class="tencontrols"><div class="tensearch">
      <input id="tennisSearch" type="search" value="${esc(_tennisQuery)}" placeholder="Joueur, tournoi, circuit, surface..." aria-label="Rechercher dans les matchs" oninput="setTennisSearch(this.value)">
      <button id="tennisSearchClear" class="${_tennisQuery ? "" : "hidden"}" onclick="clearTennisSearch()" title="Effacer la recherche" aria-label="Effacer la recherche">x</button>
    </div></div>
    <div id="tennisMatchesResults">${tennisMatchesResults(rows)}</div>
  </div>`;
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

