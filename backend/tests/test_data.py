import unittest
from pathlib import Path
from app.data import load_contractors, parse_bool
from app.ranking import explain
from app.models import FindRequest

class DataTests(unittest.TestCase):
    def test_source_conversion(self):
        rows = load_contractors(Path(__file__).resolve().parents[1] / 'data/contractors.csv')
        self.assertEqual(len(rows), 66)
        self.assertEqual(len({r['id'] for r in rows}), 66)
        self.assertEqual(sum(r['synthetic'] for r in rows), 13)
        self.assertEqual(sum(r['price_imputed'] for r in rows), 18)
        self.assertEqual(sum(r['max_hours'] is None for r in rows), 9)
        self.assertTrue(any(len(r['categories']) > 1 for r in rows))
        self.assertFalse(parse_bool('False'))
        with self.assertRaises(ValueError):
            parse_bool('maybe')
        req = FindRequest(city='Алматы', category='Флорист', event_date='2026-11-14',
                          event_format='свадьба', budget_kzt=1000000)
        self.assertIn('Оценочная цена', explain(rows[0], req))
