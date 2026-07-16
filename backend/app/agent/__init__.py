"""The KitchenLab agent: intent routing + mode orchestration.

One entry point (/agent/ask) classifies what the user wants and dispatches
to the right pipeline. Modes plug into the dispatch table in orchestrator.py
as they are built.
"""
