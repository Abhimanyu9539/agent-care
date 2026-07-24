"""Hide personal details before any text is sent to the LLM, which runs outside the hospital."""

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# 7 or more digits, maybe with spaces or dashes between them: phone numbers and ID numbers.
NUMBER = re.compile(r"\+?\d(?:[ -]?\d){6,}")


def mask(text: str, patient_name: str) -> str:
    """The text with emails, long numbers and the patient's own name replaced by placeholders."""
    text = EMAIL.sub("[EMAIL]", text)
    text = NUMBER.sub("[NUMBER]", text)
    for part in patient_name.split():
        if len(part) > 1:
            text = re.sub(rf"\b{re.escape(part)}\b", "[NAME]", text, flags=re.IGNORECASE)
    return text
