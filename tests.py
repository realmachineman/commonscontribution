"""Isolated API tests. Supabase identities are mocked; no real accounts/emails are created."""
import unittest,tempfile,threading,json,urllib.request,urllib.error,os
from unittest.mock import patch
import server

class Integration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();server.DB=os.path.join(cls.temp.name,'test.sqlite3');server.init()
  cls.identities={
   'alice-token':{'id':'e9738291-951d-4460-bc6b-38d380426d1a','email':'alice@example.invalid','email_confirmed_at':'2026-09-20','user_metadata':{'name':'Alice Test','city':'Detroit'}},
   'bob-token':{'id':'19fbff6d-531c-4a1e-aa73-5e9bda1eef1d','email':'bob@example.invalid','email_confirmed_at':'2026-09-20','user_metadata':{'name':'Bob Test','city':'Detroit'}}}
  def verify(token):
   if token not in cls.identities:raise PermissionError('Invalid Supabase session')
   return cls.identities[token]
  cls.mock=patch.object(server,'verify_supabase_token',side_effect=verify);cls.mock.start()
  cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.API);threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.base='http://127.0.0.1:'+str(cls.http.server_port)+'/api/'
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.mock.stop();cls.temp.cleanup()
 def req(self,token,path,data=None,expected=200,extra=None):
  headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {}),**(extra or {})}
  request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(request) as response:self.assertEqual(response.status,expected);return json.load(response)
  except urllib.error.HTTPError as error:self.assertEqual(error.code,expected);return json.load(error)
 def test_01_auth_boundary(self):
  self.assertIsNone(self.req(None,'me'));self.req(None,'dashboard',expected=401);self.req('forged-jwt','dashboard',expected=401)
  self.req(None,'signup',{'email':'fake@example.invalid','password':'fake-password'},410)
  self.req(None,'login',{'email':'fake@example.invalid','password':'fake-password'},410)
  self.req(None,'dashboard',expected=401,extra={'Cookie':'commons_session=legacy-cookie'})
  alice=self.req('alice-token','me');self.assertEqual(alice['id'],self.identities['alice-token']['id']);self.assertNotIn('password',alice)
  self.req('alice-token','profile',{'id':self.identities['bob-token']['id'],'name':'Alice Test','city':'Detroit','categories':[]})
  self.assertEqual(self.req('alice-token','me')['id'],alice['id'])
  self.req('alice-token','pledges',{'amount':1},400,extra={'Origin':'https://untrusted.invalid'})
 def test_02_full_exchange(self):
  req=self.req;a='alice-token';b='bob-token';alice=req(a,'me');bob=req(b,'me')
  req(a,'contributions',{'kind':'labor','quantity':2,'verifier':bob['id']});con=req(a,'dashboard')['contributions'][0]
  self.assertEqual(req(a,'me')['credits'],0);req(a,'verify',{'id':con['id']},401);req(b,'verify',{'id':con['id']});req(b,'verify',{'id':con['id']},401);self.assertEqual(req(a,'me')['credits'],30)
  req(a,'contributions',{'kind':'solar','quantity':float('nan'),'verifier':bob['id']},400)
  req(b,'listings',{'title':'Test carrots','description':'A basket','category':'Fresh Produce & Orchard Crop','mode':'credits','price':10});listing=next(x for x in req(a,'listings')if x['title']=='Test carrots')
  req(a,'trades',{'listing':listing['id'],'offer':'Ten credits','mode':'credits','amount':10,'due':'2026-10-01'});trade=req(a,'dashboard')['trades'][0]
  req(a,'trade-action',{'id':trade['id'],'action':'accept'},400);req(b,'trade-action',{'id':trade['id'],'action':'accept'});req(a,'trade-action',{'id':trade['id'],'action':'complete'});self.assertEqual(req(a,'me')['credits'],30);req(b,'trade-action',{'id':trade['id'],'action':'complete'});self.assertEqual(req(a,'me')['credits'],20);self.assertEqual(req(b,'me')['credits'],10);req(b,'trade-action',{'id':trade['id'],'action':'complete'},400)
  req(a,'pledges',{'amount':21},400);req(a,'pledges',{'amount':5});self.assertEqual(req(a,'me')['credits'],15)
  req(a,'messages',{'id':'test-message','body':'Need help in the garden'});req(a,'messages',{'id':'test-message','body':'Duplicate'});self.assertEqual(len(req(a,'messages')),1)
 def test_04_listing_contact_and_weekly_allocation(self):
  req=self.req;a='alice-token';b='bob-token';alice=req(a,'me');bob=req(b,'me')
  req(b,'listings',{'title':'Contact carrots','description':'A basket','category':'Fresh Produce & Orchard Crop','mode':'credits','price':10,'contact_email':'bob@example.invalid','contact_phone':'+1 313 555 0199'})
  listing=next(x for x in req(a,'listings') if x['title']=='Contact carrots')
  self.assertEqual(listing['contact_email'],'bob@example.invalid');self.assertEqual(listing['contact_phone'],'+1 313 555 0199')
  req(b,'listings',{'title':'Bad contact','description':'A basket','category':'Fresh Produce & Orchard Crop','mode':'swap','price':0,'contact_email':'not-an-email'},400)
  food=next(x for x in req(a,'inventory')['stocks'] if x['id']=='food');self.assertEqual(food['weeklyLimit'],4)
  req(a,'allocate',{'kind':'food','quantity':1},400)
  req(a,'contributions',{'kind':'produce','quantity':10,'verifier':bob['id']})
  produce=next(x for x in req(a,'dashboard')['contributions'] if x['kind']=='produce' and x['status']=='pending')
  req(b,'verify',{'id':produce['id']})
  food=next(x for x in req(a,'inventory')['stocks'] if x['id']=='food');self.assertEqual(food['available'],10)
  req(a,'allocate',{'kind':'food','quantity':4})
  food=next(x for x in req(a,'inventory')['stocks'] if x['id']=='food');self.assertEqual(food['available'],6);self.assertEqual(food['youRemaining'],0)
  req(a,'allocate',{'kind':'food','quantity':0.01},400)
 def test_03_no_email_based_account_takeover(self):
  with server.db() as c:
   c.execute('INSERT INTO users(id,name,email,password,city) VALUES(?,?,?,?,?)',('old-local','Original','collision@example.invalid','old-hash','Detroit'));c.commit()
   with self.assertRaises(ValueError):server.resolve_account(c,{'id':'another-uuid','email':'collision@example.invalid'})

