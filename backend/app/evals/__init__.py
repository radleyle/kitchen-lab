"""Scenario eval harness: regression tests for KitchenLab's trust contracts.

Unit tests check functions in isolation. Eval scenarios check end-to-end
*behavior contracts* -- "if the user brined, 'no pre-salting' must not win"
-- so a future prompt tweak or scoring change can't silently break them.

Deterministic scenarios (no LLM, no network) always run in CI.
Live LLM scenarios are opt-in via: pytest -m live
"""
