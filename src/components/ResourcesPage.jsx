import React,{useEffect,useState}from'react';
import{Link}from'react-router-dom';
import{Sprout,Zap,Droplets,Hammer,Package,Plus,ArrowUpRight,Clock}from'lucide-react';
import{api,resources}from'../data';

const ICONS={food:Sprout,electricity:Zap,water:Droplets,labor:Hammer};
const THRESHOLD_LABEL={critical:'Below one week of cover',low:'Below two weeks of cover',healthy:'Within weekly planning range',surplus:'Above four weeks of cover'};

export default function ResourcesPage({user,need,notify}){
 const[inventory,setInventory]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState('');
 async function load(){try{setError('');setInventory(await api('inventory'))}catch(e){setError(e.message)}}
 useEffect(()=>{load();const timer=setInterval(load,15000);return()=>clearInterval(timer)},[user?.id]);
 async function requestShare(e,stock){
  e.preventDefault();
  const quantity=Number(new FormData(e.currentTarget).get('quantity'));
  setBusy(stock.id);
  try{
   await api('allocate',{kind:stock.id,quantity});
   await load();
   notify('Your weekly share of '+stock.label.toLowerCase()+' is reserved.');
   e.currentTarget.reset();
  }catch(err){setError(err.message)}
  finally{setBusy('')}
 }
 const stocks=inventory?.stocks||[];
 return <>
  <div className="breadcrumb"><Link to="/">The Commons</Link><span>/</span><span>Resources</span></div>
  <div className="page-heading"><span className="eyebrow">COLLECTIVE RESOURCE TRACKER</span><h1>What the Commons holds this week.</h1><p>Verified contributions become shared stock. Each member may draw up to the weekly allocation limit, so food, power, water, and labor last through the week.</p></div>
  {error&&<div className="notice" role="alert">{error}</div>}
  <div className="metrics">{[
   ['Members planned for',inventory?inventory.members:'—',Package,'Used to size weekly cover'],
   ['Planning week',inventory?.week||'—',Clock,'ISO week for allocation caps'],
   ['Exchange listings',inventory?inventory.exchangeListings:'—',Sprout,'Available in the marketplace']
  ].map(([label,value,Icon,caption])=><div className="metric" key={label}><div><span>{label}</span><Icon size={18}/></div><strong>{value}</strong><small>{caption}</small></div>)}</div>
  <div className="stock-grid">
   {stocks.map(stock=>{
    const Icon=ICONS[stock.id]||Package;
    const used=Math.min(100,stock.weeklyLimit?stock.youUsed/stock.weeklyLimit*100:0);
    const cover=stock.communityWeeklyNeed?stock.available/stock.communityWeeklyNeed:0;
    return <section className={'panel stock-card threshold-'+stock.threshold} key={stock.id}>
     <div className="stock-head"><span className="glass-pill"><Icon size={15}/>{stock.label}</span><span className={'tag threshold-tag'}>{stock.threshold}</span></div>
     <strong className="stock-value">{stock.available.toLocaleString(undefined,{maximumFractionDigits:1})} <small>{stock.unit}</small></strong>
     <p className="muted">{THRESHOLD_LABEL[stock.threshold]}. {stock.contributed.toLocaleString(undefined,{maximumFractionDigits:1})} {stock.unit} contributed · {stock.allocated.toLocaleString(undefined,{maximumFractionDigits:1})} {stock.unit} already shared.</p>
     <div className="cover-meter" role="img" aria-label={`${stock.label} cover ${cover.toFixed(1)} weeks`}><i style={{width:Math.min(100,cover/4*100)+'%'}}/></div>
     <div className="stock-meta"><span>{cover.toFixed(1)} weeks of community cover</span><span>{stock.listed} listed for exchange</span></div>
     <div className="allocation-box">
      <div className="section-title compact-title"><h3>Weekly Member Allocation</h3><span>{stock.youUsed.toLocaleString(undefined,{maximumFractionDigits:1})} / {stock.weeklyLimit} {stock.unit}</span></div>
      <div className="cover-meter allocation-meter"><i style={{width:used+'%'}}/></div>
      <p className="muted">Each member may receive up to {stock.weeklyLimit} {stock.unit} per week. You have {stock.youRemaining.toLocaleString(undefined,{maximumFractionDigits:1})} {stock.unit} remaining this week.</p>
      {user?<form className="allocate-form" onSubmit={e=>requestShare(e,stock)}><input name="quantity" type="number" min="0.01" max={Math.min(stock.youRemaining,stock.available)||0.01} step="0.01" required aria-label={'Quantity of '+stock.label}/><button className="primary" disabled={busy===stock.id||stock.available<=0||stock.youRemaining<=0}>{busy===stock.id?'Reserving…':'Request this week’s share'}</button></form>:<button className="secondary" onClick={()=>need('login')}>Sign in to request a share <ArrowUpRight size={16}/></button>}
     </div>
    </section>;
   })}
  </div>
  <section className="panel">
   <span className="eyebrow">WEEKLY LIMITS AND THRESHOLDS</span>
   <h2>Fair shares, planned in the open.</h2>
   <p>Limits keep one household from drawing down the pantry or the battery before neighbors have a turn. Thresholds compare remaining stock with one week of allocations for every member.</p>
   <div className="limit-table" role="table">
    <div className="limit-row head" role="row"><span>Resource</span><span>Weekly cap / member</span><span>Critical</span><span>Low</span><span>Healthy</span></div>
    {stocks.map(stock=><div className="limit-row" role="row" key={stock.id}><span>{stock.label}</span><span>{stock.weeklyLimit} {stock.unit}</span><span>Under 1 week</span><span>Under 2 weeks</span><span>2–4 weeks</span></div>)}
   </div>
   <p className="muted">Stock comes from neighbor-verified contributions, minus shares already reserved. It is a community ledger, not a live sensor feed.</p>
   <div className="button-row"><button className="primary" onClick={()=>need('contribution')}>Log a contribution <Plus size={16}/></button><Link className="secondary button" to="/">Browse the exchange</Link></div>
  </section>
  <div className="resource-nav">{resources.map(([s,n])=><Link to={'/resources/'+s} key={s}>{n}</Link>)}</div>
 </>;
}
