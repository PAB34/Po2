/* ===================================================================
   ÉTAT GLOBAL
   =================================================================== */
var state = { player:null, matches:[], ranking:[], participants:[], guest:false };
var dirty = false;
var currentGroup = 'all';
var deferredPrompt = null;

/* ===================================================================
   DRAPEAUX (clé = nom d'équipe normalisé, comme côté serveur)
   =================================================================== */
var FLAGS = {
  'france':'🇫🇷','espagne':'🇪🇸','argentine':'🇦🇷','angleterre':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','portugal':'🇵🇹',
  'bresil':'🇧🇷','pays-bas':'🇳🇱','maroc':'🇲🇦','belgique':'🇧🇪','allemagne':'🇩🇪','croatie':'🇭🇷',
  'colombie':'🇨🇴','senegal':'🇸🇳','mexique':'🇲🇽','etats-unis':'🇺🇸','usa':'🇺🇸','uruguay':'🇺🇾',
  'japon':'🇯🇵','suisse':'🇨🇭','iran':'🇮🇷','turquie':'🇹🇷','equateur':'🇪🇨','autriche':'🇦🇹',
  'coree-du-sud':'🇰🇷','australie':'🇦🇺','algerie':'🇩🇿','egypte':'🇪🇬','canada':'🇨🇦','norvege':'🇳🇴',
  'panama':'🇵🇦',"cote-d'ivoire":'🇨🇮','cote-d-ivoire':'🇨🇮','suede':'🇸🇪','paraguay':'🇵🇾','tchequie':'🇨🇿',
  'ecosse':'🏴󠁧󠁢󠁳󠁣󠁴󠁿','tunisie':'🇹🇳','rd-congo':'🇨🇩','ouzbekistan':'🇺🇿','qatar':'🇶🇦','irak':'🇮🇶',
  'afrique-du-sud':'🇿🇦','arabie-saoudite':'🇸🇦','jordanie':'🇯🇴','bosnie-herzegovine':'🇧🇦','cap-vert':'🇨🇻',
  'ghana':'🇬🇭','curacao':'🇨🇼','haiti':'🇭🇹','nouvelle-zelande':'🇳🇿','pays-de-galles':'🏴󠁧󠁢󠁷󠁬󠁳󠁿',
  'pologne':'🇵🇱','italie':'🇮🇹','danemark':'🇩🇰','serbie':'🇷🇸','nigeria':'🇳🇬','cameroun':'🇨🇲',
  'perou':'🇵🇪','chili':'🇨🇱','grece':'🇬🇷','ukraine':'🇺🇦','hongrie':'🇭🇺','roumanie':'🇷🇴'
};
function normName(s){
  return String(s||'').trim().toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/[\u2019`]/g,"'").replace(/&/g,' et ')
    .replace(/[^a-z0-9' ]/g,' ').replace(/\s+/g,' ')
    .replace(/ /g,'-').replace(/-+/g,'-').replace(/^-|-$/g,'');
}
function flag(team){ return FLAGS[normName(team)] || '⚽'; }

/* ===================================================================
   OUTILS
   =================================================================== */
function $(id){return document.getElementById(id);}
function escapeHtml(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function fmtError(e){ if(!e) return 'erreur inconnue.'; return e.message || (e.toString&&e.toString()) || String(e); }
function msg(id,text,type){var el=$(id); if(!el)return; el.textContent=text; el.className='msg show '+(type||'ok');}
function clearMsg(id){var el=$(id); if(!el)return; el.textContent=''; el.className='msg';}
function setAll(cls,val){var els=document.querySelectorAll('.'+cls); for(var i=0;i<els.length;i++) els[i].textContent=val;}

var MONTHS=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.'];
function fmtDate(s){
  if(!s) return '';
  var m=String(s).match(/(\d{4})-(\d{2})-(\d{2})[ T]?(\d{2})?:?(\d{2})?/);
  if(!m) return String(s);
  var day=Number(m[3]), mon=MONTHS[Number(m[2])-1]||'', hh=m[4], mm=m[5];
  var out=day+' '+mon;
  if(hh!=null) out+=' · '+hh+'h'+(mm||'00');
  return out;
}

/* ===================================================================
   DÉMARRAGE
   =================================================================== */
window.addEventListener('beforeinstallprompt',function(e){ e.preventDefault(); deferredPrompt=e; });

/* ===================================================================
   AFFICHAGE MOBILE / ORDINATEUR (fiable dans l'iframe Apps Script)
   =================================================================== */
function currentOverride(){ var v=localStorage.getItem('cdm_layout'); return (v==='mobile'||v==='desktop')?v:'auto'; }
function computeMode(){
  var ov=currentOverride();
  if(ov!=='auto') return ov;
  var ss=Math.min(window.screen.width||9999, window.screen.height||9999);
  var vw=window.innerWidth||ss;
  var phone=/Mobi|Android|iPhone|iPod/i.test(navigator.userAgent);
  return (phone||ss<768||vw<900)?'mobile':'desktop';
}
function applyLayout(){
  var mode=computeMode(), de=document.documentElement;
  de.classList.toggle('mode-desktop', mode==='desktop');
  de.classList.toggle('mode-mobile', mode!=='desktop');
  if(mode==='mobile'){ if(window.__fixVP) window.__fixVP(); }
  else { de.style.zoom=''; }
  markModeToggle();
  updateDiag();
}
function updateDiag(){
  var el=document.getElementById('diag'); if(!el) return;
  var sw=window.screen?window.screen.width:'?', sh=window.screen?window.screen.height:'?';
  var iw=window.innerWidth||'?';
  var z=document.documentElement.style.zoom||'1';
  var dpr=window.devicePixelRatio||'?';
  el.textContent='écran '+sw+'×'+sh+'  ·  cadre '+iw+'  ·  zoom '+z+'  ·  DPR '+dpr+'  ·  mode '+computeMode();
}
function checkZoom(){
  try{
    var el=document.getElementById('zoomWarn'); if(!el) return;
    if(sessionStorage.getItem('cdm_zoomdismiss')==='1'){ el.style.display='none'; return; }
    var zoomFixed = !!document.documentElement.style.zoom; // correction active
    var cw=document.documentElement.clientWidth||window.innerWidth||0;
    var sw=window.screen.width||cw;
    el.style.display = (!zoomFixed && computeMode()==='mobile' && cw > sw*1.4) ? 'flex' : 'none';
  }catch(e){}
}
function dismissZoom(){ try{ sessionStorage.setItem('cdm_zoomdismiss','1'); }catch(e){} var el=document.getElementById('zoomWarn'); if(el) el.style.display='none'; }
function markModeToggle(){
  var ov=currentOverride(), btns=document.querySelectorAll('#modeToggle button');
  for(var i=0;i<btns.length;i++){ btns[i].classList.toggle('active', btns[i].getAttribute('data-mode')===ov); }
}
function setLayout(mode){
  if(mode==='auto') localStorage.removeItem('cdm_layout'); else localStorage.setItem('cdm_layout',mode);
  applyLayout();
  setTimeout(applyLayout, 80);
  window.scrollTo({top:0,behavior:'smooth'});
}
window.addEventListener('resize', applyLayout);
window.addEventListener('orientationchange', function(){ setTimeout(applyLayout,300); });
window.addEventListener('load',function(){
  applyLayout();
  setTimeout(applyLayout, 250);
  var email=localStorage.getItem('cdm2026_email')||'';
  var pseudo=localStorage.getItem('cdm2026_pseudo')||'';
  if(email){
    $('resumeBox').classList.remove('hidden');
    $('resumeName').textContent = pseudo ? 'Reprendre avec '+pseudo : 'Reprendre ma session';
    $('resumeEmail').textContent = email;
    $('loginEmail').value = email;
  }
});

/* ===================================================================
   CONNEXION / INSCRIPTION
   =================================================================== */
function authTab(tab){
  var login = tab==='login';
  $('segLogin').classList.toggle('active',login);
  $('segReg').classList.toggle('active',!login);
  $('paneLogin').classList.toggle('hidden',!login);
  $('paneReg').classList.toggle('hidden',login);
  clearMsg('loginMsg');
}
function doLogin(){
  clearMsg('loginMsg');
  var email=$('loginEmail').value.trim().toLowerCase(), password=$('loginPassword').value;
  if(!email||!password){ msg('loginMsg','Saisis ton adresse email et ton mot de passe.','err'); return; }
  msg('loginMsg','Ouverture de ton espace…','info');
  google.script.run
    .withSuccessHandler(function(d){ enterApp(d); })
    .withFailureHandler(function(e){ msg('loginMsg', fmtError(e)+' Si tu n\u2019es pas encore inscrit, choisis « Nouveau joueur ».','err'); })
    .getPlayerData({email:email});
}
function doRegister(){
  clearMsg('loginMsg');
  var pseudo=$('regPseudo').value.trim(), service=$('regService').value.trim(), email=$('regEmail').value.trim().toLowerCase(), password=$('regPassword').value;
  if(!pseudo||!service||!email||!password){ msg('loginMsg','Pseudo, service, email et mot de passe sont obligatoires.','err'); return; }
  if(password.length<8){ msg('loginMsg','Le mot de passe doit contenir au moins 8 caractères.','err'); return; }
  msg('loginMsg','Création de ton espace…','info');
  google.script.run
    .withSuccessHandler(function(d){ enterApp(d); })
    .withFailureHandler(function(e){ msg('loginMsg', fmtError(e),'err'); })
    .loginOrRegister({pseudo:pseudo,service:service,email:email});
}
function resumeSession(){
  $('loginEmail').value=localStorage.getItem('cdm2026_email')||'';
  $('loginPassword').focus();
  msg('loginMsg','Saisis ton mot de passe pour reprendre ta session.','info');
}
function forgetSession(){
  localStorage.removeItem('cdm2026_email'); localStorage.removeItem('cdm2026_pseudo'); localStorage.removeItem('cdm2026_service');
  localStorage.removeItem('pronostics_access_token');
  $('loginPassword').value=''; $('regPassword').value='';
  $('resumeBox').classList.add('hidden');
}

/* ===================================================================
   ENTRÉE DANS L'APPLI
   =================================================================== */
function enterApp(data){
  if(!data||!data.player){ msg('loginMsg','Réponse serveur incomplète (joueur manquant).','err'); return; }
  if(!Array.isArray(data.matches)){ msg('loginMsg','Réponse serveur incomplète (matchs manquants).','err'); return; }
  state.player=data.player; state.matches=data.matches; state.ranking=data.ranking||[]; state.guest=false;
  dirty=false;
  try{
    localStorage.setItem('cdm2026_email',state.player.email||'');
    localStorage.setItem('cdm2026_pseudo',state.player.pseudo||'');
    localStorage.setItem('cdm2026_service',state.player.service||'');
  }catch(e){}
  showApp();
  paintPlayer();
  $('mobilePlayer').style.display='';
  document.body.classList.remove('guest-mode');
  $('guestNote').style.display='none';
  buildGroups(); renderMatches(); updateProgress();
  go('pronos');
  checkZoom();
  window.scrollTo({top:0,behavior:'smooth'});
}
function showApp(){ $('screen-login').classList.add('hidden'); $('screen-app').classList.remove('hidden'); }
function paintPlayer(){
  var p=state.player||{pseudo:'Invité',service:'',email:''};
  setAll('js-pseudo', p.pseudo||'Joueur');
  setAll('js-service', p.service ? 'Service : '+p.service : 'Service non renseigné');
  setAll('js-avatar', (p.pseudo||'J').slice(0,1).toUpperCase());
}

/* mode invité (depuis l'écran de connexion) */
function openGuest(view){
  state.guest=true; state.player=null;
  showApp();
  setAll('js-pseudo','Invité'); setAll('js-service','Mode lecture'); setAll('js-avatar','?');
  $('mobilePlayer').style.display='none';
  $('guestNote').style.display='';
  // masque pronos + profil dans les deux navs
  toggleNav('pronos', false); toggleNav('profil', false);
  go(view||'classement');
}
function quitGuest(){
  state.guest=false;
  toggleNav('pronos', true); toggleNav('profil', true);
  $('screen-app').classList.add('hidden'); $('screen-login').classList.remove('hidden');
  window.scrollTo({top:0,behavior:'smooth'});
}
function toggleNav(view, show){
  var els=document.querySelectorAll('[data-nav="'+view+'"]');
  for(var i=0;i<els.length;i++) els[i].style.display = show ? '' : 'none';
}
function logout(){
  if(dirty && !confirm('Des pronostics ne sont pas enregistrés. Se déconnecter quand même ?')) return;
  forgetSession();
  state={player:null,matches:[],ranking:[],participants:[],guest:false}; dirty=false;
  $('savebar').classList.remove('show');
  $('screen-app').classList.add('hidden'); $('screen-login').classList.remove('hidden');
  window.scrollTo({top:0,behavior:'smooth'});
}

/* ===================================================================
   NAVIGATION ENTRE VUES
   =================================================================== */
function go(view){
  var sections=document.querySelectorAll('[data-view]');
  for(var i=0;i<sections.length;i++) sections[i].classList.toggle('hidden', sections[i].getAttribute('data-view')!==view);
  var navs=document.querySelectorAll('[data-nav]');
  for(var j=0;j<navs.length;j++) navs[j].classList.toggle('active', navs[j].getAttribute('data-nav')===view);
  if(view==='classement') loadRanking();
  if(view==='joueurs') loadJoueurs();
  if(view==='profil' && state.player){ $('profilePseudo').value=state.player.pseudo||''; $('profileService').value=state.player.service||''; }
  if(view==='profil') updateDiag();
  window.scrollTo({top:0,behavior:'smooth'});
}

/* ===================================================================
   MATCHS
   =================================================================== */
function buildGroups(){
  var groups=[]; var seen={};
  (state.matches||[]).forEach(function(m){ if(!seen[m.group]){ seen[m.group]=1; groups.push(m.group);} });
  var html='<button class="chip '+(currentGroup==='all'?'active':'')+'" onclick="selectGroup(\'all\')">Tous</button>';
  groups.forEach(function(g){
    var isFranceGroup = String(g).toUpperCase()==='I';
    var extraClass = isFranceGroup ? ' france-chip' : '';
    var label = isFranceGroup ? '🇫🇷 Groupe '+escapeHtml(g) : 'Groupe '+escapeHtml(g);
    html+='<button class="chip '+(currentGroup===g?'active':'')+extraClass+'" onclick="selectGroup(\''+escapeHtml(g)+'\')">'+label+'</button>';
  });
  $('groupChips').innerHTML=html;
}
function selectGroup(g){ currentGroup=g; buildGroups(); renderMatches(); }
function isFilled(m){ return m.prono1!=null && m.prono1!=='' && m.prono2!=null && m.prono2!==''; }

function renderMatches(){
  var grid=$('matchGrid'); var filter='all';
  var rows=(state.matches||[]).slice();
  if(currentGroup!=='all') rows=rows.filter(function(m){return String(m.group)===String(currentGroup);});
  if(filter==='missing') rows=rows.filter(function(m){return !isFilled(m);});
  if(filter==='done') rows=rows.filter(isFilled);
  if(filter==='locked') rows=rows.filter(function(m){return m.locked;});
  if(filter==='unlocked') rows=rows.filter(function(m){return !m.locked;});

  if(!rows.length){ grid.innerHTML='<div class="empty">Aucun match dans cette sélection.</div>'; return; }

  var html=''; var cur='';
  rows.forEach(function(m){
    if(m.group!==cur){
      cur=m.group;
      var gr=rows.filter(function(x){return x.group===cur;});
      var done=gr.filter(isFilled).length;
      html+='<div class="groupBar"><b>Groupe '+escapeHtml(cur)+'</b><small>'+done+'/'+gr.length+' remplis</small></div>';
    }
    html+=matchCard(m);
  });
  grid.innerHTML=html;
}

function matchCard(m){
  var locked=!!m.locked;
  var filled=isFilled(m);
  var statusClass=locked?'locked':(filled?'done':'todo');
  var statusText=locked?'Verrouillé':(filled?'Complet':'À compléter');
  var hasReal=(m.real1!=null && m.real2!=null);
  var v1=(m.prono1==null?'':m.prono1), v2=(m.prono2==null?'':m.prono2);
  var dis=locked?'disabled':'';
  return ''+
  '<article class="match '+statusClass+'" data-id="'+escapeHtml(m.id)+'">'+
    '<div class="matchTop"><span class="num">Match '+escapeHtml(m.id)+'</span><span class="badge '+statusClass+'">'+statusText+'</span></div>'+
    teamLine(m.team1, m.fifaRank1, m.id, 1, v1, dis)+
    teamLine(m.team2, m.fifaRank2, m.id, 2, v2, dis)+
    '<div class="matchFoot"><span>'+(hasReal?('<span class="realScore">Réel '+m.real1+'\u2013'+m.real2+'</span>'):'')+'</span><span>'+escapeHtml(fmtDate(m.date))+'</span></div>'+
  '</article>';
}
function teamLine(name, rank, id, side, val, dis){
  var rankHtml = rank ? '<span class="rank">#'+escapeHtml(rank)+' FIFA</span>' : '';
  return ''+
  '<div class="teamLine">'+
    '<span class="flag">'+flag(name)+'</span>'+
    '<span class="team"><span class="name">'+escapeHtml(name)+'</span>'+rankHtml+'</span>'+
    '<span class="stepper">'+
      '<button class="stepBtn" data-step="-1" '+dis+' aria-label="moins">\u2212</button>'+
      '<input class="scoreInput" inputmode="numeric" type="number" min="0" max="20" '+
        'value="'+escapeHtml(val)+'" data-match="'+escapeHtml(id)+'" data-side="'+side+'" '+dis+' aria-label="score '+escapeHtml(name)+'">'+
      '<button class="stepBtn" data-step="1" '+dis+' aria-label="plus">+</button>'+
    '</span>'+
  '</div>';
}

/* délégation d'événements sur la grille de matchs */
$('matchGrid').addEventListener('click',function(e){
  var b=e.target.closest && e.target.closest('.stepBtn'); if(!b||b.disabled) return;
  var input=b.parentNode.querySelector('.scoreInput');
  var delta=Number(b.getAttribute('data-step'));
  var cur=input.value===''?(delta>0?-1:0):Number(input.value);
  var next=Math.max(0,Math.min(20,cur+delta));
  input.value=next; onScoreChange(input);
});
$('matchGrid').addEventListener('input',function(e){
  if(e.target.classList && e.target.classList.contains('scoreInput')) onScoreChange(e.target);
});

function onScoreChange(input){
  var id=input.getAttribute('data-match'), side=input.getAttribute('data-side');
  var raw=input.value.replace(/[^0-9]/g,'').slice(0,2);
  var num = raw==='' ? '' : Math.max(0,Math.min(20,Number(raw)));
  input.value=num;
  var m=(state.matches||[]).find(function(x){return String(x.id)===String(id);});
  if(m){ if(side==='1') m.prono1=num; else m.prono2=num; }
  // statut de la carte en direct
  var card=input.closest('.match');
  if(card && m && !m.locked){
    var done=isFilled(m);
    card.className='match '+(done?'done':'todo');
    var badge=card.querySelector('.badge');
    if(badge){ badge.className='badge '+(done?'done':'todo'); badge.textContent=done?'Complet':'À compléter'; }
  }
  dirty=true; $('savebar').classList.add('show'); clearMsg('pronosMsg');
  updateProgress();
}

function updateProgress(){
  var all=state.matches||[]; var total=all.length||0;
  var done=all.filter(isFilled).length;
  setAll('js-done',done); setAll('js-total',total);
  var pct=total?Math.round(done/total*100):0;
  var bars=document.querySelectorAll('.js-progBar'); for(var i=0;i<bars.length;i++) bars[i].style.width=pct+'%';
}

/* enregistrement */
function saveAll(){
  if(!state.player){ msg('pronosMsg','Connecte-toi pour enregistrer.','err'); return; }

  var predictions=(state.matches||[]).filter(isFilled).map(function(m){
    return { idMatch:m.id, prono1:m.prono1, prono2:m.prono2 };
  });

  var bar = $('savebar');
  var barText = bar ? bar.querySelector('span') : null;
  var barBtn = bar ? bar.querySelector('button') : null;

  if(bar){
    bar.classList.add('show','saving');
    bar.classList.remove('saved','error');
  }
  if(barText) barText.textContent = 'Envoi en cours…';
  if(barBtn){
    barBtn.disabled = true;
    barBtn.textContent = '⏳ Envoi…';
  }

  msg('pronosMsg','Envoi en cours… merci de patienter.','info');

  google.script.run
    .withSuccessHandler(function(res){
      dirty=false;

      if(bar){
        bar.classList.remove('saving','error');
        bar.classList.add('saved','show');
      }
      if(barText) barText.textContent = 'Pronostics enregistrés ✅';
      if(barBtn){
        barBtn.disabled = false;
        barBtn.textContent = '💾 Enregistrer';
      }

      state.matches=res.data.matches; state.ranking=res.data.ranking||state.ranking;
      msg('pronosMsg', (res.saved||0)+' pronostic(s) enregistré(s). 👍','ok');
      renderMatches(); updateProgress();

      setTimeout(function(){
        if(!dirty && bar){
          bar.classList.remove('show','saved','saving','error');
          if(barText) barText.textContent = 'Pronostics non enregistrés';
        }
      }, 1800);
    })
    .withFailureHandler(function(e){
      if(bar){
        bar.classList.remove('saving','saved');
        bar.classList.add('show','error');
      }
      if(barText) barText.textContent = 'Erreur pendant l’envoi';
      if(barBtn){
        barBtn.disabled = false;
        barBtn.textContent = 'Réessayer';
      }
      msg('pronosMsg', fmtError(e),'err');
    })
    .savePredictions({email:state.player.email, predictions:predictions});
}

/* tirage aléatoire sur la sélection visible et modifiable */
function randomFill(){
  var cards=[].slice.call(document.querySelectorAll('#matchGrid .match'));
  var modifiable=cards.filter(function(c){ var m=findMatch(c.getAttribute('data-id')); return m && !m.locked; });
  if(!modifiable.length){ msg('pronosMsg','Aucun match modifiable dans cette sélection.','info'); return; }
  var empties=modifiable.filter(function(c){ var m=findMatch(c.getAttribute('data-id')); return m && !isFilled(m); });
  var targets=empties.length?empties:modifiable;
  if(!empties.length && !confirm('Tout est déjà rempli ici. Remplacer par un tirage aléatoire ?')) return;
  var count=0;
  targets.forEach(function(c){
    var m=findMatch(c.getAttribute('data-id')); if(!m) return;
    var s=randomScore(m); m.prono1=s[0]; m.prono2=s[1];
    var ins=c.querySelectorAll('.scoreInput');
    if(ins[0]) ins[0].value=s[0]; if(ins[1]) ins[1].value=s[1];
    var done=isFilled(m); c.className='match '+(done?'done':'todo');
    var badge=c.querySelector('.badge'); if(badge){ badge.className='badge '+(done?'done':'todo'); badge.textContent=done?'Complet':'À compléter'; }
    count++;
  });
  if(count){ dirty=true; $('savebar').classList.add('show'); updateProgress();
    msg('pronosMsg', count+' match(s) remplis par le tirage expert probabiliste. Pense à enregistrer.','info'); }
}
function findMatch(id){ return (state.matches||[]).find(function(x){return String(x.id)===String(id);}); }
/* ===================================================================
   TIRAGE EXPERT PROBABILISTE
   Critères pris en compte : classement FIFA, attaque, défense, pressing,
   transition, expérience, volatilité, avantage pays hôte et opposition de styles.
   Les valeurs ci-dessous sont volontairement simples : elles servent à orienter
   un tirage aléatoire crédible, pas à figer un score unique.
   =================================================================== */
var TEAM_PROFILES = {
  'france':{atk:93,def:91,press:78,trans:89,exp:94,tempo:70,vol:34,home:0},
  'espagne':{atk:90,def:87,press:91,trans:76,exp:88,tempo:82,vol:35,home:0},
  'argentine':{atk:89,def:88,press:74,trans:82,exp:95,tempo:68,vol:30,home:0},
  'angleterre':{atk:91,def:84,press:80,trans:86,exp:86,tempo:69,vol:42,home:0},
  'portugal':{atk:90,def:83,press:78,trans:84,exp:87,tempo:72,vol:43,home:0},
  'bresil':{atk:90,def:82,press:77,trans:88,exp:86,tempo:76,vol:48,home:0},
  'pays-bas':{atk:84,def:86,press:82,trans:80,exp:84,tempo:72,vol:39,home:0},
  'maroc':{atk:78,def:88,press:72,trans:83,exp:82,tempo:60,vol:36,home:0},
  'belgique':{atk:83,def:78,press:70,trans:80,exp:86,tempo:66,vol:48,home:0},
  'allemagne':{atk:86,def:80,press:87,trans:78,exp:88,tempo:80,vol:45,home:0},
  'croatie':{atk:78,def:82,press:68,trans:72,exp:94,tempo:58,vol:32,home:0},
  'colombie':{atk:82,def:80,press:74,trans:84,exp:80,tempo:70,vol:45,home:0},
  'senegal':{atk:78,def:82,press:74,trans:84,exp:76,tempo:68,vol:44,home:0},
  'mexique':{atk:77,def:77,press:76,trans:76,exp:82,tempo:72,vol:50,home:1},
  'etats-unis':{atk:78,def:76,press:83,trans:82,exp:76,tempo:78,vol:48,home:1},
  'usa':{atk:78,def:76,press:83,trans:82,exp:76,tempo:78,vol:48,home:1},
  'uruguay':{atk:80,def:83,press:81,trans:82,exp:86,tempo:70,vol:39,home:0},
  'japon':{atk:79,def:78,press:86,trans:84,exp:77,tempo:82,vol:44,home:0},
  'suisse':{atk:75,def:81,press:70,trans:72,exp:83,tempo:60,vol:34,home:0},
  'iran':{atk:72,def:78,press:62,trans:76,exp:80,tempo:56,vol:40,home:0},
  'turquie':{atk:80,def:73,press:76,trans:79,exp:75,tempo:76,vol:56,home:0},
  'equateur':{atk:75,def:80,press:74,trans:78,exp:74,tempo:65,vol:42,home:0},
  'autriche':{atk:76,def:79,press:86,trans:78,exp:78,tempo:79,vol:43,home:0},
  'coree-du-sud':{atk:78,def:75,press:80,trans:84,exp:78,tempo:78,vol:46,home:0},
  'australie':{atk:70,def:76,press:70,trans:73,exp:78,tempo:62,vol:39,home:0},
  'algerie':{atk:76,def:74,press:70,trans:80,exp:75,tempo:69,vol:51,home:0},
  'egypte':{atk:78,def:75,press:65,trans:78,exp:80,tempo:58,vol:42,home:0},
  'canada':{atk:76,def:72,press:79,trans:86,exp:68,tempo:78,vol:54,home:1},
  'norvege':{atk:82,def:72,press:73,trans:78,exp:68,tempo:66,vol:53,home:0},
  'panama':{atk:68,def:70,press:68,trans:72,exp:68,tempo:64,vol:50,home:0},
  "cote-d'ivoire":{atk:77,def:76,press:69,trans:82,exp:76,tempo:66,vol:49,home:0},
  'cote-d-ivoire':{atk:77,def:76,press:69,trans:82,exp:76,tempo:66,vol:49,home:0},
  'suede':{atk:73,def:78,press:72,trans:73,exp:78,tempo:61,vol:39,home:0},
  'paraguay':{atk:68,def:77,press:71,trans:70,exp:76,tempo:56,vol:36,home:0},
  'tchequie':{atk:72,def:76,press:75,trans:71,exp:76,tempo:64,vol:40,home:0},
  'ecosse':{atk:70,def:75,press:76,trans:70,exp:76,tempo:67,vol:43,home:0},
  'tunisie':{atk:68,def:77,press:66,trans:70,exp:78,tempo:54,vol:37,home:0},
  'rd-congo':{atk:73,def:73,press:66,trans:82,exp:70,tempo:64,vol:55,home:0},
  'ouzbekistan':{atk:70,def:73,press:70,trans:73,exp:66,tempo:62,vol:47,home:0},
  'qatar':{atk:71,def:70,press:64,trans:72,exp:74,tempo:58,vol:50,home:0},
  'irak':{atk:69,def:72,press:67,trans:73,exp:72,tempo:61,vol:48,home:0},
  'afrique-du-sud':{atk:70,def:72,press:70,trans:73,exp:70,tempo:64,vol:46,home:0},
  'arabie-saoudite':{atk:70,def:71,press:72,trans:72,exp:74,tempo:66,vol:49,home:0},
  'jordanie':{atk:67,def:69,press:65,trans:74,exp:68,tempo:58,vol:51,home:0},
  'bosnie-herzegovine':{atk:70,def:69,press:63,trans:68,exp:74,tempo:55,vol:46,home:0},
  'cap-vert':{atk:68,def:72,press:66,trans:75,exp:67,tempo:58,vol:47,home:0},
  'ghana':{atk:74,def:70,press:68,trans:82,exp:74,tempo:68,vol:58,home:0},
  'curacao':{atk:65,def:67,press:62,trans:69,exp:60,tempo:55,vol:58,home:0},
  'haiti':{atk:66,def:65,press:64,trans:72,exp:62,tempo:62,vol:60,home:0},
  'nouvelle-zelande':{atk:64,def:68,press:62,trans:65,exp:70,tempo:54,vol:42,home:0}
};
function clamp(n,min,max){ return Math.max(min,Math.min(max,n)); }
function derivedProfile(rank){
  rank=Number(rank)||75;
  var base=clamp(86-rank*.35,58,84);
  return {atk:base,def:base,press:base,trans:base,exp:base,tempo:62,vol:48,home:0};
}
function profile(team,rank){
  var p=TEAM_PROFILES[normName(team)] || derivedProfile(rank);
  return {
    atk:Number(p.atk)||70, def:Number(p.def)||70, press:Number(p.press)||70,
    trans:Number(p.trans)||70, exp:Number(p.exp)||70, tempo:Number(p.tempo)||62,
    vol:Number(p.vol)||48, home:Number(p.home)||0
  };
}
function expectedGoalsFor(teamA,rankA,teamB,rankB){
  var a=profile(teamA,rankA), b=profile(teamB,rankB);
  rankA=Number(rankA)||75; rankB=Number(rankB)||75;

  // Classement FIFA : avantage de niveau général.
  var rankEdge = clamp((rankB-rankA)/42, -1.25, 1.25);

  // Opposition attaque / défense.
  var qualityEdge = ((a.atk-b.def)/100)*0.85;

  // Styles : transition contre pressing haut, match fermé si deux défenses/expériences fortes.
  var transitionBonus = ((a.trans-70)/100)*0.30 + ((b.press-76)>0 ? ((a.trans-b.press)/100)*0.22 : 0);
  var tempoBonus = ((a.tempo+b.tempo-124)/100)*0.28;
  var experienceBonus = ((a.exp-b.exp)/100)*0.18;
  var homeBonus = a.home ? 0.22 : 0;
  var defensiveBrake = clamp(((b.def-74)+(b.exp-74))/100, -0.25, 0.35);

  var lambda = 1.05 + rankEdge + qualityEdge + transitionBonus + tempoBonus + experienceBonus + homeBonus - defensiveBrake;
  return clamp(lambda, 0.18, 3.40);
}
function randomScore(m){
  var l1=expectedGoalsFor(m.team1,m.fifaRank1,m.team2,m.fifaRank2);
  var l2=expectedGoalsFor(m.team2,m.fifaRank2,m.team1,m.fifaRank1);
  var p1=profile(m.team1,m.fifaRank1), p2=profile(m.team2,m.fifaRank2);
  var volatility=(p1.vol+p2.vol)/200;

  // Petit bruit contrôlé : plus le match est volatil, plus le score peut s'écarter.
  l1=clamp(l1 + (Math.random()-.5)*0.45*volatility, .15, 3.6);
  l2=clamp(l2 + (Math.random()-.5)*0.45*volatility, .15, 3.6);

  // Si les deux équipes sont proches et défensives, le nul devient plus probable.
  var close=Math.abs(l1-l2)<0.22;
  var lowTempo=((p1.tempo+p2.tempo)/2)<62;
  if(close && (lowTempo || Math.random()<0.18)){
    var d=Math.random()<0.55 ? 1 : 0;
    return [d,d];
  }

  var s1=Math.min(6,poisson(l1)), s2=Math.min(6,poisson(l2));

  // Évite quelques scores absurdes : une très grosse surprise reste possible, mais rare.
  var r1=Number(m.fifaRank1)||75, r2=Number(m.fifaRank2)||75;
  if(r1+35<r2 && s2-s1>=3 && Math.random()<0.65) s2=Math.max(0,s2-1);
  if(r2+35<r1 && s1-s2>=3 && Math.random()<0.65) s1=Math.max(0,s1-1);

  return [s1,s2];
}
function poisson(lambda){ var L=Math.exp(-lambda),p=1,k=0; do{k++;p*=Math.random();}while(p>L&&k<10); return k-1; }

/* ===================================================================
   CLASSEMENT
   =================================================================== */
function loadRanking(){
  $('rankList').innerHTML='<div class="empty">Chargement…</div>';
  google.script.run
    .withSuccessHandler(function(r){ state.ranking=r||[]; renderRanking(); })
    .withFailureHandler(function(e){ $('rankList').innerHTML='<div class="empty">'+escapeHtml(fmtError(e))+'</div>'; })
    .getRanking();
}
function renderRanking(){
  var rows=state.ranking||[];
  $('rankMeta').textContent = rows.length ? (rows.length+(rows.length>1?' joueurs':' joueur')) : '';
  if(!rows.length){ $('rankList').innerHTML='<div class="empty">Aucun participant pour le moment.</div>'; return; }
  var html='';
  var lead=rows[0];
  html+='<div class="leader"><span class="cup">🏆</span><div><b>'+escapeHtml(lead.pseudo)+'</b><small>'+escapeHtml(lead.service||'Service non renseigné')+'</small></div>'+
        '<div class="pts"><strong>'+lead.points+'</strong><span>points</span></div></div>';
  rows.forEach(function(r){
    if(r.rang===1) return;
    html+='<div class="rankRow"><div class="pos">'+r.rang+'</div>'+
      '<div class="info"><b>'+escapeHtml(r.pseudo)+'</b><span class="pill">'+escapeHtml(r.service||'Non renseigné')+'</span>'+
      '<div class="mini"><span>🎯 '+r.exacts+' exacts</span><span>✅ '+r.bonsResultats+' bons</span></div></div>'+
      '<div class="score-pts"><strong>'+r.points+'</strong><span>pts</span></div></div>';
  });
  $('rankList').innerHTML=html;
}

/* ===================================================================
   JOUEURS
   =================================================================== */
function loadJoueurs(){
  $('joueursList').innerHTML='<div class="empty">Chargement…</div>';
  google.script.run
    .withSuccessHandler(function(list){ state.participants=list||[]; renderJoueurs(); })
    .withFailureHandler(function(e){ $('joueursList').innerHTML='<div class="empty">'+escapeHtml(fmtError(e))+'</div>'; })
    .getParticipantsPublic();
}
function renderJoueurs(){
  var rows=state.participants||[];
  $('joueursMeta').textContent = rows.length ? (rows.length+(rows.length>1?' joueurs':' joueur')) : '';
  if(!rows.length){ $('joueursList').innerHTML='<div class="empty">Aucun participant inscrit pour le moment.</div>'; return; }
  $('joueursList').innerHTML = rows.map(function(r){
    return '<div class="rankRow"><div class="info"><b>'+escapeHtml(r.pseudo)+'</b><span class="pill">'+escapeHtml(r.service||'Non renseigné')+'</span>'+
      '<div class="mini"><span>📝 '+(r.pronosticsSaisis||0)+' pronos</span><span>⭐ '+(r.points||0)+' pts</span></div></div></div>';
  }).join('');
}

/* ===================================================================
   PROFIL
   =================================================================== */
function saveProfile(){
  if(!state.player){ msg('profileMsg','Connecte-toi d\u2019abord.','err'); return; }
  var pseudo=$('profilePseudo').value.trim(), service=$('profileService').value.trim();
  if(!pseudo||!service){ msg('profileMsg','Pseudo et service obligatoires.','err'); return; }
  msg('profileMsg','Mise à jour…','info');
  google.script.run
    .withSuccessHandler(function(d){
      state.player=d.player; state.matches=d.matches||state.matches; state.ranking=d.ranking||state.ranking;
      try{ localStorage.setItem('cdm2026_pseudo',state.player.pseudo||''); localStorage.setItem('cdm2026_service',state.player.service||''); }catch(e){}
      paintPlayer(); msg('profileMsg','Profil mis à jour. ✅','ok');
    })
    .withFailureHandler(function(e){ msg('profileMsg', fmtError(e),'err'); })
    .updateProfile({email:state.player.email, pseudo:pseudo, service:service});
}

/* ===================================================================
   INSTALLATION (PWA / raccourci écran d'accueil)
   =================================================================== */
function installApp(){
  if(deferredPrompt){
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function(c){ deferredPrompt=null; if(!c||c.outcome!=='accepted') showInstall(); });
    return;
  }
  showInstall();
}
function showInstall(){
  var ua=navigator.userAgent, iOS=/iphone|ipad|ipod/i.test(ua), android=/android/i.test(ua);
  var html='<div class="step"><b>📲 Ajouter un raccourci sur l\u2019écran d\u2019accueil</b><p>L\u2019application s\u2019installe comme un raccourci web et s\u2019ouvre directement sur le jeu de pronostics.</p></div>';
  if(iOS) html+='<div class="step"><b>Sur iPhone (Safari)</b><p>Touche le bouton Partager, puis « Sur l\u2019écran d\u2019accueil ».</p></div>';
  else if(android) html+='<div class="step"><b>Sur Android (Chrome)</b><p>Menu ⋮, puis « Ajouter à l\u2019écran d\u2019accueil » ou « Installer l\u2019application ».</p></div>';
  else html+='<div class="step"><b>Sur ordinateur</b><p>Utilise le menu du navigateur pour créer un raccourci, ou partage simplement le lien.</p></div>';
  $('installContent').innerHTML=html;
  $('installModal').classList.add('show');
}
function hideInstall(){ $('installModal').classList.remove('show'); }

/* avertir avant de quitter avec des modifs non enregistrées */
window.addEventListener('beforeunload',function(e){ if(dirty){ e.preventDefault(); e.returnValue=''; } });
