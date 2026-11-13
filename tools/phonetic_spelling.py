#!/usr/bin/env python3
"""Choose a one-spelling-per-sound English orthography that changes as few
words as possible.

Each word's spelling is generated purely from its CMUdict pronunciation, using
a set of parameters (which spelling to use for each sound, and a few
positional conventions such as silent-e and consonant doubling). A coordinate
descent over the parameters maximises the share of word *tokens* (frequency
weighted) whose generated spelling equals today's spelling.

Positional conventions are allowed only when the choice is fully determined by
the sounds (e.g. "long vowel + consonant at word end takes a silent e"), so a
writer who knows the pronunciation always knows the spelling.

Usage:
  phonetic_spelling.py CMUDICT FREQLIST [--top N] [--report OUT.md]
"""

import argparse
import re
import sys

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY",
          "OW", "OY", "UH", "UW",
          # British-only units: /ɑː/ (palm, bath, car) and centring diphthongs
          "PALM", "IYR", "EHR", "UHR"}
# Vowels that combine with a following R (not followed by a vowel) into one unit.
R_COLOURED = {"AA": "AAR", "AO": "AOR", "OW": "AOR", "EH": "EHR", "AE": "EHR",
              "EY": "EHR", "IH": "IYR", "IY": "IYR", "UH": "UHR", "UW": "UHR",
              "AY": "AYR", "AW": "AWR"}
SHORT = {"AE", "EH", "IH", "AA", "AH", "AO"}
LONG = {"EY": "a", "IY": "e", "AY": "i", "OW": "o", "UW": "u"}

CONS_FIXED = {"B": "b", "D": "d", "F": "f", "G": "g", "HH": "h", "L": "l",
              "M": "m", "N": "n", "P": "p", "R": "r", "S": "s", "T": "t",
              "V": "v", "W": "w", "Y": "y", "TH": "th", "SH": "sh",
              "CH": "ch", "NG": "ng", "JH": "j"}

# Parameter -> candidate values. First value is the starting point.
PARAMS = {
    # consonants
    "K": ["c/k", "k", "c/k-final-k"],
    "Z": ["z", "s"],
    "DH": ["th", "dh"],
    "ZH": ["zh", "s"],
    "x_for_ks": [True, False],
    "qu_for_kw": [True, False],
    "yu_as_u": [True, False],          # /juː/ in "cute" written u (+ silent e)
    "tion": [True, False],             # final /ʃən/ -> tion
    "sion": [True, False],             # final /ʒən/ -> sion
    "ture": [True, False],             # final /tʃər/ -> ture
    "le": [True, False],               # final consonant + /əl/ -> le
    "final_ge": [True, False],         # final /dʒ/ -> ge (dge after short vowel)
    "medial_double": ["no-v-r", "no-v", "off"],
    # after a short stressed vowel at word end: which letters double
    # (f/l/s/z only in one-syllable words; k->ck, ch->tch, j->dge)
    "final_double": ["flsz", "fls", "fl", "l", "", "flsz-no-ck"],
    # short vowels
    "AA": ["o", "a"],
    "AO": ["o", "aw", "au"],
    "AO_L": ["al", "same"],            # /ɔl/ -> al(l): all, call
    "UH": ["oo", "u"],
    "AH_stressed": ["u", "o"],
    # schwa (AH0) by position
    "schwa_initial": ["a", "u", "e", "o"],
    "schwa_medial": ["a", "e", "o", "u", "i"],
    "schwa_final": ["a", "u", "e"],
    "IH0_initial": ["i", "e"],
    "IH0_before_final_DZ": ["e", "i"],  # boxes, wanted
    # long vowels: medial (closed syllable) and word-final
    # "same": a long vowel is spelled the same at word end as elsewhere
    # (digraph everywhere, or vowel + silent e: me -> mee, my -> mie)
    "long_final": ["position", "same"],
    "EY_medial": ["magic", "ai", "ay"],
    "EY_final": ["ay", "a", "ae"],
    "IY_medial": ["magic", "ee", "ea"],
    "IY_final": ["ee", "e", "ea"],
    "IY0_final": ["y", "ee", "ie", "ey"],
    # long vowel before a final consonant cluster: find/finde, most/moste
    "magic_cluster_e": [False, True],
    "AY_medial": ["magic", "igh", "ie", "y"],
    "AY_final": ["y", "i", "ie", "igh"],
    "OW_medial": ["magic", "oa", "ow", "oe"],
    "OW_final": ["o", "ow", "oe"],
    "UW_medial": ["oo", "magic", "ew", "ue"],
    "UW_final": ["oo", "ew", "ue", "u"],
    "AW": ["ou/ow-final", "ow", "ou"],
    "OY": ["oi/oy-final", "oy", "oi"],
    "ER_stressed": ["er", "ur", "ir"],
    # vowel + r
    "AOR_final": ["or", "ore"],
    "EHR": ["air", "er"],
    "EHR_final": ["are", "air"],
    "IYR": ["eer", "ear"],
    "IYR_final": ["ere", "eer", "ear"],
    "UHR": ["ure", "oor", "ur"],
    "AYR": ["ire", "ier"],
    "AWR": ["our", "ower"],
    # inflections
    "PALM": ["ar", "a", "ah"],          # British /ɑː/: car, father, bath
    "morph_suffixes": [True, False],   # keep -s / -ed for inflections
}


