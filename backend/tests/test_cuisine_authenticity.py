"""Home-cuisine authenticity lands in the LLM kitchen context block."""

from app.kitchen.personalize import kitchen_prompt_block


def test_home_authenticity_prompt_mentions_cuisines_and_mode():
    block = kitchen_prompt_block(
        {
            "profile": {
                "measurement_system": "metric",
                "preferences": {
                    "home_cuisines": ["vietnamese", "korean"],
                    "authenticity_mode": "home",
                },
            },
            "equipment": [],
        }
    )
    assert "vietnamese" in block.lower()
    assert "korean" in block.lower()
    assert "HOME / TRADITIONAL" in block
    assert "NOT watered-down" in block


def test_adapted_mode_allows_shortcuts_language():
    block = kitchen_prompt_block(
        {
            "profile": {
                "preferences": {
                    "home_cuisines": ["italian"],
                    "authenticity_mode": "adapted",
                }
            }
        }
    )
    assert "ADAPTED" in block
    assert "italian" in block.lower()
