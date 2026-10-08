"use strict";
const $ = id => document.getElementById(id);
const defaults={openai:"gpt-6-luna",anthropic:"claude-haiku-5-5",gemini:"gemini-3.8-flash",chatgpt:"gpt-6-luna",github:"gpt-5.4"};
const settled=state=>["completed","failed","interrupted","awaiting-selection"].includes(state);
let selected=null, displayed=null, epoch=0, timer=null, pending=null, sending=false, preparing=false, admitting=false, database=null;
let libraryTimer=null, libraryEpoch=0;
const revisionCues=new Map();
const scope=sessionStorage.getItem("infographic-tab")||crypto.randomUUID();
sessionStorage.setItem("infographic-tab",scope);
const fields=["mode","panels","orientation","layout","style","representation","candidates","selection","constraints","provider","model","reasoning_effort","image_model","repair_rounds"];
for(const name of fields){
  const original=$("create").elements.namedItem(name);
  const label=original.closest("label").cloneNode(true);
  label.removeAttribute("data-guided");
  $("revision-settings").append(label);
}
function notice(text){$("notice").textContent=text;}
function controls(){
  document.querySelectorAll("form button,#candidates button").forEach(button=>button.disabled=Boolean(pending)||sending||preparing||admitting);
  $("recovery").hidden=!pending;
  $("retry").disabled=sending;
}
function saveIntent(value){
  return new Promise((resolve,reject)=>{
    const transaction=database.transaction("intent","readwrite");
    const store=transaction.objectStore("intent");
    if(value)store.put(value,scope);else store.delete(scope);
    transaction.oncomplete=resolve;transaction.onerror=()=>reject(transaction.error);
  });
}
async function api(path,body){
  const response=await fetch(path,body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json","X-Infographic":"1"},body:JSON.stringify(body)});
  const value=await response.json();
  if(!response.ok){const error=new Error(value.error||"Request failed.");error.definite=response.status<500;throw error;}
  return value;
}
function shape(form){
  const free=form.elements.namedItem("mode").value==="freeform";
  for(const name of ["panels","layout","representation"]){
    const field=form.elements.namedItem(name);field.disabled=free;field.closest("label").hidden=free;
  }
  if(form.id==="create"){
    $("topic-label").textContent=free?"What should we create?":"What should we explain?";
    form.elements.topic.placeholder=free?"A watercolor observatory on a coastal cliff at blue hour. No text.":"Explain how a heat pump works to a curious homeowner.";
    form.querySelector("button").textContent=free?"Create image":"Create infographic";
    $("empty").querySelector(".eyebrow").textContent=free?"YOUR IDEA, YOUR IMAGE":"FROM INFORMATION TO UNDERSTANDING";
    $("empty").querySelector("h2").textContent=free?"Bring your visual idea to life.":"A visual story, not another wall of text.";
    $("empty").querySelector("h2 + p").textContent=free?
      "Describe the subject, composition and treatment you want. Create artwork, review the image, then refine it without losing the original.":
      "Start with a clear brief. Get a plan, individual panels, an assembled image and a review of the actual pixels.";
    $("planning-hint").textContent=free?"Freeform creates one image per alternative, following your direction.":"Automatic planning can choose up to six panels; set an explicit count to bound it more tightly.";
  }
}
function values(form){
  const data={};
  for(const name of fields){
    const value=form.elements.namedItem(name).value;
    data[name]=name==="panels"?(value?Number(value):null):["candidates","repair_rounds"].includes(name)?Number(value):value;
  }
  if(data.mode==="freeform"){data.panels=null;data.layout="auto";data.representation="auto";}
  return data;
}
function draftKey(id){return `infographic-draft-${id}`;}
function retainDraft(){
  if(displayed)sessionStorage.setItem(draftKey(displayed),JSON.stringify({
    feedback:$("refine").elements.feedback.value,changes:values($("refine")),
    clear_references:$("refine").elements.clear_references.checked,
    clear_style_references:$("refine").elements.clear_style_references.checked
  }));
}
for(const form of [$("create"),$("refine")]){
  form.elements.provider.addEventListener("change",()=>{
    form.elements.model.value=defaults[form.elements.provider.value];
    if(form.id==="refine")retainDraft();
  });
  form.elements.mode.addEventListener("change",()=>shape(form));
}
$("refine").addEventListener("input",retainDraft);
$("refine").addEventListener("change",retainDraft);
async function upload(files,limit){
  if(files.length>limit)throw new Error(`Use at most ${limit} images for this role.`);
  return Promise.all(Array.from(files).map(file=>new Promise((resolve,reject)=>{
    if(file.size>4*1024*1024){reject(new Error("Each upload must be at most 4 MiB."));return;}
    const reader=new FileReader();
    reader.onerror=()=>reject(new Error("Could not read uploaded image."));
    reader.onload=()=>resolve(String(reader.result).split(",")[1]);
    reader.readAsDataURL(file);
  })));
}
async function refresh(){
  const generation=++libraryEpoch;clearTimeout(libraryTimer);
  const records=await api("/api/results");
  await Promise.all(records.filter(record=>record.parent_id&&!revisionCues.has(record.id)).map(async record=>{
    try{
      const detail=await api(`/api/result/${record.id}`);
      revisionCues.set(record.id,(detail.feedback||"").replace(/\s+/g," ").trim().slice(0,70));
    }catch{ /* A missing revision detail must not hide the retained status row. */ }
  }));
  if(generation!==libraryEpoch)return;
  const remaining=new Set(records.map(record=>record.id));
  for(const row of $("library").children)if(!remaining.has(row.dataset.id))row.remove();
  for(const record of records){
    let button=$("library").querySelector(`[data-id="${record.id}"]`);
    if(!button){
      button=document.createElement("button");button.className="item";button.dataset.id=record.id;
      button.onclick=()=>show(record.id).catch(error=>notice(error.message));
      $("library").append(button);
    }
    const version=record.parent_id?`Revision ${record.id.slice(0,6)} of ${record.parent_id.slice(0,6)}${revisionCues.get(record.id)?`: ${revisionCues.get(record.id)}`:""}`:`Original ${record.id.slice(0,6)}`;
    const label=`${record.brief.topic.slice(0,65)} · ${version} · ${record.status}`;
    if(button.textContent!==label)button.textContent=label;
  }
  if(records.some(record=>!settled(record.status)))libraryTimer=setTimeout(()=>refresh().catch(()=>{
    $("connection").textContent="Local · list refresh failed; use Refresh";
  }),2000);
}
async function show(id,poll=false){
  if(!poll&&displayed)retainDraft();
  const generation=++epoch;selected=id;
  clearTimeout(timer);
  if(!poll){displayed=null;$("refine").hidden=true;$("candidates").replaceChildren();$("interrupt").hidden=true;}
  const record=await api(`/api/result/${id}`);
  if(generation!==epoch||selected!==id)return;
  const adopting=displayed!==id;
  displayed=id;sessionStorage.setItem("infographic-selected",id);
  $("empty").hidden=true;$("result").hidden=false;
  $("state").textContent=record.status;$("title").textContent=record.plan?.title||record.brief.topic;
  $("identity").textContent=`Result ${id}${record.parent_id?` · revision of ${record.parent_id}`:""}`;
  $("metadata").textContent=JSON.stringify(record,null,2);
  const src=record.composite?`/artifact/${id}/${record.composite}`:null;
  $("composite").hidden=!src;$("download").hidden=!src;
  if(src){$("composite").src=src;$("download").href=src;$("download").download=`image-${id}.png`;}
  else $("composite").removeAttribute("src");
  $("files").replaceChildren();
  for(const file of record.files){
    const link=document.createElement("a");link.href=`/artifact/${id}/${file.name}`;link.download=file.name;link.textContent=file.name;$("files").append(link);
  }
  $("candidates").replaceChildren();
  for(const candidate of record.candidates||[]){
    const card=document.createElement("section"),image=document.createElement("img"),title=document.createElement("h3"),detail=document.createElement("p");
    image.src=`/artifact/${id}/${candidate.image}`;image.alt=`Candidate ${candidate.id}: ${candidate.label}`;
    title.textContent=candidate.label;detail.textContent=candidate.difference;
    card.append(image,title,detail);
    if(record.selection?.candidate===candidate.id){
      const chosen=document.createElement("p");chosen.textContent=`Selected · ${record.selection.actor}`;card.append(chosen);
    }else if(record.status==="awaiting-selection"){
      const button=document.createElement("button");button.textContent=`Choose ${candidate.id}`;
      button.onclick=()=>{if(displayed===id)submit("/api/select",{id,candidate:candidate.id},generation);};
      card.append(button);
    }
    $("candidates").append(card);
  }
  const review=record.attempts.at(-1)?.review;
  $("review").textContent=review?`${review.verdict}: ${review.summary}`:"No completed visual review yet.";
  $("issues").replaceChildren();
  for(const issue of review?.issues||[]){
    const item=document.createElement("li");item.textContent=`${issue.category}: ${issue.detail} Correction: ${issue.correction}`;$("issues").append(item);
  }
  if(adopting){
    const draft=JSON.parse(sessionStorage.getItem(draftKey(id))||"null");
    const settings=draft?.changes||record.brief;
    for(const name of fields)$("refine").elements.namedItem(name).value=settings[name]??"";
    $("refine").elements.feedback.value=draft?.feedback||"";
    for(const name of ["references","style_references"]){$("refine").elements.namedItem(name).value="";$("refine").elements.namedItem(`clear_${name}`).checked=draft?.[`clear_${name}`]===true;}
    shape($("refine"));
  }
  $("refine").hidden=record.status!=="completed";
  $("interrupt").hidden=settled(record.status);
  $("interrupt").onclick=async()=>{
    if(displayed!==id)return;
    try{await api("/api/close-interrupted",{id});if(displayed===id)await show(id,true);}
    catch(error){notice(error.message);}
  };
  notice(pending?"Submission pending. Waiting for acknowledgement; your exact request is retained.":record.error||(record.status==="awaiting-selection"?"Choose a candidate. No later panels run until you select.":
    record.status==="completed"?"Execution completed. Review the actual findings; completion is not a perfect-quality claim.":
    `Retained stage: ${record.status}. If the process stopped, acknowledge interruption; it is never replayed automatically.`));
  controls();
  if(!settled(record.status))timer=setTimeout(()=>show(id,true).catch(error=>notice(error.message)),2000);
}
async function sendSaved(){
  if(!pending||sending)return;
  sending=true;controls();
  const intent=pending;
  notice("Submission pending. Waiting for acknowledgement; your exact request is retained.");
  try{
    const result=await api(intent.path,intent.body);
    await saveIntent(null);pending=null;
    await refresh();
    if(epoch===intent.epoch)await show(result.id);
    else notice(`Work retained as ${result.id}. Your current selection has not changed.`);
  }catch(error){
    if(error.definite){await saveIntent(null);pending=null;}
    notice(`${error.message} Request identity: ${intent.body.request_id}. ${error.definite?"No automatic retry.":"Response uncertain: check retained work or retry the exact saved request."}`);
  }finally{sending=false;controls();}
}
async function submit(path,body,originEpoch=epoch){
  if(pending||sending||admitting){notice("Reconcile the retained pending request first.");return;}
  admitting=true;controls();
  notice("Saving your request before submission. No generation is confirmed yet.");
  const intent={path,body:{...body,request_id:crypto.randomUUID().replaceAll("-","")},epoch:originEpoch};
  try{await saveIntent(intent);pending=intent;controls();await sendSaved();}
  catch(error){notice(`Could not persist request safely: ${error.message}. Nothing was submitted.`);}
  finally{admitting=false;controls();}
}
$("create").onsubmit=async event=>{
  event.preventDefault();if(preparing||admitting||pending||sending)return;preparing=true;controls();
  notice("Preparing your creation request and references. No generation is confirmed yet.");
  const form=event.target,originEpoch=epoch;
  const brief={...values(form),topic:form.elements.topic.value,source:form.elements.source.value};
  const contentFiles=Array.from(form.elements.references.files),styleFiles=Array.from(form.elements.style_references.files);
  try{
    const references=await upload(contentFiles,3),style_references=await upload(styleFiles,2);
    await submit("/api/generate",{brief,references,style_references},originEpoch);
  }catch(error){notice(error.message);}
  finally{preparing=false;controls();}
};
$("refine").onsubmit=async event=>{
  event.preventDefault();if(!displayed||preparing||admitting||pending||sending)return;preparing=true;controls();
  notice("Preparing your revision request and references. The original stays unchanged.");
  const form=event.target,id=displayed,originEpoch=epoch;
  const body={id,feedback:form.elements.feedback.value,changes:values(form)};
  const attachments=[["references",3],["style_references",2]].map(([name,limit])=>({
    name,limit,clear:form.elements.namedItem(`clear_${name}`).checked,files:Array.from(form.elements.namedItem(name).files)
  }));
  try{
    for(const {name,limit,clear,files} of attachments){
      if(clear)body[name]=[];
      else if(files.length)body[name]=await upload(files,limit);
    }
    await submit("/api/refine",body,originEpoch);
  }catch(error){notice(error.message);}
  finally{preparing=false;controls();}
};
$("refresh").onclick=()=>refresh().catch(error=>notice(error.message));
$("retry").onclick=()=>sendSaved();
$("observe").onclick=async()=>{
  if(!pending)return;
  try{
    const id=pending.path==="/api/select"?pending.body.id:pending.body.request_id;
    const record=await api(`/api/result/${id}`);
    if(pending.path==="/api/select"&&record.selection?.request_id!==pending.body.request_id)throw new Error("This selection is not recorded. Retry only the exact saved request.");
    await saveIntent(null);pending=null;controls();await show(id);
  }catch(error){notice(`${error.message} No automatic replay. The exact request remains saved.`);}
};
(async()=>{
  const token=new URLSearchParams(location.hash.slice(1)).get("token");
  if(token){
    const response=await fetch("/api/session",{method:"POST",headers:{"X-Infographic-Token":token}});
    if(!response.ok)throw new Error("Invalid launch URL.");
    history.replaceState(null,"","/");
  }
  database=await new Promise((resolve,reject)=>{
    const request=indexedDB.open("infographic-requests",1);
    request.onupgradeneeded=()=>request.result.createObjectStore("intent");
    request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
  });
  pending=await new Promise((resolve,reject)=>{
    const request=database.transaction("intent").objectStore("intent").get(scope);
    request.onsuccess=()=>resolve(request.result||null);request.onerror=()=>reject(request.error);
  });
  shape($("create"));await refresh();$("connection").textContent="Local · connected";controls();
  const previous=sessionStorage.getItem("infographic-selected");
  if(previous)await show(previous);else notice("Ready. Guided infographics or freeform images: your direction comes first.");
})().catch(error=>{document.querySelectorAll("form button").forEach(button=>button.disabled=true);$("connection").textContent="Not connected";notice(error.message);});