class ProviderVerification(unittest.TestCase):
 def test_provider_is_authority(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):return json.dumps({'id':'verified-uuid','email':'person@example.invalid','email_confirmed_at':'2026-09-20'}).encode()
  with patch.object(server,'SUPABASE_URL','https://test.supabase.co'),patch.object(server,'SUPABASE_KEY','sb_publishable_test'),patch.object(server.urllib.request,'urlopen',return_value=Response()) as opened:
   result=server.verify_supabase_token('signed-token');self.assertEqual(result['id'],'verified-uuid');request=opened.call_args.args[0];self.assertEqual(request.full_url,'https://test.supabase.co/auth/v1/user');self.assertEqual(request.get_header('Authorization'),'Bearer signed-token')
 def test_unconfirmed_and_expired_rejected(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):return b'{"id":"unconfirmed","email":"person@example.invalid"}'
  with patch.object(server,'SUPABASE_URL','https://test.supabase.co'),patch.object(server,'SUPABASE_KEY','sb_publishable_test'):
   with patch.object(server.urllib.request,'urlopen',return_value=Response()):
    with self.assertRaises(PermissionError):server.verify_supabase_token('token')
   with patch.object(server.urllib.request,'urlopen',side_effect=urllib.error.HTTPError('url',401,'Unauthorized',{},None)):
    with self.assertRaises(PermissionError):server.verify_supabase_token('expired')
if __name__=='__main__':unittest.main(verbosity=2)
