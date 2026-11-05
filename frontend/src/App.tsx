import { createContext, useContext, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useOutletContext, useSearchParams } from 'react-router-dom';
import { Activity, ArrowLeft, ArrowRight, Bell, Braces, CheckCircle2, ChevronDown, CircleHelp, Code2, FileJson2, FolderKanban, Gauge, GitCompareArrows, LockKeyhole, LogOut, MailCheck, Menu, Plus, Search, Settings, ShieldCheck, Sparkles, Trash2, UploadCloud, X } from 'lucide-react';

type User={id:number;email:string;display_name:string;created_at:string;is_active:boolean};
const API=import.meta.env.VITE_API_BASE_URL||'/api';
const accessKey='api-inspector-access',refreshKey='api-inspector-refresh';
const access=()=>sessionStorage.getItem(accessKey),refresh=()=>sessionStorage.getItem(refreshKey);
const clear=()=>{sessionStorage.removeItem(accessKey);sessionStorage.removeItem(refreshKey)};
let refreshPromise:Promise<string|null>|null=null;
async function refreshAccessToken():Promise<string|null>{
  const currentRefresh=refresh();
  if(!currentRefresh)return null;
  if(!refreshPromise){
    refreshPromise=(async()=>{
      try{
        const response=await fetch(API+'/accounts/token/refresh/',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({refresh:currentRefresh})
        });
        if(!response.ok){clear();return null}
        const tokens:{access:string;refresh?:string}=await response.json();
        sessionStorage.setItem(accessKey,tokens.access);
        if(tokens.refresh)sessionStorage.setItem(refreshKey,tokens.refresh);
        return tokens.access;
      }catch{
        clear();
        return null;
      }finally{
        refreshPromise=null;
      }
    })();
  }
  return refreshPromise;
}
class ApiError extends Error{}
async function request<T>(path:string,options:RequestInit&{auth?:boolean;retry?:boolean}={}):Promise<T>{
  const {auth=true,retry=true,...init}=options;const headers=new Headers(init.headers);
  if(!(init.body instanceof FormData)&&!headers.has('Content-Type'))headers.set('Content-Type','application/json');
  if(auth&&access())headers.set('Authorization','Bearer '+access());
  let response=await fetch(API+path,{...init,headers});
  if(response.status===401&&auth&&retry&&refresh()){
    const renewedAccess=await refreshAccessToken();
    if(renewedAccess){
      headers.set('Authorization','Bearer '+renewedAccess);
      response=await fetch(API+path,{...init,headers});
    }
  }
  const raw=await response.text();let data:any=null;try{data=raw?JSON.parse(raw):null}catch{data=raw}
  if(!response.ok){if(response.status===401&&auth)clear();const first=data&&typeof data==='object'?Object.values(data)[0]:null;throw new ApiError(data?.detail|| (Array.isArray(first)?first[0]:first)||'Something went wrong. Please try again.')}
  return data as T;
}
type AuthValue={user:User|null;loading:boolean;login:(email:string,password:string)=>Promise<void>;register:(payload:any)=>Promise<void>;logout:()=>Promise<void>;reload:()=>Promise<void>};
const AuthContext=createContext<AuthValue|null>(null);
function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('AuthProvider is missing');return value}
function App(){
  const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true);
  const reload=async()=>setUser(await request<User>('/accounts/me/'));
  useEffect(()=>{let alive=true;(async()=>{if(!access()&&!refresh()){setLoading(false);return}try{const profile=await request<User>('/accounts/me/');if(alive)setUser(profile)}catch{clear();if(alive)setUser(null)}finally{if(alive)setLoading(false)}})();return()=>{alive=false}},[]);
  const login=async(email:string,password:string)=>{const tokens=await request<{access:string;refresh:string}>('/accounts/login/',{method:'POST',auth:false,body:JSON.stringify({email,password})});sessionStorage.setItem(accessKey,tokens.access);sessionStorage.setItem(refreshKey,tokens.refresh);await reload()};
  const register=async(payload:any)=>{await request('/accounts/register/',{method:'POST',auth:false,body:JSON.stringify(payload)})};
  const logout=async()=>{try{if(refresh())await request('/accounts/logout/',{method:'POST',body:JSON.stringify({refresh:refresh()}),retry:false})}finally{clear();setUser(null)}};
  const value=useMemo(()=>({user,loading,login,register,logout,reload}),[user,loading]);
  return <AuthContext.Provider value={value}><Routes>
    <Route path="/" element={<Navigate to="/app" replace/>}/>
    <Route path="/login" element={<Guest><Login/></Guest>}/><Route path="/register" element={<Guest><Register/></Guest>}/>
    <Route path="/forgot-password" element={<Guest><Forgot/></Guest>}/><Route path="/verify-email" element={<Verify/>}/><Route path="/reset-password" element={<Reset/>}/>
    <Route path="/app" element={<Protected/>}><Route index element={<Overview/>}/><Route path="applications" element={<Applications/>}/><Route path="specifications" element={<Specifications/>}/><Route path="inspections" element={<Inspections/>}/><Route path="settings" element={<SettingsPage/>}/></Route>
    <Route path="*" element={<Navigate to="/app" replace/>}/>
  </Routes></AuthContext.Provider>
}
function Guest({children}:{children:ReactNode}){const {user,loading}=useAuth();if(loading)return <Loading/>;return user?<Navigate to="/app" replace/>:<>{children}</>}
function Protected(){const {user,loading}=useAuth();if(loading)return <Loading/>;return user?<Shell/>:<Navigate to="/login" replace/>}
function Loading(){return <div className="loading"><span className="mark">A</span> Preparing your workspace...</div>}
function Brand(){return <Link to="/app" className="brand" aria-label="API Inspector home"><span className="mark"><Activity size={19}/></span><span>api<span>inspector</span></span></Link>}
function AuthLayout({eyebrow,title,subtitle,children}:{eyebrow:string;title:string;subtitle:string;children:ReactNode}){
 return <main className="auth"><section className="auth-main"><header><Brand/><small>API quality, made visible</small></header><div className="auth-box"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p className="sub">{subtitle}</p>{children}</div><footer>© 2026 API Inspector <span>Built for developers</span></footer></section><aside className="auth-side"><div className="side-kicker"><i/> API INTELLIGENCE PLATFORM</div><h2>Know what your<br/><em>API actually does.</em></h2><p>Bring your API contracts and real-world behavior into one clear picture.</p><div className="code-window"><div className="window-head"><span>● ● ●</span> contract-overview.json <b>LIVE PREVIEW</b></div><div><i>01</i><strong>GET</strong> /api/v1/users <small>200 OK</small></div><div><i>02</i><strong>POST</strong> /api/v1/auth <small>201 OK</small></div><div><i>03</i><strong className="warn">WARN</strong> Response schema differs</div><section><span><GitCompareArrows/> Contract comparison <CheckCircle2/></span><span><ShieldCheck/> Security visibility <CheckCircle2/></span><span><Braces/> OpenAPI discovery <ArrowRight/></span></section></div><label>— Clear contracts. Confident releases.</label></aside></main>
}
function Field({label,...props}:{label:string}&React.InputHTMLAttributes<HTMLInputElement>){return <div className="field"><label htmlFor={props.name}>{label}</label><input className="input" id={props.name} {...props}/></div>}
function ErrorMsg({children}:{children:string}){return children?<div className="error-msg">{children}</div>:null}
function Login(){const {login}=useAuth(),nav=useNavigate();const[email,setEmail]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);const submit=async(e:FormEvent)=>{e.preventDefault();setBusy(true);setError('');try{await login(email,password);nav('/app')}catch(x){setError((x as Error).message)}finally{setBusy(false)}};return <AuthLayout eyebrow="WELCOME BACK" title="Good to see you." subtitle="Sign in to continue building APIs you can trust."><form onSubmit={submit}><Field label="Email address" name="email" type="email" placeholder="you@company.com" autoComplete="email" required value={email} onChange={e=>setEmail(e.target.value)}/><div className="field"><div className="field-row"><label>Password</label><Link to="/forgot-password">Forgot password?</Link></div><input className="input" name="password" type="password" placeholder="Enter your password" autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)}/></div><ErrorMsg>{error}</ErrorMsg><button className="primary full" disabled={busy}>{busy?'Signing in...':'Sign in'} <ArrowRight size={16}/></button></form><div className="switch">New to API Inspector? <Link to="/register">Create an account</Link></div><div className="secure"><LockKeyhole size={14}/> Your workspace is protected with secure authentication.</div></AuthLayout>}
function Register(){const{register}=useAuth();const[email,setEmail]=useState(''),[name,setName]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[error,setError]=useState(''),[done,setDone]=useState(false),[busy,setBusy]=useState(false);const submit=async(e:FormEvent)=>{e.preventDefault();if(password!==confirm){setError('Your passwords do not match.');return}setBusy(true);setError('');try{await register({email,display_name:name,password,confirm_password:confirm});setDone(true)}catch(x){setError((x as Error).message)}finally{setBusy(false)}};return <AuthLayout eyebrow="GET STARTED" title="Make APIs make sense." subtitle="Create your account and bring clarity to every endpoint.">{done?<Success title="Check your inbox" text={'We sent a verification link to '+email+'. Open it to activate your account.'}/>:<form onSubmit={submit}><Field label="Your name" name="display_name" placeholder="Alex Morgan" required value={name} onChange={e=>setName(e.target.value)}/><Field label="Work email" name="email" type="email" placeholder="you@company.com" required value={email} onChange={e=>setEmail(e.target.value)}/><Field label="Create password" name="password" type="password" placeholder="Create a strong password" required value={password} onChange={e=>setPassword(e.target.value)}/><Field label="Confirm password" name="confirm_password" type="password" placeholder="Repeat your password" required value={confirm} onChange={e=>setConfirm(e.target.value)}/><ErrorMsg>{error}</ErrorMsg><button className="primary full" disabled={busy}>{busy?'Creating account...':'Create account'} <ArrowRight size={16}/></button><p className="terms">Use a strong password you do not use elsewhere.</p></form>}<div className="switch">Already have an account? <Link to="/login">Sign in</Link></div></AuthLayout>}
function Success({title,text}:{title:string;text:string}){return <div className="success"><span><CheckCircle2/></span><h3>{title}</h3><p>{text}</p><Link className="primary full button-link" to="/login">Back to sign in <ArrowRight size={16}/></Link></div>}
function Forgot(){const[email,setEmail]=useState(''),[done,setDone]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);const submit=async(e:FormEvent)=>{e.preventDefault();setBusy(true);try{await request('/accounts/password-reset/',{method:'POST',auth:false,body:JSON.stringify({email})});setDone(true)}catch(x){setError((x as Error).message)}finally{setBusy(false)}};return <AuthLayout eyebrow="ACCOUNT RECOVERY" title="Forgot your password?" subtitle="Enter your email and we’ll send you a reset link.">{done?<Success title="Check your inbox" text={'If an active account exists for '+email+', a reset link is on its way.'}/>:<form onSubmit={submit}><Field label="Email address" name="email" type="email" placeholder="you@company.com" required value={email} onChange={e=>setEmail(e.target.value)}/><ErrorMsg>{error}</ErrorMsg><button className="primary full" disabled={busy}>{busy?'Sending...':'Send reset link'} <ArrowRight size={16}/></button></form>}<div className="switch"><Link to="/login"><ArrowLeft size={14}/> Back to sign in</Link></div></AuthLayout>}
function Verify(){const[params]=useSearchParams();const attempted=useRef(false);const[message,setMessage]=useState('Confirming your email...'),[error,setError]=useState(false);useEffect(()=>{if(attempted.current)return;attempted.current=true;const uid=params.get('uid'),token=params.get('token');if(!uid||!token){setError(true);setMessage('This verification link is incomplete.');return}request<{detail:string}>('/accounts/verify-email/',{method:'POST',auth:false,body:JSON.stringify({uid,token})}).then(x=>setMessage(x.detail)).catch(x=>{setError(true);setMessage(x.message)})},[params]);return <AuthLayout eyebrow="EMAIL VERIFICATION" title="One quick check." subtitle="Confirming your email address."><div className="success"><span><MailCheck/></span><h3>{error?'Verification failed':'Email verification'}</h3><p>{message}</p><Link className="primary full button-link" to="/login">Continue to sign in <ArrowRight size={16}/></Link></div></AuthLayout>}
function Reset(){const[params]=useSearchParams();const[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[error,setError]=useState(''),[done,setDone]=useState(false),[busy,setBusy]=useState(false);const submit=async(e:FormEvent)=>{e.preventDefault();if(password!==confirm){setError('Your passwords do not match.');return}setBusy(true);try{await request('/accounts/password-reset/confirm/',{method:'POST',auth:false,body:JSON.stringify({uid:params.get('uid'),token:params.get('token'),new_password:password,confirm_new_password:confirm})});setDone(true)}catch(x){setError((x as Error).message)}finally{setBusy(false)}};return <AuthLayout eyebrow="NEW PASSWORD" title="Create a new password." subtitle="Choose a strong password you haven’t used before.">{done?<Success title="Password updated" text="Your password has been changed. You can now sign in."/>:<form onSubmit={submit}><Field label="New password" name="new_password" type="password" required value={password} onChange={e=>setPassword(e.target.value)}/><Field label="Confirm new password" name="confirm_new_password" type="password" required value={confirm} onChange={e=>setConfirm(e.target.value)}/><ErrorMsg>{error}</ErrorMsg><button className="primary full" disabled={busy}>{busy?'Updating...':'Update password'} <ArrowRight size={16}/></button></form>}</AuthLayout>}
function Shell(){const{user,logout}=useAuth(),nav=useNavigate(),loc=useLocation();const[mobile,setMobile]=useState(false),[menu,setMenu]=useState(false),[profileMenu,setProfileMenu]=useState(false),[notice,setNotice]=useState('');const title=loc.pathname.includes('applications')?'Applications':loc.pathname.includes('settings')?'Settings':loc.pathname.includes('specifications')?'Specifications':loc.pathname.includes('inspections')?'Inspections':'Overview';const signout=async()=>{await logout();nav('/login')};return <div className="shell">{mobile&&<button className="backdrop" onClick={()=>setMobile(false)}/>}<aside className={'sidebar '+(mobile?'open':'')}><div className="side-brand"><Brand/><button className="mobile-close" onClick={()=>setMobile(false)}><X/></button></div><div className="workspace"><span>A</span><div><b>Personal workspace</b><small>Free plan</small></div><ChevronDown size={15}/></div><small className="nav-label">WORKSPACE</small><nav><NavLink end to="/app"><Gauge/>Overview</NavLink><NavLink to="/app/applications"><FolderKanban/>Applications</NavLink><NavLink to="/app/specifications"><FileJson2/>Specifications</NavLink><NavLink to="/app/inspections"><ShieldCheck/>Inspections</NavLink></nav><small className="nav-label lower">PREFERENCES</small><nav><NavLink to="/app/settings"><Settings/>Settings</NavLink><button onClick={()=>setNotice('Help center will be available soon.')}><CircleHelp/>Help & support</button></nav><div className="side-bottom"><div className="tip"><Sparkles/><b>More clarity, less guesswork.</b><p>Your API workspace is just getting started.</p><button onClick={()=>nav('/app/specifications')}>Explore workspace <ArrowRight size={13}/></button></div><div className="account"><span>{(user?.display_name||'A').charAt(0).toUpperCase()}</span><div><b>{user?.display_name||'Account'}</b><small>{user?.email}</small></div><button onClick={()=>setMenu(!menu)}><ChevronDown size={16}/></button>{menu&&<div className="account-menu"><button onClick={()=>nav('/app/settings')}><Settings/> Account settings</button><button onClick={signout}><LogOut/> Sign out</button></div>}</div></div></aside><main className="main"><header className="topbar"><div className="crumb"><button className="mobile-menu" onClick={()=>setMobile(true)}><Menu/></button>Workspace <span>/</span> <b>{title}</b></div><div className="top-actions"><div className="top-search"><Search/> Search anything <kbd>⌘ K</kbd></div><button onClick={()=>setNotice('You are all caught up.')}><Bell/></button><div className="profile-control"><button className="avatar profile-trigger" aria-label="Open account menu" aria-expanded={profileMenu} onClick={()=>setProfileMenu(!profileMenu)}>{(user?.display_name||'A').charAt(0).toUpperCase()}</button>{profileMenu&&<div className="profile-menu"><div className="profile-menu-heading"><span className="profile-menu-avatar">{(user?.display_name||'A').charAt(0).toUpperCase()}</span><div><b>{user?.display_name||'Account'}</b><small>{user?.email}</small></div></div><div className="profile-status"><i/> {user?.is_active?'Email verified':'Email not verified'}</div><button onClick={()=>{setProfileMenu(false);nav('/app/settings')}}><Settings/> Account settings</button><button onClick={signout}><LogOut/> Sign out</button></div>}</div></div></header>{notice&&<div className="toast">{notice}<button onClick={()=>setNotice('')}><X/></button></div>}<div className="content"><Outlet context={{onNotice:setNotice}}/></div><footer className="app-footer"><span>© 2026 API Inspector</span><span><i/> All systems operational</span><span>Made for better APIs</span></footer></main></div>}
type Context={onNotice:(s:string)=>void};
function Overview(){const{user}=useAuth();const navigate=useNavigate();const first=user?.display_name?.split(' ')[0]||'there';return <><div className="welcome"><div><small className="eyebrow">YOUR WORKSPACE IS READY</small><h1>Good to have you, {first}<em>✦</em></h1><p>Here’s what’s happening across your API workspace.</p></div><button className="primary" onClick={()=>navigate('/app/specifications')}><Plus/> Import specification</button></div><section className="hero"><div><span className="hero-tag"><Sparkles/> YOUR API WORKSPACE</span><h2>Make every API<br/>easier to understand.</h2><p>Start with an OpenAPI specification. Discover endpoints, explore schemas, and build a clearer picture of your API surface.</p><button onClick={()=>navigate('/app/specifications')}>Get started <ArrowRight/></button></div><div className="hero-art"><div className="mock-file"><Code2/> openapi.yaml <i/></div><div className="mock-card"><small>API OVERVIEW</small><strong>—</strong><span>Endpoints discovered</span><div className="bars"><i/><i/><i/><i/><i/><i/></div><small>Waiting for your first spec</small></div><div className="float-card"><Activity/> Contract clarity <b>Starts here</b></div></div></section><div className="section-title"><div><h2>Workspace at a glance</h2><p>Your API activity will appear here as you get started.</p></div><small>JUST NOW</small></div><div className="stats"><Stat icon={<FileJson2/>} label="Specifications" value="0" note="No specs imported yet"/><Stat icon={<Code2/>} label="Endpoints discovered" value="—" note="Waiting for first import"/><Stat icon={<ShieldCheck/>} label="Inspections run" value="0" note="Ready when you are"/><Stat icon={<Activity/>} label="Issues detected" value="—" note="No inspection data yet"/></div><div className="lower-grid"><section className="panel"><div className="panel-title"><Sparkles/><h3>Get started in three steps</h3><small>0 OF 3 COMPLETE</small></div><div className="progress"/>{[['01','Import an API specification','Upload an OpenAPI JSON or YAML file.'],['02','Explore your API surface','Browse endpoints, parameters, and schemas.'],['03','Run your first inspection','Compare documented contracts with real behavior.']].map(x=><div className="step" key={x[0]}><b>{x[0]}</b><div><strong>{x[1]}</strong><p>{x[2]}</p></div><small>NEXT</small></div>)}</section><section className="panel activity-panel"><div className="panel-title"><Activity/><h3>Recent activity</h3><small className="live">● LIVE</small></div><div className="empty"><FolderKanban/><b>No activity yet</b><p>Once you import a specification, your workspace activity will show up here.</p></div></section></div><div className="privacy"><ShieldCheck/> Your data stays yours. API Inspector only works with the specifications and endpoints you choose to provide.</div></>}
function Stat({icon,label,value,note}:{icon:ReactNode;label:string;value:string;note:string}){return <div className="stat"><span>{icon}</span><small>ALL TIME</small><strong>{value}</strong><b>{label}</b><p>{note}</p></div>}
function EmptyPage({kind}:{kind:'specifications'|'inspections'}){const{onNotice}=useOutletContext<Context>();const specs=kind==='specifications';return <div className="subpage"><div className="sub-heading"><div><small className="eyebrow">{specs?'API CATALOG':'QUALITY & RELIABILITY'}</small><h1>{specs?'Specifications':'Inspections'}</h1><p>{specs?'Your imported API contracts, organized in one place.':'Understand the gap between your API contract and real responses.'}</p></div>{specs&&<button className="primary" onClick={()=>onNotice('Specification import is coming next.')}><Plus/> Import specification</button>}</div>{specs&&<div className="toolbar"><div><Search/><input placeholder="Search specifications..."/></div><small>0 specifications</small></div>}<section className="big-empty"><span className="empty-file">{specs?<FileJson2/>:<ShieldCheck/>}</span><small className="eyebrow">{specs?'NOTHING HERE YET':'COMING NEXT'}</small><h2>{specs?'Your API catalog starts here.':'Confidence starts with visibility.'}</h2><p>{specs?'Import an OpenAPI 3.0 or 3.1 file to automatically discover paths, methods, parameters, and schemas.':'Inspection runs will compare live API responses against your OpenAPI contract and surface meaningful differences.'}</p>{specs?<><button className="primary" onClick={()=>onNotice('The import flow will be connected when the specifications API is ready.')}><UploadCloud/> Import your first spec</button><div className="formats">SUPPORTED FORMATS <code>.json</code><code>.yaml</code><code>.yml</code></div></>:<div className="coming"><span>• Response schema comparison</span><span>• Status code validation</span><span>• Latency and contract insights</span></div>}</section></div>}
type Specification = {
  id: number;
  application: number;
  name: string;
  description: string;
  api_version: string;
  openapi_version: string;
  document: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

const emptyOpenApiDocument = JSON.stringify({
  openapi: "3.0.3",
  info: { title: "Example API", version: "1.0.0" },
  paths: {},
}, null, 2);

function Specifications() {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedApplicationId, setSelectedApplicationId] = useState("");
  const [specifications, setSpecifications] = useState<Specification[]>([]);
  const [applicationsLoading, setApplicationsLoading] = useState(true);
  const [specificationsLoading, setSpecificationsLoading] = useState(false);
  const [pageError, setPageError] = useState("");
  const [search, setSearch] = useState("");
  const [dialogMode, setDialogMode] = useState<"create" | "edit" | "view" | null>(null);
  const [activeSpecification, setActiveSpecification] = useState<Specification | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [documentText, setDocumentText] = useState(emptyOpenApiDocument);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let alive = true;
    request<Application[] | { results: Application[] }>("/applications/")
      .then((data) => {
        if (!alive) return;
        const records = Array.isArray(data) ? data : data.results || [];
        setApplications(records);
        if (records.length) setSelectedApplicationId(String(records[0].id));
      })
      .catch((error) => {
        if (alive) setPageError((error as Error).message);
      })
      .finally(() => {
        if (alive) setApplicationsLoading(false);
      });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!selectedApplicationId) {
      setSpecifications([]);
      return;
    }
    let alive = true;
    setSpecificationsLoading(true);
    setPageError("");
    request<Specification[] | { results: Specification[] }>(
      "/applications/" + selectedApplicationId + "/specifications/"
    )
      .then((data) => {
        if (!alive) return;
        setSpecifications(Array.isArray(data) ? data : data.results || []);
      })
      .catch((error) => {
        if (alive) {
          setSpecifications([]);
          setPageError((error as Error).message);
        }
      })
      .finally(() => {
        if (alive) setSpecificationsLoading(false);
      });
    return () => { alive = false; };
  }, [selectedApplicationId]);

  const openCreate = () => {
    setActiveSpecification(null);
    setName("");
    setDescription("");
    setDocumentText(emptyOpenApiDocument);
    setFormError("");
    setDialogMode("create");
  };

  const openView = (specification: Specification) => {
    setActiveSpecification(specification);
    setDialogMode("view");
  };

  const openEdit = (specification: Specification) => {
    setActiveSpecification(specification);
    setName(specification.name);
    setDescription(specification.description || "");
    setDocumentText(JSON.stringify(specification.document, null, 2));
    setFormError("");
    setDialogMode("edit");
  };

  const closeDialog = () => {
    if (saving || deleting) return;
    setDialogMode(null);
    setActiveSpecification(null);
    setFormError("");
  };

  const saveSpecification = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedApplicationId || !name.trim()) return;

    let parsedDocument: any;
    try {
      parsedDocument = JSON.parse(documentText);
    } catch {
      setFormError("The document is not valid JSON. Check the syntax and try again.");
      return;
    }

    if (!parsedDocument || typeof parsedDocument !== "object" || Array.isArray(parsedDocument)) {
      setFormError("The OpenAPI document must be a JSON object.");
      return;
    }
    if (typeof parsedDocument.openapi !== "string" || !parsedDocument.openapi.trim()) {
      setFormError('The document must contain an "openapi" version, such as "3.0.3".');
      return;
    }
    if (!parsedDocument.info || typeof parsedDocument.info.version !== "string" || !parsedDocument.info.version.trim()) {
      setFormError('The document must contain "info.version" to identify the API version.');
      return;
    }

    const payload = {
      name: name.trim(),
      description: description.trim(),
      api_version: parsedDocument.info.version,
      openapi_version: parsedDocument.openapi,
      document: parsedDocument,
    };

    setSaving(true);
    setFormError("");
    try {
      if (dialogMode === "edit" && activeSpecification) {
        const updated = await request<Specification>(
          "/specifications/" + activeSpecification.id + "/",
          { method: "PATCH", body: JSON.stringify(payload) }
        );
        setSpecifications((current) => current.map((item) =>
          item.id === activeSpecification.id ? updated : item
        ));
        setActiveSpecification(updated);
        setDialogMode("view");
      } else {
        const created = await request<Specification>(
          "/applications/" + selectedApplicationId + "/specifications/create/",
          { method: "POST", body: JSON.stringify(payload) }
        );
        setSpecifications((current) => [created, ...current]);
        setDialogMode(null);
        setActiveSpecification(null);
      }
    } catch (error) {
      setFormError((error as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const removeSpecification = async () => {
    if (!activeSpecification) return;
    if (!window.confirm('Delete "' + activeSpecification.name + '"? This action cannot be undone.')) return;
    setDeleting(true);
    setPageError("");
    try {
      await request<void>("/specifications/" + activeSpecification.id + "/", { method: "DELETE" });
      setSpecifications((current) => current.filter((item) => item.id !== activeSpecification.id));
      setDialogMode(null);
      setActiveSpecification(null);
    } catch (error) {
      setPageError((error as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  const filteredSpecifications = specifications.filter((item) =>
    (item.name + " " + item.description + " " + item.api_version)
      .toLowerCase()
      .includes(search.toLowerCase())
  );
  const selectedApplication = applications.find((item) => String(item.id) === selectedApplicationId);

  return (
    <div className="subpage specifications-page">
      <div className="sub-heading">
        <div>
          <small className="eyebrow">API CATALOG</small>
          <h1>Specifications</h1>
          <p>Manage the OpenAPI documents connected to your applications.</p>
        </div>
        <button className="primary" onClick={openCreate} disabled={!applications.length}>
          <Plus size={17} /> New specification
        </button>
      </div>

      {applicationsLoading ? (
        <div className="specifications-state"><span className="spinner" /><p>Loading applications...</p></div>
      ) : applications.length === 0 ? (
        <section className="specifications-empty">
          <span className="specifications-empty-icon"><FolderKanban size={25} /></span>
          <h2>Create an application first</h2>
          <p>Every specification belongs to an application. Create one before adding an OpenAPI document.</p>
          <button className="primary" onClick={() => navigate("/app/applications")}>
            Go to applications <ArrowRight size={16} />
          </button>
        </section>
      ) : (
        <>
          <div className="specifications-toolbar">
            <label className="application-picker">
              <span>APPLICATION</span>
              <select
                aria-label="Choose application"
                value={selectedApplicationId}
                onChange={(event) => setSelectedApplicationId(event.target.value)}
              >
                {applications.map((application) => (
                  <option key={application.id} value={application.id}>{application.name}</option>
                ))}
              </select>
              <ChevronDown size={15} />
            </label>
            <div className="specifications-search">
              <Search size={16} />
              <input
                aria-label="Search specifications"
                placeholder="Search specifications..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <span className="specifications-count">
              {specifications.length} {specifications.length === 1 ? "specification" : "specifications"}
            </span>
          </div>

          {pageError && <div className="applications-error">{pageError}</div>}

          {specificationsLoading ? (
            <div className="specifications-state"><span className="spinner" /><p>Loading specifications...</p></div>
          ) : filteredSpecifications.length ? (
            <div className="specifications-grid">
              {filteredSpecifications.map((specification) => (
                <article className="specification-card" key={specification.id}>
                  <div className="specification-card-top">
                    <span className="specification-icon"><FileJson2 size={20} /></span>
                    <span className="specification-version">OpenAPI {specification.openapi_version}</span>
                  </div>
                  <h2>{specification.name}</h2>
                  <p>{specification.description || "No description added."}</p>
                  <div className="specification-meta">
                    <span>API version <b>{specification.api_version}</b></span>
                    <span>Updated {new Date(specification.updated_at).toLocaleDateString()}</span>
                  </div>
                  <div className="specification-card-actions">
                    <button className="secondary-button" onClick={() => openView(specification)}>
                      View document <ArrowRight size={14} />
                    </button>
                    <button
                      className="specification-icon-button"
                      aria-label={"Edit " + specification.name}
                      title="Edit specification"
                      onClick={() => openEdit(specification)}
                    >
                      <Settings size={15} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <section className="specifications-empty">
              <span className="specifications-empty-icon"><FileJson2 size={25} /></span>
              <h2>{search ? "No matching specifications" : "Add your first specification"}</h2>
              <p>{search
                ? "Try a different search term."
                : "Add an OpenAPI JSON document to start exploring the API contract for " + (selectedApplication?.name || "this application") + "."}</p>
              {!search && <button className="primary" onClick={openCreate}><Plus size={16} /> New specification</button>}
            </section>
          )}
        </>
      )}

      {dialogMode && (
        <div className="specification-modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeDialog();
        }}>
          <section className="specification-modal" role="dialog" aria-modal="true" aria-labelledby="specification-modal-title">
            {dialogMode === "view" && activeSpecification ? (
              <>
                <div className="specification-modal-heading">
                  <div>
                    <small className="eyebrow">OPENAPI DOCUMENT</small>
                    <h2 id="specification-modal-title">{activeSpecification.name}</h2>
                    <p>{activeSpecification.description || "No description added."}</p>
                  </div>
                  <button className="application-modal-close" aria-label="Close" onClick={closeDialog}><X size={19} /></button>
                </div>
                <div className="specification-detail-meta">
                  <span>OpenAPI <b>{activeSpecification.openapi_version}</b></span>
                  <span>API version <b>{activeSpecification.api_version}</b></span>
                </div>
                <pre className="specification-document-preview">{JSON.stringify(activeSpecification.document, null, 2)}</pre>
                <div className="application-modal-actions">
                  <button className="danger-button" onClick={removeSpecification} disabled={deleting}>
                    <Trash2 size={15} /> {deleting ? "Deleting..." : "Delete"}
                  </button>
                  <button className="secondary-button" onClick={closeDialog}>Close</button>
                  <button className="primary" onClick={() => openEdit(activeSpecification)}>
                    <Settings size={15} /> Edit specification
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="specification-modal-heading">
                  <div>
                    <small className="eyebrow">{dialogMode === "edit" ? "UPDATE API CONTRACT" : "ADD TO API CATALOG"}</small>
                    <h2 id="specification-modal-title">{dialogMode === "edit" ? "Edit specification" : "New specification"}</h2>
                    <p>{selectedApplication?.name || "Selected application"}</p>
                  </div>
                  <button className="application-modal-close" aria-label="Close" onClick={closeDialog}><X size={19} /></button>
                </div>
                <form onSubmit={saveSpecification}>
                  <div className="field">
                    <label htmlFor="specification-name">Name</label>
                    <input
                      id="specification-name"
                      className="input"
                      maxLength={200}
                      placeholder="e.g. Public API"
                      required
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="specification-description">Description <span>OPTIONAL</span></label>
                    <textarea
                      id="specification-description"
                      className="input specification-description"
                      placeholder="What does this API specification describe?"
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="specification-document">OpenAPI document <span>JSON</span></label>
                    <textarea
                      id="specification-document"
                      className="input specification-document-input"
                      spellCheck={false}
                      required
                      value={documentText}
                      onChange={(event) => setDocumentText(event.target.value)}
                    />
                    <small className="specification-hint">The API version and OpenAPI version are read from info.version and openapi in the document.</small>
                  </div>
                  {formError && <div className="applications-error">{formError}</div>}
                  <div className="application-modal-actions">
                    <button type="button" className="secondary-button" onClick={closeDialog}>Cancel</button>
                    <button className="primary" disabled={saving || !name.trim()}>
                      {saving ? "Saving..." : dialogMode === "edit" ? "Save changes" : "Create specification"}
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </form>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function Inspections() {
  type TestCase = {
    name: string;
    description: string;
    endpoint: string;
    method: string;
    test_type: "positive" | "negative" | string;
    expected_status_codes?: number[];
    headers?: Record<string, unknown>;
    query_params?: Record<string, unknown>;
    path_params?: Record<string, unknown>;
    request_body?: Record<string, unknown> | null;
  };

  type Finding = {
    title: string;
    description: string;
    severity: "low" | "medium" | "high" | "critical" | string;
    endpoint: string;
    recommendation: string;
  };

  type TestPlan = { summary: string; test_cases: TestCase[] };
  type Analysis = { summary: string; findings: Finding[]; suggestions: string[] };

  const [applications, setApplications] = useState<Application[]>([]);
  const [specifications, setSpecifications] = useState<Specification[]>([]);
  const [applicationId, setApplicationId] = useState("");
  const [specificationId, setSpecificationId] = useState("");
  const [loadingApplications, setLoadingApplications] = useState(true);
  const [loadingSpecifications, setLoadingSpecifications] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [resultsText, setResultsText] = useState("");
  const [testPlan, setTestPlan] = useState<TestPlan | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    request<Application[] | { results: Application[] }>("/applications/")
      .then((data) => {
        if (!active) return;
        const items = Array.isArray(data) ? data : data.results || [];
        setApplications(items);
        if (items.length) setApplicationId(String(items[0].id));
      })
      .catch((err) => {
        if (active) setError((err as Error).message);
      })
      .finally(() => {
        if (active) setLoadingApplications(false);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!applicationId) {
      setSpecifications([]);
      setSpecificationId("");
      return;
    }

    let active = true;
    setLoadingSpecifications(true);
    setSpecifications([]);
    setSpecificationId("");
    setTestPlan(null);
    setAnalysis(null);
    setResultsText("");
    setError("");
    setNotice("");

    request<Specification[] | { results: Specification[] }>(
      "/applications/" + applicationId + "/specifications/"
    )
      .then((data) => {
        if (!active) return;
        const items = Array.isArray(data) ? data : data.results || [];
        setSpecifications(items);
        if (items.length) setSpecificationId(String(items[0].id));
      })
      .catch((err) => {
        if (active) setError((err as Error).message);
      })
      .finally(() => {
        if (active) setLoadingSpecifications(false);
      });

    return () => { active = false; };
  }, [applicationId]);

  const selectedSpecification = specifications.find(
    (item) => String(item.id) === specificationId
  );
  const testCases = testPlan?.test_cases || [];
  const findings = analysis?.findings || [];
  const countType = (type: string) =>
    testCases.filter((item) => item.test_type === type).length;
  const countSeverity = (severity: string) =>
    findings.filter((item) => item.severity.toLowerCase() === severity).length;

  const severityColor: Record<string, string> = {
    low: "#5eae8a",
    medium: "#d6a24d",
    high: "#e17b62",
    critical: "#e15d79",
  };

  const generateTests = async () => {
    if (!specificationId || generating || analyzing) return;
    setGenerating(true);
    setError("");
    setNotice("");
    setTestPlan(null);
    setAnalysis(null);
    setResultsText("");

    try {
      const result = await request<TestPlan>(
        "/specifications/" + specificationId + "/ai/generate-tests/",
        { method: "POST", body: JSON.stringify({ instructions: "" }) }
      );
      if (!result || !Array.isArray(result.test_cases)) {
        throw new Error("The AI service returned an invalid test plan.");
      }
      setTestPlan(result);
      setNotice("Test plan generated successfully.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  const analyzeResults = async () => {
    setError("");
    setNotice("");

    let parsed: unknown;
    try {
      parsed = JSON.parse(resultsText);
    } catch {
      setError("The execution results are not valid JSON. Check the brackets and commas, then try again.");
      return;
    }

    if (
      !Array.isArray(parsed) ||
      parsed.length === 0 ||
      parsed.length > 200 ||
      parsed.some((item) => !item || typeof item !== "object" || Array.isArray(item))
    ) {
      setError("Provide a JSON array containing between 1 and 200 result objects.");
      return;
    }

    const enrichedResults = parsed.map((item: Record<string, unknown>) => {
      const label = String(item.test_name || item.name || item.title || "").trim().toLowerCase();
      const matchingTest = testCases.find(
        (test) => test.name.trim().toLowerCase() === label
      );
      if (!matchingTest) return item;
      return {
        ...item,
        endpoint: item.endpoint || matchingTest.endpoint,
        method: item.method || matchingTest.method,
        expected_status_codes:
          Array.isArray(item.expected_status_codes) && item.expected_status_codes.length
            ? item.expected_status_codes
            : matchingTest.expected_status_codes || [],
      };
    });

    setAnalyzing(true);
    setAnalysis(null);
    try {
      const result = await request<Analysis>(
        "/specifications/" + specificationId + "/ai/analyze-results/",
        {
          method: "POST",
          body: JSON.stringify({
            test_results: enrichedResults,
            instructions: "",
          }),
        }
      );

      if (
        !result ||
        typeof result.summary !== "string" ||
        !Array.isArray(result.findings) ||
        !Array.isArray(result.suggestions)
      ) {
        throw new Error("The AI service returned an invalid analysis.");
      }

      setAnalysis(result);
      setNotice("Execution results analyzed.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  const resetInspection = () => {
    setTestPlan(null);
    setAnalysis(null);
    setResultsText("");
    setError("");
    setNotice("");
  };

  return (
    <div className="subpage inspections-page">
      <div className="sub-heading inspections-heading">
        <div>
          <small className="eyebrow">API QUALITY WORKSPACE</small>
          <h1>Inspections</h1>
          <p>Turn your API contract into test cases, then review what happened when they ran.</p>
        </div>
        {testPlan && (
          <button className="inspection-reset" type="button" onClick={resetInspection}>
            Start new inspection
          </button>
        )}
      </div>

      {error && <div className="applications-error inspection-alert" role="alert">{error}</div>}
      {notice && <div className="inspection-notice" role="status"><CheckCircle2 size={16} />{notice}</div>}

      {loadingApplications ? (
        <div className="specifications-state"><span className="spinner" /><p>Loading applications...</p></div>
      ) : applications.length === 0 ? (
        <section className="applications-empty">
          <span className="applications-empty-icon"><ShieldCheck size={25} /></span>
          <h2>No applications yet</h2>
          <p>Create an application and add an OpenAPI specification before starting an inspection.</p>
          <Link className="primary button-link" to="/app/applications">Go to applications <ArrowRight size={16} /></Link>
        </section>
      ) : (
        <>
          <section className="inspection-selector panel">
            <div className="inspection-panel-heading">
              <span className="inspection-step">01</span>
              <div>
                <h2>Choose an API</h2>
                <p>Select the application and specification you want to inspect.</p>
              </div>
            </div>
            <div className="inspection-select-grid">
              <div className="field">
                <label htmlFor="inspection-application">Application</label>
                <select
                  id="inspection-application"
                  className="input"
                  value={applicationId}
                  onChange={(event) => setApplicationId(event.target.value)}
                >
                  {applications.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="inspection-specification">API specification</label>
                <select
                  id="inspection-specification"
                  className="input"
                  value={specificationId}
                  disabled={loadingSpecifications || !specifications.length}
                  onChange={(event) => {
                    setSpecificationId(event.target.value);
                    setTestPlan(null);
                    setAnalysis(null);
                    setResultsText("");
                    setError("");
                    setNotice("");
                  }}
                >
                  {!specifications.length && <option value="">No specification available</option>}
                  {specifications.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · v{item.api_version}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {loadingSpecifications && <p className="inspection-helper">Loading specifications...</p>}
            {selectedSpecification && (
              <div className="inspection-spec-meta">
                <span>OpenAPI {selectedSpecification.openapi_version}</span>
                <span>{selectedSpecification.api_version ? "API v" + selectedSpecification.api_version : "API version not set"}</span>
                <span className="inspection-spec-name">{selectedSpecification.name}</span>
              </div>
            )}
          </section>

          {!loadingSpecifications && specifications.length === 0 ? (
            <section className="applications-empty">
              <span className="applications-empty-icon"><FileJson2 size={25} /></span>
              <h2>No API specifications</h2>
              <p>Add an OpenAPI document to this application to generate an inspection plan.</p>
              <Link className="primary button-link" to="/app/specifications">Manage specifications <ArrowRight size={16} /></Link>
            </section>
          ) : (
            <>
              <section className="inspection-generate panel">
                <div className="inspection-panel-heading">
                  <span className="inspection-step">02</span>
                  <div>
                    <h2>Generate test cases</h2>
                    <p>API Inspector reads the selected contract and builds a validated test plan automatically.</p>
                  </div>
                </div>
                <div className="inspection-generate-bottom">
                  <div className="inspection-auto-note">
                    <Sparkles size={17} />
                    <span>No prompt writing needed. Test coverage is derived from your OpenAPI document.</span>
                  </div>
                  <button
                    className="primary inspection-action"
                    type="button"
                    onClick={generateTests}
                    disabled={!specificationId || generating || analyzing}
                  >
                    {generating ? <><span className="inspection-button-spinner" />Generating...</> : <>Generate test cases <ArrowRight size={16} /></>}
                  </button>
                </div>
              </section>

              {testPlan && (
                <section className="inspection-results">
                  <div className="inspection-result-heading">
                    <div>
                      <small className="eyebrow">TEST PLAN</small>
                      <h2>Generated test cases</h2>
                      <p>{testPlan.summary}</p>
                    </div>
                    <span className="inspection-total-pill">{testCases.length} tests</span>
                  </div>

                  <div className="inspection-metrics">
                    <div className="inspection-metric">
                      <span>Total tests</span>
                      <strong>{testCases.length}</strong>
                    </div>
                    <div className="inspection-metric">
                      <span>Positive</span>
                      <strong>{countType("positive")}</strong>
                    </div>
                    <div className="inspection-metric">
                      <span>Negative</span>
                      <strong>{countType("negative")}</strong>
                    </div>
                  </div>

                  <div className="inspection-case-list">
                    {testCases.map((test, index) => (
                      <article className="inspection-case" key={test.name + index}>
                        <div className="inspection-case-top">
                          <div className="inspection-case-number">{String(index + 1).padStart(2, "0")}</div>
                          <div className="inspection-case-main">
                            <h3>{test.name}</h3>
                            <p>{test.description}</p>
                            <div className="inspection-case-meta">
                              <span className="inspection-method">{test.method}</span>
                              <code>{test.endpoint}</code>
                            </div>
                          </div>
                          <span className={"inspection-type inspection-type-" + test.test_type}>
                            {test.test_type.replace("_", " ")}
                          </span>
                        </div>
                        <div className="inspection-case-footer">
                          <span>Expected response</span>
                          {test.expected_status_codes?.length ? (
                            <div className="inspection-status-list">
                              {test.expected_status_codes.map((code) => <code key={code}>{code}</code>)}
                            </div>
                          ) : <span className="inspection-undocumented">Not defined in specification</span>}
                        </div>
                        <details className="inspection-details">
                          <summary>View request parameters and body</summary>
                          <pre>{JSON.stringify({
                            headers: test.headers || {},
                            query_params: test.query_params || {},
                            path_params: test.path_params || {},
                            request_body: test.request_body ?? null,
                          }, null, 2)}</pre>
                        </details>
                      </article>
                    ))}
                  </div>
                </section>
              )}

              {testPlan && (
                <section className="inspection-execution panel">
                  <div className="inspection-panel-heading">
                    <span className="inspection-step">03</span>
                    <div>
                      <h2>Analyze execution results</h2>
                      <p>Paste the results from your API client as a JSON array. Match each result's name to a generated test case to carry its endpoint and expected status into the analysis.</p>
                    </div>
                  </div>
                  <div className="inspection-format-note">
                    <strong>Expected format</strong>
                    <code>{"{ name, status_code, passed, response_time_ms }"}</code>
                    <span>Execution is manual in this MVP; API Inspector does not send requests to your API.</span>
                  </div>
                  <div className="field">
                    <label htmlFor="inspection-results">Execution results <span>JSON ARRAY</span></label>
                    <textarea
                      id="inspection-results"
                      className="input inspection-json-input"
                      rows={9}
                      spellCheck={false}
                      placeholder={'[\n  {\n    "name": "Get todos successfully",\n    "status_code": 200,\n    "passed": true,\n    "response_time_ms": 125\n  }\n]'}
                      value={resultsText}
                      onChange={(event) => setResultsText(event.target.value)}
                    />
                  </div>
                  <div className="inspection-execution-footer">
                    <span>Up to 200 result objects per analysis.</span>
                    <button
                      className="primary inspection-action"
                      type="button"
                      onClick={analyzeResults}
                      disabled={analyzing || generating || !resultsText.trim()}
                    >
                      {analyzing ? <><span className="inspection-button-spinner" />Analyzing...</> : <>Analyze results <ArrowRight size={16} /></>}
                    </button>
                  </div>
                </section>
              )}

              {analysis && (
                <section className="inspection-analysis">
                  <div className="inspection-result-heading">
                    <div>
                      <small className="eyebrow">ANALYSIS REPORT</small>
                      <h2>What we found</h2>
                      <p>{analysis.summary}</p>
                    </div>
                    <span className="inspection-total-pill">{findings.length} findings</span>
                  </div>

                  <div className="inspection-severity-grid">
                    {(["critical", "high", "medium", "low"] as const).map((severity) => (
                      <div className={"inspection-severity inspection-severity-" + severity} key={severity}>
                        <span>{severity}</span>
                        <strong>{countSeverity(severity)}</strong>
                      </div>
                    ))}
                  </div>

                  {findings.length === 0 ? (
                    <div className="inspection-clean-state">
                      <CheckCircle2 size={22} />
                      <div><strong>No issues detected</strong><p>The supplied results did not show a failed test or an unexpected response.</p></div>
                    </div>
                  ) : (
                    <div className="inspection-finding-list">
                      {findings.map((finding, index) => (
                        <article className="inspection-finding" key={finding.title + index}>
                          <div className="inspection-finding-heading">
                            <div><span className="inspection-finding-index">{String(index + 1).padStart(2, "0")}</span><h3>{finding.title}</h3></div>
                            <span className={"inspection-severity-tag inspection-severity-tag-" + finding.severity.toLowerCase()}>
                              {finding.severity}
                            </span>
                          </div>
                          <p>{finding.description}</p>
                          {finding.endpoint && <code className="inspection-finding-endpoint">{finding.endpoint}</code>}
                          <div className="inspection-recommendation">
                            <strong>Recommended action</strong>
                            <p>{finding.recommendation}</p>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}

                  {analysis.suggestions.length > 0 && (
                    <div className="inspection-suggestions">
                      <h3>Next steps</h3>
                      <ul>{analysis.suggestions.map((suggestion, index) => <li key={index}>{suggestion}</li>)}</ul>
                    </div>
                  )}
                </section>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
function SettingsPage(){const{user,reload}=useAuth();const[old,setOld]=useState(''),[next,setNext]=useState(''),[confirm,setConfirm]=useState(''),[error,setError]=useState(''),[success,setSuccess]=useState(''),[busy,setBusy]=useState(false);const submit=async(e:FormEvent)=>{e.preventDefault();setError('');setSuccess('');if(next!==confirm){setError('Your new passwords do not match.');return}setBusy(true);try{await request('/accounts/change-password/',{method:'POST',body:JSON.stringify({old_password:old,new_password:next,confirm_new_password:confirm})});setOld('');setNext('');setConfirm('');setSuccess('Password changed successfully.');await reload()}catch(x){setError((x as Error).message)}finally{setBusy(false)}};return <div className="subpage"><div className="sub-heading"><div><small className="eyebrow">YOUR WORKSPACE</small><h1>Settings</h1><p>Manage your account and security preferences.</p></div></div><div className="settings-grid"><section className="panel settings-panel"><h3>Profile information</h3><p>Your account details.</p><div className="detail"><small>Display name</small><b>{user?.display_name||'—'}</b></div><div className="detail"><small>Email address</small><b>{user?.email||'—'}</b><em>{user?.is_active?'Verified account':'Email not verified'}</em></div><div className="detail"><small>Member since</small><b>{user?.created_at?new Date(user.created_at).toLocaleDateString():'—'}</b></div></section><section className="panel settings-panel"><h3>Change password</h3><p>Choose a strong password to keep your account secure.</p><form onSubmit={submit}><Field label="Current password" name="old_password" type="password" required value={old} onChange={e=>setOld(e.target.value)}/><Field label="New password" name="new_password" type="password" required value={next} onChange={e=>setNext(e.target.value)}/><Field label="Confirm new password" name="confirm_new_password" type="password" required value={confirm} onChange={e=>setConfirm(e.target.value)}/><ErrorMsg>{error}</ErrorMsg>{success&&<div className="success-msg">{success}</div>}<button className="primary">Update password <ArrowRight/></button></form></section></div></div>}
type Application={id:number;name:string;description:string;created_at:string;updated_at:string};
function Applications(){
  const [items,setItems]=useState<Application[]>([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [search,setSearch]=useState('');
  const [dialog,setDialog]=useState(false);
  const [name,setName]=useState('');
  const [description,setDescription]=useState('');
  const [saving,setSaving]=useState(false);
  const [deletingId,setDeletingId]=useState<number|null>(null);

  useEffect(()=>{
    let alive=true;
    request<Application[]|{results:Application[]}>('/applications/')
      .then(data=>{if(alive)setItems(Array.isArray(data)?data:data.results||[])})
      .catch(err=>{if(alive)setError((err as Error).message)})
      .finally(()=>{if(alive)setLoading(false)});
    return()=>{alive=false};
  },[]);

  const submit=async(e:FormEvent)=>{
    e.preventDefault();
    if(!name.trim())return;
    setSaving(true);
    setError('');
    try{
      const created=await request<Application>('/applications/create/',{
        method:'POST',
        body:JSON.stringify({name:name.trim(),description:description.trim()})
      });
      setItems(current=>[created,...current]);
      setName('');
      setDescription('');
      setDialog(false);
    }catch(err){
      setError((err as Error).message);
    }finally{
      setSaving(false);
    }
  };

  const removeApplication=async(item:Application)=>{
    if(!window.confirm(`Delete "${item.name}"? This action cannot be undone.`))return;
    setDeletingId(item.id);
    setError('');
    try{
      await request<void>(`/applications/${item.id}/delete/`,{method:'DELETE'});
      setItems(current=>current.filter(application=>application.id!==item.id));
    }catch(err){
      setError((err as Error).message);
    }finally{
      setDeletingId(null);
    }
  };

  const filtered=items.filter(item=>
    (item.name+' '+item.description).toLowerCase().includes(search.toLowerCase())
  );

  return <div className="subpage applications-page">
    <div className="sub-heading">
      <div><small className="eyebrow">YOUR WORKSPACE</small><h1>Applications</h1><p>Keep the APIs you want to inspect organized in one place.</p></div>
      <button className="primary" onClick={()=>{setError('');setDialog(true)}}><Plus size={17}/> New application</button>
    </div>
    <div className="applications-toolbar">
      <div className="applications-search"><Search size={17}/><input aria-label="Search applications" placeholder="Search applications..." value={search} onChange={e=>setSearch(e.target.value)}/></div>
      <span>{items.length} {items.length===1?'application':'applications'}</span>
    </div>
    {error&&!dialog&&<div className="applications-error">{error}</div>}
    {loading?<div className="applications-state"><span className="spinner"/><p>Loading applications...</p></div>:
      filtered.length>0?<div className="applications-grid">{filtered.map(item=><article className="application-card" key={item.id}>
        <div className="application-card-top"><span className="application-icon"><FolderKanban size={20}/></span><small>APPLICATION</small></div>
        <h2>{item.name}</h2>
        <p>{item.description||'No description added.'}</p>
        <div className="application-card-footer"><span>Created {new Date(item.created_at).toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'})}</span><div className="application-card-actions"><span className="application-id">ID · {item.id}</span><button type="button" className="application-delete" aria-label={`Delete ${item.name}`} title="Delete application" disabled={deletingId===item.id} onClick={()=>removeApplication(item)}>{deletingId===item.id?<span className="delete-spinner"/>:<Trash2 size={15}/>}</button></div></div>
      </article>)}</div>:
      <section className="applications-empty">
        <span className="applications-empty-icon"><FolderKanban size={25}/></span>
        <h2>{search?'No matching applications':'Start with your first application'}</h2>
        <p>{search?'Try another search term.':'Create an application to give your API inspection work a clear home.'}</p>
        {!search&&<button className="primary" onClick={()=>setDialog(true)}><Plus size={16}/> Create application</button>}
      </section>
    }
    {dialog&&<div className="application-modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setDialog(false)}}>
      <section className="application-modal" role="dialog" aria-modal="true" aria-labelledby="application-modal-title">
        <div className="application-modal-heading"><div><small className="eyebrow">NEW WORKSPACE ITEM</small><h2 id="application-modal-title">Create application</h2><p>Add a name and an optional description.</p></div><button className="application-modal-close" type="button" aria-label="Close" onClick={()=>setDialog(false)}><X size={19}/></button></div>
        <form onSubmit={submit}>
          <div className="field"><label htmlFor="application-name">Name</label><input id="application-name" className="input" autoFocus maxLength={150} placeholder="e.g. Customer API" required value={name} onChange={e=>setName(e.target.value)}/></div>
          <div className="field"><label htmlFor="application-description">Description <span>OPTIONAL</span></label><textarea id="application-description" className="input application-description" maxLength={1000} placeholder="What does this application do?" value={description} onChange={e=>setDescription(e.target.value)}/></div>
          {error&&<div className="applications-error">{error}</div>}
          <div className="application-modal-actions"><button type="button" className="secondary-button" onClick={()=>setDialog(false)}>Cancel</button><button className="primary" disabled={saving||!name.trim()}>{saving?'Creating...':'Create application'} <ArrowRight size={16}/></button></div>
        </form>
      </section>
    </div>}
  </div>;
}
export default App;