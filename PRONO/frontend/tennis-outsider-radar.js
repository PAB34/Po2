/* Radar outsiders : extension isolee de la vue Tennis existante. */
let _outsiderRadarData = null;
let _outsiderRecentData = null;
let _outsiderDays = 7;
let _outsiderLoading = false;

function outsiderPct(value) {
  if (value === null || value === undefined || value === "") return "-";
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(1)}%` : "-";
}
function outsiderOdds(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(2) : "-";
}
function outsiderSigned(value) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n > 0 ? "+" : ""}${n.toFixed(1)}` : "-";
}
function outsiderScoreClass(score) {
  const n = Number(score || 0);
  return n >= 65 ? "priority" : n >= 48 ? "study" : n >= 32 ? "secondary" : "discard";
}
function outsiderReasons(item) {
  const positives = (item.reasons || []).map(reason => `<li>${esc(reason)}</li>`).join("");
  const warnings = (item.warnings || []).map(reason => `<li class="warn">${esc(reason)}</li>`).join("");
  return `<ul class="or-reasons">${positives}${warnings}</ul>`;
}
function outsiderMarkets(markets) {
  const usable = (markets || []).slice(0, 3);
  if (!usable.length) return `<span class="tmissing">Indispo</span>`;
  return `<div class="or-markets">${usable.map(m => `<span><b>${esc(m.label || m.key || "Marche")}</b>${esc(m.pick || "-")} ${m.prob == null ? "" : `<em>${esc(m.prob)}%</em>`}${m.fair_odds == null ? "" : `<i>@${esc(m.fair_odds)}</i>`}</span>`).join("")}</div>`;
}
function outsiderRadarTable(items) {
  if (!items || !items.length) return `<div class="note">Aucun outsider cote dans les affiches actuelles.</div>`;
  return `<div class="or-table-wrap"><table class="or-table"><thead><tr>
    <th>Score</th><th>Match</th><th>Cote</th><th>Marche</th><th>Elo</th><th>Ecart</th><th>Upsets 7j</th><th>Qualite</th><th>Pourquoi</th><th>Marches outsider</th>
  </tr></thead><tbody>${items.map(item => `<tr>
    <td><div class="or-score ${outsiderScoreClass(item.score)}"><b>${esc(item.score)}</b><span>${esc(item.label)}</span></div></td>
    <td><b>${esc(item.outsider || "-")}</b><span class="or-vs">vs ${esc(item.favorite || "-")}</span><small>${esc(item.tour || "")} · ${esc(item.tournament || "")} · ${esc(item.surface || "")}<br>${esc(item.time || "")}</small></td>
    <td class="n"><b>${outsiderOdds(item.outsider_odds)}</b></td>
    <td class="n">${outsiderPct(item.market_outsider_probability)}</td>
    <td class="n">${outsiderPct(item.elo_outsider_probability)}</td>
    <td class="n"><span class="or-edge ${Number(item.elo_edge_points || 0) >= 3 ? "positive" : Number(item.elo_edge_points || 0) <= -3 ? "negative" : ""}">${outsiderSigned(item.elo_edge_points)} pts</span></td>
    <td class="n">${esc(item.recent_upsets || 0)}</td>
    <td>${esc(item.quality || "faible")}</td>
    <td>${outsiderReasons(item)}</td>
    <td>${outsiderMarkets(item.markets)}</td>
  </tr>`).join("")}</tbody></table></div>`;
}
function recentOutsiderTable(items, empty) {
  if (!items || !items.length) return `<div class="note">${esc(empty)}</div>`;
  return `<div class="or-recent-grid">${items.map(item => `<article class="or-result ${item.upset ? "won" : "lost"}">
    <div><span>${esc(item.date || "-")}</span><b>${esc(item.outsider || "-")}</b><small>contre ${esc(item.favorite || "-")}</small></div>
    <div class="or-result-price"><b>${outsiderOdds(item.outsider_odds)}</b><span>${item.upset ? "Victoire outsider" : "Defaite outsider"}</span></div>
    <dl><dt>Tournoi</dt><dd>${esc(item.tour || "")} · ${esc(item.tournament || "-")}</dd><dt>Marche</dt><dd>${outsiderPct(item.market_outsider_probability)}</dd><dt>Elo</dt><dd>${outsiderPct(item.elo_outsider_probability)} (${outsiderSigned(item.elo_edge_points)} pts)</dd><dt>Lecture</dt><dd>${esc(item.concordance || item.decision || "Donnee collecteur uniquement")}</dd></dl>
  </article>`).join("")}</div>`;
}
function renderOutsiderRadar() {
  if (_outsiderLoading && !_outsiderRadarData) return `<div class="loading"><div class="spin"></div>Construction du radar outsiders...</div>`;
  if (!_outsiderRadarData) return `<div class="note">Radar indisponible. Recharge la vue.</div>`;
  const radar = _outsiderRadarData;
  const recent = _outsiderRecentData || { winners: [], losses: [] };
  const summary = radar.recent_summary || {};
  return `<div class="tensection outsider-radar">
    <div class="or-head"><div><h3>Radar outsiders <span>${esc(radar.candidate_count || 0)} candidats</span></h3><p>Indice de priorisation explicable. Ce score n'est ni une probabilite de victoire ni un ROI.</p></div>
      <div class="or-days">${[7, 14, 30].map(days => `<button class="${_outsiderDays === days ? "active" : ""}" onclick="setOutsiderDays(${days})">${days} jours</button>`).join("")}<button onclick="loadOutsiderRadar(true)">Actualiser</button></div></div>
    <div class="or-summary">
      <span><b>${esc(radar.priority_count || 0)}</b> prioritaires</span><span><b>${esc(summary.upset_count || 0)}</b> upsets recents</span><span><b>${summary.upset_rate == null ? "-" : esc(summary.upset_rate) + "%"}</b> taux upset</span><span><b>${outsiderOdds(summary.average_winning_outsider_odds)}</b> cote moyenne gagnante</span><span><b>${esc(summary.canonical_match_count || 0)}</b> matchs uniques</span>
    </div>
    <section class="or-section"><h4>Prochains matchs classes</h4>${outsiderRadarTable(radar.candidates || [])}</section>
    <section class="or-section"><h4>Outsiders gagnants sur ${esc(_outsiderDays)} jours</h4>${recentOutsiderTable(recent.winners, "Aucun outsider gagnant rapproche sur cette fenetre.")}</section>
    <details class="or-losses"><summary>Voir aussi les outsiders perdants (${(recent.losses || []).length})</summary>${recentOutsiderTable(recent.losses, "Aucune defaite outsider rapprochee.")}</details>
  </div>`;
}
async function loadOutsiderRadar(force = false) {
  if (_outsiderLoading) return;
  _outsiderLoading = true;
  if (_tennisMode === "outsiders") renderTennis();
  try {
    const refresh = force ? "&refresh=1" : "";
    [_outsiderRadarData, _outsiderRecentData] = await Promise.all([
      api(`/api/tennis/outsiders/radar?days=${_outsiderDays}${refresh}`),
      api(`/api/tennis/outsiders/recent?days=${_outsiderDays}`),
    ]);
  } catch (error) {
    _outsiderRadarData = null;
    _outsiderRecentData = null;
    const box = $("#tennisContent");
    if (box && _tennisMode === "outsiders") box.innerHTML = tennisModeBar() + `<div class="note">Erreur radar outsiders : ${esc(error.message || "indisponible")}</div>`;
  } finally {
    _outsiderLoading = false;
    if (_tennisMode === "outsiders" && _outsiderRadarData) renderTennis();
  }
}
function setOutsiderDays(days) {
  _outsiderDays = Number(days) || 7;
  _outsiderRadarData = null;
  _outsiderRecentData = null;
  loadOutsiderRadar(false);
}

