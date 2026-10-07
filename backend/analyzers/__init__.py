"""SENTINEL analysis engine.

Pure-static, deterministic analysis: Python `ast` + `tokenize` + a custom rule
engine. No AI, no network, no subprocesses — the code under analysis is parsed,
never executed. See `intelligence.py` for the deliberately-unused future hook.
"""
