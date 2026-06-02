const API = "/api/pronostics";
const TOKEN_KEY = "pronostics_access_token";
let mode = "login";
let player = null;
let matches = [];

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

function token() { return localStorage.getItem(TOKEN_KEY); }
function setMessage(id, text = "") { $(id).textContent = text; }
function authHeaders() { return { "Content-Type": "application/json", Authorization: `Bearer ${token()}` }; }
async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Une erreur est survenue.");
  return body;
}

function setMode(nextMode) {
  mode = nextMode;
  $("login-tab").classList.toggle("active", mode === "login");
  $("register-tab").classList.toggle("active", mode === "register");
  $("register-fields").classList.toggle("hidden", mode !== "register");
  $("pseudo").required = mode === "register";
  $("service").required = mode === "register";
  $("password").autocomplete = mode === "register" ? "new-password" : "current-password";
  setMessage("auth-message");
}

async function authenticate(event) {
  event.preventDefault();
  setMessage("auth-message");
  const payload = { email: $("email").value.trim(), password: $("password").value };
  if (mode === "register") Object.assign(payload, { pseudo: $("pseudo").value.trim(), service: $("service").value.trim() });
  try {
    const data = await request(`/${mode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    player = data.player;
    await showGame();
  } catch (error) { setMessage("auth-message", error.message); }
}

async function showGame() {
  try {
    if (!player) player = await request("/me", { headers: authHeaders() });
    $("player-name").textContent = player.pseudo;
    $("player-service").textContent = player.service;
    $("auth-screen").classList.add("hidden");
    $("game-screen").classList.remove("hidden");
    await loadMatches();
  } catch {
    logout();
  }
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  player = null;
  matches = [];
  $("game-screen").classList.add("hidden");
  $("auth-screen").classList.remove("hidden");
}

async function loadMatches() {
  matches = await request("/matches", { headers: authHeaders() });
  const groups = [...new Set(matches.map((match) => match.group))];
  $("matches").innerHTML = groups.map((group) => `<h3>Groupe ${escapeHtml(group)}</h3>${matches.filter((match) => match.group === group).map(matchCard).join("")}`).join("");
}

function matchCard(match) {
  const disabled = match.locked ? "disabled" : "";
  const date = new Date(match.match_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
  return `<article class="match"><div class="match-meta"><span>${escapeHtml(match.id)} · ${escapeHtml(date)}</span><span>${escapeHtml(match.stadium)}</span></div>
    <div class="team"><span>${escapeHtml(match.team1)}</span><input class="score" type="number" min="0" max="20" data-match="${escapeHtml(match.id)}" data-side="1" value="${match.prediction_score1 ?? ""}" ${disabled}></div>
    <div class="team"><span>${escapeHtml(match.team2)}</span><input class="score" type="number" min="0" max="20" data-match="${escapeHtml(match.id)}" data-side="2" value="${match.prediction_score2 ?? ""}" ${disabled}></div></article>`;
}

async function savePredictions() {
  const byMatch = {};
  document.querySelectorAll(".score").forEach((input) => {
    const id = input.dataset.match;
    byMatch[id] ||= { match_id: id };
    byMatch[id][`score${input.dataset.side}`] = input.value === "" ? null : Number(input.value);
  });
  const predictions = Object.values(byMatch).filter((row) => row.score1 !== null && row.score2 !== null);
  try {
    await request("/predictions", { method: "PUT", headers: authHeaders(), body: JSON.stringify({ predictions }) });
    setMessage("save-message", "Pronostics enregistrés.");
    await loadMatches();
  } catch (error) { setMessage("save-message", error.message); }
}

async function loadRanking() {
  const rows = await request("/ranking");
  $("ranking").innerHTML = rows.length ? rows.map((row) => `<div class="ranking-row"><b>#${row.rank}</b><div><strong>${escapeHtml(row.pseudo)}</strong><small>${escapeHtml(row.service)} · ${row.predictions_count} pronostics</small></div><span class="points">${row.points} pts</span></div>`).join("") : "<p>Aucun joueur inscrit.</p>";
}

document.querySelectorAll(".game-tab").forEach((button) => button.addEventListener("click", async () => {
  document.querySelectorAll(".game-tab").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  const ranking = button.dataset.view === "ranking";
  $("matches-view").classList.toggle("hidden", ranking);
  $("ranking-view").classList.toggle("hidden", !ranking);
  if (ranking) await loadRanking();
}));
$("login-tab").addEventListener("click", () => setMode("login"));
$("register-tab").addEventListener("click", () => setMode("register"));
$("auth-form").addEventListener("submit", authenticate);
$("logout").addEventListener("click", logout);
$("save").addEventListener("click", savePredictions);
$("refresh-ranking").addEventListener("click", loadRanking);
if (token()) showGame();
