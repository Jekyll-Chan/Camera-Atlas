"use strict";
const $ = id => document.getElementById(id);
const state = {photo:null, image:null, places:[], place:null, confirmed:false, step:1,
  selected:false, result:null, mode:"paint", drawing:false, last:null, undo:[], busy:false, job:null, submitKey:null};
const mask = document.createElement("canvas"), mc = mask.getContext("2d", {willReadFrequently:true});
const view = $("editor"), vc = view.getContext("2d");
const tint = document.createElement("canvas"), tc = tint.getContext("2d", {willReadFrequently:true});

function status(message="", error=false) { $("status").textContent=message; $("status").classList.toggle("error",error); }
function rememberJob(id) { try { id ? localStorage.setItem("cameraAtlasJob",id) : localStorage.removeItem("cameraAtlasJob"); } catch {} }
function invalidate() { state.job=null; state.submitKey=null; rememberJob(null); $("retryJob").hidden=true; document.querySelector('[data-step="3"]').disabled=!state.confirmed; state.result=null; $("generate").disabled=!state.selected; document.querySelector('[data-step="4"]').disabled=true; }
function go(step) {
  if (state.busy || (step>1 && !state.photo) || (step>2 && !state.confirmed) || (step===4 && !state.result)) return;
  state.step=step; document.querySelector(".steps").style.setProperty("--step-index",step-1); status();
  for(let n=1;n<=4;n++) $("step"+n).hidden=n!==step;
  document.querySelectorAll("[data-step]").forEach(b=>{
    Number(b.dataset.step)===step ? b.setAttribute("aria-current","step") : b.removeAttribute("aria-current");
    b.disabled=Number(b.dataset.step)>1 && !state.photo || Number(b.dataset.step)>2 && !state.confirmed || Number(b.dataset.step)===4 && !state.result;
  });
  if(step===3) drawView();
}
async function api(path, body, raw=false, key=null) {
  const headers={"Content-Type":raw?"application/octet-stream":"application/json"};
  if(key)headers["Idempotency-Key"]=key;
  const response=await fetch(path,{method:"POST",headers,body:raw?body:JSON.stringify(body)});
  const result=await response.json(); if(!response.ok) throw new Error(result.error||"Something went wrong. Please try again."); return result;
}
async function busy(message, action) {
  if(state.busy) return;
  state.busy=true; document.body.classList.add("busy"); status(message);
  document.querySelectorAll(".panel").forEach(panel=>panel.inert=true);
  let error=null;
  try { await action(); } catch(e) { error=e.message; }
  finally { state.busy=false; document.body.classList.remove("busy"); document.querySelectorAll(".panel").forEach(panel=>panel.inert=false); }
  go(state.step);
  if(error) {status(error,true); $("retryJob").hidden=!state.job;}
}
async function loadPhoto(photo, placeId) {
  const image=new Image(); image.src=photo.url; await image.decode();
  state.photo=photo; state.image=image; state.place=null; state.confirmed=false; state.selected=false; state.undo=[];
  mask.width=photo.width; mask.height=photo.height; mc.fillStyle="black"; mc.fillRect(0,0,mask.width,mask.height);
  const scale=Math.min(1,1000/photo.width); view.width=Math.round(photo.width*scale); view.height=Math.round(photo.height*scale);
  tint.width=view.width; tint.height=view.height;
  $("undo").disabled=true; $("place").value=placeId ? state.places.find(p=>p.id===placeId).name : "";
  $("chosen").hidden=true; $("confirm").disabled=true; invalidate(); candidates(); state.step=2;
}
$("photo").addEventListener("change",()=>{
  const file=$("photo").files[0]; if(!file)return;
  busy("Opening photo…",async()=>loadPhoto(await api("/api/photo",file,true)));
});
$("sample").onclick=()=>busy("Preparing sample…",async()=>loadPhoto(await api("/api/sample",{place_id:"san-francisco"}),"san-francisco"));
function candidates() {
  const query=$("place").value.trim().toLowerCase(); const target=$("candidates"); target.replaceChildren();
  const matches=state.places.filter(p=>!query||p.aliases.includes(query)||p.name.toLowerCase().includes(query));
  if(!matches.length) {const p=document.createElement("p"); p.className="muted"; p.textContent="Not available in this preview. Try San Francisco or Lake Lucerne."; target.append(p);}
  matches.forEach(p=>{
    const b=document.createElement("button"); b.className="candidate"+(state.place?.id===p.id?" selected":"");
    b.textContent=p.label; const small=document.createElement("small"); small.textContent=p.name+""; b.append(small);
    b.onclick=()=>{state.place=p; state.confirmed=false; invalidate(); $("chosen").hidden=false;
      $("chosen").textContent="Area marker · not an exact camera position"; $("confirm").disabled=false; candidates();};
    target.append(b);
  });
}
$("place").oninput=()=>{state.place=null;state.confirmed=false;$("confirm").disabled=true;$("chosen").hidden=true;invalidate();candidates();};
$("confirm").onclick=()=>{if(!state.place)return;state.confirmed=true;go(3);};
document.querySelectorAll("[data-step]").forEach(b=>b.onclick=()=>go(Number(b.dataset.step)));
function drawView() {
  if(!state.image)return;
  vc.clearRect(0,0,view.width,view.height); vc.drawImage(state.image,0,0,view.width,view.height);
  tc.drawImage(mask,0,0,tint.width,tint.height);const data=tc.getImageData(0,0,tint.width,tint.height);
  let count=0; for(let i=0;i<data.data.length;i+=4) {const on=data.data[i]>127; if(on)count++; data.data[i]=58;data.data[i+1]=143;data.data[i+2]=186;data.data[i+3]=on?90:0;}
  tc.putImageData(data,0,0); vc.drawImage(tint,0,0);state.selected=count>0;$("generate").disabled=!state.selected;
}
function remember() { state.undo.push(mc.getImageData(0,0,mask.width,mask.height)); if(state.undo.length>3)state.undo.shift(); $("undo").disabled=false; }
$("undo").onclick=()=>{if(!state.undo.length)return;mc.putImageData(state.undo.pop(),0,0);$("undo").disabled=!state.undo.length;invalidate();drawView();};
document.querySelectorAll("[data-region]").forEach(b=>b.onclick=()=>{
  remember(); mc.fillStyle="black";mc.fillRect(0,0,mask.width,mask.height);mc.fillStyle="white";
  const kind=b.dataset.region;
  if(kind==="top")mc.fillRect(0,0,mask.width,mask.height*.38);
  if(kind==="right")mc.fillRect(mask.width*.62,0,mask.width*.38,mask.height);
  if(kind==="all")mc.fillRect(0,0,mask.width,mask.height);
  invalidate();drawView();
});
for(const name of ["paint","erase"]) $(name).onclick=()=>{state.mode=name;$("paint").setAttribute("aria-pressed",name==="paint");$("erase").setAttribute("aria-pressed",name==="erase");};
function point(e) { const r=view.getBoundingClientRect();return [(e.clientX-r.left)*mask.width/r.width,(e.clientY-r.top)*mask.height/r.height]; }
function stroke(p) {
  mc.strokeStyle=state.mode==="paint"?"white":"black";mc.fillStyle=mc.strokeStyle;
  mc.lineWidth=Math.min(mask.width,mask.height)*Number($("brush").value)/100;mc.lineCap="round";mc.lineJoin="round";
  mc.beginPath();mc.moveTo(...(state.last||p));mc.lineTo(...p);mc.stroke();mc.beginPath();mc.arc(p[0],p[1],mc.lineWidth/2,0,Math.PI*2);mc.fill();
  state.last=p;invalidate();drawView();
}
view.onpointerdown=e=>{if(state.busy)return;e.preventDefault();remember();state.drawing=true;state.last=null;view.setPointerCapture(e.pointerId);stroke(point(e));};
view.onpointermove=e=>{if(state.drawing){e.preventDefault();stroke(point(e));}};
view.onpointerup=view.onpointercancel=()=>{state.drawing=false;state.last=null;};
$("opacity").oninput=()=>{$("opacityValue").value=$("opacity").value+"%";invalidate();};
async function getJSON(path) {
  const response=await fetch(path); const value=await response.json();
  if(!response.ok)throw new Error(value.error||"Could not reconnect. Please try again.");
  return value;
}
async function followJob(id) {
  state.job=id;rememberJob(id);$("retryJob").hidden=true;
  while(state.job===id) {
    const job=await getJSON(`/api/jobs/${id}`);
    if(job.state==="ready")return showResult(job.result);
    if(job.state==="failed")throw new Error(job.error.message);
    status(({queued:"Queued…",preparing:"Preparing…",rendering:"Mapping…",verifying:"Checking…"})[job.state]||"Processing…");
    await new Promise(resolve=>setTimeout(resolve,1200));
  }
}
async function showResult(result) {
  state.result=result; $("result").src=result.final; await $("result").decode();
  for(const [id,key,name] of [["download","final","camera-atlas.png"],["overlayDownload","overlay","map-overlay.png"],["maskDownload","mask","map-region.png"],["sourceDownload","sources","map-sources.json"]]) {
    $(id).href=result[key]+"?download=1";$(id).download=name;
  }
  const d=result.distribution;$("resultNote").textContent=d&&d.cells_with_geometry<d.eligible_cells?
    "Some areas have no map lines. Please review the map extent.":"";
  $("resultNote").hidden=!$("resultNote").textContent;
  $("compare").textContent="View original";state.step=4;
}
$("generate").onclick=()=>busy("Preparing…",async()=>{
  state.submitKey ||= crypto.randomUUID();
  const job=await api("/api/jobs",{photo_id:state.photo.id,place_id:state.place.id,confirmed:state.confirmed,
    mask:mask.toDataURL("image/png").split(",")[1],opacity:Number($("opacity").value)/100},false,state.submitKey);
  await followJob(job.id);
});
$("retryJob").onclick=()=>busy("Reconnecting…",async()=>{
  await api(`/api/jobs/${state.job}/retry`,{});await followJob(state.job);
});
async function restoreJob() {
  let id;try{id=localStorage.getItem("cameraAtlasJob");}catch{return;}
  if(!id || !/^[a-f0-9]{32}$/.test(id))return;
  await busy("Restoring…",async()=>{
    const job=await getJSON(`/api/jobs/${id}/input`), input=job.input;
    await loadPhoto(await getJSON(`/api/photo/${input.photo_id}`),input.place_id);
    state.place=state.places.find(p=>p.id===input.place_id);state.confirmed=true;
    const selection=new Image();selection.src="data:image/png;base64,"+input.mask;await selection.decode();
    mc.drawImage(selection,0,0);$("opacity").value=input.opacity*100;$("opacityValue").value=input.opacity*100+"%";
    drawView();state.step=3;await followJob(id);
  });
}
$("compare").onclick=()=>{const original=$("compare").textContent==="View original";$("result").src=original?state.photo.url:state.result.final;$("compare").textContent=original?"View print":"View original";};
$("adjust").onclick=()=>go(3);
if(location.protocol === "file:") {
  // A directly opened HTML file can show the design, but cannot run Python.
  $("local-file-notice").hidden=false;
  $("photo").disabled=true; $("sample").disabled=true;
  document.querySelector(".upload").setAttribute("aria-disabled","true");
} else {
  getJSON("/api/places").then(async data=>{state.places=data;candidates();await restoreJob();}).catch(e=>status(e.message,true));
}
