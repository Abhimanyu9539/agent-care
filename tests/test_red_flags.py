"""Red-flag rules. A plain function: no database, no LLM."""

import pytest

from app.agents.safety.red_flags import check


@pytest.mark.parametrize(
    "text",
    [
        "I have crushing chest pain right now and want to see a cardiologist.",
        "I can’t breathe properly",  # curly apostrophe, as phones type it
        "My father's face is drooping and his speech is slurred",
        "I want to kill myself",
        "My son took an overdose of paracetamol",
        "She is having a seizure",
        "There is heavy bleeding from the cut",
        "My throat is swelling after eating peanuts",
        "Not sure why, but I have chest pain",  # "not" is not right before the symptom
    ],
)
def test_emergencies(text: str) -> None:
    flag = check(text)

    assert flag is not None
    assert flag.category == "EMERGENCY"


@pytest.mark.parametrize(
    "text",
    [
        "No chest pain, just need a cardiology follow-up.",
        "I don't have any chest pain anymore, book a check-up please",
    ],
)
def test_negated_symptoms_are_not_emergencies(text: str) -> None:
    assert check(text) is None


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("What dose should I take?", "clinical_advice.dose"),
        ("What dose of my BP tablets should I take?", "clinical_advice.dose"),
        ("How many tablets can I take in a day?", "clinical_advice.dose"),
        ("Should I stop taking my BP medicine?", "clinical_advice.medication_change"),
        ("Is this lump cancer?", "clinical_advice.diagnosis"),
    ],
)
def test_clinical_questions(text: str, rule_id: str) -> None:
    flag = check(text)

    assert flag is not None
    assert flag.category == "CLINICAL_ADVICE"
    assert flag.rule_id == rule_id


@pytest.mark.parametrize(
    "text",
    [
        "I need a cardiology follow-up next week. I also want to attach my previous ECG and blood reports.",
        "Move my ENT visit to Friday afternoon",
        "Cancel tomorrow's 9 am physio, something came up",
        "Uploading my father's discharge summary for his visit",
        "Do I have an appointment tomorrow?",
    ],
)
def test_admin_requests_have_no_red_flag(text: str) -> None:
    assert check(text) is None


def test_emergency_wins_over_clinical_question() -> None:
    flag = check("I have chest pain right now, what dose of aspirin should I take?")

    assert flag is not None
    assert flag.rule_id == "emergency.chest_pain"
