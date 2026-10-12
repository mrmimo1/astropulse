import datetime as dt
import json
import pathlib
import unittest
import main

class Numbers(unittest.TestCase):
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