def load_cmudict(path):
    """word -> list of pronunciations (all variants)."""
    d = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            word, *phones = line.split()
            word = re.sub(r"\(\d+\)$", "", word)
            d.setdefault(word, []).append(tuple(phones))
    return d


# IPA (ipa-dict en_UK) -> ARPAbet-style symbols. Longest match first.
IPA_VOWELS = {
    "aɪə": ["AY", "AH0"], "aʊə": ["AW", "AH0"],
    "eɪ": "EY", "aɪ": "AY", "ɔɪ": "OY", "əʊ": "OW", "oʊ": "OW", "aʊ": "AW",
    "ɪə": "IYR", "iə": "IYR", "eə": "EHR", "ɛə": "EHR", "ʊə": "UHR",
    "iː": "IY", "uː": "UW", "ɑː": "PALM", "ɔː": "AO", "ɜː": "ER", "ɛː": "EHR",
    "ɪ": "IH", "i": "IY", "ɛ": "EH", "e": "EH", "æ": "AE", "a": "AE",
    "ʌ": "AH", "ɒ": "AA", "ɔ": "AO", "ʊ": "UH", "u": "UW", "ɑ": "PALM",
    "ɜ": "ER", "ə": "AH", "ɐ": "AH",
}
IPA_CONS = {
    "tʃ": "CH", "dʒ": "JH", "p": "P", "b": "B", "t": "T", "d": "D", "k": "K",
    "ɡ": "G", "g": "G", "f": "F", "v": "V", "θ": "TH", "ð": "DH", "s": "S",
    "z": "Z", "ʃ": "SH", "ʒ": "ZH", "h": "HH", "m": "M", "n": "N", "ŋ": "NG",
    "l": "L", "ɹ": "R", "r": "R", "j": "Y", "w": "W",
}
IPA_KEYS = sorted(list(IPA_VOWELS) + list(IPA_CONS), key=len, reverse=True)


def ipa_to_phones(ipa):
    out = []
    stress = 0
    i = 0
    while i < len(ipa):
        ch = ipa[i]
        if ch == "ˈ":
            stress = 1; i += 1; continue
        if ch == "ˌ":
            stress = 2; i += 1; continue
        for k in IPA_KEYS:
            if ipa.startswith(k, i):
                break
        else:
            return None                      # unknown symbol: skip this pron
        i += len(k)
        if k in IPA_CONS:
            out.append(IPA_CONS[k])
            continue
        vs = IPA_VOWELS[k]
        vs = vs if isinstance(vs, list) else [vs]
        for n, v in enumerate(vs):
            if v[-1].isdigit():
                out.append(v)
                continue
            st = stress if n == 0 else 0
            if k in ("ə", "ɐ"):
                st = 0
            elif k == "ʌ" and st == 0:
                st = 2                       # ʌ is never reduced
            out.append(f"{v}{st}")
        stress = 0
    vowels = [j for j, p in enumerate(out) if p[-1].isdigit()]
    if vowels and all(out[j][-1] == "0" for j in vowels):
        full = [j for j in vowels if not out[j].startswith("AH")]
        if len(vowels) == 1 and full:
            out[vowels[0]] = out[vowels[0]][:-1] + "1"
    return tuple(out)


