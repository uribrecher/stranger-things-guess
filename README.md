# Stranger Things guessing game

One player (the chooser) secretly picks a Stranger Things character. The others narrow it down with yes/no questions.

Each turn the game offers 3 random questions that are still relevant (they split the remaining characters). The players pick one and ask it out loud, the chooser answers, and the game shows who is left.

```
uv run game.py              # or: python3 game.py
uv run game.py --validate   # how each question splits the characters
python3 -m unittest tests.test_game
```

Options: `--max-questions N` (default 10), `--seed N`. During play, `u` undoes the last answer.

## Files

- `characters.jsonl`: 77 characters, one JSON object per line.
- `questions.json`: the question list; each question is a rule over a character field.
- `game.py`: the game (standard library only).
