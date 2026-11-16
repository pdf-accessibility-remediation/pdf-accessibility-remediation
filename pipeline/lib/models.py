"""models.py: what the pipeline knows about models, shared by every step that sends a request (decide.py, the language
step's requests in lib/langreq.py).

    models.temperature_omitted(model_id) -> the OMIT_TEMPERATURE entry it matches, or None
"""
# The temperature sent with every request. Changing it changes every run that sends one; there is no command-line override.
TEMPERATURE = 0
# Models whose maker says to leave temperature at its default, or that reject any other value: no temperature is sent.
# An id matches if it starts with an entry. A model OpenRouter lists as not accepting temperature is also left out.
OMIT_TEMPERATURE = [
    'anthropic/claude-opus-4.7', 'anthropic/claude-opus-4.8', 'anthropic/claude-opus-4.9',   # Opus 4.7 and later
    'anthropic/claude-opus-5',                                                               # (add each new Opus major here)
    'openai/o1', 'openai/o3', 'openai/o4',                                                   # OpenAI reasoning models
    'openai/gpt-5',                                                                          # GPT-5 family (reasoning)
    'google/gemini-3',                                                                       # every Gemini 3 model
]

def temperature_omitted(model):
    return next((p for p in OMIT_TEMPERATURE if str(model).startswith(p)), None)
