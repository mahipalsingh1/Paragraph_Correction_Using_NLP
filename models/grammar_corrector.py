# models/grammar_corrector.py
from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import re

PUBLIC_MODELS: List[str] = [
    "vennify/t5-base-grammar-correction",
    "prithivida/grammar_error_correcter_v1",
    "oliverguhr/grammar-correction",
]

def _simple_tokens(t: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z\-']*|\d+|[^\w\s]", t)

def _smart_join(tokens: List[str]) -> str:
    out = ""
    for tok in tokens:
        if re.match(r"[A-Za-z0-9]", tok):
            if out and out[-1].isalnum():
                out += " " + tok
            else:
                out += tok if not out else " " + tok
        else:
            out += tok
    return re.sub(r"\s+([,.;:!?])", r"\1", out).strip()

class GrammarCorrector:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._load_first_available()

    def _load_first_available(self):
        candidates = [self.model_name] if self.model_name else PUBLIC_MODELS
        last_err = None
        for name in candidates:
            if not name:
                continue
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(name)
                self.model_name = name
                return
            except Exception as e:
                last_err = e
        raise RuntimeError(
            "No valid grammar model could be loaded. "
            "Tried: " + ", ".join([c for c in candidates if c]) + f". Last error: {last_err}"
        )

    def _build_prompt(self, text: str) -> str:
        return "grammar: correct grammar and spelling, keep names and places unchanged: " + text

    # -------- Generation --------
    def _generate(
        self,
        prompt: str,
        num_beams: int = 8,
        max_new_tokens: int = 128,
        topk: int = 1,
        do_sample: bool = True,
        temperature: float = 0.9,
        top_p: float = 0.92,
    ) -> List[str]:
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True)
        kwargs = dict(
            max_new_tokens=max_new_tokens,
            num_beams=num_beams,
            num_return_sequences=topk,
            length_penalty=0.7,
            no_repeat_ngram_size=3,
            early_stopping=True,
            do_sample=do_sample,
        )
        if do_sample:
            kwargs.update(dict(temperature=temperature, top_p=top_p))
        outputs = self.model.generate(**inputs, **kwargs)
        return [self.tokenizer.decode(o, skip_special_tokens=True) for o in outputs]

    # -------- Public API --------
    def correct(self, text: str) -> str:
        prompt = self._build_prompt(text)
        return self._generate(prompt, num_beams=6, max_new_tokens=128, topk=1, do_sample=False)[0]

    def correct_with_params(self, text: str, num_beams: int = 6, max_new_tokens: int = 128) -> str:
        prompt = self._build_prompt(text)
        return self._generate(prompt, num_beams=num_beams, max_new_tokens=max_new_tokens, topk=1, do_sample=False)[0]

    def correct_topk(
        self,
        text: str,
        k: int = 3,
        num_beams: int = 8,
        max_new_tokens: int = 128
    ) -> List[str]:
        prompt = self._build_prompt(text)
        raw = self._generate(
            prompt,
            num_beams=num_beams,
            max_new_tokens=max_new_tokens,
            topk=k,
            do_sample=True,
            temperature=0.95,      # slightly higher for more variety
            top_p=0.9,
        )
        seen, outs = set(), []
        for cand in raw:
            if cand not in seen:
                outs.append(cand)
                seen.add(cand)
        return outs[:k]

    # -------- Proper-noun guardrail --------
    def enforce_locked_proper_nouns(
        self,
        original_after_spell: str,
        corrected: str,
        locked_positions: Dict[int, str]
    ) -> str:
        if not locked_positions:
            return corrected

        src_tok = _simple_tokens(original_after_spell)
        tgt_tok = _simple_tokens(corrected)

        i = j = 0
        out: List[str] = []

        while i < len(src_tok) and j < len(tgt_tok):
            s_is_word = bool(re.match(r"[A-Za-z]", src_tok[i]))
            t_is_word = bool(re.match(r"[A-Za-z]", tgt_tok[j]))

            if s_is_word and (i in locked_positions) and t_is_word:
                canon = locked_positions[i]
                out.append(canon)
                i += 1
                j += 1
                continue

            out.append(tgt_tok[j])
            i += 1
            j += 1

        out.extend(tgt_tok[j:])
        text = _smart_join(out)

        # Final adjacent duplicate word removal
        tokens = _simple_tokens(text)
        dedup: List[str] = []
        for tok in tokens:
            if dedup and re.match(r"[A-Za-z]", tok) and re.match(r"[A-Za-z]", dedup[-1]) and tok.lower() == dedup[-1].lower():
                continue
            dedup.append(tok)
        return _smart_join(dedup)
