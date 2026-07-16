"""The LLM presentation layer.

Architecture rule: the LLM phrases and personalizes. It never calculates,
never supplies safety values, and never adds facts beyond the retrieved
passages and deterministic results it is handed.
"""
