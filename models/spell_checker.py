# models/spell_checker.py
import re
from difflib import get_close_matches
from typing import Dict, Tuple
from spellchecker import SpellChecker

# ---------------- Abbreviation expansion ----------------
ABBREV = {
    # Basic pronouns and contractions
    "im": "i am", "i'm": "i am", "m": "am",
    "u": "you", "ur": "your", "urs": "yours",
    "r": "are", "y": "why", "yup": "yes",
    "n": "and", "nd": "and", "d": "the",
    "bt": "but", "bcoz": "because", "cuz": "because",
    "coz": "because", "cz": "because","frm":"from","alot":"a lot",

    # Greetings
    "hii": "hi", "hiii": "hi", "hlw": "hello",
    "helo": "hello", "heyya": "hey", "heyy": "hey",
    "gm": "good morning", "gn": "good night",
    "gudnyt": "good night", "gudmrng": "good morning",

    # Common short forms
    "pls": "please", "plz": "please", "plzz": "please",
    "plsss": "please", "sry": "sorry", "srz": "sorry",
    "thx": "thanks", "tnx": "thanks", "tq": "thank you",
    "ty": "thank you", "tysm": "thank you so much",
    "thnx": "thanks", "thnks": "thanks", "thanq": "thank you",
    "nyc": "nice", "nycly": "nicely", "gud": "good",
    "gr8": "great", "grt": "great",

    # Abbreviations
    "asap": "as soon as possible", "bday": "birthday",
    "hbd": "happy birthday", "gn8": "good night",
    "gmorning": "good morning", "gdaftrn": "good afternoon",
    "tc": "take care", "gnite": "good night", "nite": "night",

    # Internet slang
    "lol": "laughing out loud", "rofl": "rolling on the floor laughing",
    "lmao": "laughing my ass off", "omg": "oh my god",
    "wtf": "what the fuck", "wth": "what the hell",
    "idk": "i do not know", "idc": "i do not care",
    "imo": "in my opinion", "imho": "in my humble opinion",
    "brb": "be right back", "bbl": "be back later",
    "ttyl": "talk to you later", "tbh": "to be honest",
    "ikr": "i know right", "ofc": "of course",
    "smh": "shaking my head", "np": "no problem",
    "nvm": "never mind", "btw": "by the way",
    "bc": "because", "afaik": "as far as i know", "omw": "on my way",
    "gg": "good game", "dw": "do not worry",
    "hmu": "hit me up", "wyd": "what are you doing",
    "wru": "where are you", "sup": "what is up",
    "wbu": "what about you", "hbu": "how about you",
    "lmk": "let me know", "idts": "i do not think so",
    "ily": "i love you", "ilu": "i love you", "ilysm": "i love you so much",

    # Numbers + Words
    "b4": "before", "l8r": "later",
    "2day": "today", "2mrw": "tomorrow", "2moro": "tomorrow",
    "4u": "for you", "4me": "for me", "bff": "best friends forever",
    "bf": "boyfriend", "gf": "girlfriend", "bffs": "best friends forever",
    "xoxo": "hugs and kisses",

    # Chat fillers
    "ya": "yeah", "yaar": "friend", "dude": "friend",
    "bro": "brother", "sis": "sister", "bruh": "brother",
    "jk": "just kidding", "k": "okay", "kk": "okay",
    "okie": "okay", "okies": "okay", "okk": "okay",
    "yolo": "you only live once", "fyi": "for your information",
    "faq": "frequently asked questions",

    # Extra
    "atm": "at the moment", "cya": "see you",
    "g2g": "got to go", "gtg": "got to go",
    "msg": "message", "txt": "text", "vid": "video",
    "pic": "picture", "dp": "display picture",
    "bio": "biography", "status": "status message",
    "prolly": "probably", "smth": "something",
    "tho": "though", "thru": "through", "ppl": "people",
    "tmrw": "tomorrow", "tmr": "tomorrow",
    "becoz": "because", "luv": "love", "muah": "kiss",
    "xmas": "christmas", "ny": "new year",

    # Hinglish style
    "acha": "okay", "accha": "okay", "haan": "yes",
    "h": "yes", "nope": "no", "pakka": "sure", "mast": "great",
    "faltu": "useless", "thik": "fine", "thik h": "fine",
    "sahi": "right", "chill": "relax", "chod": "leave",

    # Academic / domain
    "clg": "college", "collg": "college", "colly": "college",
    "uni": "university", "dept": "department", "addr": "address",
    "batt": "battery",

    # Proper-noun noise (cities)
    "jodhpurr": "jodhpur", "jodpur": "jodhpur",
    "mysru": "mysore", "myrs": "mysore", "mysuru": "mysuru",

    # India‑specific misspellings
    "kranataka": "karnataka", "kranatka": "karnataka",
    "krnatka": "karnataka", "krnataka": "karnataka",
    "karnatka": "karnataka", "karanataka": "karnataka",
    "karnatak": "karnataka",
    "rajsthan": "rajasthan", "rajashtan": "rajasthan",

    # Common confusion
    "talkathon": "hackathon",
}

# ---------------- Proper‑noun lexicon (compact seed) ----------------
INDIAN_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa",
    "Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala",
    "Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland",
    "Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura",
    "Uttar Pradesh","Uttarakhand","West Bengal","Delhi","Jammu and Kashmir",
    "Ladakh","Puducherry","Chandigarh","Andaman and Nicobar Islands","Lakshadweep"
]

