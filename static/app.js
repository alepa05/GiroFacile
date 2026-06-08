let deliveries = [];
let selectedCustomer = null;
let customersCache = [];
let depositsCache = [];
let vehiclesCache = [];
let editingDeliveryIndex = null;
let lastMapsUrl = "";
let lastRouteResult = null;
let profilePhotoData = localStorage.getItem("girofacile_profile_photo") || "";

function updateDashboardStats(){
  try{
    const stops = deliveries.length;
    const kg = deliveries.reduce((a,d)=>a+(parseFloat(d.peso_kg)||0),0);
    const colli = deliveries.reduce((a,d)=>a+(parseInt(d.colli)||0),0);
    const warnings = deliveries.filter(d=>d.ztl || d.sponda).length;
    const fuel = document.getElementById("fuelPrice")?.value || "";
    const setText = (id,val)=>{ const el=document.getElementById(id); if(el) el.textContent=val; };
    setText("statDeliveries", stops);
    setText("statWarnings", warnings);
    setText("summaryStops", stops);
    setText("summaryKg", kg.toFixed(0)+" kg");
    setText("summaryColli", colli);
    setText("statColli", colli);
    setText("statFuel", fuel ? fuel+" € / L" : "€ / L");
  }catch(e){}
}

async function api(path, options = {}) {
  const headers = options.body instanceof FormData ? (options.headers || {}) : {"Content-Type":"application/json", ...(options.headers || {})};
  const res = await fetch(path, {...options, headers});
  if (!res.ok) {
    let msg = "Errore";
    try { const j = await res.json(); msg = j.detail || msg; } catch(e) {}
    throw new Error(msg);
  }
  return await res.json();
}
function boolVal(id){ return document.getElementById(id).value === "true"; }
function val(id){ return document.getElementById(id).value; }
function set(id,v){ const el=document.getElementById(id); if(el) el.value = v ?? ""; }
function esc(s){ return String(s ?? "").replace(/[&<>"']/g, m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m])); }
function fascia(d){
  const m = (d.scarico_mattina_da || d.scarico_mattina_a) ? `${d.scarico_mattina_da||"--"}-${d.scarico_mattina_a||"--"}` : "--";
  const p = (d.scarico_pomeriggio_da || d.scarico_pomeriggio_a) ? `${d.scarico_pomeriggio_da||"--"}-${d.scarico_pomeriggio_a||"--"}` : "--";
  return `${m} / ${p}`;
}
function mapsAddressUrl(address){ return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(address || ""); }
async function copyText(text, msg="Copiato negli appunti"){
  try{
    await navigator.clipboard.writeText(text || "");
    toast(msg);
  }catch(e){
    prompt("Copia questo link:", text || "");
  }
}
function toast(msg){
  const old = document.querySelector(".toast"); if(old) old.remove();
  const div = document.createElement("div");
  div.className = "toast";
  div.textContent = msg;
  document.body.appendChild(div);
  setTimeout(()=>div.remove(), 2600);
}

function loadProfilePanel(){
  const name = localStorage.getItem("girofacile_profile_name") || "Admin";
  const email = localStorage.getItem("girofacile_profile_email") || "";
  const role = localStorage.getItem("girofacile_profile_role") || "Amministratore";
  const photo = localStorage.getItem("girofacile_profile_photo") || "";
  const initials = (name || "Admin").trim().charAt(0).toUpperCase() || "A";
  const setText = (id,val)=>{ const el=document.getElementById(id); if(el) el.textContent=val; };
  setText("topProfileName", name);
  setText("topProfileRole", role);
  const topAvatar = document.getElementById("topProfileAvatar");
  if(topAvatar){
    topAvatar.innerHTML = photo ? `<img src="${photo}" alt="Profilo">` : initials;
  }
  const preview = document.getElementById("profilePreview");
  if(preview){ preview.innerHTML = photo ? `<img src="${photo}" alt="Profilo">` : initials; }
  set("profileName", name); set("profileEmail", email); set("profileRole", role);
}
function openProfilePanel(){
  loadProfilePanel();
  const el=document.getElementById("profileOverlay"); if(el) el.classList.remove("hidden");
}
function closeProfilePanel(ev){
  const el=document.getElementById("profileOverlay"); if(el) el.classList.add("hidden");
}
function previewProfilePhoto(event){
  const file = event.target.files && event.target.files[0];
  if(!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    profilePhotoData = reader.result;
    const preview = document.getElementById("profilePreview");
    if(preview) preview.innerHTML = `<img src="${profilePhotoData}" alt="Profilo">`;
  };
  reader.readAsDataURL(file);
}
function saveProfilePanel(){
  const name = val("profileName") || "Admin";
  const email = val("profileEmail") || "";
  const role = val("profileRole") || "Amministratore";
  localStorage.setItem("girofacile_profile_name", name);
  localStorage.setItem("girofacile_profile_email", email);
  localStorage.setItem("girofacile_profile_role", role);
  if(profilePhotoData) localStorage.setItem("girofacile_profile_photo", profilePhotoData);
  if(val("profilePassword")) localStorage.setItem("girofacile_profile_password_changed", new Date().toISOString());
  set("profilePassword", "");
  loadProfilePanel();
  closeProfilePanel();
  toast("Profilo salvato");
}
function printStopsTable(){
  if(!lastRouteResult){ alert("Nessun risultato giro da stampare"); return; }
  const r = lastRouteResult;
  const consegne = r.consegne || [];
  const rows = consegne.map(d => `
    <tr>
      <td>${esc(d.ordine)}</td>
      <td>${esc(d.cliente_nome)}</td>
      <td>${esc(d.indirizzo)}</td>
      <td>${esc(d.arrivo_stimato || "-")}</td>
      <td>${esc(d.partenza_stimata || "-")}</td>
      <td>${Math.round(parseFloat(d.attesa_min)||0)} min</td>
      <td>${d.km_tappa ?? "-"}</td>
      <td>${esc(d.warning || "OK")}</td>
    </tr>`).join("");
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Stampa dettaglio fermate - GiroFacile</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif;margin:28px;color:#111827;font-size:13px;}
    h1{font-size:24px;margin:0 0 6px;} .meta{margin:0 0 16px;line-height:1.7;color:#374151;}
    table{width:100%;border-collapse:collapse;} th,td{border:1px solid #d1d5db;padding:8px;text-align:left;vertical-align:top;}
    th{background:#f3f4f6;font-size:12px;} td{font-size:12px;} .footer{margin-top:18px;color:#6b7280;font-size:11px;}
    @page{size:auto;margin:12mm;}
  </style></head><body>
    <h1>GiroFacile - Dettaglio fermate</h1>
    <div class="meta">
      <strong>Giro:</strong> ${esc(r.nome || val("routeName") || "Giro consegne")}<br>
      <strong>Data:</strong> ${esc(r.data_giro || val("routeDate") || "-")} · <strong>Partenza:</strong> ${esc(r.orario_partenza || "-")} · <strong>Rientro stimato:</strong> ${esc(r.orario_rientro_stimato || "-")}<br>
      <strong>Km totali:</strong> ${r.totale_km ?? "-"} km · <strong>Tempo totale:</strong> ${Math.round(r.totale_minuti || 0)} min · <strong>Costo carburante:</strong> € ${r.costo_carburante ?? "-"}
    </div>
    <table><thead><tr><th>Ordine</th><th>Cliente</th><th>Indirizzo</th><th>Arrivo</th><th>Ripartenza</th><th>Attesa</th><th>Km tappa</th><th>Avvisi</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="footer">Stampa generata da GiroFacile</div>
  </body></html>`;
  const w = window.open("", "_blank");
  if(!w){ alert("Consenti i popup per stampare il dettaglio fermate"); return; }
  w.document.open(); w.document.write(html); w.document.close();
  setTimeout(()=>{ w.focus(); w.print(); }, 300);
}

async function checkLogin(){
  const me = await api("/api/me");
  if(me.authenticated){
    document.getElementById("loginCard").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    document.getElementById("logoutBtn").classList.remove("hidden");
    initApp();
  }
}
async function login(){
  try{
    await api("/api/login", {method:"POST", body:JSON.stringify({username:val("loginUser"), password:val("loginPass")})});
    checkLogin();
  }catch(e){ alert(e.message); }
}
document.getElementById("logoutBtn").onclick = async () => { await api("/api/logout", {method:"POST", body:"{}"}); location.reload(); };

function showTab(name){
  document.querySelectorAll(".tab").forEach(x=>x.classList.add("hidden"));
  document.getElementById("tab-"+name).classList.remove("hidden");
  document.querySelectorAll(".nav-item").forEach(x=>x.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(x=>{ if((x.textContent||"").toLowerCase().includes(name) || (name==='giro' && x.textContent.includes('Dashboard'))) x.classList.add("active"); });
  if(name==="clienti") loadCustomers();
  if(name==="depositi") loadDeposits();
  if(name==="mezzi") loadVehicles();
  if(name==="storico") loadRoutes();
}
async function initApp(){
  document.getElementById("routeDate").value = new Date().toISOString().slice(0,10);
  document.getElementById("fuelPrice")?.addEventListener("input", updateDashboardStats);
  loadProfilePanel();
  await loadDeposits(); await loadVehicles(); await loadCustomers();
  updateDashboardStats();
}

async function loadDeposits(){
  depositsCache = await api("/api/deposits");
  const body = document.getElementById("depositsBody"), sel = document.getElementById("routeDeposit");
  body.innerHTML = ""; sel.innerHTML = "";
  depositsCache.forEach(x=>{
    body.innerHTML += `<tr><td>${esc(x.nome)}</td><td>${esc(x.indirizzo)}</td><td>${x.predefinito?"Sì":"No"}</td><td><button onclick="editDeposit(${x.id})">Modifica</button><button onclick="deleteDeposit(${x.id})">Elimina</button></td></tr>`;
    sel.innerHTML += `<option value="${x.id}">${esc(x.nome)} - ${esc(x.indirizzo)}</option>`;
  });
}
function editDeposit(id){
  const x = depositsCache.find(d=>d.id===id); if(!x) return;
  set("depId", x.id); set("depNome", x.nome); set("depIndirizzo", x.indirizzo);
  document.getElementById("depDefault").checked = !!x.predefinito;
}
function resetDepositForm(){ set("depId",""); set("depNome",""); set("depIndirizzo",""); document.getElementById("depDefault").checked=false; }
async function saveDeposit(){
  const payload = {nome:val("depNome"), indirizzo:val("depIndirizzo"), predefinito:document.getElementById("depDefault").checked};
  const id = val("depId");
  await api(id?`/api/deposits/${id}`:"/api/deposits", {method:id?"PUT":"POST", body:JSON.stringify(payload)});
  resetDepositForm(); loadDeposits();
}
async function deleteDeposit(id){ if(confirm("Eliminare deposito?")){ await api(`/api/deposits/${id}`, {method:"DELETE"}); loadDeposits(); } }

async function loadVehicles(){
  vehiclesCache = await api("/api/vehicles");
  const body = document.getElementById("vehiclesBody"), sel = document.getElementById("routeVehicle");
  body.innerHTML = ""; sel.innerHTML = `<option value="">Nessun mezzo</option>`;
  vehiclesCache.forEach(x=>{
    body.innerHTML += `<tr><td>${esc(x.nome)}</td><td>${esc(x.targa||"")}</td><td>${x.consumo_l_100km}</td><td>${x.ha_sponda?"Sì":"No"}</td><td>${x.accesso_ztl?"Sì":"No"}</td><td><button onclick="editVehicle(${x.id})">Modifica</button><button onclick="deleteVehicle(${x.id})">Elimina</button></td></tr>`;
    sel.innerHTML += `<option value="${x.id}">${esc(x.nome)} - ${x.consumo_l_100km} L/100km</option>`;
  });
}
function editVehicle(id){
  const x = vehiclesCache.find(v=>v.id===id); if(!x) return;
  set("vId",x.id); set("vNome",x.nome); set("vTarga",x.targa); set("vConsumo",x.consumo_l_100km); set("vKg",x.capacita_kg); set("vColli",x.capacita_colli);
  set("vSponda",x.ha_sponda?"true":"false"); set("vZtl",x.accesso_ztl?"true":"false");
}
function resetVehicleForm(){ ["vId","vNome","vTarga"].forEach(id=>set(id,"")); set("vConsumo",8.5); set("vKg",1000); set("vColli",100); set("vSponda","false"); set("vZtl","false"); }
async function saveVehicle(){
  const payload = {nome:val("vNome"), targa:val("vTarga"), consumo_l_100km:parseFloat(val("vConsumo")||8.5), capacita_kg:parseFloat(val("vKg")||1000), capacita_colli:parseInt(val("vColli")||100), ha_sponda:boolVal("vSponda"), accesso_ztl:boolVal("vZtl")};
  const id = val("vId");
  await api(id?`/api/vehicles/${id}`:"/api/vehicles", {method:id?"PUT":"POST", body:JSON.stringify(payload)});
  resetVehicleForm(); loadVehicles();
}
async function deleteVehicle(id){ if(confirm("Eliminare mezzo?")){ await api(`/api/vehicles/${id}`, {method:"DELETE"}); loadVehicles(); } }

async function loadCustomers(){
  const q = document.getElementById("customerListSearch")?.value || "";
  customersCache = await api("/api/customers?q="+encodeURIComponent(q));
  const body = document.getElementById("customersBody");
  if(!body) return;
  body.innerHTML = "";
  customersCache.forEach(x=>{
    body.innerHTML += `<tr><td>${esc(x.codice_cliente||"")}</td><td>${esc(x.nome)}</td><td>${esc(x.indirizzo)}</td><td>${fascia(x)}</td><td>${x.ztl?"Sì":"No"}</td><td>${x.sponda?"Sì":"No"}</td><td><button onclick="editCustomer(${x.id})">Modifica</button><button onclick="deleteCustomer(${x.id})">Elimina</button></td></tr>`;
  });
}
function editCustomer(id){
  const c = customersCache.find(x=>x.id===id); if(!c) return;
  set("cId",c.id); set("cCodice",c.codice_cliente); set("cNome",c.nome); set("cIndirizzo",c.indirizzo); set("cComune",c.comune); set("cTelefono",c.telefono); set("cReferente",c.referente);
  set("cMattinaDa",c.scarico_mattina_da); set("cMattinaA",c.scarico_mattina_a); set("cPomeriggioDa",c.scarico_pomeriggio_da); set("cPomeriggioA",c.scarico_pomeriggio_a);
  set("cScarico",c.tempo_scarico_min); set("cZtl",c.ztl?"true":"false"); set("cSponda",c.sponda?"true":"false"); set("cNote",c.note);
}
function resetCustomerForm(){
  ["cId","cCodice","cNome","cIndirizzo","cComune","cTelefono","cReferente","cMattinaDa","cMattinaA","cPomeriggioDa","cPomeriggioA","cNote"].forEach(id=>set(id,""));
  set("cScarico",10); set("cZtl","false"); set("cSponda","false");
}
async function saveCustomer(){
  const payload = {codice_cliente:val("cCodice"), nome:val("cNome"), indirizzo:val("cIndirizzo"), comune:val("cComune"), telefono:val("cTelefono"), referente:val("cReferente"),
    scarico_mattina_da:val("cMattinaDa")||null, scarico_mattina_a:val("cMattinaA")||null, scarico_pomeriggio_da:val("cPomeriggioDa")||null, scarico_pomeriggio_a:val("cPomeriggioA")||null,
    tempo_scarico_min:parseInt(val("cScarico")||10), ztl:boolVal("cZtl"), sponda:boolVal("cSponda"), note:val("cNote")};
  const id = val("cId");
  await api(id?`/api/customers/${id}`:"/api/customers", {method:id?"PUT":"POST", body:JSON.stringify(payload)});
  resetCustomerForm(); loadCustomers();
}
async function deleteCustomer(id){ if(confirm("Eliminare cliente?")){ await api(`/api/customers/${id}`, {method:"DELETE"}); loadCustomers(); } }

async function importCustomers(){
  const file = document.getElementById("importFile").files[0];
  if(!file){ alert("Scegli un file CSV o Excel"); return; }
  const fd = new FormData(); fd.append("file", file);
  const res = await fetch("/api/customers/import", {method:"POST", body:fd});
  if(!res.ok){ alert("Errore import"); return; }
  const j = await res.json();
  alert(`Import completato. Creati: ${j.created}, aggiornati: ${j.updated}`);
  loadCustomers();
}

async function searchCustomersForDelivery(){
  const q = val("customerSearch"), box = document.getElementById("customerSuggestions");
  if(q.length < 2){ box.innerHTML=""; return; }
  const rows = await api("/api/customers?q="+encodeURIComponent(q));
  box.innerHTML = "";
  rows.slice(0,10).forEach(c=>{
    const div = document.createElement("div");
    div.className = "suggestion";
    div.innerHTML = `<b>${esc(c.codice_cliente||"")}</b> ${esc(c.nome)}<br><small>${esc(c.indirizzo)} - ${fascia(c)}</small>`;
    div.onclick = () => selectCustomer(c);
    box.appendChild(div);
  });
}
function selectCustomer(c){
  selectedCustomer = c;
  document.getElementById("customerSuggestions").innerHTML = "";
  set("customerSearch", `${c.codice_cliente || ""} ${c.nome}`);
  set("dCliente", c.nome); set("dIndirizzo", c.indirizzo);
  set("dMattinaDa", c.scarico_mattina_da); set("dMattinaA", c.scarico_mattina_a); set("dPomeriggioDa", c.scarico_pomeriggio_da); set("dPomeriggioA", c.scarico_pomeriggio_a);
  set("dScarico", c.tempo_scarico_min || 10); set("dZtl", c.ztl?"true":"false"); set("dSponda", c.sponda?"true":"false"); set("dNote", c.note);
}
function deliveryPayloadFromForm(){
  const cliente = val("dCliente"), indirizzo = val("dIndirizzo");
  if(!cliente || !indirizzo){ alert("Inserisci cliente e indirizzo"); return null; }
  return {customer_id:selectedCustomer?.id || null, cliente_nome:cliente, indirizzo, peso_kg:parseFloat(val("dPeso")||0), colli:parseInt(val("dColli")||0),
    scarico_mattina_da:val("dMattinaDa")||null, scarico_mattina_a:val("dMattinaA")||null, scarico_pomeriggio_da:val("dPomeriggioDa")||null, scarico_pomeriggio_a:val("dPomeriggioA")||null,
    tempo_scarico_min:parseInt(val("dScarico")||10), ztl:boolVal("dZtl"), sponda:boolVal("dSponda"), note:val("dNote")};
}
function addDelivery(){
  const payload = deliveryPayloadFromForm();
  if(!payload) return;
  if(editingDeliveryIndex !== null){
    deliveries[editingDeliveryIndex] = payload;
    toast("Consegna aggiornata");
    cancelDeliveryEdit(false);
  }else{
    deliveries.push(payload);
  }
  resetDeliveryForm();
  renderDeliveries();
}
function editDelivery(i){
  const d = deliveries[i]; if(!d) return;
  editingDeliveryIndex = i;
  selectedCustomer = d.customer_id ? {id:d.customer_id} : null;
  set("customerSearch", d.cliente_nome);
  set("dCliente", d.cliente_nome); set("dIndirizzo", d.indirizzo);
  set("dMattinaDa", d.scarico_mattina_da); set("dMattinaA", d.scarico_mattina_a); set("dPomeriggioDa", d.scarico_pomeriggio_da); set("dPomeriggioA", d.scarico_pomeriggio_a);
  set("dScarico", d.tempo_scarico_min || 10); set("dPeso", d.peso_kg || 0); set("dColli", d.colli || 0);
  set("dZtl", d.ztl?"true":"false"); set("dSponda", d.sponda?"true":"false"); set("dNote", d.note || "");
  document.getElementById("deliveryFormTitle").textContent = "Modifica consegna";
  document.getElementById("saveDeliveryBtn").textContent = "Salva modifica";
  document.getElementById("cancelEditDeliveryBtn").classList.remove("hidden");
  document.getElementById("customerSearch").scrollIntoView({behavior:"smooth", block:"center"});
}
function cancelDeliveryEdit(clear=true){
  editingDeliveryIndex = null;
  document.getElementById("deliveryFormTitle").textContent = "Aggiungi consegna";
  document.getElementById("saveDeliveryBtn").textContent = "+ Aggiungi consegna";
  document.getElementById("cancelEditDeliveryBtn").classList.add("hidden");
  if(clear) resetDeliveryForm();
}
function resetDeliveryForm(){
  selectedCustomer = null;
  ["customerSearch","dCliente","dIndirizzo","dMattinaDa","dMattinaA","dPomeriggioDa","dPomeriggioA","dPeso","dColli","dNote"].forEach(id=>set(id,""));
  set("dScarico",10); set("dZtl","false"); set("dSponda","false");
}
function renderDeliveries(){
  updateDashboardStats();
  const body = document.getElementById("deliveryBody");
  body.innerHTML = "";
  deliveries.forEach((d,i)=>{
    body.innerHTML += `<tr><td><strong>${esc(d.cliente_nome)}</strong></td><td>${esc(d.indirizzo)}</td><td>${fascia(d)}</td><td>${d.tempo_scarico_min} min</td><td>${d.ztl?"Sì":"No"}</td><td>${d.sponda?"Sì":"No"}</td><td class="row-actions"><button onclick="editDelivery(${i})">Modifica</button><button onclick="removeDelivery(${i})">X</button></td></tr>`;
  });
}
function removeDelivery(i){ deliveries.splice(i,1); if(editingDeliveryIndex===i) cancelDeliveryEdit(); renderDeliveries(); }

function warnTypeCounts(consegne){
  const counts = {sponda:0, ztl:0, attesa:0, critici:0};
  (consegne||[]).forEach(d=>{
    const w = (d.warning||"").toLowerCase();
    if(w) counts.critici++;
    if(w.includes("sponda")) counts.sponda++;
    if(w.includes("ztl")) counts.ztl++;
    if((parseFloat(d.attesa_min)||0)>0 || w.includes("attesa") || w.includes("apertura")) counts.attesa++;
  });
  return counts;
}
function warningBadges(warning){
  if(!warning) return `<span class="badge ok-badge">OK</span>`;
  return String(warning).split(";").map(x=>x.trim()).filter(Boolean).map(x=>{
    const low=x.toLowerCase();
    const cls = low.includes("sponda") || low.includes("non fattibile") || low.includes("chiusura") ? "badge danger-badge" : (low.includes("ztl") ? "badge orange-badge" : "badge warn-badge");
    return `<span class="${cls}">${esc(x)}</span>`;
  }).join(" ");
}
function renderRouteResult(r, targetId="routeResult", fromHistory=false){
  lastRouteResult = r;
  lastMapsUrl = r.google_maps_url || "";
  const consegne = r.consegne || [];
  const counts = warnTypeCounts(consegne);
  const target = document.getElementById(targetId);
  const title = fromHistory ? `Risultato giro salvato` : `Risultato giro`;
  let rows = "";
  consegne.forEach(d=>{
    rows += `<tr>
      <td><strong>${d.ordine}</strong></td>
      <td><strong>${esc(d.cliente_nome)}</strong></td>
      <td>${esc(d.indirizzo)}</td>
      <td>${esc(d.arrivo_stimato||"-")}</td>
      <td>${esc(d.partenza_stimata||"-")}</td>
      <td>${Math.round(parseFloat(d.attesa_min)||0)} min</td>
      <td>${d.km_tappa ?? "-"}</td>
      <td>${warningBadges(d.warning)}</td>
      <td class="row-actions compact"><a target="_blank" href="${mapsAddressUrl(d.indirizzo)}"><button title="Apri fermata su Maps">📍</button></a><button onclick="copyText('${esc(d.indirizzo).replace(/'/g,"\\'")}', 'Indirizzo copiato')" title="Copia indirizzo">⧉</button></td>
    </tr>`;
  });
  target.innerHTML = `<section class="result-pro">
    <div class="result-header">
      <div><h2>${title}</h2><p>Analisi del percorso e delle fermate pianificate${fromHistory ? " dallo storico" : ""}.</p></div>
    </div>
    <div class="result-layout">
      <div class="result-main">
        <div class="result-cards">
          <div class="mini-card"><span class="mini-icon blue">◷</span><div><small>Partenza</small><strong>${esc(r.orario_partenza||"-")}</strong></div></div>
          <div class="mini-card"><span class="mini-icon orange">↩</span><div><small>Rientro stimato</small><strong>${esc(r.orario_rientro_stimato||"-")}</strong></div></div>
          <div class="mini-card"><span class="mini-icon green">⌖</span><div><small>Km totali</small><strong>${r.totale_km ?? "-"} km</strong></div></div>
          <div class="mini-card"><span class="mini-icon purple">◴</span><div><small>Tempo totale</small><strong>${Math.round(r.totale_minuti||0)} min</strong></div></div>
          <div class="mini-card"><span class="mini-icon blue">⛽</span><div><small>Litri stimati</small><strong>${r.litri_stimati ?? "-"} L</strong></div></div>
          <div class="mini-card"><span class="mini-icon purple">€</span><div><small>Costo carburante</small><strong>€ ${r.costo_carburante ?? "-"}</strong></div></div>
        </div>
        <div class="alerts-panel">
          <h3>Avvisi principali</h3>
          <div class="alert-grid">
            <div class="alert-card danger"><strong>🚚 Sponda richiesta non disponibile</strong><span>${counts.sponda} fermate</span></div>
            <div class="alert-card orange"><strong>🏙 Cliente in ZTL</strong><span>${counts.ztl} fermate</span></div>
            <div class="alert-card yellow"><strong>🕒 Arrivo prima dell'apertura / attesa</strong><span>${counts.attesa} fermate</span></div>
          </div>
        </div>
        <div class="stops-panel">
          <h3>Dettaglio fermate</h3>
          <div class="tableWrap"><table class="result-table"><thead><tr><th>Ordine</th><th>Cliente</th><th>Indirizzo</th><th>Arrivo</th><th>Ripartenza</th><th>Attesa</th><th>Km tappa</th><th>Avvisi</th><th>Azioni</th></tr></thead><tbody>${rows}</tbody></table></div>
        </div>
      </div>
      <aside class="result-summary-card">
        <h3>Riepilogo esito</h3>
        <div class="summary-row"><span>Totale fermate</span><strong>${consegne.length}</strong></div>
        <div class="summary-row"><span>Avvisi critici</span><strong>${counts.critici}</strong></div>
        <div class="summary-row"><span>Soste con attesa</span><strong>${counts.attesa}</strong></div>
        <div class="summary-highlight"><span>Costo totale stimato</span><strong>€ ${r.costo_totale ?? r.costo_carburante ?? "-"}</strong></div>
        <a target="_blank" href="${esc(r.google_maps_url||'#')}"><button class="btn-primary full">Apri in Google Maps</button></a>
        <button class="btn-secondary full" onclick="copyText(lastMapsUrl, 'Link Google Maps copiato')">Condividi link Google Maps</button>
        <button class="btn-secondary full" onclick="printStopsTable()">Stampa dettaglio fermate</button>
      </aside>
    </div>
  </section>`;
}

async function optimizeRoute(){
  if(!deliveries.length){ alert("Aggiungi almeno una consegna"); return; }
  const payload = {nome:val("routeName") || "Giro consegne", data_giro:val("routeDate"), orario_partenza:val("routeStart")||"08:00", deposit_id:parseInt(val("routeDeposit")),
    vehicle_id:val("routeVehicle") ? parseInt(val("routeVehicle")) : null, rientro_deposito:boolVal("returnDepot"), prezzo_carburante_litro:parseFloat(val("fuelPrice")||1.75), consegne:deliveries};
  const box = document.getElementById("routeResult");
  box.innerHTML = `<div class="resultBox">Calcolo in corso...</div>`;
  try{
    const r = await api("/api/routes/optimize", {method:"POST", body:JSON.stringify(payload)});
    renderRouteResult(r, "routeResult", false);
    const setText = (id,val)=>{ const el=document.getElementById(id); if(el) el.textContent=val; };
    setText("summaryKm", r.totale_km + " km");
    setText("summaryTime", Math.round(r.totale_minuti) + " min");
    setText("summaryCost", "€ " + r.costo_carburante);
    loadRoutes();
    document.getElementById("routeResult").scrollIntoView({behavior:"smooth", block:"start"});
  }catch(e){ box.innerHTML = `<div class="resultBox warn">Errore calcolo: ${esc(e.message)}</div>`; }
}
async function loadRoutes(){
  const rows = await api("/api/routes");
  const body = document.getElementById("routesBody");
  body.innerHTML = "";
  rows.forEach(r=>{
    body.innerHTML += `<tr><td>${esc(r.data_giro)}</td><td><strong>${esc(r.nome)}</strong></td><td>${r.orario_partenza||""}</td><td>${r.orario_rientro_stimato||""}</td><td>${r.totale_km}</td><td>€ ${r.costo_carburante}</td><td class="row-actions"><button onclick="openSavedRoute(${r.id})">Apri risultato</button>${r.google_maps_url?`<a target="_blank" href="${r.google_maps_url}"><button>Maps</button></a><button onclick="copyText('${String(r.google_maps_url).replace(/'/g,"\\'")}', 'Link Google Maps copiato')">Condividi</button>`:""}</td></tr>`;
  });
}
async function openSavedRoute(id){
  try{
    const r = await api(`/api/routes/${id}`);
    renderRouteResult(r, "historyResult", true);
    document.getElementById("historyResult").scrollIntoView({behavior:"smooth", block:"start"});
  }catch(e){ alert(e.message); }
}
checkLogin().catch(()=>{});
