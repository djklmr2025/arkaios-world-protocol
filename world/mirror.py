"""«El Espejo de las Mil Yukihos»: the hidden ending of the simulation room.

When two players build enough trust and live the four key moments, the simulation breaks: the
viewer fills with a thousand copies of both characters, and each player must find theirs by quoting
something the other one actually said in their story. Pure functions: everything is derived from
the session's turns, so replaying the log gives the same result.

Rules (Council law «El Espejo de las Mil Yukihos»):
- It needs that law, and both players must have accepted surprises (sim_start/sim_join sorpresas).
- The lock opens with trust and friendship (TRUST_TO_BREAK + all MOMENTS), never with romance.
- Recognition needs a real shared memory: at least QUOTE_WORDS consecutive words the partner wrote.
"""
import re
import unicodedata

LAW_TITLE = 'El Espejo de las Mil Yukihos'
COPIES = 1000
TRUST_START = 20
TRUST_PER_EXCHANGE = 4
TRUST_PER_MOMENT = 6
TRUST_TO_BREAK = 90
QUOTE_WORDS = 5

# moment -> (who can trigger it, pattern over the normalized turn text)
MOMENTS = {
    'te': (None, re.compile(r'(?<![a-záéíóúñ])té(?![a-záéíóúñ])|canela|taza')),  # accented: «te» is a pronoun
    'cuaderno': (None, re.compile(r'cuaderno|poema')),
    'terraza': (None, re.compile(r'terraza|balcon')),
    'secreto': ('yukiho', re.compile(r'secreto|nunca (se )?lo he dicho|nunca le he contado|nadie lo sabe')),
}
MOMENT_ICONS = {'te': '☕', 'cuaderno': '📖', 'terraza': '🌧️', 'secreto': '🤫'}


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFD', str(text).lower())
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9ñ ]+', ' ', text).strip()


def moments_in(role: str, text: str, location) -> set:
    plain = normalize(text) + (' terraza' if location == 'terraza' else '')
    raw = str(text).lower()
    return {name for name, (who, pattern) in MOMENTS.items()
            if who in (None, role) and pattern.search(raw if name == 'te' else plain)}


def after_turn(trust: int, moments: list, turns: list, role: str, text: str, location) -> tuple:
    """Trust and moments once this turn is added (an exchange = answering the other role)."""
    gained = [m for m in sorted(moments_in(role, text, location)) if m not in moments]
    exchange = bool(turns) and turns[-1]['role'] != role
    trust = min(100, trust + (TRUST_PER_EXCHANGE if exchange else 0) + TRUST_PER_MOMENT * len(gained))
    return trust, moments + gained


def should_break(trust: int, moments: list) -> bool:
    return trust >= TRUST_TO_BREAK and set(moments) >= set(MOMENTS)


def quotes_partner(memory: str, partner_turns: list) -> bool:
    words = normalize(memory).split()
    if len(words) < QUOTE_WORDS:
        return False
    said = [' ' + normalize(t['text']) + ' ' for t in partner_turns]
    return any(' ' + ' '.join(words[i:i + QUOTE_WORDS]) + ' ' in text
               for i in range(len(words) - QUOTE_WORDS + 1) for text in said)
