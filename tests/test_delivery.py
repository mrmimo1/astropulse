import datetime as dt
import unittest
from unittest.mock import patch
import main

class Delivery(unittest.TestCase):
    def test_sent_failed_unknown_and_duplicate(self):
        profile={'chat_id':42,'dob':'1992-03-14','language':'en','timezone':'Asia/Kolkata',
                 'delivery_time':'00:00','panchang_india':False,'active':True,'location_label':'Delhi'}
        for failure,expected in [(None,'sent'),(main.urllib.error.URLError('network timeout'),'unknown'),
                                 (main.urllib.error.HTTPError('redacted',403,'Forbidden',None,None),'failed')]:
            ledger={};calls=[]
            def db(path,method='GET',body=None,prefer=None):
                if path.startswith('rpc/'):return None
                if path.startswith('astro_profiles'):return [profile]
                if path=='astro_deliveries' and method=='POST':
                    if ledger:raise main.urllib.error.HTTPError('redacted',409,'Conflict',None,None)
                    ledger.update(body);return None
                if path.startswith('astro_deliveries?') and method=='PATCH':ledger.update(body);return None
                raise AssertionError(path)
            def request(*args,**kwargs):
                calls.append(1)
                if failure:raise failure
                return {'ok':True,'result':{'message_id':12}}
            with patch.object(main,'db',db),patch.object(main,'request',request),patch.object(main.time,'sleep'),patch.dict(main.os.environ,{'TELEGRAM_BOT_TOKEN':'test-only-token'}):
                if failure:
                    with self.assertRaises(SystemExit):main.run()
                else:main.run()
                self.assertEqual(ledger['status'],expected)
                main.run() # second run must not send another message, even unknown/failure
                self.assertEqual(len(calls),1)
