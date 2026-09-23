import unittest
import numpy as np
from app.ranking import FindRequest, Ranker, description_relevance, explain


def request(event_format, budget_kzt, language=None, duration_hours=None):
    return FindRequest(city="Алматы", event_date="2026-11-14", category="Музыканты",
                       event_format=event_format, budget_kzt=budget_kzt,
                       language=language, duration_hours=duration_hours)


class Encoder:
    def __init__(self):
        self.calls = []

    def encode(self, texts):
        self.calls.append(list(texts))
        return np.array([[0., 0.] if t == "zero" else [1., 0.] for t in texts])


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(id=i, description=d, price_from_kzt=100,
                          languages=["русский"], max_hours=5)
                     for i, d in [("b", "Живая музыка"), ("a", "Ведущий квиза")]]
        self.req = request("Корпоратив", 200, "RU", 3)
        self.model = Encoder()
        self.ranker = Ranker(self.rows, self.model)

    def test_ties_cache_and_input_unchanged(self):
        first = self.ranker.rank_and_explain(self.rows, self.req)
        second = self.ranker.rank_and_explain(list(reversed(self.rows)), self.req)
        self.assertEqual(first, second)
        self.assertEqual([c["id"] for c in first], ["a", "b"])
        self.assertEqual(len(self.model.calls), 2)
        self.assertNotIn("score", self.rows[0])
        self.assertTrue(all(len(c["explanation"].split(". ")) <= 2 for c in first))

    def test_no_invented_matches(self):
        text = explain(self.rows[0], request("Свадьба", 0, "KZ", 8))
        self.assertNotIn("укладывается", text)
        self.assertNotIn("достаточно", text)
        self.assertNotIn("подходит по формату", text)
        self.assertIn("нет точных ключевых слов запроса", text)
        self.assertNotIn("Живая музыка", text)

    def test_long_bio_is_replaced_by_short_keyword_evidence(self):
        bio = "Лучший ведущий города. Работаю только на английском. " * 100 + "Веду корпоратив."
        row = {**self.rows[0], "description": bio, "event_formats": ["корпоратив"]}
        text = explain(row, self.req)
        self.assertIn("ключевые слова запроса: «корпоратив»", text)
        self.assertIn("формат «Корпоратив» указан в профиле", text)
        self.assertNotIn("Лучший", text)
        self.assertNotIn("английском", text)
        self.assertEqual(len(text.split(". ")), 2)
        self.assertLess(len(text), 400)

    def test_keyword_evidence_is_bounded_and_does_not_assert_a_match(self):
        text = description_relevance("Не провожу корпоратив. Музыка, танцы, квиз, шоу.",
                                     "Корпоратив музыка танцы квиз шоу")
        self.assertEqual(text, "В описании найдены ключевые слова запроса: «корпоратив, музыка, танцы»")
        self.assertLessEqual(len(text.split()), 15)
        self.assertNotIn("подходит", text)

    def test_unrelated_description_does_not_claim_format_support(self):
        row = {**self.rows[0], "event_formats": ["свадьба"]}
        text = explain(row, self.req)
        self.assertNotIn("указан в профиле", text)
        self.assertIn("нет точных ключевых слов запроса", text)

    def test_stale_and_unknown_candidates(self):
        for updates in [{"description": "changed"}, {"id": "unknown"}]:
            with self.assertRaises(ValueError):
                self.ranker.rank_and_explain([{**self.rows[0], **updates}], self.req)

    def test_all_languages_without_requested_language(self):
        row = {**self.rows[0], "languages": ["русский", "казахский"]}
        text = explain(row, request("корпоратив", 200))
        self.assertIn("языки работы: русский, казахский", text)

    def test_requested_language_matches_any_list_position(self):
        row = {**self.rows[0], "languages": ["русский", "казахский"]}
        for language in row["languages"]:
            with self.subTest(language=language):
                text = explain(row, request("корпоратив", 200, language))
                self.assertIn(f"язык работы: {language}. В описании", text)
                self.assertNotIn("языки работы:", text)

    def test_unmatched_language_has_no_language_claim(self):
        row = {**self.rows[0], "languages": ["русский", "казахский"]}
        for language in ["английский", "рус"]:
            with self.subTest(language=language):
                text = explain(row, request("корпоратив", 200, language))
                self.assertNotIn("язык работы:", text)
                self.assertNotIn("языки работы:", text)

    def test_missing_languages_have_no_language_claim(self):
        for languages in [[], None]:
            with self.subTest(languages=languages):
                text = explain({**self.rows[0], "languages": languages}, request("корпоратив", 200))
                self.assertNotIn("языки работы:", text)

    def test_zero_vector(self):
        ranker = Ranker([dict(id="z", description="zero")], self.model)
        result = ranker.rank_and_explain([dict(id="z", description="zero")], self.req)
        self.assertEqual(result[0]["score"], 0.)

    def test_empty_and_duplicates(self):
        self.assertEqual(self.ranker.rank_and_explain([], self.req), [])
        with self.assertRaises(ValueError):
            Ranker(self.rows + self.rows, self.model)
        with self.assertRaises(ValueError):
            self.ranker.rank_and_explain(self.rows + self.rows, self.req)


if __name__ == "__main__":
    unittest.main()
