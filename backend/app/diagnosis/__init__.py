"""Structured dish diagnosis: symptom taxonomy -> weighted causes ->
follow-up questions -> evidence-adjusted ranking.

Trust split, same as the rest of the app:
  - scoring.py   pure math (priors x evidence factors), unit-tested
  - engine.py    LLM translates free text into structured verdicts only;
                 it never computes or overrides the ranking
"""
