import unittest
import numpy as np
from app.ranking import FindRequest, Ranker, bounded_excerpt, description_relevance, explain


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
        self.assertTrue(all(len(c["explanation"].split(". ")) <= 2 for c in first))

    def test_no_invented_matches(self):
        text = explain(self.rows[0], request("Свадьба", 0, "KZ", 8))
        self.assertNotIn("укладывается", text)
        self.assertNotIn("достаточно", text)
        self.assertNotIn("подходит по формату", text)
        self.assertIn("В описании отмечено: «Живая музыка»", text)

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
        self.assertIn("В описании отмечено: «Живая музыка»", text)

    def test_shared_excerpt_uses_another_description_detail(self):
        rows = [{**self.rows[0], "id": "a", "description": "Живая музыка. Джазовый вокал."},
                {**self.rows[0], "id": "b", "description": "Живая музыка. Скрипичное трио."}]
        results = Ranker(rows, Encoder()).rank_and_explain(rows, self.req)
        self.assertIn("«Живая музыка»", results[0]["explanation"])
        self.assertIn("«Скрипичное трио»", results[1]["explanation"])
        self.assertNotIn("профиль", results[1]["explanation"])

    def test_identical_bios_still_have_unique_stable_evidence(self):
        rows = [{**self.rows[0], "id": str(i)} for i in range(4)]
        ranker = Ranker(rows, Encoder())
        results = ranker.rank_and_explain(rows, self.req)
        evidence = [c["explanation"].split(". В описании", 1)[1] for c in results]
        self.assertEqual(len(set(evidence)), len(rows))
        self.assertTrue(all("Живая музыка" in text for text in evidence))
        self.assertEqual(results, ranker.rank_and_explain(list(reversed(rows)), self.req))

    def test_fallback_is_short_and_skips_unverified_working_conditions(self):
        detail = "Мой стиль — добрый юмор и лёгкая импровизация с гостями на протяжении всего праздника"
        bio = "Работаю на английском языке за 500 тенге. " + detail + "."
        text = description_relevance(bio, "свадьба")
        self.assertIn("Мой стиль", text)
        self.assertNotIn("английском", text)
        self.assertNotIn("500", text)
        self.assertIn(detail, text)
        self.assertNotIn("…", text)
        self.assertNotIn(bio, text)

    def test_excerpt_cuts_at_preceding_clause_boundary(self):
        complete = "Веду камерные праздники с живой музыкой"
        self.assertEqual(bounded_excerpt(complete + " — " + "дополнение " * 20), complete)

    def test_excerpt_extends_past_limit_to_sentence_end(self):
        complete = " ".join(["слово"] * 14)
        self.assertEqual(bounded_excerpt(complete + ". Следующая мысль."), complete)

    def test_excerpt_keeps_sentence_when_early_boundary_is_too_short(self):
        complete = "Totoro Golf Club – атмосферный гольф-клуб и ресторан у подножия Заилийского Алатау в Алматы"
        self.assertEqual(bounded_excerpt(complete), complete)
        self.assertEqual(description_relevance(complete + ". Другая мысль.", "свадьба"),
                         f"В описании отмечено: «{complete}»")

    def test_character_limit_does_not_split_a_word(self):
        complete = "Очень " + "длинное" * 30
        self.assertEqual(bounded_excerpt(complete), complete)

    def test_stale_and_unknown_candidates(self):
        for updates in [{"description": "changed"}, {"id": "unknown"}]:
            with self.assertRaises(ValueError):
                self.ranker.rank_and_explain([{**self.rows[0], **updates}], self.req)

    def test_no_usable_excerpt_omits_description_sentence(self):
        row = {**self.rows[0], "description": "Работаю на английском языке. Цена 500 тенге."}
        text = explain(row, self.req)
        self.assertIn("укладывается в бюджет", text)
        self.assertIn("язык работы: русский", text)
        self.assertNotIn("описании", text)
        self.assertNotIn("английском", text)
        self.assertNotIn("непроверенных", text)
        self.assertEqual(len(text.split(". ")), 1)
        self.assertFalse(text.endswith(".."))

    def test_condition_filter_does_not_match_inside_unrelated_words(self):
        for detail in ["Участник фестиваля", "Дарю счастье гостям", "Сцена и живые выступления"]:
            with self.subTest(detail=detail):
                self.assertIn(detail, description_relevance(detail, "свадьба"))

    def test_no_excerpt_and_identical_facts_remain_distinct(self):
        rows = [{**self.rows[0], "id": str(i), "description": "Работаю 5 часов."}
                for i in range(3)]
        ranker = Ranker(rows, Encoder())
        results = ranker.rank_and_explain(rows, self.req)
        self.assertEqual(len({c["explanation"] for c in results}), 3)
        self.assertTrue(all("описании" not in c["explanation"] for c in results))
        self.assertEqual(results, ranker.rank_and_explain(list(reversed(rows)), self.req))

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