// Extension des fonctions globales de la vue Tennis, sans modifier le gros fichier app.js.
tennisModeBar = function tennisModeBarWithOutsiders() {
  return `<div class="tenmode">
    <button class="${_tennisMode === "matches" ? "active" : ""}" onclick="setTennisMode('matches')">Lecture matchs</button>
    <button class="${_tennisMode === "outsiders" ? "active" : ""}" onclick="setTennisMode('outsiders')">Radar outsiders</button>
    <button class="${_tennisMode === "brackets" ? "active" : ""}" onclick="setTennisMode('brackets')">Tableaux</button>
    <button class="${_tennisMode === "lexicon" ? "active" : ""}" onclick="setTennisMode('lexicon')">Lexique</button>
  </div>`;
};
setTennisMode = function setTennisModeWithOutsiders(mode) {
  _tennisMode = mode;
  renderTennis();
  if (mode === "brackets" && !_tennisBrackets) loadTennisBrackets(false);
  if (mode === "outsiders" && !_outsiderRadarData) loadOutsiderRadar(false);
};
renderTennis = function renderTennisWithOutsiders() {
  const box = $("#tennisContent");
  if (!_tennisData) return;
  const body = _tennisMode === "brackets" ? renderTennisBrackets()
    : _tennisMode === "lexicon" ? renderTennisLexicon()
    : _tennisMode === "outsiders" ? renderOutsiderRadar()
    : renderTennisMatches();
  box.innerHTML = tennisModeBar() + body;
};
