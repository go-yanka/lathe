# Model-class detection (owner design: the analyst drafts specs FOR the implementer in use, guided by
# per-class standards; pins anchor on class for revalidated reuse). Pure logic, harness-built.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "model_class"
HEADER = ""
GLUE = ""
FUNCTIONS = [
    {
        "name": "model_class",
        "prompt": (
            "Write a pure Python function model_class(model) that classifies an implementer model string "
            "into one of exactly three classes: 'frontier', 'local-large', 'local-small'. Rules, applied "
            "in this order (case-insensitive matching on the whole string): "
            "(1) if model is None or not a string or empty, return 'local-small' (the safe assumption); "
            "(2) if it contains any of 'claude', 'fable', 'opus', 'sonnet', 'gpt', 'gemini', return "
            "'frontier'; "
            "(3) look for a parameter-size token: a number followed immediately by 'b' as its own token "
            "(digits possibly with a dot, e.g. '9b', '35B', '7.5b') found anywhere in the string using the "
            "regex r'(\\d+(?:\\.\\d+)?)\\s*[bB]\\b'; if found and the number is >= 27, return 'local-large', "
            "else return 'local-small'; "
            "(4) no size token found: return 'local-small'. "
            "Put `import re` as the FIRST line INSIDE the function body. "
            "Worked examples: model_class('openai:fable') -> 'frontier'; model_class('ornith-1.0-9b-Q4_K_M') "
            "-> 'local-small'; model_class('qwen-35B-instruct') -> 'local-large'; model_class('openai:local') "
            "-> 'local-small'. Output ONLY the Python function code - no prose, no markdown."
        ),
        "tests": [
            "assert model_class('openai:fable') == 'frontier'",
            "assert model_class('claude') == 'frontier'",
            "assert model_class('ornith-1.0-9b-Q4_K_M.gguf') == 'local-small'",
            "assert model_class('qwen-35B-instruct') == 'local-large'",
            "assert model_class('openai:local') == 'local-small'",
            "assert model_class(None) == 'local-small'",
            "assert model_class('llama-3-70b') == 'local-large'",
            "assert model_class('GPT-5') == 'frontier'",
            "assert model_class('mistral-7.5b') == 'local-small'",
        ],
    },
]
