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


class AIDelivery(unittest.TestCase):
    def test_ai_off_and_cap_exhausted_never_call_provider(self):
        profile = {'chat_id': 42, 'dob': '1992-03-14', 'language': 'bn', 'ai_enabled': False}
        with patch.dict(main.os.environ, {'GEMINI_API_KEY': 'offline-placeholder'}, clear=True), \
             patch.object(main, 'ai_generate') as generate, patch.object(main, 'db', return_value=False) as db:
            self.assertIsNone(main.ai_for(profile, '2026-10-11'))
            db.assert_not_called()
            profile['ai_enabled'] = True
            self.assertIsNone(main.ai_for(profile, '2026-10-11'))
            db.assert_called_once_with('rpc/astro_ai_claim', 'POST',
                {'p_chat_id': 42, 'p_kind': 'digest', 'p_limit': 5})
            generate.assert_not_called()

    def test_ai_payload_omits_birth_and_location_identifiers(self):
        profile = {'chat_id': 42, 'dob': '1992-03-14', 'language': 'bn', 'ai_enabled': True,
                   'latitude': 19.1, 'longitude': 72.8, 'location_label': 'Private place'}
        output = {'thought': 'এখন কাজটা দেখে নিন।', 'action': 'প্রথম ধাপ লিখুন।', 'reminder': 'ভবিষ্যদ্বাণী নয়।'}
        with patch.dict(main.os.environ, {'GEMINI_API_KEY': 'offline-placeholder'}, clear=True), \
             patch.object(main, 'db', return_value=True), patch.object(main, 'ai_generate', return_value=output) as generate:
            self.assertEqual(main.ai_for(profile, '2026-10-11', weather={'category': 'rain'}), output)
            payload = generate.call_args.args[0]
            self.assertEqual(set(payload), {'language', 'date', 'kind', 'numbers', 'weather'})
            self.assertEqual(payload['weather'], 'rain')
            self.assertNotIn(profile['dob'], json.dumps(payload))
            self.assertNotIn(profile['location_label'], json.dumps(payload))

    def test_ai_provider_failure_allows_catalog_fallback(self):
        profile = {'chat_id': 42, 'dob': '1992-03-14', 'language': 'bn', 'ai_enabled': True}
        with patch.dict(main.os.environ, {'GEMINI_API_KEY': 'offline-placeholder'}, clear=True), \
             patch.object(main, 'db', return_value=True), patch.object(main, 'ai_generate', side_effect=RuntimeError('offline')):
            self.assertIsNone(main.ai_for(profile, '2026-10-11'))
        text = main.render(profile, '2026-10-11')
        self.assertIn(main.SHORT_READING['bn']['notice'], text)
        self.assertNotIn('ছোট্ট', text)
