import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from test_ranking import Encoder


class LanguageExplanationTests(unittest.TestCase):
    def test_dataset_languages_are_preserved_in_search_explanations(self):
        query = dict(city="Алматы", category="Ведущий", budget_kzt=1000000,
                     event_format="корпоратив", duration_hours=1, event_date="2026-11-14")
        app = create_app(encoder=Encoder())
        with TestClient(app) as client:
            response = client.post("/api/find", json=query)
            self.assertEqual(response.status_code, 200)
            rows = {row["id"]: row for row in app.state.contractors}
            for candidate in response.json()["candidates"]:
                self.assertEqual(set(candidate), {"id", "name", "category", "city",
                                                 "price_from_kzt", "explanation", "synthetic",
                                                 "price_imputed", "city_imputed"})
                self.assertNotIn(rows[candidate["id"]]["description"], candidate["explanation"])
                self.assertLessEqual(len(candidate["explanation"].split(". ")), 2)
                self.assertLess(len(candidate["explanation"]), 450)
            multilingual = [c for c in response.json()["candidates"]
                            if len(rows[c["id"]]["languages"]) > 1]
            self.assertTrue(multilingual)
            for candidate in multilingual:
                languages = rows[candidate["id"]]["languages"]
                self.assertIn(f"языки работы: {', '.join(languages)}",
                              candidate["explanation"])


if __name__ == "__main__":
    unittest.main()
