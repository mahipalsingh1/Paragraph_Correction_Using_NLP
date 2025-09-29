# utils/academic_rules.py
import re

# Keywords indicating academic contexts where "studying" is preferred
ACADEMIC_KEYWORDS = (
    "college", "university", "school", "institute", "campus", "degree",
    "btech", "b.tech", "mtech", "m.tech", "bsc", "msc", "phd", "semester",
)

# Words suggesting actual residence context; in such cases keep "staying"
HOSTEL_CLUES = (
    "hostel", "dorm", "dormitory", "pg", "paying guest", "stay at",
    "staying at", "room", "flat", "apartment", "rent",
)

def prefer_studying(text: str) -> str:
    """
    Heuristic rewrite:
      - If academic keywords are present and no strong "residence" clues are found,
        rewrite 'stay/staying in' → 'study/studying in'.
      - Conservatively scoped to avoid over-correction.
    """
    t = text
    low = t.lower()

    has_academic = any(k in low for k in ACADEMIC_KEYWORDS)
    has_hostel   = any(h in low for h in HOSTEL_CLUES)

    if has_academic and not has_hostel:
        # common variants
        t = re.sub(r"\bi am stay(?:ing)? in\b", "i am studying in", t, flags=re.IGNORECASE)
        t = re.sub(r"\bstay(?:ing)? in\b", "studying in", t, flags=re.IGNORECASE)
        # minor variants like "stay at college"
        t = re.sub(r"\bi am stay(?:ing)? at\b", "i am studying at", t, flags=re.IGNORECASE)
        t = re.sub(r"\bstay(?:ing)? at\b", "studying at", t, flags=re.IGNORECASE)

    return t
