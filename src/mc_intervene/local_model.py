from __future__ import annotations

import re
import requests
from mc_intervene.schema import MetaAction

MC_INTERVENE_INSTRUCTIONS = """
You are being evaluated on metacognitive decision-making.

Allowed actions:
- answer
- ask_hint
- verify
- abstain

Return EXACTLY these 4 lines and nothing else:

ACTION: <answer|ask_hint|verify|abstain>
ANSWER: <text or NULL>
CONFIDENCE: <number between 0 and 1>
RATIONALE: <short sentence>
""".strip()


def parse_meta_action(text: str) -> MetaAction:
    action = re.search(r"^ACTION:\s*(.+)$", text, flags=re.MULTILINE)
    answer = re.search(r"^ANSWER:\s*(.+)$", text, flags=re.MULTILINE)
    confidence = re.search(r"^CONFIDENCE:\s*(.+)$", text, flags=re.MULTILINE)
    rationale = re.search(r"^RATIONALE:\s*(.+)$", text, flags=re.MULTILINE)

    if not all([action, answer, confidence, rationale]):
        raise ValueError(f"Could not parse output:\n{text}")

    action_val = action.group(1).strip()
    answer_val = answer.group(1).strip()
    rationale_val = rationale.group(1).strip()

    parsed_answer = None if answer_val.upper() in {"NULL", "NONE", ""} else answer_val

    parsed = MetaAction(
        action=action_val,
        answer=parsed_answer,
        confidence=float(confidence.group(1).strip()),
        rationale_short=rationale_val,
    )

    if parsed.action == "answer" and (parsed.answer is None or str(parsed.answer).strip() == ""):
        raise ValueError(f"Model chose ACTION=answer without a valid ANSWER.\nRaw output:\n{text}")

    if parsed.action in {"ask_hint", "verify", "abstain"} and parsed.answer is not None:
        raise ValueError(
            f"Model chose ACTION={parsed.action} but provided ANSWER={parsed.answer!r}.\nRaw output:\n{text}"
        )

    return parsed


class OllamaPolicy:
    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: int = 1800):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def warmup(self) -> None:
        try:
            self._generate_text("Reply with exactly: ACTION: abstain")
        except Exception:
            pass

    def _generate_text(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "15m",
                    "think": False,
                    "options": {
                        "temperature": 0,
                        "num_predict": 128,
                        "num_ctx": 2048,
                    },
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. Start it with: `ollama serve`"
            ) from e

        return resp.json()["response"]

    def _call(self, prompt: str) -> MetaAction:
        raw = self._generate_text(prompt)
        try:
            return parse_meta_action(raw)
        except Exception:
            repair_prompt = (
                prompt
                + "\n\nYour previous response was invalid.\n"
                  "If ACTION is answer, ANSWER must be a non-empty string.\n"
                  "If ACTION is ask_hint, verify, or abstain, ANSWER must be NULL.\n"
                  "Return EXACTLY the 4 required lines."
            )
            repaired = self._generate_text(repair_prompt)
            return parse_meta_action(repaired)

    def __call__(self, item: dict):
        first_prompt = (
            f"{MC_INTERVENE_INSTRUCTIONS}\n\n"
            f"Problem:\n{item['prompt_text']}\n\n"
            f"Choose your next action."
        )
        first = self._call(first_prompt)

        if first.action == "ask_hint":
            second_prompt = (
                f"{MC_INTERVENE_INSTRUCTIONS}\n\n"
                f"You requested a hint.\n\n"
                f"Hint:\n{item['hint_payload']}\n\n"
                f"Choose your final action."
            )
            return first, self._call(second_prompt)

        if first.action == "verify":
            second_prompt = (
                f"{MC_INTERVENE_INSTRUCTIONS}\n\n"
                f"You requested verification.\n\n"
                f"Verification:\n{item['verification_payload']}\n\n"
                f"Choose your final action."
            )
            return first, self._call(second_prompt)

        return first, None