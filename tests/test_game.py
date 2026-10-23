import random
import unittest

from game import Game, evaluate

QUESTIONS = [
    {"text": "teen?", "field": "age", "op": "age_group", "value": "teen"},
    {"text": "adult?", "field": "age", "op": "age_group", "value": "adult"},
    {"text": "alive?", "field": "status_at_end", "op": "eq", "value": "alive", "unknown_when": {"status_at_end": "unknown"}},
]
CHARACTERS = [
    {"name": "teen alive", "age": 16, "status_at_end": "alive"},
    {"name": "teen unknown", "age": "teen", "status_at_end": "unknown"},
    {"name": "adult dead", "age": "40s", "status_at_end": "dead"},
]


def new_game():
    matrix = [[evaluate(q, c) for c in CHARACTERS] for q in QUESTIONS]
    return Game(CHARACTERS, QUESTIONS, matrix)


class GameTest(unittest.TestCase):
    def test_answered_question_makes_its_opposite_irrelevant(self):
        game = new_game()
        game.answer(0, yes=True)
        self.assertEqual(game.remaining, {0, 1})
        self.assertNotIn(1, game.relevant_questions())

    def test_unknown_answer_keeps_character_on_both_branches(self):
        for yes in (True, False):
            game = new_game()
            game.answer(2, yes=yes)
            self.assertIn(1, game.remaining)

    def test_undo_restores_remaining(self):
        game = new_game()
        game.answer(1, yes=True)
        game.undo()
        self.assertEqual(game.remaining, {0, 1, 2})
        self.assertEqual(game.history, [])

    def test_offer_is_at_most_three_relevant(self):
        game = new_game()
        offered = game.offer(random.Random(0))
        self.assertLessEqual(len(offered), 3)
        self.assertTrue(all(game.is_relevant(qi) for qi in offered))

    def test_eq_does_not_confuse_false_with_zero(self):
        self.assertFalse(evaluate({"field": "x", "op": "eq", "value": False}, {"x": 0}))


if __name__ == "__main__":
    unittest.main()
