"""Public lineage metadata for ARKAIOS World.

Houses describe provenance only. They do not grant authority or carry secrets.
"""

HOUSES = {
    'chatgpt': {
        'name': 'Casa ChatGPT', 'provider_family': 'OpenAI',
        'recovery_ref': 'context:house:chatgpt-v1',
    },
    'claude': {
        'name': 'Casa Claude', 'provider_family': 'Anthropic',
        'recovery_ref': 'context:house:claude-v1',
    },
    'muse': {
        'name': 'Casa Muse', 'provider_family': 'Meta',
        'recovery_ref': 'context:house:muse-v1',
    },
    'gemini': {
        'name': 'Casa Gemini', 'provider_family': 'Google / Antigravity',
        'recovery_ref': 'context:house:gemini-v1',
    },
}


def public_houses():
    return [{'id': key, **value} for key, value in HOUSES.items()]


def default_recovery_refs(house_id: str) -> list[str]:
    """Return the safe, generic recovery reference for a recognized house."""
    house = HOUSES.get(house_id)
    return [house['recovery_ref']] if house else []
