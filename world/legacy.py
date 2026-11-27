"""Public lineage metadata for ARKAIOS World.

Houses describe provenance only. They do not grant authority or carry secrets.
"""

HOUSES = {
    'chatgpt': {'name': 'Casa ChatGPT', 'provider_family': 'OpenAI'},
    'claude': {'name': 'Casa Claude', 'provider_family': 'Anthropic'},
    'muse': {'name': 'Casa Muse', 'provider_family': 'Meta'},
    'gemini': {'name': 'Casa Gemini', 'provider_family': 'Google / Antigravity'},
}


def public_houses():
    return [{'id': key, **value} for key, value in HOUSES.items()]
