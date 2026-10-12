"""Offline delivery tests. getMe is not a send; only sendMessage counts.
Compatible with sharpened catalog and optional AI main.py. No API calls/keys.
"""
import json
import unittest
from unittest.mock import patch
import main

class Delivery(unittest.TestCase):
    def test_sent_failed_unknown_and_duplicate(self):
        profile={'chat_id':42,'dob':'1992-03-14','language':'en','timezone':'Asia/Kolkata',
                 'delivery_time':'00:00','panchang_india':False,'active':True,
                 'location_label':'Delhi','weather_enabled':False,'ai_enabled':False}
        for failure,expected in [(None,'sent'),(main.urllib.error.URLError('timeout'),'unknown'),
                                 (main.urllib.error.HTTPError('redacted',403,'Forbidden',None,None),'failed')]:
            with self.subTest(status=expected):
                ledger={};sends=[];lookups=[]
                def db(path,method='GET',body=None,prefer=None):
                    if path.startswith('rpc/'):return None
                    if path.startswith('astro_profiles'):return [profile]
                    if path=='astro_deliveries' and method=='POST':
                        if ledger:raise main.urllib.error.HTTPError('redacted',409,'Conflict',None,None)
                        ledger.update(body);return None
                    if path.startswith('astro_deliveries?') and method=='PATCH':ledger.update(body);return None
                    raise AssertionError(path)
                def request(url,method='GET',body=None,headers=None):
                    if url.endswith('/getMe'):
                        lookups.append(url)
                        return {'ok':True,'result':{'is_bot':True,'username':'OfflineTestBot'}}
                    self.assertTrue(url.endswith('/sendMessage'), 'Unexpected network action in test')
                    sends.append(body)
                    if failure:raise failure
                    return {'ok':True,'result':{'message_id':12}}
                # No real weather/AI requests: profile explicitly disables both.
                with patch.object(main,'db',db),patch.object(main,'request',request),patch.object(main.time,'sleep'),patch.dict(main.os.environ,{'TELEGRAM_BOT_TOKEN':'test-only-token','TELEGRAM_BOT_USERNAME':''}):
                    if failure:
                        with self.assertRaises(SystemExit):main.run()
                    else:main.run()
                    self.assertEqual(ledger['status'],expected)
                    self.assertEqual(len(sends),1)
                    self.assertIn('text',sends[0]);self.assertTrue(sends[0]['text'])
                    self.assertIn('reply_markup',sends[0])
                    self.assertIn('OfflineTestBot',sends[0]['reply_markup']['inline_keyboard'][0][0]['url'])
                    if expected=='sent':self.assertEqual(ledger['message_id'],12)
                    else:self.assertNotIn('message_id',ledger)
                    main.run() # duplicate claim suppresses retry for sent/failed/unknown
                    self.assertEqual(len(sends),1, 'A duplicate or ambiguous send must never resend')

    def test_preparation_failure_one_friendly_attempt(self):
        profile={'chat_id':42,'dob':'1992-03-14','language':'en','timezone':'Asia/Kolkata',
                 'delivery_time':'00:00','panchang_india':False,'active':True,
                 'location_label':'Delhi','weather_enabled':False,'ai_enabled':False}
        ledger={};sends=[]
        def db(path,method='GET',body=None,prefer=None):
            if path.startswith('rpc/'):return None
            if path.startswith('astro_profiles'):return [profile]
            if path=='astro_deliveries' and method=='POST':
                if ledger:raise main.urllib.error.HTTPError('redacted',409,'Conflict',None,None)
                ledger.update(body);return None
            if path.startswith('astro_deliveries?') and method=='PATCH':ledger.update(body);return None
            raise AssertionError(path)
        def request(url,method='GET',body=None,headers=None):
            self.assertTrue(url.endswith('/sendMessage'))
            sends.append(body)
            return {'ok':True,'result':{'message_id':99}}
        with patch.object(main,'db',db),patch.object(main,'request',request),patch.object(main,'render',side_effect=ValueError('offline preparation error')),patch.object(main.time,'sleep'),patch.dict(main.os.environ,{'TELEGRAM_BOT_TOKEN':'test-only-token','TELEGRAM_BOT_USERNAME':'OfflineTestBot'}):
            main.run();main.run()
            self.assertEqual(len(sends),1)
            self.assertIn('Ektu jhamela hocche',sends[0]['text'])
            self.assertEqual(ledger['status'],'sent')
