import unittest
from fastapi.testclient import TestClient
from app.main import create_app
from test_ranking import Encoder


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.encoder = Encoder()
        self.client = TestClient(create_app(encoder=self.encoder))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.query = dict(city='Алматы', category='Ведущий', event_date='2026-11-14',
                          event_format='Живая музыка на корпоратив', budget_kzt=1000000,
                          language='RU', duration_hours=4)

    def test_complete_flow_and_cache(self):
        first = self.client.post('/api/find', json=self.query)
        self.assertEqual(first.status_code, 200)
        body = first.json()
        self.assertEqual(body['status'], 'ok')
        self.assertEqual(len(body['candidates']), 3)
        self.assertEqual(body['excluded_count'], 5)
        self.assertFalse(any(c['synthetic'] for c in body['candidates']))
        self.assertTrue(all('описании' in c['explanation'] for c in body['candidates']))
        self.assertEqual(body, self.client.post('/api/find', json=self.query).json())
        self.assertEqual(len(self.encoder.calls), 2)
        self.assertEqual(self.client.get('/health').json()['contractors'], 66)

    def test_missing_category(self):
        self.query['category'] = 'Несуществующая категория'
        body = self.client.post('/api/find', json=self.query).json()
        self.assertEqual(body['status'], 'no_category_in_city')
        self.assertEqual(body['candidates'], [])

    def test_each_hard_filter(self):
        from app.filters import filter_candidates
        from app.models import FindRequest
        row = dict(id="fixture", city="Алматы", categories=["Ведущий", "Шоу"],
                   busy_dates=["2026-11-15"], price_from_kzt=100,
                   languages=["русский"], max_hours=5)
        req = {**self.query, "budget_kzt": 200, "duration_hours": 4}
        self.assertEqual(filter_candidates([row], FindRequest(**req))[1], "ok")
        for change in [dict(budget_kzt=0), dict(language="EN"), dict(duration_hours=9),
                       dict(event_date="2026-11-15")]:
            with self.subTest(change=change):
                matched, status, count, reasons = filter_candidates([row], FindRequest(**{**req, **change}))
                self.assertEqual(status, "no_match")
                self.assertEqual(count, 1)
                self.assertTrue(reasons)
        self.assertEqual(filter_candidates([row], FindRequest(**{**req, "category": "Шоу"}))[1], "ok")
        row["max_hours"] = None
        self.assertEqual(filter_candidates([row], FindRequest(**req))[1], "no_match")

    def test_invalid_requests(self):
        for change in [dict(budget_kzt=-1), dict(event_date='not-a-date'),
                       dict(duration_hours=0), dict(event_format='  ')]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post('/api/find', json={**self.query, **change}).status_code, 422)

if __name__ == '__main__':
    unittest.main()
