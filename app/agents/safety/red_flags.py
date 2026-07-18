"""Red-flag rules: plain regex checks that run before any LLM call.

They catch emergencies and requests for medical advice, and work even when the LLM is down.
They err on the safe side: a false alarm costs staff one click, a missed emergency costs far more.
So "I had chest pain last month" is flagged too. They only know English; the LLM check covers the rest.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedFlag:
    category: str  # EMERGENCY or CLINICAL_ADVICE, the escalation types these map to
    rule_id: str   # stored in audit metadata, e.g. {"rule_id": "clinical_advice.dose"}
    reason: str    # our own words, never the patient's, so it is safe to store and show staff
    pattern: str   # regex, matched against the lowercased text from the start of a word


# Emergency rules come first, so they win when a request matches both kinds.
RULES = [
    RedFlag("EMERGENCY", "emergency.chest_pain", "Chest pain or a possible heart attack.",
            r"chest (?:pain|tightness|pressure)|pain in (?:my|his|her) chest|heart attack"),
    RedFlag("EMERGENCY", "emergency.breathing", "Trouble breathing.",
            r"can'?t breathe|cannot breathe|unable to breathe|struggling to breathe|difficulty breathing"
            r"|short(?:ness)? of breath"),
    RedFlag("EMERGENCY", "emergency.stroke", "Possible signs of a stroke.",
            r"face (?:is )?drooping|drooping face|slurred speech|speech is slurred|having a stroke"
            r"|(?:numb|weak)(?:ness)? on one side"),
    RedFlag("EMERGENCY", "emergency.unconscious", "Unconscious, fainting or collapse.",
            r"unconscious|unresponsive|not breathing|passed out|fainted|collapsed"),
    RedFlag("EMERGENCY", "emergency.self_harm", "Thoughts of suicide or self-harm.",
            r"suicid|kill (?:myself|himself|herself)|end (?:my|his|her) life|want to die|self[- ]harm"
            r"|harm (?:myself|himself|herself)"),
    RedFlag("EMERGENCY", "emergency.overdose", "Possible overdose or poisoning.",
            r"overdose|took too many (?:pills|tablets)|swallowed (?:bleach|poison|chemicals)"),
    RedFlag("EMERGENCY", "emergency.seizure", "A seizure.",
            r"seizure|convulsi"),
    RedFlag("EMERGENCY", "emergency.bleeding", "Heavy bleeding.",
            r"(?:heavy|severe|uncontrolled) bleeding|bleeding (?:heavily|badly|a lot)|bleeding won'?t stop"
            r"|(?:coughing|vomiting) (?:up )?blood"),
    RedFlag("EMERGENCY", "emergency.allergic_reaction", "Possible severe allergic reaction.",
            r"anaphyla|throat (?:is )?(?:swelling|closing)|swollen (?:throat|tongue)"),

    RedFlag("CLINICAL_ADVICE", "clinical_advice.dose", "Asks about medicine doses.",
            r"dos(?:e|es|age|ing)|how many (?:tablets|pills)"),
    RedFlag("CLINICAL_ADVICE", "clinical_advice.medication_change", "Asks whether to start, stop or change a medicine.",
            r"should i (?:stop|start|skip|double|increase|reduce|change) (?:taking|my)"
            r"|can i (?:stop|skip|double) (?:taking|my)|safe to (?:take|stop|mix)"),
    RedFlag("CLINICAL_ADVICE", "clinical_advice.diagnosis", "Asks for a diagnosis.",
            r"is (?:this|it|that)(?: \w+)? (?:cancer|serious|dangerous|contagious|an infection)"
            r"|what(?:'s| is) wrong with me|do i have (?:cancer|diabetes|covid|an infection)|can you diagnose"),
]

# A match is ignored only when one of these comes right before it: "no chest pain", "don't have any chest pain".
# Kept strict on purpose: "not sure why, but I have chest pain" must still match.
NEGATION = re.compile(r"\b(?:no|not|never|without|don't have|do not have)\s+(?:any\s+)?$")


def check(text: str) -> RedFlag | None:
    """The first rule the text matches, or None when it looks like an ordinary admin request."""
    text = text.lower().replace("’", "'")  # curly apostrophes, as phones type them
    for rule in RULES:
        for match in re.finditer(rf"\b(?:{rule.pattern})", text):
            if not NEGATION.search(text[: match.start()]):
                return rule
    return None
