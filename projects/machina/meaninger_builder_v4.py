#!/usr/bin/env python3
"""
MEANINGER BUILDER v4 — LINGUISTIC DETERMINISTIC EXTRACTOR
Pass 1: Morphological analysis (prefixes, negation, directionality)
Pass 2: Semantic role extraction (POS-tagged, verb-object-direction)
Preserves negation, encodes opposition, extracts semantic roles not just content words.
"""

import json, os, re, signal, sys, time
from collections import Counter, defaultdict
from typing import Dict, Any, Tuple, List

# =============================================================================
# CONFIG
# =============================================================================
STATE_FILE      = "meaninger_state.json"
UNDERSTAND_FILE = "meaninger_understand.txt"
MEANINGS_FILE   = "meaninger_meanings.txt"
POS_FILE        = "understand_pos.txt"
NEG_FILE        = "understand_neg.txt"
NEU_FILE        = "understand_neu.txt"
DICT_FILE       = "meaninger_dict.jsonl"
LOG_FILE        = "meaninger_run.log"

SEP = "|"
MAX_ENTRIES = int(os.environ.get("MAX_ENTRIES", 0))

_state: Dict[str, Any] = {}
_shutdown = False

# =============================================================================
# SIGNALS
# =============================================================================
def _sig(signum, frame):
    global _shutdown
    _shutdown = True
    _save_state()
    print("\n[SHUTDOWN] Saved.")
    sys.exit(0)

signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)

# =============================================================================
# STATE
# =============================================================================
def _save_state():
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_state, f)
    os.replace(tmp, STATE_FILE)

def _load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_idx": -1, "global_freq": {}, "start": time.time(), "v": "4.0"}

