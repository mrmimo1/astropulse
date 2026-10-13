"""Offline tests for the current personalized digest. No live API calls."""
import unittest
import main as m


def profile(language='bn', name='Riya', dob='2001-08-23'):
    return dict(chat_id=42, dob=dob, display_name=name, language=language,
                location_label='Kolkata, India', timezone='Asia/Kolkata',
                latitude=22.57, longitude=88.36, panchang_india=True,
                weather_enabled=True, ai_enabled=False, ai_scope_version=0,
                delivery_time='08:30', active=True)


class Numbers(unittest.TestCase):
    def test_reduce_all(self):
        for value, expected in [(1,1),(9,9),(10,1),(11,2),(22,4),(99,9),(2042,8)]:
            self.assertEqual(m.reduce_number(value), expected)
        for value in [0,-1]:
            with self.assertRaises(ValueError): m.reduce_number(value)

    def test_shared_fixtures(self):
        cases = [('1999-01-15','2026-10-12',[6,8,8,9,3,5]),
                 ('2001-08-23','2026-10-12',[5,7,5,6,9,5]),
                 ('1994-12-07','2026-10-12',[7,6,2,3,6,5]),
                 ('1999-01-15','2026-10-13',[6,8,8,9,4,6])]
        for dob, date, expected in cases:
            self.assertEqual(m.numbers(dob,date)['values'], expected)
            self.assertEqual(len(m.numbers(dob,date)['traces']),6)

    def test_invalid_dates(self):
        for dob, date in [('2001-02-29','2026-10-12'),('1999-01-15','2026-02-30')]:
            with self.assertRaises(ValueError): m.numbers(dob,date)

    def test_all_languages_and_names(self):
        for lang in ['bn','en','hi']:
            for name in ['Riya','Arko',None,'']:
                p=profile(lang,name)
                text=m.render(p,'2026-10-12',weather={'category':'rain','low':24,'high':29})
                first=text.splitlines()[0]
                self.assertTrue(first.startswith('🌅'))
                if name: self.assertIn(name,first)
                else: self.assertNotIn(',',first)
                self.assertNotIn('Sayantan',text)
                self.assertIn('🎨',text);self.assertIn('🔢',text)
                self.assertEqual(int('🎧' in text)+int('🎙️' in text),1)
                self.assertIn('Open-Meteo',text)
                self.assertNotIn('undefined',text)
                if lang=='hi': self.assertNotRegex(text,r'[\u0900-\u097f]')

    def test_user_and_date_variation(self):
        texts=[m.render(profile(dob=dob),'2026-10-12') for dob in
               ['1999-01-15','2001-08-23','1994-12-07']]
        self.assertEqual(len(set(texts)),3)
        texts=[m.render(profile(),date) for date in
               ['2026-10-12','2026-10-13','2026-10-14']]
        self.assertEqual(len(set(texts)),3)

    def test_calendar_media_alternation(self):
        for start in ['2026-10-12','2026-12-30','2028-02-28']:
            previous=None
            for offset in range(5):
                date=(m.dt.date.fromisoformat(start)+m.dt.timedelta(days=offset)).isoformat()
                text=m.render(profile(),date)
                kind='song' if '🎧' in text else 'podcast'
                if previous: self.assertNotEqual(kind,previous)
                previous=kind
                self.assertEqual(text,m.render(profile(),date))

    def test_ai_payload_privacy_and_old_scope(self):
        p=profile();payload=m.digest_payload(p,'2026-10-12',{'category':'rain'})
        self.assertEqual(payload['name'],'Riya')
        self.assertEqual(payload['city'],m.city_name(p))
        for key in ['dob','birth_place','birth_time','latitude','longitude','chat_id']:
            self.assertNotIn(key,payload)
        p.update(ai_enabled=True,ai_scope_version=0)
        self.assertIsNone(m.ai_for(p,'2026-10-12'))


if __name__=='__main__': unittest.main()
