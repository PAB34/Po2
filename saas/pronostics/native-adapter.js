const PRONOSTICS_API = "/api/pronostics";
const PRONOSTICS_TOKEN_KEY = "pronostics_access_token";

function nativeToken() {
  return localStorage.getItem(PRONOSTICS_TOKEN_KEY) || "";
}

function nativeHeaders(authenticated) {
  const headers = { "Content-Type": "application/json" };
  if (authenticated && nativeToken()) headers.Authorization = `Bearer ${nativeToken()}`;
  return headers;
}

async function nativeRequest(path, options = {}) {
  const response = await fetch(`${PRONOSTICS_API}${path}`, options);
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Une erreur est survenue.");
  return body;
}

function nativeMatch(match) {
  return {
    id: match.id, group: match.group, team1: match.team1, team2: match.team2,
    date: match.match_at, stadium: match.stadium, locked: match.locked,
    real1: match.real_score1, real2: match.real_score2,
    prono1: match.prediction_score1, prono2: match.prediction_score2,
    fifaRank1: match.fifa_rank1, fifaRank2: match.fifa_rank2,
  };
}

function nativeRanking(row) {
  return {
    rang: row.rank, pseudo: row.pseudo, service: row.service, points: row.points,
    exacts: row.exact_scores, bonsResultats: row.good_results, saisis: row.predictions_count,
  };
}

async function nativePlayerData(player) {
  const [matches, ranking] = await Promise.all([
    nativeRequest("/matches", { headers: nativeHeaders(true) }),
    nativeRequest("/ranking"),
  ]);
  const adaptedMatches = matches.map(nativeMatch);
  return {
    player, matches: adaptedMatches,
    done: adaptedMatches.filter((match) => match.prono1 != null && match.prono2 != null).length,
    total: adaptedMatches.length, ranking: ranking.map(nativeRanking),
  };
}

async function nativeCall(method, payload) {
  if (method === "getPlayerData") {
    const response = await nativeRequest("/login", {
      method: "POST", headers: nativeHeaders(false),
      body: JSON.stringify({ email: payload.email, password: document.getElementById("loginPassword").value }),
    });
    localStorage.setItem(PRONOSTICS_TOKEN_KEY, response.access_token);
    document.getElementById("loginPassword").value = "";
    return nativePlayerData(response.player);
  }
  if (method === "loginOrRegister") {
    const response = await nativeRequest("/register", {
      method: "POST", headers: nativeHeaders(false),
      body: JSON.stringify({ ...payload, password: document.getElementById("regPassword").value }),
    });
    localStorage.setItem(PRONOSTICS_TOKEN_KEY, response.access_token);
    document.getElementById("regPassword").value = "";
    return nativePlayerData(response.player);
  }
  if (method === "savePredictions") {
    const predictions = payload.predictions.map((row) => ({
      match_id: row.idMatch, score1: row.prono1, score2: row.prono2,
    }));
    await nativeRequest("/predictions", {
      method: "PUT", headers: nativeHeaders(true), body: JSON.stringify({ predictions }),
    });
    const data = await nativePlayerData(state.player);
    return { ok: true, saved: predictions.length, data, ranking: data.ranking };
  }
  if (method === "getRanking") {
    return (await nativeRequest("/ranking")).map(nativeRanking);
  }
  if (method === "getParticipantsPublic") {
    return (await nativeRequest("/participants")).map((row) => ({
      pseudo: row.pseudo, service: row.service, pronosticsSaisis: row.predictions_count,
      points: row.points, exacts: row.exact_scores, bonsResultats: row.good_results,
    }));
  }
  if (method === "updateProfile") {
    const player = await nativeRequest("/me", {
      method: "PATCH", headers: nativeHeaders(true),
      body: JSON.stringify({ pseudo: payload.pseudo, service: payload.service }),
    });
    return nativePlayerData(player);
  }
  throw new Error(`Méthode native inconnue : ${method}`);
}

function nativeRunner() {
  let success = () => {};
  let failure = () => {};
  const runner = {
    withSuccessHandler(callback) { success = callback; return runner; },
    withFailureHandler(callback) { failure = callback; return runner; },
  };
  for (const method of ["getPlayerData", "loginOrRegister", "savePredictions", "getRanking", "getParticipantsPublic", "updateProfile"]) {
    runner[method] = (payload) => { nativeCall(method, payload).then(success).catch(failure); };
  }
  return runner;
}

window.google = { script: {} };
Object.defineProperty(window.google.script, "run", { get: nativeRunner });
