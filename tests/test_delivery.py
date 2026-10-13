"""Mocked delivery tests. Never uses live Telegram, Supabase or AI."""
import contextlib
import copy
import io
import json
import unittest
import urllib.error
from unittest.mock import patch
import main as m


def profile():
    return dict(chat_id=42,dob='1999-01-15',display_name='Riya',language='bn',
                timezone='Asia/Kolkata',delivery_time='08:30',active=True,
                location_label='Kolkata, India',latitude=22.57,longitude=88.36,
                panchang_india=True,weather_enabled=True,ai_enabled=False,
                ai_scope_version=0)


class Delivery(unittest.TestCase):
    def exercise(self, mode='ok', generated=None, weather=None, before_due=False,
                 page=False, panchang_fails=False):
        p=profile();claims=set();sends=[];writes=[];summaries=[]
        def db(path, method='GET', body=None, prefer=None):
            if path=='rpc/astro_cleanup': return None
            if path.startswith('astro_profiles?active=eq.true'):
                if page:
                    return [copy.deepcopy(p) for _ in range(500)] if 'offset=0' in path else []
                return [copy.deepcopy(p)]
            if path.startswith('astro_profiles?chat_id=eq.'):
                return [] if mode=='stop' else [copy.deepcopy(p)]
            if path=='astro_deliveries' and method=='POST':
                key=(body['chat_id'],body['local_date'])
                if mode=='duplicate' or key in claims:
                    raise urllib.error.HTTPError('https://mock',409,'conflict',None,None)
                claims.add(key);writes.append((path,method,copy.deepcopy(body)));return None
            if path.startswith('astro_deliveries?'):
                writes.append((path,method,copy.deepcopy(body)))
                if method=='DELETE': claims.clear()
                return None
            raise AssertionError('Unexpected DB call '+path)
        def request(url,method='GET',body=None,headers=None):
            self.assertIn('/sendMessage',url);sends.append(copy.deepcopy(body))
            if mode=='timeout': raise TimeoutError('mock timeout')
            if mode=='http': raise urllib.error.HTTPError(url,400,'mock failure',None,None)
            if mode=='false': return {'ok':False}
            return {'ok':True,'result':{'message_id':123}}
        def pan(*args):
            if panchang_fails: raise urllib.error.URLError('mock unavailable')
            return None
        with patch.object(m,'db',side_effect=db), patch.object(m,'request',side_effect=request), \
             patch.object(m,'discover_bot_username',return_value='AstroPulseTestBot'), \
             patch.object(m,'due',return_value=(not before_due,'2026-10-13')), \
             patch.object(m,'panchang',side_effect=pan), \
             patch.object(m,'fetch_weather',return_value=weather), \
             patch.object(m,'ai_for',return_value=generated), \
             patch.object(m.time,'sleep'), patch.dict(m.os.environ,{'TELEGRAM_BOT_TOKEN':'fake'}):
            for _ in range(2 if mode in ['ok','timeout','http','false'] else 1):
                out=io.StringIO()
                with contextlib.redirect_stdout(out):
                    if mode in ['timeout','http','false']:
                        # First run errors for review, second skips the existing claim.
                        try: m.run()
                        except SystemExit: pass
                    else: m.run()
                summaries.append(json.loads(out.getvalue()))
        return sends,writes,summaries

    def test_due_and_timezone(self):
        p=profile()
        self.assertFalse(m.due(p,m.dt.datetime(2026,10,13,2,59,tzinfo=m.dt.timezone.utc))[0])
        self.assertEqual(m.due(p,m.dt.datetime(2026,10,13,3,0,tzinfo=m.dt.timezone.utc)),(True,'2026-10-13'))
        p['timezone']='Asia/Calcutta'
        self.assertTrue(m.due(p,m.dt.datetime(2026,10,13,3,0,tzinfo=m.dt.timezone.utc))[0])

    def test_sends_once_and_records_message(self):
        sends,writes,counts=self.exercise(weather={'category':'rain','low':24,'high':29})
        self.assertEqual(len(sends),1)
        self.assertEqual(sends[0]['chat_id'],42)
        self.assertIn('Riya',sends[0]['text'].splitlines()[0])
        self.assertNotIn('Sayantan',sends[0]['text'])
        self.assertIn('Open-Meteo',sends[0]['text'])
        self.assertEqual(counts[0]['sent'],1);self.assertEqual(counts[1]['skipped'],1)
        self.assertIn({'status':'sent','message_id':123},[body for _,method,body in writes if method=='PATCH'])

    def test_duplicate_claim_suppresses_send(self):
        sends,_,counts=self.exercise(mode='duplicate')
        self.assertEqual(sends,[]);self.assertEqual(counts[0]['skipped'],1)

    def test_stop_after_claim_suppresses_send(self):
        sends,writes,_=self.exercise(mode='stop')
        self.assertEqual(sends,[]);self.assertTrue(any(method=='DELETE' for _,method,_ in writes))

    def test_not_due_suppresses_send(self):
        sends,writes,_=self.exercise(before_due=True)
        self.assertEqual(sends,[]);self.assertEqual(writes,[])

    def test_failed_or_uncertain_send_never_retries(self):
        for mode,status in [('timeout','unknown'),('http','failed'),('false','failed')]:
            with self.subTest(mode=mode):
                sends,writes,counts=self.exercise(mode=mode)
                self.assertEqual(len(sends),1)
                self.assertIn({'status':status},[body for _,method,body in writes if method=='PATCH'])
                self.assertEqual(counts[1]['skipped'],1)

    def test_pagination_and_same_user_dedup(self):
        sends,_,counts=self.exercise(page=True)
        self.assertEqual(len(sends),1)
        self.assertEqual(counts[0]['skipped'],499)

    def test_panchang_failure_and_missing_weather_keep_digest(self):
        sends,_,_=self.exercise(panchang_fails=True)
        text=sends[0]['text']
        self.assertIn('এখন আবহাওয়ার তথ্য পাওয়া যায়নি',text)
        self.assertNotIn('Ektu jhamela',text)
        self.assertIn('🎨',text);self.assertIn('🔢',text)

    def test_current_ai_note_contract(self):
        note='A gentle morning can leave room for one clear thought. Later the day may feel a little lighter. Keep some patience today.'
        sends,_,_=self.exercise(generated={'note':note})
        self.assertIn(note,sends[0]['text'])
        self.assertNotIn('Ektu jhamela',sends[0]['text'])

    def test_ai_weather_omission_uses_full_normal_note(self):
        sends,_,_=self.exercise(generated={'note':'One thought may become clearer today. Give it some time and do not rush to decide.'},weather={'category':'rain','low':24,'high':29})
        self.assertIn('Open-Meteo',sends[0]['text'])
        self.assertIn('বৃষ্টি',sends[0]['text'])
        self.assertNotIn('Ektu jhamela',sends[0]['text'])

    def test_all_languages_share_markup_and_single_media(self):
        for lang in ['bn','en','hi']:
            p={**profile(),'language':lang}
            normal=m.render(p,'2026-10-13')
            ai=m.render_ai(p,'2026-10-13',{'note':'One small thought can give this morning room to breathe. Later you may feel a little lighter. Take your time today.'})
            for text in [normal,ai]:
                self.assertEqual(int('🎧' in text)+int('🎙️' in text),1)
                self.assertIn('Riya',text.splitlines()[0])
                self.assertNotIn('Sayantan',text)
            markup=m.share_markup(lang,'AstroPulseTestBot')
            self.assertTrue(markup['inline_keyboard'][0][0]['text'].startswith('📤'))


if __name__=='__main__': unittest.main()
