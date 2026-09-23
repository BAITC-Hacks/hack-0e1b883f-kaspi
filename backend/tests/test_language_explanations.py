import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from test_ranking import Encoder


class LanguageExplanationTests(unittest.TestCase):
    def test_wedding_fallbacks_reference_distinct_source_details(self):
        query = dict(city="Алматы", category="Ведущий", budget_kzt=1000000,
                     event_format="свадьба", duration_hours=10, language="русский",
                     event_date="2026-11-14")
        with TestClient(create_app(encoder=Encoder())) as client:
            response = client.post("/api/find", json=query)
            self.assertEqual(response.status_code, 200)
            candidates = {c["id"]: c for c in response.json()["candidates"]}
            goku = candidates["HK-27222"]["explanation"]
            emilia = candidates["HK-42352"]["explanation"]
            self.assertIn("европейская подача, тонкий юмор", goku)
            self.assertIn("Опыт ведения свадеб 13 лет", emilia)
            evidence = [c["explanation"].split(". В описании", 1)[1]
                        for c in candidates.values()]
            self.assertEqual(len(evidence), len(set(evidence)))
            for c in candidates.values():
                self.assertLessEqual(len(c["explanation"].split(". ")), 2)
                self.assertLess(len(c["explanation"]), 450)

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
