"""Check the LLM connection: ask the model one question and print its reply.

Run from the project root: python -m scripts.ask_llm
"""

from app.config import get_settings
from app.llm.client import make_model

model = make_model(get_settings())
reply = model.invoke("In one sentence: what does a hospital receptionist do?")
print(reply.content)