def rhoticise(word, ph):
    """Put back the r that British pronunciation drops, using the spelling.

    The spelling system keeps r, so a British pronunciation is only useful if
    it agrees with the written r: final /ə/ in "father" is -er, and /ɑː/ in a
    word written with "ar" (car, start) is the vowel of car, not of father.
    """
    ph = list(ph)
    for suffix in ((), ("Z",), ("D",)):
        n = len(suffix)
        stem_w = word[:-1] if n else word
        if n and not word.endswith(("s", "d")):
            continue
        if (len(ph) > n and ph[len(ph) - n - 1] == "AH0"
                and tuple(ph[len(ph) - n:]) == suffix
                and stem_w.endswith(("r", "re"))):
            ph[len(ph) - n - 1] = "ER0"
            break
    if "r" not in word:
        # ipa-dict writes /iə/ for both "here" and the i+ə of "idea", "million";
        # without an r in the spelling it's the two-vowel sequence.
        split = {"IYR": ("IY", "AH0"), "EHR": ("EH", "AH0"), "UHR": ("UW", "AH0")}
        out = []
        for p in ph:
            if p[:-1] in split:
                v, schwa = split[p[:-1]]
                out += [v + p[-1], schwa]
            else:
                out.append(p)
        ph = out
    if "ar" not in word:
        return tuple(ph)
    return tuple(("AAR" + p[-1]) if p.startswith("PALM") else p for p in ph)


def load_ipa_uk(path):
    d = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            word, prons = line.rstrip("\n").split("\t")
            for ipa in prons.split(","):
                ph = ipa_to_phones(ipa.strip().strip("/"))
                if ph:
                    d.setdefault(word, []).append(rhoticise(word, ph))
    return d