POPULAR_CITIES = [
    "Mumbai","Delhi","Bengaluru","Bangalore","Kolkata","Chennai","Hyderabad","Pune",
    "Ahmedabad","Jaipur","Kochi","Indore","Bhopal","Lucknow","Kanpur","Nagpur",
    "Surat","Vadodara","Visakhapatnam","Patna","Varanasi","Udaipur","Jodhpur",
    "Kota","Mysuru","Mysore","Mangalore","Noida","Gurugram","Gurgaon","Thane","Nashik"
]

COMMON_FIRST_NAMES = [
    "Rahul","Rohit","Amit","Aman","Ankit","Mahipal","Ayesha","Priya","Neha",
    "Vikas","Vikram","Karan","Arjun","Raj","Riya","Rakesh","Aditi","Mohit",
    "Sanjay","Suresh","Anurag","Deepak","Pooja","Manish","Shreya","Siddharth"
]

LEX_STATE = {s.lower(): s for s in INDIAN_STATES}
LEX_CITY  = {c.lower(): c for c in POPULAR_CITIES}
LEX_NAME  = {n.lower(): n for n in COMMON_FIRST_NAMES}
ALL_LEX   = {**LEX_STATE, **LEX_CITY, **LEX_NAME}  # lowercase → Canonical

# ---------------- Helpers ----------------
def _closest_proper(token: str, cutoff: float = 0.94) -> Tuple[str, str] | None:
    """
    Fuzzy match a single token to state/city/name lexicon.
    Returns (canonical, tag) or None.
    Uses a stricter threshold for person names to avoid false positives.
    """
    low = token.lower()
    if low in ALL_LEX:
        if low in LEX_STATE: tag = "state"
        elif low in LEX_CITY: tag = "city"
        else: tag = "person"
        return ALL_LEX[low], tag

    match = get_close_matches(low, list(ALL_LEX.keys()), n=1, cutoff=cutoff)
    if match:
        m = match[0]
        tag = "state" if m in LEX_STATE else ("city" if m in LEX_CITY else "person")
        # Person names: demand higher certainty (reduces false locks)
        if tag == "person" and not get_close_matches(low, [m], n=1, cutoff=max(0.96, cutoff)):
            return None
        return ALL_LEX[m], tag
    return None

def _retok(text: str):
    # word/punct tokenizer sufficient for chatty inputs
    return re.findall(r"[A-Za-z][A-Za-z\-']*|\d+|[^\w\s]", text, flags=re.UNICODE)

def _smart_join(tokens):
    out = ""
    for t in tokens:
        if re.match(r"[A-Za-z0-9]", t):
            if out and (out[-1].isalnum() or out[-1] in {')',']','"',"'"}):
                out += " " + t
            else:
                out += t if not out else " " + t
        else:
            out += t
    return re.sub(r"\s+([,.;:!?])", r"\1", out).strip()

def _light_post_edits(text: str) -> str:
    # Insert 'from' after "I am <State>" if missing (model often omits 'from')
    text = re.sub(
        r"\b(I|i)\s+am\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b",
        r"\1 am from \2",
        text,
    )
    # Fix spacing around commas if any slipped through
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",([A-Za-z])", r", \1", text)
    # Normalize "home lot" -> "home a lot"
    text = re.sub(r"\bhome lot\b", "home a lot", text, flags=re.IGNORECASE)
    return text

# ---------------- SpellCorrector ----------------
class SpellCorrector:
    def __init__(self):
        self.spell = SpellChecker()

    def normalize_tokens(self, text: str) -> str:
        toks = _retok(text.lower())
        out = []
        for t in toks:
            if re.match(r"[A-Za-z]", t):
                out.append(ABBREV.get(t, t))
            else:
                out.append(t)
        return _smart_join(out)

    def correct_spelling(self, text: str, use_lexicon: bool = True, lexicon_cutoff: float = 0.94) -> str:
        return self.correct_spelling_with_stats(text, use_lexicon, lexicon_cutoff)[0]

    def correct_spelling_with_stats(self, text: str, use_lexicon: bool = True, lexicon_cutoff: float = 0.94) -> tuple[str, Dict[str,int]]:
        """
        Returns (corrected_text, stats)
        stats = {
            'lexicon_hits': int,
            'alpha_tokens': int,
            'locked_positions': Dict[int,str]  # token_index -> canonical proper noun
        }
        """
        norm = self.normalize_tokens(text)
        toks = _retok(norm)

        fixed: list[str] = []
        locked_map: Dict[int, str] = {}
        hits = 0
        alpha_tokens = 0

        for idx, t in enumerate(toks):
            if not re.match(r"[A-Za-z]", t):
                fixed.append(t)
                continue

            alpha_tokens += 1

            # Prefer proper‑noun lexicon first (and lock it)
            if use_lexicon:
                m = _closest_proper(t, cutoff=lexicon_cutoff)
                if m:
                    fixed.append(m[0])          # canonical case (e.g., Karnataka)
                    locked_map[idx] = m[0]      # remember original position for guardrail
                    hits += 1
                    continue

            # Fallback to dictionary spellchecker
            low = t.lower()
            if low not in self.spell and t.isalpha():
                cand = self.spell.correction(low)
                # Preserve capitalization if original token looked like a name
                fixed.append(cand.capitalize() if (cand and t[:1].isupper()) else (cand or t))
            else:
                fixed.append(t)

        out = _smart_join(fixed)
        out = _light_post_edits(out)
        stats = {"lexicon_hits": hits, "alpha_tokens": alpha_tokens, "locked_positions": locked_map}
        return out, stats
