const API='http://127.0.0.1:8000/api';
export const token=()=>localStorage.getItem('fg_token');
export const setToken=(t)=>localStorage.setItem('fg_token',t);
async function request(path,opts={}){
  const headers={...(opts.headers||{})}; if(token()) headers.Authorization=`Bearer ${token()}`;
  const r=await fetch(API+path,{...opts,headers}); const data=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(data.detail||'Request failed'); return data;
}
export const login=(body)=>request('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export const register=(body)=>request('/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export const dashboard=()=>request('/dashboard');
export const simulate=()=>request('/transactions/simulate',{method:'POST'});
export const sendLocation=(body)=>request('/location',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export const sendBehavior=(body)=>request('/behavior',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export const behaviorStatus=()=>request('/behavior/status');
export async function importCsv(file){const f=new FormData();f.append('file',file);return request('/transactions/import',{method:'POST',body:f});}
