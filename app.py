# app.py
import time
import re
import streamlit as st
from models.spell_checker import SpellCorrector
from models.grammar_corrector import GrammarCorrector
from utils.text_cleaner import clean_text
from utils.academic_rules import prefer_studying

st.set_page_config(page_title="Smart Text Corrector", page_icon="📝", layout="wide")

st.sidebar.header("Settings")
decoding_mode = st.sidebar.selectbox(
    "Quality vs Speed",
    ["Balanced (beam=6)", "Faster (beam=1)", "Higher quality (beam=8)"],
    index=0
)
max_new_tokens = st.sidebar.slider("Max new tokens", min_value=48, max_value=256, value=128, step=16)
suggest_k = st.sidebar.slider("Suggestions (top‑k)", min_value=1, max_value=5, value=3, step=1)
show_debug = st.sidebar.checkbox("Show debug info", value=False)

@st.cache_resource(show_spinner=False)
def load_spell():
    return SpellCorrector()

@st.cache_resource(show_spinner=False)
def load_grammar():
    return GrammarCorrector()

spell_corrector = load_spell()
grammar_corrector = load_grammar()

st.title("📝 NLP-based Spell, Sentence & Paragraph Corrector")
st.markdown(
    "Enter text below to get spelling normalization and grammar/style fixes. "
    "Proper nouns are protected and you can pick from multiple suggestions if enabled."
)

user_text = st.text_area("Enter text:", height=200, placeholder="Type or paste paragraph here…")

def beams_for(mode: str) -> int:
    if mode.startswith("Faster"):
        return 1
    if mode.startswith("Higher"):
        return 8
    return 6

def _dedup_adjacent_words_simple(t: str) -> str:
    tokens = re.findall(r"[A-Za-z][A-Za-z\-']*|\d+|[^\w\s]", t)
    out = []
    for tok in tokens:
        if out and tok.isalpha() and out[-1].isalpha() and tok.lower() == out[-1].lower():
            continue
        out.append(tok)
    s = ""
    for tok in out:
        if re.match(r"[A-Za-z0-9]", tok):
            s += (" " if s and s[-1].isalnum() else "") + tok
        else:
            s += tok
    s = re.sub(r"\s+([,.;:!?])", r"\1", s).strip()
    return s

def _final_touchups(t: str) -> str:
    # Fix missing space after commas if any survived
    t = re.sub(r",([A-Za-z])", r", \1", t)
    return t

def run_pipeline(text: str, beams: int, k: int, max_tokens: int):
    cleaned = clean_text(text)
    spell_corrected, cov = spell_corrector.correct_spelling_with_stats(
        cleaned, use_lexicon=True, lexicon_cutoff=0.94
    )
    spell_corrected = prefer_studying(spell_corrected)

    if k > 1:
        candidates = grammar_corrector.correct_topk(
            spell_corrected, k=k, num_beams=beams, max_new_tokens=max_tokens
        )
        guarded = [
            grammar_corrector.enforce_locked_proper_nouns(
                spell_corrected, c, cov.get("locked_positions", {})
            )
            for c in candidates
        ]
    else:
        best = grammar_corrector.correct_with_params(
            spell_corrected, num_beams=beams, max_new_tokens=max_tokens
        )
        guarded = [
            grammar_corrector.enforce_locked_proper_nouns(
                spell_corrected, best, cov.get("locked_positions", {})
            )
        ]

    guarded = [_dedup_adjacent_words_simple(g) for g in guarded]
    guarded = [_final_touchups(g) for g in guarded]
    return cleaned, spell_corrected, cov, guarded

# Single button to compute results and store in session
if st.button("Correct Text"):
    if not user_text.strip():
        st.warning("⚠️ Please enter some text to correct.")
    else:
        with st.spinner("Correcting… ⏳"):
            t0 = time.time()
            beams = beams_for(decoding_mode)
            cleaned, spell_corrected, cov, guarded = run_pipeline(
                user_text, beams, suggest_k, max_new_tokens
            )
            latency = time.time() - t0

        # Store in session so the radio can update output live
        st.session_state.pipeline = {
            "cleaned": cleaned,
            "spell_corrected": spell_corrected,
            "cov": cov,
            "guarded": guarded,
            "latency": latency,
            "beams": beams,
        }
        # Reset selection to first option for each new run
        st.session_state.choice = 0

# Render results from session (enables live radio switching)
if "pipeline" in st.session_state:
    cleaned = st.session_state.pipeline["cleaned"]
    spell_corrected = st.session_state.pipeline["spell_corrected"]
    cov = st.session_state.pipeline["cov"]
    guarded = st.session_state.pipeline["guarded"]
    latency = st.session_state.pipeline["latency"]
    beams = st.session_state.pipeline["beams"]

    st.subheader("Corrected Output:")
    if "choice" not in st.session_state:
        st.session_state.choice = 0

    if len(guarded) > 1:
        st.session_state.choice = st.radio(
            "Pick a suggestion:",
            options=list(range(len(guarded))),
            format_func=lambda i: f"Option {i+1}",
            horizontal=True,
            index=min(st.session_state.choice, len(guarded) - 1),
        )
    else:
        st.session_state.choice = 0

    final_text = guarded[st.session_state.choice]
    st.success(final_text)

    st.caption(
        f"Processed in {latency:.2f}s • decoding={decoding_mode} • max_new_tokens={max_new_tokens} "
        f"• suggestions={len(guarded)} • proper‑noun matches={cov.get('lexicon_hits',0)}/{cov.get('alpha_tokens',0)}"
    )

    st.subheader("Comparison:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Original**")
        st.info(user_text)
    with col2:
        st.markdown("**After spell/normalize**")
        st.info(spell_corrected)
    with col3:
        st.markdown("**Final**")
        st.info(final_text)

    if show_debug:
        st.divider()
        st.markdown("Debug")
        st.code(
            f"cleaned={repr(cleaned)}\n"
            f"spell_corrected={repr(spell_corrected)}\n"
            f"locked_positions={cov.get('locked_positions', {})}\n"
            f"decoding_mode={decoding_mode}, beams={beams}, max_new_tokens={max_new_tokens}\n"
            f"candidates={guarded}"
        )
