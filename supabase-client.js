import {SUPABASE_URL as base, SUPABASE_PUBLISHABLE_KEY as key} from './supabase-config.js';
const storageKey = 'hinge-supabase-session-v1';
let session;
try { session = JSON.parse(localStorage.getItem(storageKey)); } catch { session = null; }
let refreshing = null;
const photos = new Map();
let photoEpoch = 0;
function save(value) {
  session = value;
  if (value) localStorage.setItem(storageKey, JSON.stringify(value)); else localStorage.removeItem(storageKey);
}
function clearPhotos() { photoEpoch++; for (const value of photos.values()) if(typeof value === 'string') URL.revokeObjectURL(value); photos.clear(); }
window.addEventListener('storage', event => { if(event.key===storageKey){session=event.newValue?JSON.parse(event.newValue):null;clearPhotos();} });
async function raw(path, {method='GET', body, token, binary=false, mime='application/json'}={}) {
  const headers = {apikey:key};
  if(token) headers.Authorization='Bearer '+token;
  if(body!==undefined) headers['Content-Type']=mime;
  if(binary)headers['Cache-Control']='max-age=0';
  if(path.startsWith('/storage/v1/object/authenticated/'))headers['Cache-Control']='no-cache';
  const response=await fetch(base+path,{method,headers,body:body===undefined?undefined:binary?body:JSON.stringify(body),cache:'no-store'});
  if(!response.ok){const data=await response.json().catch(()=>({}));const e=new Error(data.message||data.msg||data.error_description||data.error||'Supabase request failed');e.status=response.status;throw e;}
  return response;
}
function remember(data) {
  const value={access_token:data.access_token,refresh_token:data.refresh_token,expires_at:data.expires_at||Math.floor(Date.now()/1000)+data.expires_in,user:data.user};save(value);return value;
}
async function accessToken() {
  if(!session){const e=new Error('Please log in');e.status=401;throw e;}
  if(session.expires_at > Date.now()/1000+60) return session.access_token;
  if(!refreshing) refreshing=(async()=>{
    try {const response=await raw('/auth/v1/token?grant_type=refresh_token',{method:'POST',body:{refresh_token:session.refresh_token}});return remember(await response.json()).access_token;}
    catch(e){if(e.status===400||e.status===401){save(null);clearPhotos();}throw e;}
    finally{refreshing=null;}
  })();
  return refreshing;
}
async function rpc(name, body={}) {
  return (await raw('/rest/v1/rpc/'+name,{method:'POST',body,token:await accessToken()})).json();
}
async function removeObject(path) {
  await raw('/storage/v1/object/dating-photos',{method:'DELETE',body:{prefixes:[path]},token:await accessToken()});
}
async function photoInfo(id) { return rpc('dating_photo',{p_id:id}); }
export async function hydratePhotos(root) {
  const epoch=photoEpoch;
  for(const img of root.querySelectorAll('img[data-photo]')){
    const id=img.dataset.photo;
    try {
      if(!photos.has(id)) photos.set(id,(async()=>{
        const info=await photoInfo(id);
        const response=await raw('/storage/v1/object/authenticated/dating-photos/'+info.path,{token:await accessToken()});
        return URL.createObjectURL(await response.blob());
      })());
      const url=await photos.get(id);
      if(epoch!==photoEpoch){if(typeof url==='string')URL.revokeObjectURL(url);continue;}
      photos.set(id,url);if(img.isConnected)img.src=url;
    }catch{photos.delete(id);if(img.isConnected)img.alt='Photo unavailable';}
  }
}
export async function api(path, method='GET', body) {
  if(path==='/api/login'||path==='/api/signup') {
    const signup=path.endsWith('signup');
    const response=await raw(signup?'/auth/v1/signup':'/auth/v1/token?grant_type=password',{
      method:'POST',body:signup?{email:body.email,password:body.password,data:{name:body.name,age:body.age}}:{email:body.email,password:body.password}});
    const data=await response.json();
    if(!data.access_token)return {confirmation:true};
    remember(data);clearPhotos();return {app:await rpc('dating_bootstrap')};
  }
  if(path==='/api/logout'){
    try{await raw('/auth/v1/logout?scope=local',{method:'POST',body:{},token:await accessToken()});}
    catch{} finally{save(null);clearPhotos();}
    return {ok:true};
  }
  if(path==='/api/app')return rpc('dating_bootstrap');
  const parts=path.split('?')[0].split('/').filter(Boolean);
  if(parts[1]==='conversations'&&parts[3]==='messages'&&method==='GET'){
    const before=new URLSearchParams(path.split('?')[1]).get('before');
    return rpc('dating_messages',{p_conversation:parts[2],...(before?{p_before:before}:{})});
  }
  if(path==='/api/photos'&&method==='POST'){
    const id=crypto.randomUUID?.()||'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=crypto.getRandomValues(new Uint8Array(1))[0]%16;return(c==='x'?r:(r&3)|8).toString(16);});
    const binary=Uint8Array.from(atob(body.data),c=>c.charCodeAt(0));
    const token=await accessToken(), object=session.user.id+'/'+id;
    await raw('/storage/v1/object/dating-photos/'+object,{method:'POST',body:binary,binary:true,mime:'image/jpeg',token});
    try{return await rpc('dating_action',{p_action:'photo_register',p_body:{id,mime:'image/jpeg'}});}
    catch(e){await removeObject(object).catch(()=>{});throw e;}
  }
  if(parts[1]==='photos'&&method==='DELETE'){
    const info=await photoInfo(parts[2]);
    const result=await rpc('dating_action',{p_action:'photo_delete',p_body:{id:parts[2]}});
    await removeObject(info.path).catch(()=>{});clearPhotos();return result;
  }
  let action, payload=body||{};
  if(path==='/api/profile'){action='profile';}
  else if(path==='/api/likes'){action='like';}
  else if(parts[1]==='likes'&&parts[3]==='accept'){action='accept';payload={target:parts[2]};}
  else if(path==='/api/pass'){action='pass';}
  else if(path==='/api/passes'){action='revisit';}
  else if(path==='/api/blocks'){action='block';clearPhotos();}
  else if(parts[1]==='conversations'){action=method==='DELETE'?'unmatch':'message';payload={...payload,conversation:parts[2]};}
  else throw new Error('Unknown operation');
  return rpc('dating_action',{p_action:action,p_body:payload});
}
