import unittest
import numpy as np
from app.ranking import FindRequest, Ranker, explain


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
        self.assertNotEqual(first[0]["explanation"], first[1]["explanation"])

    def test_no_invented_matches(self):
        text = explain(self.rows[0], request("Свадьба", 0, "KZ", 8))
        self.assertNotIn("укладывается", text)
        self.assertNotIn("достаточно", text)
        self.assertNotIn("подходит по формату", text)
        self.assertIn("Живая музыка", text)

    def test_stale_and_unknown_candidates(self):
        for updates in [{"description": "changed"}, {"id": "unknown"}]:
            with self.assertRaises(ValueError):
                self.ranker.rank_and_explain([{**self.rows[0], **updates}], self.req)

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

