/* Ligue 1 PRONO — frontend (auth JWT + tableau de probas + actu) */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const TOKEN_KEY = "prono_token";
const token = () => localStorage.getItem(TOKEN_KEY) || "";

function downloadTextFile(filename, content, mime = "text/plain") {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
function safeFilenamePart(value, fallback = "export") {
  return String(value || fallback).normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase() || fallback;
}
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
function tennisAnchorCell(row, key) {
  const anchors = row.derived_anchors;
  const cell = anchors && anchors[key];
  if (!cell) return pctTennis(row[key]);
  const eloReco = anchors.anchor_recommended === "elo";
  let html = `<b>${pctTennis(cell.value_ref)}</b>`;
  // Fourchette affichee seulement en cas de vrai desaccord (sinon valeur unique, pas de bruit)
  if (cell.value_elo !== null && cell.value_elo !== undefined && cell.single === false) {
    const badge = eloReco ? `<span class="anchor-badge">Elo</span>` : "";
    const tip = `Cotes ${cell.value_market}% | Elo ${cell.value_elo}% | ecart ${cell.spread} pts (${anchors.calibration_flag || "-"})`;
    html += `<div class="anchor-range${eloReco ? " elo" : ""}" title="${esc(tip)}">${cell.range_min}–${cell.range_max}%${badge}</div>`;
  }
  return html;
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
const TENNIS_LEXICON_SECTIONS = [
  { title: "Decision et marche", intro: "Ces indicateurs servent a lire le match sans chercher a battre le marche. Le marche devigotte reste le socle; le reste qualifie la prudence, la coherence et les angles a verifier.", items: [
    { name: "Marche", provides: "Probabilite implicite du favori apres retrait de la marge bookmaker.", source: "Flux de cotes prematch disponibles dans le backend PRONO.", calculation: "Les cotes joueur 1 / joueur 2 sont converties en probabilites implicites, puis normalisees pour retirer l'overround. Si une cote manque, le match ne rentre pas dans le tableau principal cote." },
    { name: "Favori", provides: "Joueur retenu comme reference de lecture pour la ligne du match.", source: "Consensus du marche et moteur de lecture PRONO.", calculation: "Le favori correspond au cote le plus faible / probabilite marche la plus haute. Les colonnes de probabilite, fourchette et ecart Elo se lisent ensuite par rapport a ce favori." },
    { name: "Lecture", provides: "Statut qualitatif: favorable, vigilance, neutre ou donnees insuffisantes.", source: "Marche, Elo, forme, fatigue, recuperation et qualite de donnees.", calculation: "Le moteur compare le favori marche aux contrepoints sportifs. Une lecture favorable peut coexister avec une vigilance forte si le marche reste clair mais que plusieurs facteurs de risque augmentent l'incertitude." },
    { name: "Fourchette", provides: "Zone de probabilite raisonnable autour de la lecture, plutot qu'un chiffre unique trop precis.", source: "Probabilite marche, qualite de donnees, coherence Elo/forme et risques contexte.", calculation: "Plus les donnees sont solides et concordantes, plus la fourchette est resserree. Fatigue, H2H sensible, manque d'historique ou conflit Elo/marche l'elargissent." },
    { name: "Concordance", provides: "Accord qualitatif entre marche, Elo, forme recente et qualite des donnees.", source: "Moteur coach PRONO.", calculation: "Le signal ne modifie pas la proba marche. Il classe l'accord: concordance forte, Elo renforce, forme contraire, conflit fort, marche seul ou donnees faibles." },
    { name: "Calibration historique du statut", provides: "Compare les statuts decision x concordance passes au resultat reel du favori.", source: "Snapshots prematch PRONO stockes dans decision_history.sqlite3, rapproches aux resultats finaux.", calculation: "Pour les statuts identiques, calcule n, taux de victoire favori, proba marche moyenne, delta, IC Wilson 95%, Brier marche/Elo et ROI. Non concluant si n < 50 ou si l'intervalle du delta contient zero." },
  ] },
  { title: "Forme et fatigue", intro: "La forme est volontairement descriptive. Elle aide a comprendre le moment sportif du joueur, mais elle n'est pas une promesse de victoire.", items: [
    { name: "Forme", provides: "Etat du cycle joueur: pic probable, montee, plateau, alerte forme ou sous-rythme.", source: "Historique match par match local, controle de fraicheur SportScore quand la donnee locale est ancienne, contexte du tournoi en cours.", calculation: "Score borne entre -35 et +30 points: activite sur 90 jours, date du dernier match, serie, momentum 90j et taux de victoires. Le label vient du score long: pic probable >= +16, montee >= +7, alerte <= -7, sous-rythme <= -18." },
    { name: "Momentum", provides: "Direction recente du niveau de resultats.", source: "Historique local des resultats recents du joueur.", calculation: "Signal positif quand le momentum 90j est >= +8, fort a partir de +25. Signal negatif quand il passe sous -20, ou neutre/negatif sur faible volume." },
    { name: "Serie", provides: "Enchainement de victoires ou defaites recentes.", source: "Historique local match par match.", calculation: "+2 ou plus ajoute un signal positif; +3 ou plus est fort. -2 ou moins ajoute un risque; -1 est penalise surtout quand le volume 90j est faible." },
    { name: "Charge tournoi", provides: "Fatigue liee au parcours deja joue dans le tournoi courant.", source: "Tableau et matchs deja termines du tournoi courant.", calculation: "Tours gagnes, sets laches, jeux joues, duree estimee, tie-breaks, matchs decisifs, matchs sur 14 jours et jours de repos. Charge lourde si environ 65 jeux ou 150 minutes, ou plusieurs matchs decisifs." },
    { name: "Recuperation", provides: "Risque d'enchainement ou de rupture de rythme.", source: "Date du dernier match officiel et contexte du tournoi.", calculation: "Penalite si le joueur enchaine sans repos; penalite aussi si l'inactivite est longue. Une base locale ancienne est verifiee avec SportScore quand disponible." },
  ] },
  { title: "Elo et niveau", intro: "L'Elo est un contrepoint de niveau. Il sert surtout a savoir si le marche est aligne avec l'historique sportif.", items: [
    { name: "Elo surface", provides: "Probabilite calculee avec l'historique sur la surface du jour.", source: "Fichiers Elo locaux ATP/WTA rapproches par nom joueur.", calculation: "Les points Elo surface des deux joueurs sont transformes en probabilite via une courbe logistique. Indisponible si un joueur n'est pas rapproche ou si l'historique est insuffisant." },
    { name: "Elo global", provides: "Probabilite de niveau general toutes surfaces.", source: "Fichiers Elo locaux ATP/WTA rapproches par nom joueur.", calculation: "Meme transformation que l'Elo surface, mais sur le niveau global. Utile quand la surface manque ou quand le profil surface est trop court." },
    { name: "Lecture Elo", provides: "Ecart entre le marche et l'Elo de reference pour le favori.", source: "Probabilite marche devigotte + Elo surface si disponible, sinon Elo global.", calculation: "Ecart = proba Elo - proba marche du favori. Negatif: Elo plus prudent que le marche. Positif: Elo plus optimiste. Proche de zero: marche et Elo alignes." },
  ] },
  { title: "Stats joueurs et marches secondaires", intro: "Ces chiffres ouvrent des angles de lecture: aces, doubles fautes, breaks, tenue de service, tie-break. Ils ne remplacent pas les lignes reelles du bookmaker.", items: [
    { name: "Aces joueur", provides: "Projection d'aces attendus et probabilites de depasser certains seuils.", source: "Historique brut match par match: TennisMyLife ATP, archive locale, Jeff Sackmann WTA selon disponibilite.", calculation: "Modele joueur + adversaire + surface. Il utilise les aces, jeux de service et echantillons surface/total. Les bornes [min-max] representent un intervalle probable a 80%." },
    { name: "Doubles fautes", provides: "Projection de doubles fautes et seuils de depassement.", source: "Memes donnees brutes que les aces quand elles sont fiables.", calculation: "Les lignes aberrantes sont rejetees: valeurs negatives, stats de break impossibles, volumes incoherents. Le moteur ajuste par surface et adversaire." },
    { name: "Tenue de service", provides: "Probabilite estimee de conserver son service.", source: "Jeux de service, breaks concades, niveau retour adverse et surface.", calculation: "Taux joueur historique pondere par la surface et le profil de retour adverse. Plus l'echantillon est faible, plus la confiance descend." },
    { name: "Breaks attendus", provides: "Nombre moyen de breaks que le joueur peut realiser et probabilite d'au moins un break.", source: "Jeux de retour, balles de break et tenue de service adverse.", calculation: "Croisement entre capacite de retour du joueur et vulnerabilite au service de l'adversaire, avec correction surface." },
    { name: "Tie-break", provides: "Probabilite qu'au moins un set aille au tie-break.", source: "Profils de service/retour des deux joueurs et calibration 2021-2025.", calculation: "Plus les deux joueurs tiennent souvent leur service, plus le risque de tie-break monte. Le signal est valide hors echantillon quand la calibration 2025 bat la reference simple." },
    { name: "Validation 2025", provides: "Controle de robustesse hors echantillon des sous-modeles.", source: "Backtest local sur saison 2025, hors donnees de calibration 2021-2024.", calculation: "Comparaison Brier du modele contre une reference simple. 'Valide' signifie que le modele est meilleur sur l'echantillon teste; sinon le signal reste affiche mais a lire avec prudence." },
  ] },
  { title: "Sources et limites", intro: "Le tableau est une aide a la decision. Il doit rendre les angles lisibles, pas donner une certitude artificielle.", items: [
    { name: "H2H", provides: "Historique des confrontations directes entre les deux joueurs.", source: "Historique local ATP/WTA, enrichi par le contexte tournoi quand disponible.", calculation: "Compte les victoires directes et signale les confrontations pertinentes, notamment meme surface ou meme adversaire la saison precedente." },
    { name: "Confrontations a venir", provides: "Liste des matchs futurs ou live conserves dans le tableau.", source: "Flux cotes + sources de calendrier/tableaux ESPN ou SportScore selon disponibilite.", calculation: "Les matchs passes sont masques. Les matchs live peuvent rester visibles si le flux les marque encore live; les finales sans cote vont dans la section cotes en attente." },
    { name: "Qualite", provides: "Fiabilite globale de la lecture.", source: "Couverture des cotes, Elo, historique recent, stats joueurs et contexte tournoi.", calculation: "Qualite elevee si marche, Elo, forme et stats joueurs sont disponibles et coherents. Qualite faible si trop de briques manquent ou si les donnees sont anciennes." },
    { name: "Limite majeure", provides: "Ce que l'outil ne garantit pas.", source: "Nature des donnees sportives et des marches de paris.", calculation: "Aucun indicateur ne garantit un gain. Une bonne lecture peut perdre; l'objectif est de mieux comprendre le risque et d'eviter les tickets pris a l'aveugle." },
  ] },
];
TENNIS_LEXICON_SECTIONS.unshift({ title: "Colonnes du tableau principal", intro: "Ces entrees correspondent aux colonnes visibles dans Lecture matchs. L'ordre suit le tableau pour faciliter la lecture.", items: [
  { name: "Circuit", provides: "Indique ATP ou WTA.", source: "Flux de matchs et classement du tournoi.", calculation: "Le circuit est associe a chaque confrontation au moment de la fusion calendrier/cotes." },
  { name: "Heure", provides: "Horaire lisible du match et statut live si detecte.", source: "Flux calendrier/tableaux et flux cotes.", calculation: "Le backend masque les matchs termines, conserve les futurs et peut garder le live quand la source le signale encore en cours." },
  { name: "Tournoi", provides: "Nom de l'epreuve concernee.", source: "Calendrier/tableau tournoi et flux cotes.", calculation: "Les noms sont normalises pour rapprocher les confrontations entre sources." },
  { name: "Match", provides: "Affiche la confrontation, les signaux rapides, H2H, source et preuve textuelle.", source: "Fusion joueur/cotes/calendrier/historique coach.", calculation: "Le moteur agrege les deux joueurs, le H2H, les alertes, la source de confrontation et les preuves de forme/fatigue." },
  { name: "Forme", provides: "Resume le cycle de chaque joueur.", source: "Moteur coach PRONO.", calculation: "Affiche le label du score de forme long pour joueur 1 et joueur 2: pic probable, montee, plateau, alerte forme ou sous-rythme." },
  { name: "Lecture", provides: "Decision qualitative et favori retenu, avec fourchette et fiabilite.", source: "Marche, Elo, forme, fatigue, qualite de donnees.", calculation: "Synthese prudente: le statut peut etre favorable tout en gardant une vigilance si les risques contextuels sont lourds." },
  { name: "Concordance", provides: "Decrit si marche, Elo et forme racontent la meme histoire.", source: "Moteur coach PRONO.", calculation: "Compare le favori du marche aux probabilites Elo et au delta de forme des deux joueurs. Ne modifie pas les probabilites." },
  { name: "Marche", provides: "Probabilite marche devigotte du favori.", source: "Cotes bookmaker disponibles.", calculation: "Probabilites implicites des deux cotes, renormalisees pour retirer la marge." },
  { name: "Elo surface", provides: "Probabilite Elo sur la surface du jour.", source: "Base Elo locale par surface.", calculation: "Difference Elo surface convertie en probabilite. Indispo si rapprochement ou echantillon insuffisant." },
  { name: "Elo global", provides: "Probabilite Elo toutes surfaces.", source: "Base Elo locale globale.", calculation: "Difference Elo globale convertie en probabilite. Sert aussi de secours quand la surface manque." },
  { name: "Lecture Elo", provides: "Sens et amplitude de l'ecart Elo vs marche.", source: "Marche devigotte + Elo de reference.", calculation: "Proba Elo moins proba marche. Negatif = Elo plus prudent; positif = Elo plus optimiste; proche de zero = aligne." },
  { name: "Contexte", provides: "Impact relatif des facteurs non-marche: fatigue, parcours, recuperation, adversaire.", source: "Moteur coach et contexte tournoi courant.", calculation: "Classe en avantage relatif, desavantage relatif ou neutre selon les facteurs accumules autour du favori et de l'adversaire." },
  { name: "Cote", provides: "Cote decimale du favori retenu.", source: "Flux de cotes.", calculation: "Cote brute affichee pour donner le prix du marche associe a la probabilite devigotte." },
  { name: "Stats marches", provides: "Angles secondaires: total jeux, handicap, tie-break, aces ou autres signaux disponibles.", source: "Modeles secondaires calibres et stats joueurs.", calculation: "Chaque pastille affiche un pick, une probabilite et une confiance. Ce ne sont pas forcement les lignes exactes du bookmaker." },
  { name: "Fav 2-0", provides: "Probabilite que le favori gagne en deux sets en best-of-3.", source: "Double ancrage: cotes devigottees et niveau Elo.", calculation: "Calcule sur les deux ancres (cotes et Elo) et restitue en fourchette. La valeur affichee suit l'ancre la mieux calibree historiquement pour ce type de match; sous-titre viole = avis Elo recommande." },
  { name: "Fav 2-1", provides: "Probabilite que le favori gagne en trois sets.", source: "Double ancrage: cotes devigottees et niveau Elo.", calculation: "Meme distribution 2-0 / 2-1 / 3 sets, calculee deux fois (cotes et Elo). La fourchette n'apparait qu'en cas de vrai desaccord (>= 3 pts)." },
  { name: "3 sets", provides: "Probabilite que le match aille en trois sets.", source: "Double ancrage: cotes devigottees et niveau Elo.", calculation: "Augmente quand les joueurs sont proches. Sur un conflit fort (marche vs Elo), l'avis Elo remonte souvent cette probabilite; la valeur de reference suit l'ancre la mieux calibree." },
] });
TENNIS_LEXICON_SECTIONS.push({ title: "Details Stats+", intro: "Ces indicateurs apparaissent dans le panneau detaille ouvert avec le bouton Stats+. Ils expliquent le niveau, la taille d'echantillon et les marches statistiques joueur.", items: [
  { name: "Stats+", provides: "Panneau detaille joueur contre joueur.", source: "Moteur props PRONO, bases Elo et historiques bruts.", calculation: "Combine stats joueur, adversaire et surface. Il affiche les signaux disponibles sans forcer une conclusion si l'echantillon est trop court." },
  { name: "Echantillon surface", provides: "Nombre de matchs bruts disponibles sur la surface du jour pour le joueur.", source: "Historique match par match enrichi.", calculation: "Plus il est eleve, plus les projections aces/service/breaks sont stables." },
  { name: "Echantillon total", provides: "Nombre total de matchs bruts disponibles pour le joueur.", source: "Historique match par match enrichi.", calculation: "Sert de secours quand la surface du jour est courte et pour estimer la confiance globale." },
  { name: "Confiance stats", provides: "Qualite de l'echantillon des statistiques joueur.", source: "Moteur props PRONO.", calculation: "Elevee, moyenne ou faible selon volume surface, volume total, fraicheur et coherence des lignes brutes." },
  { name: "Source stats joueur", provides: "Origine des stats brutes utilisees.", source: "TennisMyLife live + archives, archives locales, Jeff Sackmann WTA selon cas.", calculation: "Le backend privilegie l'archive locale; pour certains ATP peu couverts, il complete via TennisMyLife live avec cache serveur." },
  { name: "Elo joueur Stats+", provides: "Points Elo globaux et surface de chaque joueur.", source: "Base Elo locale.", calculation: "Affiche le niveau absolu, pas seulement la probabilite du favori. Utile pour voir l'ecart de classe entre joueurs." },
  { name: "Statut Elo", provides: "Indique si le profil Elo est etabli ou exploratoire.", source: "Base Elo et nombre de matchs rapproches.", calculation: "Exploratoire quand l'historique est court ou incertain; etabli quand le volume rend le niveau plus fiable." },
  { name: "Aces attendus", provides: "Nombre moyen d'aces projetes pour le joueur.", source: "Aces historiques, jeux de service, surface et retour adverse.", calculation: "Moyenne ajustee par surface et adversaire. A lire comme centre de gravite, pas comme prediction exacte." },
  { name: "Intervalle 80%", provides: "Zone probable basse-haute autour de la projection.", source: "Distribution historique joueur ajustee.", calculation: "Environ 80% des scenarios modelises tombent dans cette plage; plus elle est large, plus le marche est volatil." },
  { name: "Plus de X", provides: "Probabilite de depasser un seuil statistique donne.", source: "Distribution joueur issue du modele props.", calculation: "Exemple: O4.5 44% signifie que le modele donne 44% de chances de finir a 5 aces ou plus." },
  { name: "Doubles fautes attendues", provides: "Nombre moyen de doubles fautes projetees.", source: "Doubles fautes historiques et pression retour adverse.", calculation: "Ajuste par surface, niveau de retour et profil joueur. Les lignes aberrantes sont rejetees avant calcul." },
  { name: "Risque d'etre breake", provides: "Probabilite que le joueur perde au moins un jeu de service.", source: "Tenue de service du joueur + capacite de retour adverse.", calculation: "Plus la tenue de service est basse et l'adversaire fort en retour, plus le risque monte." },
  { name: "Au moins un break", provides: "Probabilite que le joueur realise au moins un break.", source: "Profil retour joueur + vulnerabilite service adverse.", calculation: "Associe a Breaks attendus pour lire a la fois la moyenne et la chance minimale de break." },
] });
function tennisLexiconMarkdown() {
  const lines = ["# Lexique Tennis PRONO", "", "Export genere le " + new Date().toISOString(), "", "Le marche devigotte reste la reference. Les indicateurs sportifs servent a qualifier la decision, la vigilance et les angles a verifier.", ""];
  TENNIS_LEXICON_SECTIONS.forEach(section => {
    lines.push("## " + section.title, "", section.intro, "");
    section.items.forEach(item => {
      lines.push("### " + item.name, "", "- Ce que ca fournit : " + item.provides, "- Source : " + item.source, "- Calcul : " + item.calculation, "");
    });
  });
  return lines.join("\n");
}
function exportTennisLexiconMarkdown() {
  downloadTextFile("lexique-tennis-prono.md", tennisLexiconMarkdown(), "text/markdown");
}
function renderTennisLexicon() {
  const sections = TENNIS_LEXICON_SECTIONS.map(section => `<section class="lex-section"><div><h3>${esc(section.title)}</h3><p>${esc(section.intro)}</p></div><div class="lex-grid">${section.items.map(item => `<article class="lex-card"><h4>${esc(item.name)}</h4><dl><dt>Ce que ca fournit</dt><dd>${esc(item.provides)}</dd><dt>Source</dt><dd>${esc(item.source)}</dd><dt>Calcul</dt><dd>${esc(item.calculation)}</dd></dl></article>`).join("")}</div></section>`).join("");
  return `<div class="tensection lex-page"><div class="lex-top"><div><h3>Lexique des indicateurs <span>${TENNIS_LEXICON_SECTIONS.reduce((n, s) => n + s.items.length, 0)} definitions</span></h3><p>Une page de reference pour comprendre ce que chaque signal apporte, d'ou vient l'information et comment elle est transformee.</p></div><button class="tenexport" onclick="exportTennisLexiconMarkdown()">Exporter MD</button></div>${sections}</div>`;
}
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
function tennisDecisionCalibration(row) {
  const cal = row.decision_calibration;
  if (!cal) return "";
  const cls = cal.conclusion === "favori_surcote_historique" ? "warn" : cal.conclusion === "favori_souscote_historique" ? "ok" : "neutral";
  return `<small class="tcal ${esc(cls)}" title="${esc(cal.detail || "Calibration historique non disponible")}">${esc(cal.detail || cal.label || "Calibration historique non concluant")}</small>`;
}
function tennisDecision(row) {
  const range = row.fourchette_min == null || row.fourchette_max == null ? "-" : `${row.fourchette_min}-${row.fourchette_max}%`;
  return `<div class="tdecision ${esc(row.decision_level || "neutral")}">
    <span>${esc(row.decision || "Neutre")}</span>
    <b>${esc(row.favori || "-")}</b>
    <small>Fourchette ${esc(range)} | fiabilite ${esc(row.qualite || "faible")}</small>${tennisDecisionCalibration(row)}
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
function tennisLevel(level) {
  if (!level || (level.elo_global == null && level.elo_surface == null)) return `<div class="prop-level unavailable"><b>Elo indisponible</b><span>Historique insuffisant ou joueur non rapproche</span></div>`;
  const sample = Number(level.sample || 0);
  return `<div class="prop-level" title="${esc(level.source || "agregat Elo local")}">
    <span><small>Elo global</small><b>${level.elo_global == null ? "-" : esc(Math.round(level.elo_global))}</b></span>
    <span><small>Elo ${esc(rowSurfaceLabel(level.surface))}</small><b>${level.elo_surface == null ? "-" : esc(Math.round(level.elo_surface))}</b></span>
    <span><small>Echantillon Elo</small><b>${esc(sample)} match${sample > 1 ? "s" : ""}</b></span>
    <span><small>Statut</small><b>${level.established ? "Etabli" : "Exploratoire"}</b></span>
  </div>`;
}
function rowSurfaceLabel(surface) {
  return ({clay: "terre", grass: "gazon", hard: "dur"})[surface] || "surface";
}
function tennisPropsPlayer(player, level) {
  const name = (player && player.player) || (level && level.player) || "Joueur";
  const sampleLabel = player ? `${esc(player.confidence || "faible")} | ${esc(player.sample_surface || 0)} surface, ${esc(player.sample_total || 0)} total${player.source ? ` | ${esc(player.source)}` : ""}` : "statistiques de service indisponibles";
  const header = `<div class="prop-player-head"><h5>${esc(name)}</h5><span>${sampleLabel}</span></div>${tennisLevel(level)}`;
  if (!player) return `<section class="tprop-player unavailable">${header}<div class="prop-data-missing"><b>Aces, service et breaks non calcules</b><span>Aucun historique brut match par match suffisamment fiable n'a ete retrouve pour ce joueur.</span></div></section>`;
  const aceRange = player.aces_interval || [];
  const dfRange = player.double_faults_interval || [];
  return `<section class="tprop-player">
    ${header}
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
    <div class="prop-panel-head"><div><b>Niveau, service et retour</b><span>${esc(row.surface || props.surface || "Surface inconnue")} | modele joueur + adversaire + surface</span></div><div><b>${pctTennis(props.tiebreak_probability)}</b><span>Au moins un tie-break</span></div></div>
    <div class="prop-players">${props.players.map((player, index) => tennisPropsPlayer(player, (row.levels || [])[index])).join("")}</div>
    ${tennisValidation(props)}
    <p>Seuils statistiques issus de l'historique match par match. Ils ne representent pas les lignes actuellement proposees par un bookmaker.</p>
  </div>`;
}
function tennisTable(rows) {
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
      <td class="n">${tennisAnchorCell(row, "p20")}</td>
      <td class="n">${tennisAnchorCell(row, "p21")}</td>
      <td class="n">${tennisAnchorCell(row, "p3")}</td>
    </tr><tr id="props-${key}" class="tprop-row ${expanded ? "" : "hidden"}"><td colspan="17">${tennisPropsPanel(row)}</td></tr>`;
  }).join("")}</tbody></table></div>`;
}
function tennisModeBar() {
  return `<div class="tenmode">
    <button class="${_tennisMode === "matches" ? "active" : ""}" onclick="setTennisMode('matches')">Lecture matchs</button>
    <button class="${_tennisMode === "brackets" ? "active" : ""}" onclick="setTennisMode('brackets')">Tableaux</button>
    <button class="${_tennisMode === "lexicon" ? "active" : ""}" onclick="setTennisMode('lexicon')">Lexique</button>
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
  const body = _tennisMode === "brackets" ? renderTennisBrackets() : _tennisMode === "lexicon" ? renderTennisLexicon() : renderTennisMatches();
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
function cleanTennisExportValue(value) {
  if (value === undefined || typeof value === "function") return undefined;
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(cleanTennisExportValue).filter(v => v !== undefined);
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cleanTennisExportValue(item)]).filter(([, item]) => item !== undefined));
}
function tennisExportPlayer(row, index) {
  const props = row.props && row.props.players ? row.props.players[index] : null;
  const level = row.levels && row.levels[index] ? row.levels[index] : null;
  return cleanTennisExportValue({
    name: index === 0 ? row.joueur1 : row.joueur2,
    form_label: index === 0 ? row.cycle1 : row.cycle2,
    fatigue: index === 0 ? row.fatigue1 : row.fatigue2,
    elo: level,
    advanced_stats: props,
  });
}
function tennisExportRow(row) {
  return cleanTennisExportValue({
    identity: {
      circuit: row.tour,
      kickoff: row.heure || row.kickoff,
      kickoff_raw: row.kickoff,
      tournament: row.tournoi,
      round: row.round,
      surface: row.surface,
      match: row.match,
      source: row.match_source,
      live: Boolean(row.live),
    },
    players: [tennisExportPlayer(row, 0), tennisExportPlayer(row, 1)],
    h2h: { summary: row.h2h, alert: row.alerte },
    lecture: {
      favorite: row.favori,
      decision: row.decision,
      decision_level: row.decision_level,
      decision_detail: row.decision_detail,
      quality: row.qualite,
      range_min: row.fourchette_min,
      range_max: row.fourchette_max,
      concordance: row.concordance,
      concordance_level: row.concordance_level,
      concordance_detail: row.concordance_detail,
      evidence: row.preuves,
    },
    probabilities: {
      market: row.proba_marche,
      elo_surface: row.proba_elo_surface,
      elo_global: row.proba_elo_global,
      favorite_2_0: row.p20,
      favorite_2_1: row.p21,
      three_sets: row.p3,
      derived_anchors: row.derived_anchors,
      odds: row.cote,
      odds_status: row.odds_status,
    },
    elo: {
      reference: row.elo_reference,
      gap_vs_market_points: row.ecart_elo,
      detail: row.elo_detail,
    },
    context: {
      impact: row.impact_contexte,
      favorite_cycle: row.cycle_favori,
      favorite_fatigue: row.fatigue_favori,
      opponent_cycle: row.cycle_adversaire,
      opponent_fatigue: row.fatigue_adversaire,
    },
    secondary_markets: row.markets || [],
    advanced_stats: row.props || null,
    raw: row,
  });
}
function currentTennisExportRows() {
  return sortedTennisRows(filteredTennisRows(tennisAllRows()));
}
function currentTennisPendingRows() {
  return sortedTennisRows(filteredTennisRows((_tennisData || {}).pending_odds || []));
}
function exportTennisMatchesJson() {
  const rows = currentTennisExportRows();
  const pending = currentTennisPendingRows();
  const filenameSuffix = _tennisQuery ? safeFilenamePart(_tennisQuery, "filtre") : "tous-matchs";
  const payload = {
    export_type: "tennis_matches_reading",
    exported_at: new Date().toISOString(),
    app_source: "PRONO Tennis",
    filter: _tennisQuery || null,
    sort: _tennisSort,
    columns: TENNIS_SORT_COLUMNS.map(([key, label]) => ({ key, label })),
    counts: { matches: rows.length, pending_odds: pending.length },
    matches: rows.map(tennisExportRow),
    pending_odds: pending.map(tennisExportRow),
    note: "Export base sur les lignes actuellement visibles apres recherche et tri. Outil de lecture, pas de garantie de gain.",
  };
  downloadTextFile(`lecture-tennis-${filenameSuffix}-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(payload, null, 2), "application/json");
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
  const exportBtn = $("#tennisExportJsonBtn");
  if (exportBtn) exportBtn.textContent = `Exporter JSON (${currentTennisExportRows().length + currentTennisPendingRows().length})`;
}
function clearTennisSearch() {
  _tennisQuery = "";
  renderTennis();
  const input = $("#tennisSearch");
  if (input) input.focus();
}
function renderTennisMatches() {
  const rows = tennisAllRows();
  const visible = filteredTennisRows(rows).length;
  const pending = currentTennisPendingRows().length;
  return `<div class="tensection">
    <div class="tencontrols"><div class="tensearch">
      <input id="tennisSearch" type="search" value="${esc(_tennisQuery)}" placeholder="Joueur, tournoi, circuit, surface..." aria-label="Rechercher dans les matchs" oninput="setTennisSearch(this.value)">
      <button id="tennisSearchClear" class="${_tennisQuery ? "" : "hidden"}" onclick="clearTennisSearch()" title="Effacer la recherche" aria-label="Effacer la recherche">x</button>
    </div><button id="tennisExportJsonBtn" class="tenexport" onclick="exportTennisMatchesJson()" title="Exporter les lignes visibles apres recherche et tri">Exporter JSON (${esc(visible + pending)})</button></div>
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

