import {api, hydratePhotos} from './supabase-client.js';
const app = document.querySelector('#app');
const dialog = document.querySelector('#like-dialog');
let state = null, authMode = 'login', selectedMatch = null, likedItem = null;
let busy = false, generation = 0, toastTimer;
const older = {};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const route = () => location.hash.slice(1) || 'discover';
const status = text => { document.querySelector('#database-status').textContent = text; };
function toast(text) {
  const el = document.querySelector('#toast'); el.textContent = text; el.classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('visible'), 4500);
}
async function refresh() {
  if (busy) return;
  const stamp = generation;
  try {
    const data = await api('/api/app');
    if (stamp !== generation || busy) return;
    const changed = JSON.stringify(data) !== JSON.stringify(state);
    state = data; status('Connected · updates every 3s');
    if (changed && route() !== 'profile') render();
    else if (!document.querySelector('#profile-form') && route() === 'profile') render();
  } catch (error) {
    if (stamp !== generation || busy) return;
    if (error.status === 401) state = null;
    status(state ? 'Connection lost — retry Refresh' : 'Sign in to continue');
    if (!state) render();
  }
}
async function mutate(path, method, body, after) {
  if (busy) return;
  busy = true; generation++; status('Saving…');
  document.querySelectorAll('button[type="submit"]').forEach(b => b.disabled = true);
  try {
    const result = await api(path, method, body);
    if (result.app) state = result.app;
    generation++; status('Saved · connected');
    if(result.confirmation){toast('Check your email to confirm your account, then log in.');authMode='login';}
    else if (after) after(result);
    render();
    return result;
  } catch (error) { if(error.status === 401 && state){state=null;render();} status('Action failed — please retry'); toast(error.message); }
  finally { busy = false; document.querySelectorAll('button[type="submit"]').forEach(b => b.disabled = false); }
}
function header(title, subtitle, extra='') {
  return `<header class="page-head"><div><span class="eyebrow">MADE FOR SOMETHING REAL</span><h1>${esc(title)}</h1><p class="subtitle">${esc(subtitle)}</p></div>${extra}</header>`;
}
function empty(title, text) {
  return `<section class="empty"><span class="symbol">♡</span><h2>${esc(title)}</h2><p>${esc(text)}</p></section>`;
}
function image(url, name, className='') {
  return url ? `<img data-photo="${esc(url.split('/').pop())}" alt="${esc(name)}" class="${className}" loading="lazy">` : `<div class="photo-placeholder ${className}">☺</div>`;
}
function auth() {
  const signup = authMode === 'signup';
  return header(signup ? 'Your next chapter.' : 'Good to see you.', 'Meet someone through a little curiosity.') +
    `<form id="auth-form" class="edit-form"><h2>${signup ? 'Create an account' : 'Log in'}</h2>
    ${signup ? '<label for="name">Name</label><input id="name" name="name" maxlength="40" required><label for="age">Age (18+)</label><input id="age" name="age" type="number" min="18" max="120" value="27" required>' : ''}
    <label for="email">Email</label><input id="email" name="email" type="email" autocomplete="username" maxlength="254" required>
    <label for="password">Password</label><input id="password" name="password" type="password" minlength="10" maxlength="128" autocomplete="${signup?'new-password':'current-password'}" required>
    <button class="primary" type="submit">${signup?'Create account':'Log in'}</button>
    <button class="secondary" type="button" data-auth-switch>${signup?'Already have an account? Log in':'New here? Create an account'}</button>
    <p class="demo-note">Supabase test accounts: maya@hinge.test, theo@hinge.test, priya@hinge.test, jonah@hinge.test, lena@hinge.test, marcus@hinge.test.<br>Password for all: <strong>HingeTest2026!</strong><br>Confirm your email after creating an account. Use separate browsers or private windows to test two people. Messages come only from signed-in accounts.</p></form>`;
}
function discover() {
  const p = state.discover[0];
  return header('Meet someone new.', 'Good connections start with a little curiosity.') + (!p ?
    empty('You’re all caught up.', 'Revisit passed profiles or check your incoming likes.') + '<button class="secondary" data-revisit>Revisit passed profiles</button>' :
    `<div class="discovery-layout"><div><article class="profile-card"><div class="profile-heading"><h2>${esc(p.name)}, ${p.age}</h2><button class="text-button" data-block="${p.id}">Block</button></div>
    ${p.photos.length ? p.photos.map((url,i) => `<div class="photo-wrap">${image(url,p.name)}<button class="heart" data-like="${p.id}" data-kind="photo" data-item="${url.split('/').pop()}" aria-label="Like ${esc(p.name)}'s photo ${i+1}">♡</button></div>`).join('') : '<div class="photo-wrap photo-placeholder">No photos yet</div>'}
    <div class="details"><span>⌖ ${esc(p.location)}</span><span>${esc(p.job)}</span></div>
    ${p.prompts.map(prompt => `<div class="prompt"><small>${esc(prompt.title)}</small><p>${esc(prompt.answer)}</p><button class="heart" data-like="${p.id}" data-kind="prompt" data-item="${prompt.id}" aria-label="Like ${esc(p.name)}'s prompt">♡</button></div>`).join('')}
    </article><div class="profile-actions"><button class="skip" data-pass="${p.id}" aria-label="Pass on ${esc(p.name)}">×</button><span class="hint">Like a photo or prompt to start something.</span></div></div>
    <aside class="discovery-aside"><div class="note-card"><span class="symbol">✧</span><h3>Less scrolling.<br>More sparks.</h3><p>Make a thoughtful first move. If they like you back, you can start a conversation.</p></div><p class="demo-note">Seeded accounts use illustrative photos. Messages are written by signed-in users. No automated replies.</p></aside></div>`);
}
function likes() {
  return header('Someone noticed you.', 'Like back to open a conversation.') + (state.likes.length ? `<div class="likes-grid">${state.likes.map(l => {
    const p = l.person;
    const prompt = state.me.prompts.find(x => x.id === l.itemID);
    const ownPhoto = state.me.photos.find(x => x.endsWith('/'+l.itemID));
    return `<article class="like-card">${image(p.photos[0],p.name)}<section><span class="eyebrow">LIKED YOUR ${l.itemType.toUpperCase()}</span><h2>${esc(p.name)}, ${p.age}</h2>
      ${prompt?`<p>${esc(prompt.title)} · ${esc(prompt.answer)}</p>`:ownPhoto?`<img class="liked-thumbnail" data-photo="${l.itemID}" alt="Your liked photo">`:'<p>The original item has been removed.</p>'}
      ${l.comment?`<p>“${esc(l.comment)}”</p>`:''}<div class="button-row"><button class="primary" data-accept="${p.id}">Like back & match</button><button class="secondary" data-pass="${p.id}">Pass</button><button class="text-button" data-block="${p.id}">Block</button></div></section></article>`;
  }).join('')}</div>` : empty('All caught up on likes.', 'A like from another account will appear here.'));
}
function matches() {
  if (!state.matches.length) return header('Your next conversation.', 'A match is just the beginning.') + empty('No matches yet.', 'When two people like each other, a conversation opens here.');
  if (!state.matches.some(m => m.id === selectedMatch)) selectedMatch = state.matches[0].id;
  const match = state.matches.find(m => m.id === selectedMatch), p = match.person;
  const messages = [...(older[match.id] || []), ...match.messages].filter((m,i,a) => a.findIndex(x=>x.id===m.id)===i).sort((a,b)=>Number(a.id)-Number(b.id));
  return header('Your next conversation.', 'Messages are delivered to the other signed-in account.') + `<div class="match-layout"><div class="match-list">${state.matches.map(m => `<button class="match-item ${m.id===selectedMatch?'selected':''}" data-chat="${m.id}">${image(m.person.photos[0],m.person.name,'avatar')}<span>${esc(m.person.name)}<small>${esc(m.messages.at(-1)?.text || 'Say hello')}</small></span></button>`).join('')}</div>
    <section class="chat"><div class="chat-header">${esc(p.name)}<div class="button-row"><button class="text-button" data-unmatch="${match.id}">Unmatch</button><button class="text-button" data-block="${p.id}">Block</button></div></div>
    <div class="messages" role="log" aria-label="Messages">${messages.length>=100?`<button class="secondary" data-older="${match.id}" data-before="${messages[0].id}">Load older messages</button>`:''}${messages.map(m=>`<div class="bubble ${m.mine?'mine':''}">${esc(m.text)}</div>`).join('') || '<p class="subtitle">You connected! Start with a hello.</p>'}</div>
    <form class="chat-form" id="chat-form"><input name="message" aria-label="Your message" placeholder="Say hello…" maxlength="1000" required autocomplete="off"><button class="primary" type="submit">Send</button></form></section></div>`;
}
function profile() {
  const p = state.me;
  return header('A little more you.', 'Your account is shared across web and iOS.', '<button class="secondary" data-logout>Log out</button>') +
    `<section class="edit-form"><h3>Your photos</h3><div class="photo-grid">${p.photos.map(url=>`<div>${image(url,'Your profile photo')}<button class="text-button" data-delete-photo="${url.split('/').pop()}">Remove photo</button></div>`).join('')}</div>
    ${p.photos.length<6?'<label for="photo-file">Add a photo (JPEG or PNG)</label><input id="photo-file" type="file" accept="image/jpeg,image/png">':''}
    <form id="profile-form"><div class="field-row"><div><label for="name">Name</label><input id="name" name="name" maxlength="40" value="${esc(p.name)}" required></div><div><label for="age">Age (18+)</label><input id="age" name="age" type="number" min="18" max="120" value="${p.age}" required></div></div>
    <label for="location">Location</label><input id="location" name="location" maxlength="80" value="${esc(p.location)}" required>
    <label for="job">Work</label><input id="job" name="job" maxlength="80" value="${esc(p.job)}">
    ${p.prompts.map((x,i)=>`<label for="prompt-${i}">Prompt ${i+1}</label><input id="prompt-${i}" name="title-${i}" maxlength="100" value="${esc(x.title)}" required><label for="answer-${i}">Your answer</label><textarea id="answer-${i}" name="answer-${i}" maxlength="300" required>${esc(x.answer)}</textarea>`).join('')}
    <button class="primary" type="submit">Save profile</button></form></section>`;
}
function render() {
  const draft = document.querySelector('[name="message"]')?.value || '';
  const focused = document.activeElement?.getAttribute('name') === 'message';
  const position = document.activeElement?.selectionStart;
  const current = route();
  app.innerHTML = state ? ({discover,likes,matches,profile}[current] || discover)() : auth();
  document.querySelectorAll('[data-nav]').forEach(el=>el.classList.toggle('active',el.dataset.nav===current));
  document.querySelector('#match-count').textContent = state?.matches.length || 0;
  document.querySelector('#like-count').textContent = state?.likes.length || 0;
  document.querySelector('#signed-in').textContent = state ? `Signed in as ${state.me.name}` : 'Sign in to connect';
  const input = document.querySelector('[name="message"]');
  if (input) { input.value = draft; if(focused){input.focus();input.setSelectionRange(position,position);} }
  hydratePhotos(app);
  const messages=document.querySelector('.messages'); if(messages) messages.scrollTop=messages.scrollHeight;
}
app.addEventListener('click', async event => {
  const b=event.target.closest('button'); if(!b || busy) return;
  if(b.hasAttribute('data-auth-switch')) { authMode=authMode==='login'?'signup':'login';render(); }
  if(b.dataset.like) {
    likedItem={target:b.dataset.like,itemType:b.dataset.kind,itemID:b.dataset.item};
    document.querySelector('#like-context').textContent=`You’re liking a ${b.dataset.kind}. Add a personal hello.`;
    document.querySelector('#comment').value='';dialog.showModal();
  }
  if(b.dataset.pass) await mutate('/api/pass','POST',{target:b.dataset.pass});
  if(b.hasAttribute('data-revisit')) await mutate('/api/passes','DELETE');
  if(b.dataset.accept) await mutate(`/api/likes/${b.dataset.accept}/accept`,'POST',{},result=>{
    selectedMatch=result.matchID;location.hash='matches';toast('It’s a match!');
  });
  if(b.dataset.chat) { selectedMatch=b.dataset.chat;const input=document.querySelector('[name="message"]');if(input)input.value='';render(); }
  if(b.dataset.block && confirm('Block this person? They will disappear from your profiles, likes, and conversations.')) await mutate('/api/blocks','POST',{target:b.dataset.block});
  if(b.dataset.unmatch && confirm('End this match? Both people will lose access to the conversation.')) await mutate(`/api/conversations/${b.dataset.unmatch}`,'DELETE');
  if(b.dataset.deletePhoto) await mutate(`/api/photos/${b.dataset.deletePhoto}`,'DELETE');
  if(b.hasAttribute('data-logout')) await mutate('/api/logout','POST',{},()=>{state=null;selectedMatch=null;Object.keys(older).forEach(k=>delete older[k]);});
  if(b.dataset.older) {
    try {const result=await api(`/api/conversations/${b.dataset.older}/messages?before=${b.dataset.before}`);older[b.dataset.older]=[...result.messages,...(older[b.dataset.older]||[])];render();if(!result.messages.length)toast('You’ve reached the beginning.');}catch(e){toast(e.message);}
  }
});
app.addEventListener('submit', async event => {
  event.preventDefault();const form=event.target;const data=Object.fromEntries(new FormData(form));
  if(form.id==='auth-form') {
    if(authMode==='signup') data.age=Number(data.age);
    await mutate(authMode==='signup'?'/api/signup':'/api/login','POST',data,()=>{selectedMatch=null;location.hash='discover';});
  }
  if(form.id==='profile-form') {
    const prompts=state.me.prompts.map((p,i)=>({...p,title:data[`title-${i}`],answer:data[`answer-${i}`]}));
    await mutate('/api/profile','PUT',{name:data.name,age:Number(data.age),location:data.location,job:data.job,height:state.me.height,prompts},()=>toast('Profile saved.'));
  }
  if(form.id==='chat-form') {
    const text=data.message.trim();if(!text)return;
    await mutate(`/api/conversations/${selectedMatch}/messages`,'POST',{text,clientID:crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`},()=>{const input=document.querySelector('[name="message"]');if(input)input.value='';});
  }
});
document.querySelector('#like-form').addEventListener('submit', async event=>{
  event.preventDefault();if(!likedItem || busy)return;
  await mutate('/api/likes','POST',{...likedItem,comment:document.querySelector('#comment').value.trim()},result=>{
    dialog.close();if(result.matchID){selectedMatch=result.matchID;location.hash='matches';toast('It’s a match!');}else toast('Like sent.');
  });
});
document.querySelector('.close').addEventListener('click',()=>dialog.close());
app.addEventListener('change',async event=>{
  if(event.target.id!=='photo-file')return;
  const file=event.target.files[0];if(!file)return;
  if(file.size>15*1024*1024){toast('Choose a photo smaller than 15 MB.');return;}
  try {
    const bitmap=await createImageBitmap(file);const scale=Math.min(1,1200/Math.max(bitmap.width,bitmap.height));
    const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
    canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
    const data=canvas.toDataURL('image/jpeg',0.82).split(',')[1];
    await mutate('/api/photos','POST',{data});
  }catch(e){toast('Could not load that photo. Try JPEG or PNG.');}
});
document.querySelector('#refresh').addEventListener('click',refresh);
window.addEventListener('hashchange',render);
setInterval(()=>{if(!document.hidden && state)refresh();},3000);
render();refresh();
