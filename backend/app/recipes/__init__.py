"""Recipe generation (cook mode) and standardization (adapt mode).

Three trust layers, explicitly separated:
  - skeleton (steps, amounts):  LLM culinary competence, labeled uncited
  - why/science annotations:    grounded in retrieved evidence, cited
  - internal temperatures:      safety table enforced deterministically
                                AFTER generation -- Python gets the last word
"""
