"""Masking personal details before text goes to the LLM. No database needed."""

from app.llm.mask import mask


def test_masks_emails_long_numbers_and_the_patients_name() -> None:
    text = "This is asha RAO, asha.rao@mail.co.in, phone +91 98765-43210, ID 1234 5678 9012."

    assert mask(text, "Asha Rao") == "This is [NAME] [NAME], [EMAIL], phone [NUMBER], ID [NUMBER]."


def test_keeps_short_numbers_and_other_words() -> None:
    text = "Ali wants 2 visits on 14/08 at 10:30, with Alison."

    assert mask(text, "Ali Khan") == "[NAME] wants 2 visits on 14/08 at 10:30, with Alison."
