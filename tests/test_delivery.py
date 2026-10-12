import datetime as dt
import json
import pathlib
import unittest
import main

class Numbers(unittest.TestCase):
    def test_bengali_fallback_copy_and_all_number_variants(self):
        expected = [
            'আজ সংখ্যার মিলকে শুরু করার একটা ভাবনা হিসেবে নিন।',
            'আজ সংখ্যার মিলকে অন্যভাবে দেখার একটা ভাবনা হিসেবে নিন।',
            'আজ সংখ্যার মিলকে থেমে দেখে নেওয়ার একটা ভাবনা হিসেবে নিন।',
        ]
        self.assertEqual(main.SHORT_READING['bn']['tones'], expected)
        self.assertEqual(main.SHORT_READING['bn']['notice'],
                         'রং আর সংখ্যা এখানে ভাবনার প্রতীক, ভাগ্য বা ভবিষ্যতের সংকেত নয়। সিদ্ধান্ত নিন বাস্তব তথ্য আর নিজের পরিস্থিতি দেখে।')
        for birth in ['1992-03-14', '1990-01-01', '2000-09-09']:
            for day in range(1, 29):
                p = {'language': 'bn', 'dob': birth}
                date = '2026-10-%02d' % day
                text = main.short_reading(p, date)
                n = main.numbers(birth, date)
                tone = main.theme_tone(n['values'][0], n['values'][4])
                self.assertIn(expected[tone], text)
                self.assertIn(main.SHORT_READING['bn']['day'][n['values'][4]-1], text)
                self.assertNotIn('ছোট্ট', text)
                self.assertLess(len(text), 4096)

    def test_bengali_ai_copy_keeps_fixed_symbolic_reminder(self):
        p = {'language': 'bn'}
        output = {'thought': 'কাজ অনেক হলে কোথা থেকে শুরু করবেন, ভাবা কঠিন হতে পারে।',
                  'action': 'একটা কাজ বেছে নিয়ে তার প্রথম ধাপটা লিখুন।',
                  'reminder': 'This provider reminder must not override the fixed one.'}
        text = main.render_ai(p, '2026-10-11', output)
        self.assertEqual(text.splitlines(), [
            '🌷 আজ একটু ভেবে দেখুন', output['thought'], output['action'],
            '✨ মনে রাখবেন: সংখ্যা এখানে ভাবনার প্রতীক, ভবিষ্যদ্বাণী নয়।'])
        self.assertNotIn(output['reminder'], text)
        self.assertNotIn('ছোট্ট', text)
        for rule in ['warm and conversational', 'connected sentences',
                     'Practical confidence', 'future outcomes', 'ছোট্ট filler']:
            self.assertIn(rule, main.AI_RULES)

    def test_shared_fixtures(self):
        fixtures=json.loads((pathlib.Path(__file__).parent/'fixtures.json').read_text())
        for f in fixtures:
            self.assertEqual(main.numbers(f['dob'],f['target']),{k:f[k] for k in ['values','traces','method']})
    def test_independent_known_case(self):
        # DOB 14-03-1992: 1+4+0+3+1+9+9+2=29->11->2.
        # 2026 target: year 14+3+2026=2043->9, Oct=9+10->1, day=1+11->3.
        self.assertEqual(main.numbers('1992-03-14','2026-10-11')['values'],[5,2,9,1,3,4])
    def test_reduce_all(self):
        for n,v in [(11,2),(22,4),(33,6),(29,2),(999,9)]:self.assertEqual(main.reduce_number(n),v)
        with self.assertRaises(ValueError):main.reduce_number(0)
    def test_invalid_date(self):
        with self.assertRaises(ValueError):main.numbers('2001-02-29','2026-10-11')
    def test_due(self):
        p={'timezone':'Asia/Kolkata','delivery_time':'07:00'}
        self.assertEqual(main.due(p,dt.datetime(2026,10,11,1,29,tzinfo=dt.timezone.utc)),(False,'2026-10-11'))
        self.assertEqual(main.due(p,dt.datetime(2026,10,11,1,30,tzinfo=dt.timezone.utc)),(True,'2026-10-11'))
    def test_all_languages(self):
        for lang in ['en','bn','hi']:
            p={'language':lang,'dob':'1992-03-14','timezone':'Asia/Kolkata','location_label':'Delhi','panchang_india':True}
            text=main.render(p,'2026-10-11')
            self.assertLess(len(text),4096)
            self.assertIn(main.SHORT_READING[lang]['notice'],text)
            self.assertIn('🎧',text)
            self.assertIn('🎙️',text)
            self.assertIn(main.SHORT_READING[lang]['advice'],text)
            # Detailed /why output retains the full phase/medical disclaimer.
            detailed=main.render(p,'2026-10-11',why=True)
            self.assertIn(main.DISCLAIMER[lang],detailed)
            if lang != 'bn':self.assertIn(main.METHOD,detailed)
