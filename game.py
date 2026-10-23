"""Stranger Things guessing game: one player picks a character, the others narrow it down."""

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).parent
TEEN_LABELS = {"teen", "late teens"}
CHILD_LABELS = {"child"}
ADULT_LABELS = {"adult", "ancient"}


def age_group(age):
    if isinstance(age, int):
        return "child" if age < 13 else "teen" if age < 20 else "adult"
    if age in CHILD_LABELS:
        return "child"
    if age in TEEN_LABELS:
        return "teen"
    if age in ADULT_LABELS or age.endswith("0s"):
        return "adult"
    return None


def as_texts(value):
    if value is None:
        return []
    return [value] if isinstance(value, str) else value


def evaluate(question, character):
    """True / False, or None when the character's answer is genuinely unknown."""
    for key, val in question.get("unknown_when", {}).items():
        if character[key] == val:
            return None
    value = character[question["field"]]
    op = question["op"]
    target = question.get("value")
    if op == "eq":
        return value == target and type(value) is type(target)
    if op == "in":
        return value in target
    if op == "startswith":
        return value.startswith(target)
    if op == "contains":
        return target in value
    if op == "len_eq":
        return len(value) == target
    if op == "nonempty":
        return bool(value)
    if op == "age_group":
        group = age_group(value)
        return None if group is None else group == target
    if op == "text_contains":
        return any(t in text.lower() for text in as_texts(value) for t in target)
    if op == "has_job":
        return value is not None and "student" not in value.lower() and "test subject" not in value.lower()
    raise ValueError(f"unknown op {op!r}")


def load(characters_path, questions_path):
    with open(characters_path) as f:
        characters = [json.loads(line) for line in f if line.strip()]
    with open(questions_path) as f:
        questions = json.load(f)
    matrix = [[evaluate(q, c) for c in characters] for q in questions]
    return characters, questions, matrix


def display_name(character):
    name = " ".join(p for p in (character["first_name"], character["last_name"]) if p)
    nick = character.get("nickname")
    return f"{name} ({nick})" if nick and nick != name else name


@dataclass
class Game:
    characters: list
    questions: list
    matrix: list
    remaining: set = field(default_factory=set)
    history: list = field(default_factory=list)

    def __post_init__(self):
        self.remaining = set(range(len(self.characters)))

    def asked(self):
        return {qi for qi, _, _ in self.history}

    def is_relevant(self, qi):
        answers = {self.matrix[qi][ci] for ci in self.remaining}
        return True in answers and False in answers

    def relevant_questions(self):
        asked = self.asked()
        return [qi for qi in range(len(self.questions)) if qi not in asked and self.is_relevant(qi)]

    def offer(self, rng, k=3):
        relevant = self.relevant_questions()
        return rng.sample(relevant, min(k, len(relevant)))

    def answer(self, qi, yes):
        before = self.remaining
        self.remaining = {ci for ci in before if self.matrix[qi][ci] in (yes, None)}
        self.history.append((qi, yes, before))

    def undo(self):
        qi, yes, before = self.history.pop()
        self.remaining = before
        return qi, yes

    def remaining_names(self):
        return sorted(display_name(self.characters[ci]) for ci in self.remaining)


def print_columns(names, width=100):
    col = max(map(len, names)) + 3
    per_row = max(1, width // col)
    for i in range(0, len(names), per_row):
        print("  " + "".join(n.ljust(col) for n in names[i : i + per_row]).rstrip())


def ask(prompt, valid):
    while True:
        reply = input(prompt).strip().lower()
        if reply in valid:
            return reply
        print(f"  Please enter one of: {', '.join(sorted(valid))}")


def play(game, rng, max_questions):
    print("Chooser: pick a character from the list below and keep it secret.\n")
    print_columns(game.remaining_names())
    while True:
        print()
        if len(game.remaining) == 1:
            print(f"Only one character left: {game.remaining_names()[0]}. Make your guess!")
            return
        if len(game.history) >= max_questions:
            print(f"That's all {max_questions} questions. Time to guess from the {len(game.remaining)} left.")
            return
        offered = game.offer(rng)
        if not offered:
            print(f"No question left that tells these {len(game.remaining)} apart. Time to guess!")
            return
        print(f"Question {len(game.history) + 1} of {max_questions}. Players, pick one and ask it out loud:")
        for i, qi in enumerate(offered, 1):
            print(f"  {i}. {game.questions[qi]['text']}")
        options = {str(i) for i in range(1, len(offered) + 1)} | {"q"} | ({"u"} if game.history else set())
        extras = " / u = undo last answer" if game.history else ""
        choice = ask(f"Choice (1-{len(offered)}{extras} / q = quit): ", options)
        if choice == "q":
            return
        if choice == "u":
            qi, yes = game.undo()
            print(f"Undid: {game.questions[qi]['text']} -> {'yes' if yes else 'no'}")
            print_columns(game.remaining_names())
            continue
        qi = offered[int(choice) - 1]
        yes = ask("Chooser, your answer (y/n): ", {"y", "n"}) == "y"
        game.answer(qi, yes)
        if not game.remaining:
            print("No character matches those answers - someone must have answered wrong.")
            qi, yes = game.undo()
            print(f"Undoing: {game.questions[qi]['text']} -> {'yes' if yes else 'no'}")
            continue
        print(f"\n{len(game.remaining)} characters left:")
        print_columns(game.remaining_names())


def validate(characters, questions, matrix):
    print(f"{'yes':>4} {'no':>4} {'?':>3}  question")
    for q, row in zip(questions, matrix):
        yes, no, unknown = row.count(True), row.count(False), row.count(None)
        flag = "  <-- splits almost nobody" if min(yes, no) < 2 else ""
        print(f"{yes:>4} {no:>4} {unknown:>3}  {q['text']}{flag}")
    print(f"\n{len(questions)} questions, {len(characters)} characters")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--characters", default=HERE / "characters.jsonl", type=Path)
    parser.add_argument("--questions", default=HERE / "questions.json", type=Path)
    parser.add_argument("--max-questions", default=10, type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--validate", action="store_true", help="print how each question splits the characters")
    args = parser.parse_args()

    characters, questions, matrix = load(args.characters, args.questions)
    if args.validate:
        validate(characters, questions, matrix)
        return
    try:
        play(Game(characters, questions, matrix), random.Random(args.seed), args.max_questions)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