# =============================================================================
# LOAD DICTIONARY
# =============================================================================
def _load_dict():
    entries = []
    with open(DICT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries

# =============================================================================
# MORPHOLOGICAL DATABASE
# =============================================================================

# Prefixes with semantic tags
PREFIX_TAGS = {
    # Negation / Opposition
    "un": "NOT", "dis": "NOT", "in": "NOT", "non": "NOT", "ab": "AWAY",
    "mal": "BAD", "mis": "WRONG", "pseudo": "FAKE", "anti": "AGAINST",
    "counter": "OPPOSE", "de": "REMOVE", "down": "LESS", "under": "LESS",
    # Positive / Directional
    "pro": "FOR", "en": "IN", "co": "WITH", "bene": "GOOD", "ad": "TOWARD",
    "con": "WITH", "com": "WITH", "col": "WITH", "cor": "WITH",
    "re": "AGAIN", "over": "MORE", "up": "MORE", "super": "ABOVE",
    "hyper": "ABOVE", "extra": "BEYOND", "ultra": "BEYOND",
    "sub": "BELOW", " hypo": "BELOW", "infra": "BELOW",
    "pre": "BEFORE", "fore": "BEFORE", "post": "AFTER",
    "inter": "BETWEEN", "trans": "ACROSS", "dia": "THROUGH",
    "peri": "AROUND", "circum": "AROUND", "ambi": "BOTH",
    "multi": "MANY", "poly": "MANY", "uni": "ONE", "mono": "ONE",
    "bi": "TWO", "di": "TWO", "tri": "THREE",
}

# Negation markers in definitions
NEGATION_LEXICON = {
    "not", "no", "without", "never", "none", "lack", "lacking", "absence",
    "absent", "missing", "void", "empty", "devoid", "exclude", "excluding",
    "exclusion", "deny", "denial", "refuse", "refusing", "reject", "rejecting",
    "remove", "removing", "absence", "away", "apart", "opposite", "reverse",
    "contrary", "contradict", "negate", "negation", "null", "nullify",
    "cancel", "undo", "unmake", "destroy", "damage", "harm", "hurt",
    "injure", "injury", "wound", "break", "ruin", "spoil", "corrupt",
    "decay", "rot", "waste", "lose", "loss", "fail", "failure", "fall",
    "drop", "decline", "decrease", "reduce", "less", "lessen", "lower",
    "weaken", "impair", "deteriorate", "degrade", "debase", "demean",
    "defile", "pollute", "contaminate", "taint", "poison", "infect",
    "disease", "sick", "ill", "bad", "evil", "wrong", "false", "fake",
    "fraud", "lie", "cheat", "steal", "kill", "die", "death", "dead",
}

# Directional markers
DIRECTIONAL_TAGS = {
    "toward": "TO", "towards": "TO", "to": "TO", "into": "IN",
    "onto": "ON", "upon": "ON",
    "away": "AWAY", "from": "FROM", "off": "OFF", "out": "OUT",
    "out_of": "OUT", "outside": "OUT",
    "against": "AGAINST", "opposing": "AGAINST", "opposed": "AGAINST",
    "across": "ACROSS", "through": "THROUGH", "over": "OVER",
    "under": "UNDER", "beneath": "UNDER", "below": "UNDER",
    "above": "ABOVE", "over": "ABOVE", "up": "UP", "down": "DOWN",
    "back": "BACK", "forward": "FORWARD", "ahead": "FORWARD",
    "around": "AROUND", "about": "AROUND", "surrounding": "AROUND",
    "between": "BETWEEN", "among": "AMONG", "within": "IN", "inside": "IN",
    "before": "BEFORE", "after": "AFTER", "behind": "BEHIND", "beyond": "BEYOND",
    "beside": "BESIDE", "near": "NEAR", "close": "NEAR", "far": "FAR",
    "here": "HERE", "there": "THERE", "where": "WHERE",
}

# Semantic weight by POS (approximate, used for ranking)
POS_WEIGHTS = {
    "NN": 3.0, "NNS": 3.0, "NNP": 3.0, "NNPS": 3.0,  # Nouns
    "VB": 2.5, "VBD": 2.5, "VBG": 2.5, "VBN": 2.5, "VBP": 2.5, "VBZ": 2.5,  # Verbs
    "JJ": 1.5, "JJR": 1.5, "JJS": 1.5,  # Adjectives
    "RB": 0.8, "RBR": 0.8, "RBS": 0.8,  # Adverbs (lower weight)
    "IN": 1.0,  # Prepositions (directional)
}

# =============================================================================
# POS TAGGER (NLTK)
# =============================================================================
_pos_tagger = None

def _get_tagger():
    global _pos_tagger
    if _pos_tagger is None:
        import nltk
        try:
            nltk.data.find("taggers/averaged_perceptron_tagger_eng")
        except LookupError:
            nltk.download("averaged_perceptron_tagger_eng", quiet=True)
        _pos_tagger = nltk.pos_tag
    return _pos_tagger

# =============================================================================
# PASS 1: MORPHOLOGICAL ANALYSIS
# =============================================================================
def _analyze_morphology(word: str) -> Tuple[str, List[str]]:
    """
    Returns (base_word, list_of_prefix_tags)
    """
    w = word.lower().strip()
    tags = []

    # Check for multi-syllable prefixes first (longer matches first)
    sorted_prefixes = sorted(PREFIX_TAGS.keys(), key=len, reverse=True)
    remaining = w

    for prefix in sorted_prefixes:
        if remaining.startswith(prefix) and len(remaining) > len(prefix) + 1:
            tags.append(PREFIX_TAGS[prefix])
            remaining = remaining[len(prefix):]
            # Only take first matching prefix (avoid over-analysis)
            break

    return remaining, tags

# =============================================================================
# PASS 2: SEMANTIC ROLE EXTRACTION
# =============================================================================
def _extract_semantic_roles(defin: str, word: str) -> Tuple[str, str, str, List[str]]:
    """
    Returns (meaning_string, valence, directionality, semantic_roles)
    Semantic roles: [AGENT, ACTION, PATIENT, DIRECTION, INSTRUMENT, ...]
    """
    # Clean definition
    cleaned = re.sub(r'\(.*?\)', '', defin)
    cleaned = cleaned.replace("`", "").replace("'", "").replace("\"", "")

    # Tokenize and POS tag
    tokens = re.findall(r"[a-zA-Z]+", cleaned.lower())
    if not tokens:
        return "unknown", "neu", "", []

    tagger = _get_tagger()
    tagged = tagger(tokens)

    # Detect negation in definition
    neg_detected = any(tok in NEGATION_LEXICON for tok in tokens)

    # Detect directionality
    direction = ""
    for tok in tokens:
        if tok in DIRECTIONAL_TAGS:
            direction = DIRECTIONAL_TAGS[tok]
            break

    # Extract semantic roles
    roles = []

    # Find main verb and its arguments
    verbs = [(tok, pos) for tok, pos in tagged if pos.startswith("VB")]
    nouns = [(tok, pos) for tok, pos in tagged if pos.startswith("NN")]
    adjs = [(tok, pos) for tok, pos in tagged if pos.startswith("JJ")]
    preps = [(tok, pos) for tok, pos in tagged if pos == "IN"]

    # Role 1: Action (primary verb or nominalization)
    if verbs:
        # Prefer non-auxiliary verbs
        main_verbs = [v for v, p in verbs if v not in {"be", "is", "are", "was", "were", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "shall"}]
        if main_verbs:
            roles.append(f"ACT:{main_verbs[0]}")
        else:
            roles.append(f"ACT:{verbs[0][0]}")
    elif nouns:
        # Nominalization: use first noun as state/entity
        roles.append(f"ENT:{nouns[0][0]}")

    # Role 2: Patient / Object (noun closest to verb, or second noun)
    if len(nouns) >= 2:
        roles.append(f"PAT:{nouns[1][0]}")
    elif len(nouns) == 1:
        roles.append(f"PAT:{nouns[0][0]}")

    # Role 3: Direction / Location (preposition + noun, or directional)
    if direction:
        roles.append(f"DIR:{direction}")
    elif preps and len(nouns) >= 2:
        roles.append(f"DIR:{preps[0][0]}_{nouns[-1][0]}")

    # Role 4: Quality / Attribute (adjective)
    if adjs:
        roles.append(f"QUAL:{adjs[0][0]}")

    # Build meaning string from highest-weighted tokens
    scored = []
    for tok, pos in tagged:
        weight = POS_WEIGHTS.get(pos, 0.5)
        # Boost for semantic relevance
        if tok in NEGATION_LEXICON:
            weight += 2.0  # Negation is semantically critical
        if tok in DIRECTIONAL_TAGS:
            weight += 1.5
        scored.append((tok, weight))

    # Sort by weight, take top 3, remove duplicates
    seen = set()
    top_meaning = []
    for tok, weight in sorted(scored, key=lambda x: x[1], reverse=True):
        if tok not in seen and len(tok) > 2:
            seen.add(tok)
            top_meaning.append(tok)
        if len(top_meaning) >= 3:
            break

    meaning = ";".join(top_meaning) if top_meaning else "unknown"

    # Determine valence
    _, morph_tags = _analyze_morphology(word)

    # Count valence signals
    neg_signals = sum(1 for t in morph_tags if t in {"NOT", "AWAY", "BAD", "WRONG", "FAKE", "AGAINST", "OPPOSE", "REMOVE", "LESS"})
    pos_signals = sum(1 for t in morph_tags if t in {"FOR", "IN", "WITH", "GOOD", "TOWARD", "MORE", "ABOVE", "AGAIN"})

    if neg_detected:
        neg_signals += 1

    if neg_signals > pos_signals:
        valence = "neg"
    elif pos_signals > neg_signals:
        valence = "pos"
    else:
        valence = "neu"

    return meaning, valence, direction, roles

# =============================================================================
# STATS ENGINE (unchanged)
# =============================================================================
def _stats(word: str, global_freq: Dict) -> tuple:
    w = word.lower()
    local = Counter(c for c in w if c.isalpha())
    for ch, cnt in local.items():
        global_freq[ch] = global_freq.get(ch, 0) + cnt
    vowels = set("aeiou")
    vc = sum(local[c] for c in local if c in vowels)
    cc = sum(local[c] for c in local if c not in vowels)
    vr = round(vc / max(cc, 1), 3)
    lf = "".join(f"{c}{local[c]}" for c in sorted(local.keys()))
    return lf, len(w), vc, cc, vr

# =============================================================================
# CLEAN
# =============================================================================
def _clean(s: str) -> str:
    s = s.replace("|", "").replace("\n", " ").replace("\r", " ").strip()
    s = re.sub(r'\s+', ' ', s)
    return s

# =============================================================================
# BUILD ENTRY
# =============================================================================
def _build_entry(idx: int, word: str, defin: str, stats: tuple, 
                 meaning: str, valence: str, direction: str, roles: List[str],
                 morph_tags: List[str]) -> str:
    lf, L, vc, cc, vr = stats
    d_words = defin.split()[:8]
    d_compressed = "_".join(d_words)

    # Morphological tag string
    morph_str = ";".join(morph_tags) if morph_tags else "NONE"

    # Roles string
    roles_str = ";".join(roles) if roles else "NONE"

    fields = [
        str(idx),
        _clean(word),
        _clean(d_compressed),
        lf,
        str(L),
        str(vc),
        str(cc),
        str(vr),
        meaning,
        valence,
        direction if direction else "NONE",
        morph_str,
        roles_str,
        str(int(time.time()))
    ]
    return SEP.join(fields)

# =============================================================================
# MAIN
# =============================================================================
def main():
    global _state
    _state = _load_state()

    dictionary = _load_dict()
    total = len(dictionary)
    resume = _state["last_idx"] + 1
    target = total if MAX_ENTRIES == 0 else min(resume + MAX_ENTRIES, total)

    print(f"[RUN] Total: {total} | Resume: {resume} | Target: {target}")
    print(f"[RUN] LINGUISTIC EXTRACTOR v4 — morphology + semantic roles + POS tagging")
    print(f"[RUN] Ctrl+C = graceful stop. Restart resumes.\n")

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n--- V4_START {int(time.time())} RESUME {resume}/{target} ---\n")

    pos_count = 0
    neg_count = 0
    neu_count = 0
    start_t = time.time()

    for idx in range(resume, target):
        if _shutdown:
            break

        entry = dictionary[idx]
        word = entry["w"]
        defin = entry["d"]

        # Stats
        stats = _stats(word, _state["global_freq"])

        # Morphology
        base_word, morph_tags = _analyze_morphology(word)

        # Semantic roles
        meaning, valence, direction, roles = _extract_semantic_roles(defin, word)

        # Build entry
        line = _build_entry(idx, word, defin, stats, meaning, valence, direction, roles, morph_tags)
        with open(UNDERSTAND_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        # Clean meaning file
        with open(MEANINGS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{_clean(word)}|{meaning}|{valence}|{';'.join(morph_tags) if morph_tags else 'NONE'}|{';'.join(roles) if roles else 'NONE'}\n")

        # Bucket
        bucket_line = f"{_clean(word)}|{_clean(defin)}|{meaning}|{valence}|{direction if direction else 'NONE'}|{';'.join(roles) if roles else 'NONE'}\n"
        if valence == "pos":
            with open(POS_FILE, "a", encoding="utf-8") as f:
                f.write(bucket_line)
            pos_count += 1
        elif valence == "neg":
            with open(NEG_FILE, "a", encoding="utf-8") as f:
                f.write(bucket_line)
            neg_count += 1
        else:
            with open(NEU_FILE, "a", encoding="utf-8") as f:
                f.write(bucket_line)
            neu_count += 1

        _state["last_idx"] = idx
        _save_state()

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{int(time.time())} {idx+1}/{target} {word} {valence}\n")

        if (idx + 1) % 1000 == 0:
            elapsed = time.time() - start_t
            wpm = (idx + 1 - resume) / (elapsed / 60)
            print(f"[PROGRESS] {idx+1}/{target} | {wpm:.0f} words/min | pos:{pos_count} neg:{neg_count} neu:{neu_count}")

    print(f"\n[DONE] Last: {_state['last_idx']}")
    print(f"[BUCKETS] pos:{pos_count} neg:{neg_count} neu:{neu_count}")
    print(f"[FILES] {UNDERSTAND_FILE} | {MEANINGS_FILE} | {POS_FILE} | {NEG_FILE} | {NEU_FILE}")

if __name__ == "__main__":
    main()
