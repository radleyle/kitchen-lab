"""Function-aware ingredient substitution.

The answer to "what can replace X in this dish" is a database join:
    substitutions WHERE original = X AND function = <the job X does here>

The LLM's only role is picking that function from a closed list, based on
the dish context. When it can't tell, we return options grouped by
function and ask -- we never guess which job the ingredient was doing.
"""
