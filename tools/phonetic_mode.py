#!/usr/bin/env python3
"""Build the "fully phonetic" spelling table: every sound has one spelling.

American and British pronunciations are lined up sound by sound. Consonants
come from the American one (so r and t are always written), plus the British
"y" in new/tune. Each vowel is spelled by its pair (American vowel, British
vowel), which picks its lexical set, e.g. American "cat" vowel + British
"father" vowel = the BATH set = "ah" (bahth, kahnt).

The key is in docs/phonetic-mode.md.

Usage:
  phonetic_mode.py CMUDICT FREQLIST UK_IPA [--top N] [--json OUT]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phonetic_spelling import VOWELS, load_cmudict, load_freq, load_ipa_uk, to_units  # noqa: E402
import spelling_levels  # noqa: E402

CONSONANTS = {
    # th spells both th sounds (thin, this), as in normal spelling
    "B": "b", "CH": "ch", "D": "d", "DH": "th", "F": "f", "G": "g", "HH": "h",
    "JH": "j", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ng", "P": "p",
    "R": "r", "S": "s", "SH": "sh", "T": "t", "TH": "th", "V": "v", "W": "w",
    "Y": "y", "Z": "z", "ZH": "zh",
}
# Vowels that are the same lexical set in both accents.
PLAIN_VOWELS = {
    "IH": "i", "EH": "e", "UH": "oo", "IY": "ee", "EY": "ay", "AY": "iy",
    "OY": "oy", "OW": "oh", "UW": "uu", "AW": "ow", "ER": "er",
    # vowel + r (the r is part of the unit)
    "AAR": "aar", "AOR": "or", "EHR": "air", "IYR": "eer", "UHR": "oor",
    "AYR": "iyer", "AWR": "ower",
}


def is_vowel(u):
    return u is not None and u[1] is not None


def align(us, uk):
    """Line up two unit sequences. Returns [(us_unit|None, uk_unit|None)]."""
    def cost(a, b):
        if a[0] == b[0]:
            return 0.0
        if is_vowel(a) and is_vowel(b):
            return 1.0
        if not is_vowel(a) and not is_vowel(b):
            return 2.0
        return 4.0

    def gap(u):
        return 0.3 if u[0] in ("R", "Y") else 1.5   # British drops r, adds y

    n, m = len(us), len(uk)
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        best[i][0] = best[i - 1][0] + gap(us[i - 1])
    for j in range(1, m + 1):
        best[0][j] = best[0][j - 1] + gap(uk[j - 1])
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best[i][j] = min(best[i - 1][j - 1] + cost(us[i - 1], uk[j - 1]),
                             best[i - 1][j] + gap(us[i - 1]),
                             best[i][j - 1] + gap(uk[j - 1]))
    pairs = []
    i, j = n, m
    while i or j:
        if i and j and best[i][j] == best[i - 1][j - 1] + cost(us[i - 1], uk[j - 1]):
            pairs.append((us[i - 1], uk[j - 1]))
            i, j = i - 1, j - 1
        elif i and best[i][j] == best[i - 1][j] + gap(us[i - 1]):
            pairs.append((us[i - 1], None))
            i -= 1
        else:
            pairs.append((None, uk[j - 1]))
            j -= 1
    return pairs[::-1]


def spell_vowel(us, uk, final, before_r=False):
    """Spelling for an American vowel unit, given the British one it lines up with."""
    base, stress = us
    ukb = uk[0] if is_vowel(uk) else None
    if base == "AA" and before_r and ukb is None:
        return "aa"                                  # no British form: aren't, like car
    if base == "AH" and stress == 0:
        return "a"                                   # schwa: about, the
    if base == "IY" and stress == 0 and final:
        return "y"                                   # happy, city
    if base == "AE":
        return "ah" if ukb == "PALM" else "a"        # bath vs trap
    if base == "AA":
        if ukb == "PALM":
            return "aa"                              # palm: father, calm
        return "aw" if ukb == "AO" else "o"          # lot: hot
    if base == "AO":
        if ukb == "AA":
            return "o"                               # cloth: off, dog (merged with lot)
        return "aa" if ukb == "PALM" else "aw"       # thought: saw
    if base == "AH":
        return "o" if ukb == "AA" else "u"           # what, of / strut: cup
    return PLAIN_VOWELS[base]


def spell(us_phones, uk_phones):
    us = to_units(us_phones)
    uk = to_units(uk_phones) if uk_phones else []
    pairs = align(us, uk) if uk else [(u, None) for u in us]
    out = []
    last_vowel = max((k for k, (a, _) in enumerate(pairs) if is_vowel(a)), default=-1)
    for k, (a, b) in enumerate(pairs):
        if a is None:
            # British-only sound: keep the "y" of new / tune before uu
            nxt = next((p[0] for p in pairs[k + 1:] if p[0] is not None), None)
            if b is not None and b[0] == "Y" and nxt is not None and nxt[0] == "UW":
                out.append("y")
            continue
        if is_vowel(a):
            final = k == last_vowel and all(not is_vowel(p[0]) and p[0] is None
                                            for p in pairs[k + 1:])
            nxt = next((p[0] for p in pairs[k + 1:] if p[0] is not None), None)
            out.append(spell_vowel(a, b, final, before_r=nxt is not None and nxt[0] == "R"))
        else:
            out.append(CONSONANTS[a[0]])
    return "".join(out)


# Rows for the popup key: (sound, spelling, example words). The examples are
# respelled by the generator itself so the key always matches the table.
KEY = [
    ("kit", "i", ["sit", "women"]), ("dress", "e", ["bed", "said"]),
    ("trap", "a", ["cat", "have"]), ("bath", "ah", ["bath", "ask"]),
    ("lot", "o", ["hot", "what"]), ("strut", "u", ["cup", "love"]),
    ("foot", "oo", ["book", "should"]), ("fleece", "ee", ["see", "leave"]),
    ("face", "ay", ["day", "make"]), ("price", "iy", ["my", "night"]),
    ("choice", "oy", ["boy", "noise"]), ("goat", "oh", ["go", "home"]),
    ("goose", "uu", ["food", "two"]), ("cute", "yuu", ["new", "music"]),
    ("mouth", "ow", ["out", "house"]), ("palm", "aa", ["father", "calm"]),
    ("thought", "aw", ["saw", "thought"]), ("nurse / -er", "er", ["her", "better"]),
    ("start", "aar", ["car", "far"]), ("north", "or", ["for", "door"]),
    ("near", "eer", ["here", "near"]), ("square", "air", ["care", "there"]),
    ("cure", "oor", ["poor", "tour"]), ("schwa", "a", ["about", "the"]),
    ("happy", "y", ["happy", "city"]),
    ("k", "k", ["cat", "quick"]), ("ks", "ks", ["box"]), ("z", "z", ["is", "please"]),
    ("f", "f", ["phone", "laugh"]), ("j", "j", ["judge", "general"]),
    ("th (thin, this)", "th", ["think", "this"]),
    ("zh", "zh", ["measure", "vision"]), ("w", "w", ["when", "what"]),
]


# British spellings missing from CMUdict, matched to their American form for
# the pronunciation: offence -> offense, colour -> color, centre -> center.
US_VARIANTS = [("our", "or"), ("ence", "ense"), ("tre", "ter"), ("isation", "ization"),
               ("ise", "ize"), ("ised", "ized"), ("ising", "izing"), ("yse", "yze"),
               ("ogue", "og"), ("lled", "led"), ("lling", "ling"), ("ae", "e"), ("oe", "e")]


def american_form(word, us):
    """The American spelling of a British-spelled word, if CMUdict has it."""
    for gb, am in US_VARIANTS:
        i = word.rfind(gb)
        if i >= 0:
            alt = word[:i] + am + word[i + len(gb):]
            if alt in us:
                return alt
    return None


def contraction_uk(word, us, uk):
    """British pronunciation of a contraction, from its base word: the British
    dictionary has "what" and "are" but not "what's" and "aren't"."""
    head = word.split("'")[0]
    # n't contractions: the base is the word before the n (aren't -> are)
    bases = [word[:-3], head] if word.endswith("n't") else [head]
    for base in bases:
        if base in uk and base in us:
            full, stem = us[word][0], us[base][0]
            if full[:len(stem)] == stem:
                return uk[base][0] + full[len(stem):]
    return None


def is_abbreviation(word, prons):
    """CMUdict lists abbreviations under their spoken form (st = "street",
    mr = "mister", fbi = "eff bee eye"). Spot them so they're left alone:
    no vowel letter at all, or a short word whose letters can't be matched to
    any of its pronunciations."""
    if not set(word) & set("aeiouy"):
        return True
    return len(word) <= 4 and not any(spelling_levels.align(word, p) for p in prons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmudict")
    ap.add_argument("freq")
    ap.add_argument("uk")
    ap.add_argument("--top", type=int, default=50000)
    ap.add_argument("--json")
    ap.add_argument("--wordlist", default="/usr/share/dict/words",
                    help="dictionary of real words, to cover words the frequency list misses")
    a = ap.parse_args()

    us, uk = load_cmudict(a.cmudict), load_ipa_uk(a.uk)
    ranked = [w for w, _ in load_freq(a.freq) if w.isalpha() and w.isascii()]
    # single letters are letter names ("t" = "tee"), except the words a and I
    words = [w for w in ranked if w in us and (len(w) > 1 or w in ("a", "i"))][:a.top]
    # The frequency list comes from film subtitles, so it misses many written
    # words (learners, browsers). Also cover every word that's in both CMUdict
    # and a real-word list (the British dictionary or the system dictionary);
    # that leaves out most of CMUdict's names.
    with open(a.wordlist) as f:
        real = {w.strip() for w in f if w.strip().islower()}
    seen = set(words)
    words += sorted(w for w in us if w not in seen and w.isalpha() and w.isascii()
                    and len(w) > 1 and (w in uk or w in real))
    words = [w for w in words
             if not is_abbreviation(w, spelling_levels.pronunciations(w, us, uk))]
    # Contractions aren't in the word list but CMUdict has them (can't, I'm).
    common = set(ranked[:5000])
    words += [w for w in us if "'" in w and w.split("'")[0] in common
              and w.split("'", 1)[1] in ("t", "s", "m", "re", "ve", "ll", "d")]
    # British spellings CMUdict lacks (offence, colour), via the American form
    british = {}
    for w in ranked[:a.top]:
        if w not in us:
            am = american_form(w, us)
            if am:
                british[w] = am
    words += sorted(british)

    def respell(w):
        if w in british:
            return spell(us[british[w]][0], uk[w][0] if w in uk else None)
        uk_pron = uk[w][0] if w in uk else (contraction_uk(w, us, uk) if "'" in w else None)
        return spell(us[w][0], uk_pron)

    table, same = {}, []
    for w in words:
        sp = respell(w)
        if sp != w:
            table[w] = sp
        else:
            same.append(w)
    key = [{"sound": s, "spelling": sp,
            "examples": ", ".join(f"{w} → {respell(w)}" for w in ex if w in us)}
           for s, sp, ex in KEY]
    print(f"{len(table)} of {len(words)} words change", file=sys.stderr)
    if a.json:
        with open(a.json, "w") as f:
            # "same": known words that don't change, so the extension doesn't try
            # to build them from a shorter word (need is not nee + d)
            json.dump({"key": key, "words": table, "same": sorted(same)}, f,
                      separators=(",", ":"), ensure_ascii=False)
    for row in key:
        print(f"{row['sound']:12} {row['spelling']:5} {row['examples']}")


if __name__ == "__main__":
    main()
