"""Local persistent API. Python 3.10+, no dependencies. Bind loopback by default."""
import os,json,sqlite3,secrets,hashlib,hmac,time,re,datetime,urllib.request,urllib.error,mimetypes,pathlib
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse,parse_qs
DB=os.getenv('COMMONS_DB','commons.sqlite3')
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS kyc_sessions(user TEXT PRIMARY KEY,session TEXT,status TEXT)')
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,city TEXT,categories TEXT DEFAULT '[]',bio TEXT DEFAULT '',avatar TEXT DEFAULT '',credits REAL DEFAULT 0,score REAL DEFAULT 0);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user TEXT,expires REAL);CREATE TABLE IF NOT EXISTS listings(id TEXT PRIMARY KEY,user TEXT,title TEXT,description TEXT,category TEXT,city TEXT,mode TEXT,price REAL,status TEXT DEFAULT 'available',image TEXT,contact_email TEXT DEFAULT '',contact_phone TEXT DEFAULT '');CREATE TABLE IF NOT EXISTS trades(id TEXT PRIMARY KEY,listing TEXT,buyer TEXT,seller TEXT,offer TEXT,mode TEXT,amount REAL,due TEXT,status TEXT DEFAULT 'pending',buyer_done INTEGER DEFAULT 0,seller_done INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS contributions(id TEXT PRIMARY KEY,user TEXT,kind TEXT,quantity REAL,credits REAL,verifier TEXT,status TEXT DEFAULT 'pending',created REAL);CREATE TABLE IF NOT EXISTS pledges(id TEXT PRIMARY KEY,user TEXT,amount REAL,created REAL);CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,user TEXT,body TEXT,created REAL);CREATE TABLE IF NOT EXISTS contacts(id TEXT PRIMARY KEY,email TEXT,body TEXT,created REAL);CREATE TABLE IF NOT EXISTS allocations(id TEXT PRIMARY KEY,user TEXT,kind TEXT,quantity REAL,week TEXT,created REAL);''')
  cols={row[1] for row in c.execute('PRAGMA table_info(listings)')}
  if 'contact_email' not in cols:c.execute('ALTER TABLE listings ADD COLUMN contact_email TEXT DEFAULT ""')
  if 'contact_phone' not in cols:c.execute('ALTER TABLE listings ADD COLUMN contact_phone TEXT DEFAULT ""')
  if not c.execute('SELECT id FROM users LIMIT 1').fetchone():
   for uid,name,city,cats,bio in [('seed1','Maya Chen','Detroit',['Fresh Produce & Orchard Crop','Gardening Supplies & Seeds'],'Growing food and sharing what the garden gives.'),('seed2','Marcus Williams','Detroit',['Carpentry & Woodworking','Plumbing Materials & Fixtures'],'Carpenter, repairer, neighbor. Happy to trade skills.'),('seed3','Priya Patel','Detroit',['Solar Power Systems & Panels','Bicycles & Human-Powered Transport'],'Solar steward and weekend bicycle mechanic.')]:
    c.execute('INSERT INTO users(id,name,email,password,city,categories,bio) VALUES(?,?,?,?,?,?,?)',(uid,name,uid+'@example.invalid','disabled',city,json.dumps(cats),bio))
   for row in [('l1','seed1','A little extra from the garden','Fresh heirloom tomatoes, picked this morning. A 5 lb basket to share.','Fresh Produce & Orchard Crop','Detroit','swap',0,'garden'),('l2','seed2','Good wood. Better neighbors.','Two hours of carpentry: raised beds, shelves, or a repair you have been putting off.','Carpentry & Woodworking','Detroit','credits',30,'workshop'),('l3','seed3','A brighter kind of energy','One kWh of contributed solar generation. Demonstration listing; no live meter connected.','Solar Power Systems & Panels','Detroit','credits',1,'solar'),('l4','seed1','Start something green','Six basil and kale seedlings, ready for your windowsill or community plot.','Gardening Supplies & Seeds','Detroit','fiat',8,'greenhouse'),('l5','seed2','A helping hand with plumbing','Fix a dripping tap or install a garden hose connection. Materials by agreement.','Plumbing Materials & Fixtures','Detroit','swap',0,'water')]:
    c.execute('INSERT INTO listings(id,user,title,description,category,city,mode,price,image) VALUES(?,?,?,?,?,?,?,?,?)',row)
def load_config():
 # Only read local env files; process environment takes precedence.
 for filename in ['.env.local','.env']:
  path=pathlib.Path(__file__).parent/filename
  if path.is_file():
   for line in path.read_text().splitlines():
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line:continue
    key,value=line.split('=',1);os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))
load_config()
PUBLIC_CONFIG_PATH=pathlib.Path(__file__).parent/'config'/'supabase.public.json'
PUBLIC_CONFIG=json.loads(PUBLIC_CONFIG_PATH.read_text()) if PUBLIC_CONFIG_PATH.is_file() else {}
SUPABASE_URL=(os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL') or PUBLIC_CONFIG.get('url','')).rstrip('/')
SUPABASE_KEY=os.getenv('SUPABASE_PUBLISHABLE_KEY') or os.getenv('VITE_SUPABASE_PUBLISHABLE_KEY') or PUBLIC_CONFIG.get('publishableKey','')
if SUPABASE_KEY.startswith('sb_secret_'):raise RuntimeError('Use a Supabase publishable key, never a secret key.')
if SUPABASE_KEY.startswith('eyJ'):
 import base64
 try:role=json.loads(base64.urlsafe_b64decode(SUPABASE_KEY.split('.')[1]+'==')).get('role')
 except Exception:raise RuntimeError('Invalid Supabase key')
 if role!='anon':raise RuntimeError('Use only a publishable key or legacy anon key')

def verify_supabase_token(token):
 if not SUPABASE_URL or not SUPABASE_KEY:raise PermissionError('Supabase authentication is not configured')
 if len(token)>16384:raise PermissionError('Invalid session')
 request=urllib.request.Request(SUPABASE_URL+'/auth/v1/user',headers={'apikey':SUPABASE_KEY,'Authorization':'Bearer '+token,'Accept':'application/json'})
 try:
  with urllib.request.urlopen(request,timeout=10) as response:user=json.load(response)
 except urllib.error.HTTPError as e:
  if e.code in [400,401,403]:raise PermissionError('Your session has expired. Please sign in again.')
  raise ConnectionError('Account provider is temporarily unavailable')
 except (urllib.error.URLError,TimeoutError):raise ConnectionError('Account provider is temporarily unavailable')
 if not user.get('id') or not user.get('email') or not user.get('email_confirmed_at'):raise PermissionError('Confirm your email before signing in.')
 return user

def resolve_account(c,identity):
 # Supabase's verified UUID is the ONLY account binding. Never link by client input or email.
 uid=identity['id'];row=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
 if row:return row
 email=identity['email'].lower()
 if c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():raise ValueError('An older local profile uses this email. The organizer must explicitly migrate it; accounts are not automatically merged.')
 meta=identity.get('user_metadata') or {}
 c.execute('INSERT OR IGNORE INTO users(id,name,email,password,city) VALUES(?,?,?,?,?)',(uid,str(meta.get('name') or email.split('@')[0])[:200],email,'supabase-managed',str(meta.get('city') or 'Not specified')[:200]))
 c.commit();return c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()

def public(u):
 d=dict(u);d.pop('password',None);d['categories']=json.loads(d['categories']);return d

STOCKS=(
 {'id':'food','label':'Food in Stock','unit':'kg','kinds':('produce',),'weekly_limit':4,'categories':('Pantry Staples & Grains','Fresh Produce & Orchard Crop','Livestock & Poultry','Dairy & Eggs','Meats & Seafood','Baking & Sweeteners','Spices & Condiments','Beverages (Coffee, Tea, Juices)','Preserved & Canned Foods','Gardening Supplies & Seeds','Animal Feed & Forage','Beekeeping & Honey Production')},
 {'id':'electricity','label':'Electricity','unit':'kWh','kinds':('solar','kinetic'),'weekly_limit':8,'categories':('Liquid & Gas Fuels','Solid Fuels (Firewood, Charcoal)','Primary & Rechargeable Batteries','Solar Power Systems & Panels','Generators & Inverters','Emergency & Off-Grid Lighting','Heating & Stoves','Portable Power Stations','Fuel Storage Containers')},
 {'id':'water','label':'Water Supply','unit':'L','kinds':('water',),'weekly_limit':25,'categories':('Water Purification & Filtration','Water Storage & Transport','Personal Hygiene & Toiletries','Sanitation & Waste Management','Feminine Care Products','Baby Care & Diapering','Cleaning Chemicals & Detergents','Off-Grid Sanitation Facilities')},
 {'id':'labor','label':'Shared Labor','unit':'hours','kinds':('labor',),'weekly_limit':4,'categories':('General Contracting & Construction','Roofing & Exterior Repair','Landscaping & Land Clearing','Tailoring & Clothing Alteration','Barbering & Hair Styling','Childcare & Babysitting','Accounting, Tax & Bookkeeping','Legal Services & Mediation','Graphic Design & Digital Services','IT, Computer & Appliance Repair','Photography & Media Production','Carpentry & Woodworking','Hand Tools','Power Tools & Accessories')}
)

def iso_week():
 return datetime.date.today().strftime('%G-W%V')

def contact_email(data):
 v=str(data.get('contact_email','')).strip()
 if len(v)>320:raise ValueError('Contact email is too long')
 if v and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$',v):raise ValueError('Please provide a valid contact email')
 return v.lower()

def contact_phone(data):
 v=str(data.get('contact_phone','')).strip()
 if len(v)>40:raise ValueError('Contact phone is too long')
 if v:
  digits=re.sub(r'\D','',v)
  if len(digits)<7 or len(digits)>15:raise ValueError('Please provide a valid phone number')
 return v

def inventory_payload(c,uid):
 member_count=c.execute("SELECT COUNT(*) FROM users WHERE id NOT LIKE 'seed%'").fetchone()[0] or 1
 week=iso_week()
 listings=[dict(r) for r in c.execute('SELECT category FROM listings WHERE status="available"')]
 stocks=[]
 for spec in STOCKS:
  kinds=spec['kinds']
  placeholders=','.join('?'*len(kinds))
  contributed=c.execute(f'SELECT COALESCE(SUM(quantity),0) FROM contributions WHERE status="verified" AND kind IN ({placeholders})',kinds).fetchone()[0]
  allocated=c.execute('SELECT COALESCE(SUM(quantity),0) FROM allocations WHERE kind=?',(spec['id'],)).fetchone()[0]
  allocated_week=c.execute('SELECT COALESCE(SUM(quantity),0) FROM allocations WHERE kind=? AND week=?',(spec['id'],week)).fetchone()[0]
  you_used=c.execute('SELECT COALESCE(SUM(quantity),0) FROM allocations WHERE kind=? AND week=? AND user=?',(spec['id'],week,uid or '')).fetchone()[0] if uid else 0
  available=max(0,round(contributed-allocated,2))
  need=spec['weekly_limit']*member_count
  cover=available/need if need else 0
  threshold='critical' if cover<1 else 'low' if cover<2 else 'surplus' if cover>4 else 'healthy'
  listed=sum(1 for item in listings if item['category'] in spec['categories'])
  stocks.append({'id':spec['id'],'label':spec['label'],'unit':spec['unit'],'weeklyLimit':spec['weekly_limit'],'contributed':round(contributed,2),'allocated':round(allocated,2),'allocatedThisWeek':round(allocated_week,2),'available':available,'youUsed':round(you_used,2),'youRemaining':round(max(0,spec['weekly_limit']-you_used),2),'members':member_count,'communityWeeklyNeed':need,'threshold':threshold,'listed':listed})
 return {'week':week,'members':member_count,'exchangeListings':len(listings),'stocks':stocks}
class API(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,status,data,cookie=None):
  b=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(b)))
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(b)
 def do_GET(self):self.run('GET')
 def do_POST(self):self.run('POST')
 def run(self,method):
  try:
   path=urlparse(self.path).path
   if method=='GET' and not path.startswith('/api/'):
    root=pathlib.Path('dist').resolve();asset=(root/path.lstrip('/')).resolve()
    if not asset.is_relative_to(root):return self.send(403,{'error':'Forbidden'})
    if not asset.is_file():asset=root/'index.html'
    if not asset.is_file():return self.send(404,{'error':'Run npm run build, or use the Vite development server.'})
    raw=asset.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(asset))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
   if method=='POST':
    origin=self.headers.get('Origin');host=self.headers.get('Host')
    if origin:
     allowed={host,'www.40a.org','40a.org'}
     if urlparse(origin).netloc not in allowed:raise ValueError('Invalid request origin')
   size=int(self.headers.get('Content-Length',0))
   if size>100000:raise ValueError('Request too large')
   data=json.loads(self.rfile.read(size) or '{}') if method=='POST' else {}
   authorization=self.headers.get('Authorization','');identity=None
   if authorization:
    if not authorization.startswith('Bearer '):raise PermissionError('Invalid authentication method')
    identity=verify_supabase_token(authorization[7:])
   with db() as c:
    u=resolve_account(c,identity) if identity else None
    uid=u['id'] if u else None
    def auth():
     if not uid:raise PermissionError('Please sign in first')
    def required(k):
     v=str(data.get(k,'')).strip()
     if not v or len(v)>3000:raise ValueError('Please provide '+k)
     return v
    def number(k):
     n=float(data.get(k,0))
     if not 0<n<=1000000:raise ValueError('Amount must be greater than zero and at most 1,000,000')
     return n
    if path=='/api/me':return self.send(200,public(u) if u else None)
    if path=='/api/config':return self.send(200,{'supabaseUrl':SUPABASE_URL,'supabasePublishableKey':SUPABASE_KEY})
    if path in ['/api/signup','/api/login','/api/logout','/api/password']:return self.send(410,{'error':'Accounts are managed by Supabase. Use the account form.'})
    if path=='/api/listings' and method=='GET':return self.send(200,[dict(r) for r in c.execute('SELECT l.*,u.name FROM listings l JOIN users u ON u.id=l.user ORDER BY l.rowid DESC')])
    if path=='/api/resource-stats':
     return self.send(200,{'ledger':[dict(r) for r in c.execute('SELECT c.kind,c.quantity,c.credits,c.created,u.name FROM contributions c JOIN users u ON u.id=c.user WHERE c.status="verified" ORDER BY c.created DESC LIMIT 50')],'leaders':[dict(r) for r in c.execute('SELECT u.name,c.kind,SUM(c.quantity) AS quantity FROM contributions c JOIN users u ON u.id=c.user WHERE c.status="verified" GROUP BY u.id,c.kind ORDER BY quantity DESC')],'listings':[dict(r) for r in c.execute('SELECT l.*,u.name FROM listings l JOIN users u ON u.id=l.user WHERE l.status="available"')]})
    if path=='/api/inventory':return self.send(200,inventory_payload(c,uid))
    if path=='/api/members':return self.send(200,[{k:v for k,v in public(r).items() if k not in ['email','credits']} for r in c.execute('SELECT * FROM users')])
    if path=='/api/contact' and method=='POST':c.execute('INSERT INTO contacts VALUES(?,?,?,?)',(secrets.token_hex(12),required('email'),required('body'),time.time()));c.commit();return self.send(200,{'message':'Message saved for the local community organizer.'})
    auth()
    if path=='/api/profile' and method=='POST':
     cats=data.get('categories',[])
     if not isinstance(cats,list) or len(cats)>100:raise ValueError('Invalid categories')
     avatar=str(data.get('avatar',''))
     if avatar and not avatar.startswith('https://'):raise ValueError('Profile photo must be an HTTPS URL')
     c.execute('UPDATE users SET name=?,city=?,bio=?,categories=?,avatar=? WHERE id=?',(required('name'),required('city'),str(data.get('bio',''))[:2000],json.dumps(cats),avatar,uid))
    elif path=='/api/listings' and method=='POST':
     mode=required('mode')
     if mode not in ['swap','credits','fiat','web3']:raise ValueError('Invalid exchange type')
     price=0 if mode=='swap' else number('price')
     c.execute('INSERT INTO listings(id,user,title,description,category,city,mode,price,image,contact_email,contact_phone) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(secrets.token_hex(12),uid,required('title'),required('description'),required('category'),u['city'],mode,price,data.get('image','garden'),contact_email(data),contact_phone(data)))
    elif path=='/api/trades' and method=='POST':
     l=c.execute('SELECT * FROM listings WHERE id=?',(required('listing'),)).fetchone()
     if not l or l['user']==uid or l['status']!='available':raise ValueError('This listing is not available to request')
     mode=required('mode')
     if mode not in ['swap','credits','fiat','web3']:raise ValueError('Invalid exchange type')
     if mode=='web3':raise ValueError('On-chain escrow is not configured. Choose another settlement method.')
     amount=0 if mode=='swap' else number('amount')
     c.execute('INSERT INTO trades(id,listing,buyer,seller,offer,mode,amount,due) VALUES(?,?,?,?,?,?,?,?)',(secrets.token_hex(12),l['id'],uid,l['user'],required('offer'),mode,amount,required('due')))
    elif path=='/api/trade-action' and method=='POST':
     c.execute('BEGIN IMMEDIATE');t=c.execute('SELECT * FROM trades WHERE id=?',(required('id'),)).fetchone();action=required('action')
     if not t or uid not in [t['buyer'],t['seller']]:raise PermissionError('Request not accessible')
     if action in ['accept','decline']:
      if uid!=t['seller'] or t['status']!='pending':raise ValueError('Only the listing owner can respond to a pending request')
      if action=='accept':
       l=c.execute('SELECT status FROM listings WHERE id=?',(t['listing'],)).fetchone()
       if l['status']!='available':raise ValueError('Listing is already reserved')
       c.execute('UPDATE listings SET status="reserved" WHERE id=?',(t['listing'],))
       c.execute('UPDATE trades SET status="declined" WHERE listing=? AND id<>? AND status="pending"',(t['listing'],t['id']))
      c.execute('UPDATE trades SET status=? WHERE id=?',('accepted' if action=='accept' else 'declined',t['id']))
     elif action=='complete':
      if t['status']!='accepted':raise ValueError('This trade is not awaiting completion')
      col='buyer_done' if uid==t['buyer'] else 'seller_done';c.execute('UPDATE trades SET '+col+'=1 WHERE id=?',(t['id'],));t=c.execute('SELECT * FROM trades WHERE id=?',(t['id'],)).fetchone()
      if t['buyer_done'] and t['seller_done']:
       if t['mode']=='credits':
        if c.execute('SELECT credits FROM users WHERE id=?',(t['buyer'],)).fetchone()[0]<t['amount']:raise ValueError('Buyer has insufficient credits')
        c.execute('UPDATE users SET credits=credits-? WHERE id=?',(t['amount'],t['buyer']));c.execute('UPDATE users SET credits=credits+? WHERE id=?',(t['amount'],t['seller']))
       c.execute('UPDATE trades SET status="completed" WHERE id=?',(t['id'],));c.execute('UPDATE listings SET status="exchanged" WHERE id=?',(t['listing'],));c.execute('UPDATE users SET score=score+5 WHERE id IN (?,?)',(t['buyer'],t['seller']))
     else:raise ValueError('Invalid action')
    elif path=='/api/contributions' and method=='POST':
     kind=required('kind');rates={'labor':15,'produce':2.5,'solar':1,'kinetic':1,'water':0.25}
     if kind not in rates:raise ValueError('Unknown contribution')
     q=number('quantity');verifier=required('verifier')
     if verifier==uid or not c.execute('SELECT id FROM users WHERE id=?',(verifier,)).fetchone():raise ValueError('Choose another member to verify your contribution')
     c.execute('INSERT INTO contributions VALUES(?,?,?,?,?,?,?,?)',(secrets.token_hex(12),uid,kind,q,round(q*rates[kind],2),verifier,'pending',time.time()))
    elif path=='/api/verify' and method=='POST':
     c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM contributions WHERE id=?',(required('id'),)).fetchone()
     if not r or r['verifier']!=uid or r['status']!='pending':raise PermissionError('Only the nominated verifier may confirm a pending contribution')
     c.execute('UPDATE contributions SET status="verified" WHERE id=?',(r['id'],));c.execute('UPDATE users SET credits=credits+?,score=score+? WHERE id=?',(r['credits'],r['credits'],r['user']))
    elif path=='/api/pledges' and method=='POST':
     amount=number('amount');c.execute('BEGIN IMMEDIATE')
     if c.execute('SELECT credits FROM users WHERE id=?',(uid,)).fetchone()[0]<amount:raise ValueError('Insufficient credits')
     c.execute('UPDATE users SET credits=credits-? WHERE id=?',(amount,uid));c.execute('INSERT INTO pledges VALUES(?,?,?,?)',(secrets.token_hex(12),uid,amount,time.time()))
    elif path=='/api/allocate' and method=='POST':
     spec=next((item for item in STOCKS if item['id']==required('kind')),None)
     if not spec:raise ValueError('Unknown shared resource')
     quantity=number('quantity');week=iso_week();c.execute('BEGIN IMMEDIATE')
     inventory=inventory_payload(c,uid);stock=next(item for item in inventory['stocks'] if item['id']==spec['id'])
     if quantity>stock['youRemaining']+1e-9:raise ValueError('That amount is above your weekly allocation of '+str(spec['weekly_limit'])+' '+spec['unit'])
     if quantity>stock['available']+1e-9:raise ValueError('There is not enough '+spec['label'].lower()+' in the Commons this week')
     c.execute('INSERT INTO allocations VALUES(?,?,?,?,?,?)',(secrets.token_hex(12),uid,spec['id'],quantity,week,time.time()))
    elif path=='/api/dashboard':
     return self.send(200,{'trades':[dict(r) for r in c.execute('SELECT t.*,l.title FROM trades t JOIN listings l ON l.id=t.listing WHERE buyer=? OR seller=?',(uid,uid))],'contributions':[dict(r) for r in c.execute('SELECT c.*,u.name FROM contributions c JOIN users u ON u.id=c.user WHERE c.user=? OR c.verifier=?',(uid,uid))],'pledges':c.execute('SELECT COALESCE(SUM(amount),0) FROM pledges WHERE user=?',(uid,)).fetchone()[0],'pool':c.execute('SELECT COALESCE(SUM(amount),0) FROM pledges').fetchone()[0]})
    elif path=='/api/messages' and method=='GET':return self.send(200,[dict(r) for r in c.execute('SELECT m.*,u.name FROM messages m JOIN users u ON u.id=m.user ORDER BY created DESC LIMIT 100')][::-1])
    elif path=='/api/messages' and method=='POST':c.execute('INSERT OR IGNORE INTO messages VALUES(?,?,?,?)',(required('id'),uid,required('body'),time.time()))
    elif path=='/api/kyc' and method=='POST':
     key=os.getenv('DIDIT_API_KEY');workflow=os.getenv('DIDIT_WORKFLOW_ID')
     if not key or not workflow:return self.send(503,{'error':'Identity verification is not configured yet. Contact the community organizer.'})
     req=urllib.request.Request('https://verification.didit.me/v3/session/',data=json.dumps({'workflow_id':workflow,'vendor_data':uid}).encode(),headers={'Content-Type':'application/json','x-api-key':key})
     with urllib.request.urlopen(req,timeout=20) as resp:session=json.load(resp)
     c.execute('INSERT OR REPLACE INTO kyc_sessions VALUES(?,?,?)',(uid,session['session_id'],'Pending'));c.commit();return self.send(200,{'url':session['url']})
    elif path=='/api/kyc-status':
     row=c.execute('SELECT * FROM kyc_sessions WHERE user=?',(uid,)).fetchone()
     if not row:return self.send(200,{'status':'Not started'})
     key=os.getenv('DIDIT_API_KEY')
     if not key:return self.send(503,{'error':'Verification provider is not configured'})
     req=urllib.request.Request('https://verification.didit.me/v3/session/'+row['session']+'/decision/',headers={'x-api-key':key,'Accept':'application/json'})
     with urllib.request.urlopen(req,timeout=20) as resp:decision=json.load(resp)
     if decision.get('vendor_data')!=uid:raise ValueError('Verification account mismatch')
     status=str(decision['status']);c.execute('UPDATE kyc_sessions SET status=? WHERE user=?',(status,uid));c.commit();return self.send(200,{'status':status})
    else:return self.send(404,{'error':'Endpoint not found'})
    c.commit();return self.send(200,{'ok':True})
  except (BrokenPipeError,ConnectionResetError):return
  except ConnectionError as e:self.send(503,{'error':str(e)})
  except PermissionError as e:self.send(401,{'error':str(e)})
  except sqlite3.IntegrityError:self.send(409,{'error':'This email is already registered'})
  except (ValueError,KeyError,TypeError) as e:self.send(400,{'error':str(e)})
  except Exception as e:print(type(e).__name__,str(e));self.send(500,{'error':'The request could not be completed. Please try again.'})
if __name__=='__main__':
 init()
 host=os.getenv('HOST','127.0.0.1');port=int(os.getenv('PORT','8000'))
 print('Commons API: http://'+host+':'+str(port),flush=True)
 ThreadingHTTPServer((host,port),API).serve_forever()