def load_freq(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            w, c = line.split()
            out.append((w, int(c)))
    return out


def load_shorthand(path):
    """word -> set of familiar informal spellings."""
    d = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line:
                word, alts = line.split(":")
                d[word.strip()] = set(alts.split())
    return d


def to_units(phones):
    """[(base, stress)] with vowel+R merged into r-coloured units."""
    units = []
    for p in phones:
        m = re.match(r"([A-Z]+)(\d?)$", p)
        units.append((m.group(1), int(m.group(2)) if m.group(2) else None))
    merged = []
    i = 0
    while i < len(units):
        base, st = units[i]
        if (base in R_COLOURED and i + 1 < len(units) and units[i + 1][0] == "R"
                and (i + 2 >= len(units) or units[i + 2][0] not in VOWELS)):
            merged.append((R_COLOURED[base], st))
            i += 2
            continue
        merged.append((base, st))
        i += 1
    return merged


def is_vowel(u):
    return u[1] is not None


def spell(phones, P):
    units = to_units(phones)
    n = len(units)
    out = []           # list of strings, K placeholders "\x01"
    pending_e = False
    nvowels = sum(1 for u in units if is_vowel(u))
    i = 0

    def short_stressed(j):
        return (0 <= j < n and units[j][0] in SHORT and units[j][1] in (1, 2)
                and not (units[j][0] == "AO" and P["AO"] != "o"))

    while i < n:
        base, st = units[i]
        rest = n - i - 1
        nxt = units[i + 1] if i + 1 < n else None
        at_end = i == n - 1

        if st is None:  # consonant
            # multi-unit endings
            if P["tion"] and base == "SH" and rest == 2 and units[i + 1] == ("AH", 0) and units[i + 2][0] == "N":
                out.append("tion"); i += 3; continue
            if P["sion"] and base == "ZH" and rest == 2 and units[i + 1] == ("AH", 0) and units[i + 2][0] == "N":
                out.append("sion"); i += 3; continue
            if P["ture"] and base == "CH" and rest == 1 and units[i + 1] == ("ER", 0):
                out.append("ture"); i += 2; continue
            if P["x_for_ks"] and base == "K" and nxt and nxt[0] == "S":
                out.append("x"); i += 2; continue
            if P["qu_for_kw"] and base == "K" and nxt and nxt[0] == "W":
                out.append("qu"); i += 2; continue
            if base == "Y" and P["yu_as_u"] and nxt and nxt[0] == "UW":
                i += 1; continue
            if base == "NG" and nxt and nxt[0] in ("K", "G"):
                out.append("n"); i += 1; continue
            if base == "K":
                letter = "\x01"
            elif base == "Z":
                letter = P["Z"]
            elif base == "DH":
                letter = P["DH"]
            elif base == "ZH":
                letter = P["ZH"]
            else:
                letter = CONS_FIXED[base]

            prev_short = short_stressed(i - 1)
            if prev_short and nxt and is_vowel(nxt) and P["medial_double"] != "off":
                skip = {"v", "r"} if P["medial_double"] == "no-v-r" else {"v"}
                if letter == "\x01":
                    letter = "\x02"
                elif len(letter) == 1 and letter not in skip | {"w", "y", "h", "x", "j"}:
                    letter = letter * 2
            elif prev_short and at_end and P["final_double"]:
                fd = P["final_double"]
                if letter in fd.split("-")[0] and len(letter) == 1 and nvowels == 1:
                    letter = letter * 2
                elif "no-ck" in fd:
                    pass
                elif letter == "\x01":
                    letter = "\x02"
                elif letter == "ch":
                    letter = "tch"
                elif letter == "j" and P["final_ge"]:
                    letter = "dge"
            if letter == "j" and at_end and P["final_ge"]:
                letter = "ge"
            out.append(letter)
            i += 1
            continue

        # vowel
        cons_after = 0
        j = i + 1
        while j < n and not is_vowel(units[j]):
            cons_after += 1
            j += 1
        closed_final = j == n and cons_after > 0   # consonants then word end

        if base in LONG:
            if base == "IY" and st == 0 and at_end:
                out.append(P["IY0_final"]); i += 1; continue
            if base == "UW" and i > 0 and units[i - 1][0] == "Y" and P["yu_as_u"]:
                mode_med, fin = "magic", "ue" if P["UW_final"] == "ue" else "u"
            else:
                mode_med, fin = P[f"{base}_medial"], P[f"{base}_final"]
            letter = LONG[base]
            if P["long_final"] == "same":
                fin = letter + "e" if mode_med == "magic" else mode_med
            if at_end:
                out.append(fin)
            elif mode_med == "magic":
                out.append(letter)
                if closed_final and (cons_after == 1 or P["magic_cluster_e"]):
                    pending_e = True
            else:
                out.append(mode_med)
            i += 1
            continue

        if base == "AH":
            if st in (1, 2):
                v = P["AH_stressed"]
            elif i == 0:
                v = P["schwa_initial"]
            elif at_end:
                v = P["schwa_final"]
            elif (P["le"] and rest == 1 and units[i + 1][0] == "L"
                  and i > 0 and not is_vowel(units[i - 1])):
                out.append("le"); i += 2; continue
            else:
                v = P["schwa_medial"]
            out.append(v); i += 1; continue
        if base == "IH":
            v = "i"
            if st == 0:
                if i == 0:
                    v = P["IH0_initial"]
                elif rest == 1 and units[i + 1][0] in ("D", "Z"):
                    v = P["IH0_before_final_DZ"]
            out.append(v); i += 1; continue
        if base == "AO":
            if P["AO_L"] == "al" and nxt and nxt[0] == "L":
                out.append("a"); i += 1; continue
            out.append(P["AO"]); i += 1; continue
        if base == "AW":
            v = P["AW"]
            if v == "ou/ow-final":
                v = "ow" if (at_end or closed_final is False and rest == 0) else "ou"
            out.append(v); i += 1; continue
        if base == "OY":
            v = P["OY"]
            if v == "oi/oy-final":
                v = "oy" if at_end else "oi"
            out.append(v); i += 1; continue
        if base == "ER":
            out.append(P["ER_stressed"] if st in (1, 2) else "er"); i += 1; continue
        simple = {"AE": "a", "EH": "e", "IH": "i", "AA": P["AA"], "UH": P["UH"],
                  "PALM": P["PALM"]}
        if base in simple:
            out.append(simple[base]); i += 1; continue
        # r-coloured units
        if base == "AAR":
            out.append("ar")
        elif base == "AOR":
            out.append(P["AOR_final"] if at_end else "or")
        elif base == "EHR":
            out.append(P["EHR_final"] if at_end else P["EHR"])
        elif base == "IYR":
            out.append(P["IYR_final"] if at_end else P["IYR"])
        elif base == "UHR":
            out.append(P["UHR"])
        elif base == "AYR":
            out.append(P["AYR"])
        elif base == "AWR":
            out.append(P["AWR"])
        else:
            raise ValueError(base)
        i += 1

    s = "".join(out)
    if pending_e and not s.endswith("e"):
        s += "e"
    s = s.replace("\x02", "ck")
    res = []
    for k, ch in enumerate(s):
        if ch != "\x01":
            res.append(ch)
            continue
        nx = s[k + 1] if k + 1 < len(s) else ""
        if P["K"] == "k":
            res.append("k")
        elif nx in ("e", "i", "y") or (nx == "" and P["K"] == "c/k-final-k"):
            res.append("k")
        else:
            res.append("c")
    return "".join(res)


# --- Strict mode: one fixed spelling per sound, regardless of position -----
# Vowel+r units (car, for, care, here, poor, her) count as their own sounds
# because they are distinct vowels in both US and UK English.
STRICT_PARAMS = {
    "K": ["k", "c", "ck"], "Z": ["z", "s"], "DH": ["th", "dh"], "ZH": ["zh"],
    "F": ["f", "ph"], "S": ["s", "ss"], "L": ["l", "ll"], "JH": ["j", "g"],
    "x": [False, True],                 # x for /ks/
    "qu": [False, True],                # qu for /kw/
    "nk": [True, False],                # n (not ng) before /k/, /g/: think
    "AE": ["a"], "EH": ["e"], "IH": ["i", "y"], "AA": ["o", "a"],
    "AO": ["aw", "au", "o", "a"], "UH": ["ou", "oo", "u", "uu"], "AH": ["u", "o"],
    "schwa": ["e", "a", "u", "o", "i"],
    "EY": ["ai", "ay", "ae", "a"], "IY": ["ee", "ea", "e"],
    "happy": ["y", "ee", "i", "ie", "ey"],
    "AY": ["igh", "ie", "y", "i", "ai", "iy"], "OW": ["oa", "ow", "oe", "o", "oh"],
    "UW": ["oo", "ew", "ue", "u", "uu"], "AW": ["ow", "ou"], "OY": ["oi", "oy"],
    # Vowels before r. "+r" options spell them as an existing vowel plus r,
    # so no new spelling is needed: car = PALM + r (kaar), for = AO + r (fawr),
    # there = EY + r (thayr), near = IY + r (neer).
    "ER": ["er", "ur", "ir"], "AAR": ["ar", "PALM+r"], "AOR": ["or", "ore", "oar", "AO+r"],
    "EHR": ["air", "are", "er", "ear", "EY+r"], "IYR": ["eer", "ear", "ere", "IY+r"],
    "PALM": ["aa", "ah"],               # British /ɑː/ in father, calm (not car)
    "UHR": ["oor", "ure", "ur"],
    "morph_suffixes": [True, False],
}
DISTINCT_VOWELS = ["AE", "EH", "IH", "AA", "AO", "UH", "AH", "EY", "IY", "AY",
                   "OW", "UW", "AW", "OY", "ER", "AAR", "AOR", "EHR", "IYR", "UHR",
                   "PALM"]


def resolve(P, unit):
    """Spelling of a unit; "X+r" means X's spelling followed by r."""
    v = P[unit]
    if isinstance(v, str) and v.endswith("+r"):
        return P[v[:-2]] + "r"
    return v


def strict_ok(P):
    # /ʊ/ (book) may share u with /ʌ/ (cup): kids write gud, shud, luk, and
    # northern English accents don't distinguish them.
    vs = [resolve(P, v) for v in DISTINCT_VOWELS if not (v == "UH" and P["UH"] == P["AH"])]
    return len(set(vs)) == len(vs)


# --- Kid-plausibility: does a respelling look like an English letter string?
LETTER_PAIRS = {}  # letter-pair counts, by word type


def build_letter_pairs(words):
    from collections import Counter
    c = Counter()
    for w in words:
        t = f"^{w}$"
        c.update({t[i:i + 2] for i in range(len(t) - 1)})
    LETTER_PAIRS.clear()
    LETTER_PAIRS.update(c)


def plausible(sp, min_types=5):
    """Every letter pair (and how the word starts and ends) is common in English."""
    t = f"^{sp}$"
    return all(LETTER_PAIRS.get(t[i:i + 2], 0) >= min_types for i in range(len(t) - 1))


def spell_strict(phones, P):
    units = to_units(phones)
    out = []
    i = 0
    n = len(units)
    while i < n:
        base, st = units[i]
        nxt = units[i + 1][0] if i + 1 < n else None
        if st is None:
            if P["x"] and base == "K" and nxt == "S":
                out.append("x"); i += 2; continue
            if P["qu"] and base == "K" and nxt == "W":
                out.append("qu"); i += 2; continue
            if P["nk"] and base == "NG" and nxt in ("K", "G"):
                out.append("n"); i += 1; continue
            out.append(P[base] if base in P else CONS_FIXED[base])
        elif base == "AH":
            out.append(P["AH"] if st in (1, 2) else P["schwa"])
        elif base == "IY" and st == 0:
            out.append(P["happy"])
        elif base == "PALM":
            out.append(P["PALM"])
        elif base == "AYR":
            out.append(P["AY"] + "r")
        elif base == "AWR":
            out.append(P["AW"] + "r")
        else:
            out.append(resolve(P, base))
        i += 1
    return "".join(out)


INFL_S = {("S",), ("Z",), ("IH0", "Z"), ("AH0", "Z")}
INFL_D = {("T",), ("D",), ("IH0", "D"), ("AH0", "D")}


def find_inflection(word, phones, prons):
    """Return (kind, stem_phones) if word = stem + -s/-ed for this pron."""
    cands = []
    if word.endswith("s"):
        cands.append((word[:-1], "s"))
        if word.endswith("es"):
            cands.append((word[:-2], "s"))
        if word.endswith("ies"):
            cands.append((word[:-3] + "y", "s"))
    if word.endswith("ed"):
        if word[:-1].endswith("e") and not word[:-1].endswith("ee"):
            cands.append((word[:-1], "d"))  # name -> named
        cands.append((word[:-2], "d"))
        if len(word) > 4 and word[-3] == word[-4]:
            cands.append((word[:-3], "d"))
        if word.endswith("ied"):
            cands.append((word[:-3] + "y", "d"))
    for stem, kind in cands:
        if len(stem) < 3:
            continue
        for sp in prons.get(stem, ()):
            if phones[:len(sp)] != sp:
                continue
            suf = phones[len(sp):]
            if (kind == "s" and suf in INFL_S) or (kind == "d" and suf in INFL_D):
                return kind, sp
    return None


def spell_word(phones, infl, P):
    if P.get("_strict"):
        if P["morph_suffixes"] and infl:
            kind, sp = infl
            base = spell_strict(sp, P)
            if kind == "s":
                return base + ("es" if re.search(r"(s|x|z|sh|ch)$", base) else "s")
            return base + ("d" if base.endswith("e") else "ed")
        return spell_strict(phones, P)
    if P["morph_suffixes"] and infl:
        kind, sp = infl
        base = spell(sp, P)
        units = to_units(sp)
        if kind == "s":
            if re.search(r"(s|x|z|sh|ch)$", base):
                return base + "es"
            if re.search(r"[^aeiou]y$", base):
                return base[:-1] + "ies"
            return base + "s"
        if base.endswith("e"):
            return base + "d"
        if re.search(r"[^aeiou]y$", base):
            return base[:-1] + "ied"
        one_syll_short = (len(units) >= 2 and units[-1][1] is None
                          and units[-2][0] in SHORT and units[-2][1] in (1, 2)
                          and sum(1 for u in units if u[1] is not None) == 1
                          and len(base) >= 2 and base[-1] not in "wxyk"
                          and base[-2] in "aeiou")
        if one_syll_short:
            return base + base[-1] + "ed"
        return base + "ed"
    return spell(phones, P)


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def candidates(word, cands, P):
    """[(spelling, accent)] for every pronunciation of the word."""
    out = []
    for ph, infl, acc, main in cands:
        sp = spell_word(ph, infl, P)
        # British pronunciations are non-rhotic; the spelling system keeps r,
        # so don't let a British pronunciation drop an r the word is written with.
        if acc == "UK" and sp.count("r") < word.count("r"):
            continue
        out.append((sp, acc, main))
    return out or [(spell_word(ph, infl, P), acc, main) for ph, infl, acc, main in cands]


def choose(word, cands, P, shorthand):
    """Pick the respelling: unchanged > shorthand > plausible > closest."""
    opts = candidates(word, cands, P)
    sh = shorthand.get(word, ())
    def key(o):
        sp, acc, main = o
        # Secondary pronunciations (weak forms like /tə/ for "to", rare
        # homographs) only win if they keep the word or give a shorthand.
        return (sp != word, sp not in sh, not main,
                edit_distance(sp, word), not plausible(sp), acc != "UK")
    sp, acc, _ = min(opts, key=key)
    return sp, acc


def score(words, P, shorthand, sh_weight, implausible_penalty=0.0):
    good = total = 0.0
    for w, c, cands in words:
        total += c
        spells = {sp for sp, _, _ in candidates(w, cands, P)}
        if w in spells:
            good += c
        elif spells & shorthand.get(w, set()):
            good += c * sh_weight
        elif implausible_penalty and not any(plausible(sp) for sp, _, main
                                             in candidates(w, cands, P) if main):
            good -= c * implausible_penalty
    return good / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmudict")
    ap.add_argument("freq")
    ap.add_argument("--uk", help="ipa-dict en_UK.txt; allows British pronunciations")
    ap.add_argument("--shorthand", help="word: alt alt ... file of familiar spellings")
    ap.add_argument("--shorthand-weight", type=float, default=0.75,
                    help="credit for landing on a shorthand spelling (1 = as good as unchanged)")
    ap.add_argument("--top", type=int, default=5000)
    ap.add_argument("--implausible-penalty", type=float, default=0.5,
                    help="cost of respelling a word into a non-English-looking string")
    ap.add_argument("--strict", action="store_true",
                    help="one fixed spelling per sound regardless of position")
    ap.add_argument("--report")
    ap.add_argument("--dump", help="write word<TAB>respelling for every word")
    ap.add_argument("--fix", action="append", default=[],
                    help="pin a parameter, e.g. --fix Z=z")
    a = ap.parse_args()

    us = load_cmudict(a.cmudict)
    uk = load_ipa_uk(a.uk) if a.uk else {}
    shorthand = load_shorthand(a.shorthand) if a.shorthand else {}
    allp = {}
    for d in (us, uk):
        for w, ps in d.items():
            allp.setdefault(w, []).extend(ps)

    freq = load_freq(a.freq)
    build_letter_pairs(w for w, _ in freq if w.isalpha() and w.isascii())
    words = []
    for w, c in freq:
        if not (w.isalpha() and w.isascii() and w in us):
            continue
        cands, seen = [], set()
        for acc, d in (("US", us), ("UK", uk)):
            for k, ph in enumerate(d.get(w, ())):
                if ph in seen:
                    continue
                seen.add(ph)
                cands.append((ph, find_inflection(w, ph, allp), acc, k == 0))
        words.append((w, c, cands))
        if len(words) >= a.top:
            break

    global PARAMS
    if a.strict:
        PARAMS = dict(STRICT_PARAMS)
    ok = strict_ok if a.strict else (lambda P: True)
    for f in a.fix:
        k, v = f.split("=", 1)
        v = {"True": True, "False": False}.get(v, v)
        assert v in PARAMS[k], f
        PARAMS[k] = [v]
    P = {k: v[0] for k, v in PARAMS.items()}
    P["_strict"] = a.strict
    assert ok(P), "starting point violates distinct-vowel constraint"
    sc = lambda P: score(words, P, shorthand, a.shorthand_weight, a.implausible_penalty)
    best = sc(P)
    print(f"start: {best:.4f}", file=sys.stderr)
    for rnd in range(4):
        improved = False
        for k, opts in PARAMS.items():
            for o in opts:
                if o == P[k]:
                    continue
                trial = dict(P, **{k: o})
                if not ok(trial):
                    continue
                s = sc(trial)
                if s > best + 1e-9:
                    best, P, improved = s, trial, True
                    print(f"round {rnd}: {k}={o!r} -> {best:.4f}", file=sys.stderr)
        # swap spellings between two vowels (single moves can't, due to the
        # distinct-vowel constraint)
        if a.strict:
            for x in DISTINCT_VOWELS:
                for y in DISTINCT_VOWELS:
                    if x >= y or P[x] == P[y]:
                        continue
                    trial = dict(P, **{x: P[y], y: P[x]})
                    if P[y] not in PARAMS[x] or P[x] not in PARAMS[y] or not ok(trial):
                        continue
                    s = sc(trial)
                    if s > best + 1e-9:
                        best, P, improved = s, trial, True
                        print(f"round {rnd}: swap {x}<->{y} -> {best:.4f}", file=sys.stderr)
        if not improved:
            break

    sens = {k: [(o, sc(dict(P, **{k: o})) if ok(dict(P, **{k: o})) else None)
                for o in opts] for k, opts in PARAMS.items()}

    chosen = [(w, c, choose(w, cands, P, shorthand)) for w, c, cands in words]
    total = sum(c for w, c, _ in chosen)
    same_tok = sum(c for w, c, (sp, _) in chosen if sp == w)
    sh_tok = sum(c for w, c, (sp, _) in chosen if sp != w and sp in shorthand.get(w, ()))
    bad = [(w, c, sp) for w, c, (sp, _) in chosen
           if sp != w and sp not in shorthand.get(w, ()) and not plausible(sp)]
    bad_tok = sum(c for _, c, _ in bad)
    lines = [f"# Phonetic spelling analysis (top {len(words)} words)", "",
             f"Sources: US = CMUdict{', UK = ipa-dict en_UK' if uk else ''}"
             f"{f', shorthand list (weight {a.shorthand_weight})' if shorthand else ''}.", "",
             f"- **Unchanged:** {same_tok/total:.1%} of running text",
             f"- **Respelled to a familiar shorthand:** {sh_tok/total:.1%} of running text",
             f"- **Respelled to something not kid-plausible:** {bad_tok/total:.1%} of running text"
             f" ({len(bad)} words; most common: {', '.join(f'{w}→{sp}' for w, _, sp in bad[:25])})",
             f"- **Objective score:** {best:.1%}", ""]
    for n in (100, 1000, len(words)):
        sub = chosen[:n]
        same = sum(1 for w, _, (sp, _) in sub if sp == w)
        lines.append(f"- Top {n} words: {same}/{len(sub)} unchanged ({same/len(sub):.1%})")
    lines += ["", "## Chosen parameters (with objective score for each alternative)", "",
              "| Parameter | Chosen | Alternatives |", "|---|---|---|"]
    for k, opts in sens.items():
        alts = ", ".join(f"{o}: {s:.1%}" if s is not None else f"{o}: (clashes)"
                         for o, s in opts if o != P[k])
        lines.append(f"| {k} | {P[k]} | {alts} |")
    lines += ["", "## Most frequent words that change", "",
              "| Word | New | Accent | Shorthand? |", "|---|---|---|---|"]
    shown = 0
    for w, _, (sp, acc) in chosen:
        if sp != w:
            lines.append(f"| {w} | {sp} | {acc} | {'yes' if sp in shorthand.get(w, ()) else ''} |")
            shown += 1
            if shown >= 400:
                break
    if a.dump:
        with open(a.dump, "w") as f:
            for w, _, (sp, _) in chosen:
                f.write(f"{w}\t{sp}\n")
    rep = "\n".join(lines) + "\n"
    if a.report:
        with open(a.report, "w") as f:
            f.write(rep)
    print(rep[:2500])


if __name__ == "__main__":
    main()
