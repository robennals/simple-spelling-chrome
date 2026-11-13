#!/usr/bin/env python3
"""Build a graded sequence of English spelling fixes.

Each *level* is one rule that respells a class of irregular spellings into a
familiar, casual form (night -> nite, though -> tho, head -> hed). Levels are
applied cumulatively; the browser extension lets the reader choose how many.

How a rule decides what to change:

1. Every pronunciation of a word (American from CMUdict, British from
   ipa-dict) is aligned letter-chunk by letter-chunk to its sounds, e.g.
   h|ea|d = HH|EH|D.
2. A rule looks at (chunk, sound) pairs, e.g. "ea pronounced EH -> e".
3. The rule only fires if it gives the *same* result for every pronunciation.
   So if any accent reads the word the way it's written (British /wɒt/ for
   "what"), it is left alone, and a sound any accent pronounces (the r in
   "car") is never dropped.
4. The result is rejected if it is a different-sounding real word
   (dough -> "do").

Usage:
  spelling_levels.py CMUDICT FREQLIST UK_IPA [--top N] [--json OUT] [--report OUT.md]
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from phonetic_spelling import load_cmudict, load_freq, load_ipa_uk  # noqa: E402

VOWEL_PHONES = {"AA", "AE", "AH", "AO", "AW", "AX", "AY", "EH", "ER", "EY", "IH",
                "IY", "OW", "OY", "UH", "UW"}
SHORT_PHONES = {"AE", "EH", "IH", "AA", "AH", "UH"}

# ---------------------------------------------------------------------------
# Pronunciations
# ---------------------------------------------------------------------------


def normalise(phones):
    """ARPAbet (with stress) -> (tuple of plain phones, n stressed vowels).

    Unstressed AH (schwa) becomes AX so rules can tell it from the vowel of
    "cup". British-only units are expanded to plain phones.
    """
    out, stressed = [], 0
    for p in phones:
        m = re.match(r"([A-Z]+)(\d?)$", p)
        base, st = m.group(1), m.group(2)
        if st in ("1", "2"):
            stressed += 1
        if base == "AH" and st == "0":
            out.append("AX")
        elif base == "PALM":
            out.append("AA")
        elif base in ("AAR", "IYR", "EHR", "UHR"):
            out += [{"AAR": "AA", "IYR": "IY", "EHR": "EH", "UHR": "UH"}[base], "R"]
        else:
            out.append(base)
    return tuple(out), stressed


def pronunciations(word, us, uk):
    """All distinct pronunciations, dropping unstressed weak forms (/tə/ for "to")."""
    prons = {}
    for d in (us, uk):
        for ph in d.get(word, ()):
            p, st = normalise(ph)
            prons[p] = max(prons.get(p, 0), st)
    if not prons:
        return []
    if max(prons.values()) == 0:
        return list(prons)
    return [p for p, st in prons.items() if st > 0]


# ---------------------------------------------------------------------------
# Letter-to-sound alignment
# ---------------------------------------------------------------------------

GRAPHEMES = """
b: B | -
bb: B
c: K | S | SH | CH
cc: K | K S
ch: CH | K | SH
ck: K
d: D | JH | T | -
dd: D
dg: JH
dge: JH
f: F | V
ff: F
g: G | JH | ZH
gg: G | JH
gh: G | F | -
gn: N
gu: G | G W
h: HH | -
j: JH | Y | HH
k: K
kn: N
l: L | -
ll: L
le: AX L | L
m: M
mb: M
mm: M
mn: M
n: N | NG
nn: N
ng: NG | NG G | N JH
p: P | -
ph: F | V
pp: P
ps: S
q: K
qu: K W | K
r: R | -
rr: R
rh: R
s: S | Z | SH | ZH | -
sc: S | S K
sch: SH | S K
sh: SH
ss: S | SH | Z
t: T | SH | CH | -
tch: CH
th: TH | DH | T
tt: T
thm: DH AX M | TH AX M
ti: SH
ci: SH
si: ZH | SH
v: V
w: W | -
wh: W | HH | HH W
wr: R
x: K S | G Z | Z | K SH
y: Y | IY | AY | IH | AX
z: Z | S | ZH
zz: Z | T S
xc: K S
tion: SH AX N | CH AX N
sion: ZH AX N | SH AX N
ssion: SH AX N
cian: SH AX N
tious: SH AX S
cious: SH AX S
ssi: SH
eau: Y UW | OW
a: AE | EY | AA | AO | AX | EH | IH | ER | AH | -
ai: EY | EH | AX | IH | AY | AE
ay: EY | IY | EH
au: AO | AA | AE | EY | OW
aw: AO | AA
ae: EH | IY | EY
e: EH | IY | IH | AX | EY | -
ea: IY | EH | EY | IY AX | IH | AX
ee: IY | IH
ei: EY | IY | AY | EH | IH | AX
eigh: EY | AY
ey: EY | IY | AY
eu: UW | Y UW
ew: UW | Y UW | OW
eo: IY | EH | IY AX | IY OW
eye: AY
i: IH | AY | IY | AX | Y | -
ie: IY | AY | IH | EH | IY AX | AY AX | IY EH
igh: AY
o: AA | OW | AH | UW | UH | AX | AO | IH | W AH | -
oa: OW | AO
oe: OW | UW | AH
oi: OY | W AA
oo: UW | UH | AH | OW
ou: AW | UW | AH | UH | OW | AO | AX
ough: OW | UW | AH F | AO F | AA F | AW | AO | AA
augh: AO | AE F | AA F | AA
ow: AW | OW
oy: OY
u: AH | UW | Y UW | UH | AX | IH | EH | - | W | Y AX
ue: UW | Y UW | -
ui: UW | IH | AY | W IH
uy: AY
ar: AA R | AO R | ER | EH R | AX R | AA
er: ER | EH R | AX R | IH R | AA R
ir: ER | AY R | IH R
or: AO R | ER | OW R | AO | AX R
ur: ER | UH R | Y UH R | Y ER
ear: IY R | ER | EH R | AA R | IH R
eer: IY R | IH R
ere: IY R | EH R | ER
air: EH R
are: EH R | AA R | ER
our: AW ER | AO R | ER | UH R | AW R | AW AX | OW R | AO
oor: AO R | UH R | OW R | AO
ure: Y UH R | UH R | ER | Y ER | AO R | AO
ore: AO R | OW R | AO
ire: AY ER | AY R | AY AX
oar: AO R | OW R | AO
"""

G2P = {}
for line in GRAPHEMES.strip().splitlines():
    g, rhs = line.split(":")
    G2P[g.strip()] = [() if alt.strip() == "-" else tuple(alt.split())
                      for alt in rhs.split("|")]
MAX_G = max(len(g) for g in G2P)


def align(word, phones):
    """Cheapest split of word into (grapheme, phones) chunks, or None."""
    n, m = len(word), len(phones)

    @lru_cache(maxsize=None)
    def best(i, j):
        if i == n:
            return (0.0, ()) if j == m else None
        res = None
        for L in range(1, min(MAX_G, n - i) + 1):
            g = word[i:i + L]
            for p in G2P.get(g, ()):
                if phones[j:j + len(p)] != p:
                    continue
                cost = 1.0
                if not p:
                    # silent letters: final e is free-ish, r costs more
                    cost += 0.1 if g == "e" else (1.5 if g == "r" else 0.6)
                sub = best(i + L, j + len(p))
                if sub is not None and (res is None or cost + sub[0] < res[0]):
                    res = (cost + sub[0], ((g, p),) + sub[1])
        return res

    r = best(0, 0)
    return list(r[1]) if r else None


# ---------------------------------------------------------------------------
# Chunk helpers used by rules
# ---------------------------------------------------------------------------
# A chunk is [text, phones, original_grapheme]. Rules edit text.

VOWEL_LETTERS = set("aeiouy")


def text_of(chunks):
    return "".join(c[0] for c in chunks)


def is_cons_chunk(c):
    return bool(c[1]) and c[1][0] not in VOWEL_PHONES and c[0] and c[0][0] not in VOWEL_LETTERS


def starts_vowel(c):
    """Chunk is a pronounced vowel (silent letters don't count)."""
    return bool(c[0]) and bool(c[1]) and c[1][0] in VOWEL_PHONES


def double_after(chunks, i):
    """After making chunk i a short vowel, double a lone following consonant
    if a vowel follows it (heavy -> hevvy, ready -> reddy)."""
    if i + 2 >= len(chunks):
        return True
    nxt, after = chunks[i + 1], chunks[i + 2]
    if not (is_cons_chunk(nxt) and len(nxt[0]) == 1 and starts_vowel(after)):
        return True
    t = nxt[0]
    if t in "hwyxj":
        return True
    if nxt[1] == ("Z",) and t == "s":
        nxt[0] = "zz"
    elif t in ("c", "k"):
        nxt[0] = "ck"
    else:
        nxt[0] = t * 2
    return True


MAGIC_SUFFIXES = {"", "s", "ly", "ness", "ful", "ment"}


def make_long(chunks, i, letter, open_spelling=None):
    """Spell chunk i as a single vowel letter made long with a silent e
    (great -> grate). In an open syllable use open_spelling (default: the
    bare letter, as in ti|ger). Returns False if the word shape doesn't fit."""
    rest = chunks[i + 1:]
    if not rest:
        return False
    if rest[0][0] == "s" and len(rest) == 1:
        return False                       # sighs: don't make "sise"
    if is_cons_chunk(rest[0]) and len(rest[0][0]) == 1:
        tail = text_of(rest[1:])
        if tail in MAGIC_SUFFIXES:
            chunks[i][0] = letter
            rest[0][0] = rest[0][0] + "e"
            return True
        if starts_vowel(rest[1]) if len(rest) > 1 else False:
            chunks[i][0] = open_spelling or letter   # open syllable: nay|bor
            return True
    return False


# ---------------------------------------------------------------------------
# Rules. Each returns True if it changed the chunks.
# ---------------------------------------------------------------------------

def r_ough(ch):
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if g == "ough":
            end = i == len(ch) - 1
            new = {("OW",): "o", ("UW",): "u", ("AH", "F"): "uff" if end else "uf",
                   ("AO", "F"): "off" if end else "of", ("AA", "F"): "off" if end else "of",
                   ("AW",): "ow"}.get(p)
        elif g == "augh" and p in (("AE", "F"), ("AA", "F")):
            new = "aff" if i == len(ch) - 1 else "af"
        else:
            continue
        if new and t == g:
            ch[i][0] = new
            changed = True
    return changed


SIGHT = {
    "of": "ov", "said": "sed", "says": "sez", "does": "duz", "friend": "frend",
    "friends": "frends", "friendly": "frendly", "friendship": "frendship",
    "one": "wun", "once": "wunce", "anyone": "ennywun", "someone": "sumwun",
    "everyone": "evrywun", "women": "wimmin", "busy": "bizzy", "business": "bizness",
    "any": "enny", "many": "menny", "anybody": "ennybody", "anything": "ennything",
    "anyway": "ennyway", "anywhere": "ennyware", "their": "thare", "theirs": "thares", "people": "peeple",
    "sugar": "shugar", "sure": "shur", "are": "ar", "were": "wer",
    "who": "hoo", "whom": "hoom", "whose": "hooz", "could": "cud", "would": "wud",
    "should": "shud", "couldn": "cudn", "wouldn": "wudn", "shouldn": "shudn",
    "colonel": "kernel", "yacht": "yot",
}


def r_silent(ch):
    """Drop silent consonants that don't follow a regular pattern."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if p or t != g or g not in ("b", "d", "h", "l", "n", "p", "s", "t", "w", "c", "g"):
            continue
        prev = ch[i - 1][0] if i else ""
        nxt = ch[i + 1][0] if i + 1 < len(ch) else ""
        if prev.endswith(g) or nxt.startswith(g):
            continue                         # half of a doubled letter
        # regular silent letters: talk, half, calm, folk; listen, castle
        if g == "l" and prev in ("a", "o") and nxt[:1] in ("k", "f", "m"):
            continue
        if g == "t" and prev == "s" and nxt in ("le", "en", "e"):
            continue
        if g == "g" and nxt == "n":
            continue
        if g == "h" and (i == len(ch) - 1 or prev[-1:] in VOWEL_LETTERS):
            continue                         # oh, ah, yeah
        if g == "t" and i == len(ch) - 1:
            continue                         # ballet, buffet (French loans)
        ch[i][0] = ""
        double_after(ch, i - 1) if i and ch[i - 1][1] and ch[i - 1][1][0] in SHORT_PHONES else None
        changed = True
    for i, (t, p, g) in enumerate(ch):
        if g == "mn" and t == "mn" and i == len(ch) - 1:      # autumn
            ch[i][0] = "m"
            changed = True
    return changed


def r_ea(ch):
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t != g:
            continue
        if g == "ea" and p == ("EH",):
            ch[i][0] = "e"
            double_after(ch, i)
            changed = True
        elif g == "ea" and p == ("EY",):
            changed |= make_long(ch, i, "a")
        elif g == "ear" and p in (("ER",), ("ER", "R")):
            ch[i][0] = "er"
            changed = True
        elif g == "ear" and p in (("AA", "R"), ("AA",)):
            ch[i][0] = "ar"
            changed = True
        elif g == "ear" and p in (("EH", "R"),):
            # like care / caring / cares: bear -> bare, wearing -> waring,
            # pears -> pares; before other consonants use air
            rest = ch[i + 1:]
            if not rest:
                ch[i][0] = "are"
            elif starts_vowel(rest[0]):
                ch[i][0] = "ar"
            elif text_of(rest) == "s":
                ch[i][0] = "are"
            else:
                ch[i][0] = "air"
            changed = True
    return changed


def r_short_u(ch):
    """o / ou / oo pronounced like 'cup' -> u (love -> luv, young -> yung)."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t != g or p != ("AH",) or g not in ("o", "ou", "oo"):
            continue
        ch[i][0] = "u"
        # drop a silent e that would now make it look long: love -> luv,
        # some|thing -> sumthing
        if (i + 2 < len(ch) and ch[i + 2][2] == "e" and not ch[i + 2][1]
                and is_cons_chunk(ch[i + 1])
                and (i + 3 == len(ch) or not starts_vowel(ch[i + 3]))):
            ch[i + 2][0] = ""
        else:
            double_after(ch, i)
        changed = True
    return changed


def r_igh(ch):
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == g and g in ("igh", "eigh") and p == ("AY",):
            if i == len(ch) - 1:
                ch[i][0] = "i"
                changed = True
            else:
                changed |= make_long(ch, i, "i")
    return changed


def r_ey(ch):
    """eigh / ey / ei pronounced like 'day' -> a (eight -> ate, they -> thay)."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == g and g in ("eigh", "ey", "ei") and p == ("EY",):
            if i == len(ch) - 1:
                ch[i][0] = "ay"
                changed = True
            else:
                changed |= make_long(ch, i, "a", "ay")
    return changed


def r_ought(ch):
    """ough / augh sounding like 'saw' -> aw (thought -> thawt, caught -> cawt)."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == g and g in ("ough", "augh") and p in (("AO",), ("AA",)):
            ch[i][0] = "aw"
            changed = True
    return changed


def r_ph(ch):
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == "ph" and p == ("F",):
            ch[i][0] = "f"
            changed = True
    return changed


def r_initial(ch):
    """Silent first letters: knife -> nife, write -> rite, gnome -> nome,
    rhythm -> rythm, ghost -> gost. gh keeps its h before e/i/y, where it
    stops the g sounding like j (ghetto, not "getto")."""
    if len(ch) > 1 and ch[1][0] == "ow":
        return False                         # know -> "now" would misread
    if not ch or ch[0][2] != ch[0][0]:
        return False
    first = ch[0][0]
    if first in ("kn", "wr", "gn"):
        ch[0][0] = first[1]
        return True
    if first == "rh" or (first == "gh" and len(ch) > 1 and ch[1][0][:1] in ("a", "o", "u")):
        ch[0][0] = first[0]
        return True
    return False


def r_ch(ch):
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == "ch" and p == ("K",):
            prev_short = i and ch[i - 1][1] and ch[i - 1][1][0] in SHORT_PHONES
            nxt_vowel = i + 1 < len(ch) and starts_vowel(ch[i + 1])
            ch[i][0] = "ck" if prev_short and nxt_vowel else "k"
            changed = True
        elif t == "ch" and p == ("SH",):
            ch[i][0] = "sh"
            changed = True
        elif t == "sch" and p == ("S", "K"):
            ch[i][0] = "sk"                  # school -> skool
            changed = True
    return changed


def r_oo(ch):
    """o / ou / oe / ui pronounced like 'food' -> oo (move -> moov)."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t != g or p != ("UW",) or g not in ("o", "ou", "oe", "ui"):
            continue
        ch[i][0] = "oo"
        if i + 1 < len(ch) and ch[i + 1][0] == "s" and ch[i + 1][1] == ("Z",):
            ch[i + 1][0] = "z"                   # lose -> looz, losing -> loozing
        if (i + 2 == len(ch) - 1 and ch[-1][2] == "e" and not ch[-1][1]
                and is_cons_chunk(ch[i + 1])):
            ch[-1][0] = ""                       # move -> moov
        changed = True
    return changed


def r_ow(ch):
    """ow sounding like 'know' -> o at the end, oa before a consonant, so ow
    always sounds like 'now' (know -> no, knowing -> noing, own -> oan, bowl -> boal)."""
    for i, (t, p, g) in enumerate(ch):
        if not (t == g == "ow" and p == ("OW",)):
            continue
        rest = ch[i + 1:]
        if not rest or text_of(rest) in ("s", "ly"):
            ch[i][0] = "o"                   # know -> no, shows -> shos, slowly
            return True
        if is_cons_chunk(rest[0]):
            ch[i][0] = "oa"                  # own -> oan, known -> noan
            return True
        ch[i][0] = "o"                       # knowing -> noing, like go -> going
        return True
    return False


def r_book(ch):
    """oo / ou sounding like 'book' -> u, as in put, push, full
    (book -> buk, good -> gud, look -> luk)."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == g and g in ("oo",) and p == ("UH",):
            ch[i][0] = "u"
            changed = True
    return changed


def r_ere(ch):
    """ere sounding like 'care' -> are, so ere always sounds like 'here'
    (there -> thare, where -> whare)."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == g == "ere" and p in (("EH", "R"),):
            ch[i][0] = "are"
            changed = True
    return changed


LONG_PHONES = {"EY": "a", "IY": "e", "AY": "i", "OW": "o", "UW": "u"}


def r_cluster_e(ch):
    """A long vowel before two consonants at the end takes a silent e, like
    paste and change: find -> finde, child -> childe, most -> moste, kinds -> kindes.

    Not o before l (old, told, bolt): in London and much of southern England
    that vowel sounds close to the short o of "doll", so the spelling already
    fits an accent. The dictionaries don't record this, so it's listed here."""
    for i, (t, p, g) in enumerate(ch):
        if not (len(t) == 1 and t == g and p and p[0] in LONG_PHONES
                and LONG_PHONES[p[0]] == t):
            continue
        rest = ch[i + 1:]
        if t == "o" and rest and rest[0][0] in ("l", "ll"):
            return False                     # old, told, bolt
        if len(rest) == 2 and rest[-1][0] == "s":
            return False                     # rolls, signs: one consonant + plural s
        plural = rest and rest[-1][0] == "s" and len(rest) == 3
        cons = rest[:-1] if plural else rest
        # counted by letters, so a casual variant that drops a sound
        # ("mos" for most) still has the same cluster
        if len(cons) == 2 and all(c[0] and not set(c[0]) & VOWEL_LETTERS
                                  and (c[1] or c[0] == c[2]) for c in cons):
            cons[-1][0] = cons[-1][0] + "e"
            return True
        return False
    return False


def r_wh(ch):
    """Drop the h of wh: what -> wat, when -> wen, which -> wich; where wh
    sounds like h, write h: whole -> hole. A deliberate choice: Scottish,
    Irish and some American speakers still say "hw"."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == g == "wh":
            ch[i][0] = "h" if p == ("HH",) else "w"
            changed = True
    return changed


def r_wa(ch):
    """a after w / qu sounding like 'hot' -> o, so a never needs a special
    rule after w (what -> wot, watch -> wotch, want -> wont, was -> wos).
    Not where the vowel is long: before r or l + consonant (war, walk, wall)
    or in an open syllable (water)."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if not (t == g == "a" and i > 0 and p in (("AA",), ("AH",), ("AO",))
                and ch[i - 1][2] in ("w", "wh", "qu")):
            continue
        nxt = ch[i + 1] if i + 1 < len(ch) else None
        after = ch[i + 2] if i + 2 < len(ch) else None
        if nxt and nxt[0][:1] == "r":
            continue                         # war, warm
        if nxt and nxt[0][:1] == "l" and (after is None or not starts_vowel(after)):
            continue                         # walk, wall (but wallet is fine)
        if nxt and len(nxt[0]) == 1 and after is not None and starts_vowel(after):
            continue                         # water: open syllable
        ch[i][0] = "o"
        changed = True
    return changed


def r_ui(ch):
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if t == g == "ui" and p == ("IH",):
            ch[i][0] = "i"
            changed = True
    return changed


def _ve(ch):
    return (len(ch) >= 3 and ch[-1][2] == "e" and not ch[-1][1] and ch[-2][0] == "v"
            and ch[-3][1] and ch[-3][1][0] in SHORT_PHONES and len(ch[-3][0]) == 1)


def n_vowels(ch):
    return sum(1 for c in ch if c[1] and c[1][0] in VOWEL_PHONES)


def r_ve(ch):
    """have -> hav, give -> giv, forgive -> forgiv: e after v, short stressed vowel."""
    if _ve(ch) and (n_vowels(ch) == 1 or text_of(ch).endswith(("give", "live"))):
        ch[-1][0] = ""
        return True
    return False


def r_ive(ch):
    """The -ive suffix: active -> activ, massive -> massiv."""
    if _ve(ch) and n_vowels(ch) > 1 and not text_of(ch).endswith(("give", "live")):
        ch[-1][0] = ""
        return True
    return False


def r_syncope(ch):
    """Vowels nobody pronounces: every -> evry, different -> diffrent."""
    changed = False
    for i, (t, p, g) in enumerate(ch):
        if (not p and t == g and g in ("a", "e", "i", "o", "u") and 0 < i < len(ch) - 1
                and is_cons_chunk(ch[i - 1]) and is_cons_chunk(ch[i + 1])):
            if g == "e" and i + 2 == len(ch) and ch[-1][0] in ("d", "s", "n", "r"):
                continue                     # called, times, taken: endings
            if g == "e" and i >= 2 and ch[i - 2][1] and ch[i - 2][1][-1] in (
                    "EY", "IY", "AY", "OW", "UW", "AW", "OY"):
                continue                     # magic e: makes, lately, useless
            if g == "a" and ch[i + 1][0] == "ll":
                continue                     # basically, not "basiclly"
            ch[i][0] = ""
            changed = True
    return changed


LEVELS = [
    ("ough", "ough/augh by sound", "though → tho, through → thru, enough → enuff, laugh → laff", r_ough),
    ("sight", "Common irregular words", "of → ov, said → sed, does → duz, one → wun, could → cud", None),
    ("silent", "Unexpected silent letters", "debt → det, island → iland, hour → our, answer → anser", r_silent),
    ("ea", "ea that isn't 'ee'", "head → hed, great → grate, learn → lern, heart → hart", r_ea),
    ("short_u", "o / ou sounding like 'cup'", "love → luv, mother → muther, young → yung, blood → blud", r_short_u),
    ("igh", "igh → i", "night → nite, light → lite, high → hi, height → hite", r_igh),
    ("ey", "ei / ey / eigh sounding like 'day'", "they → thay, eight → ate, weigh → way", r_ey),
    ("ought", "ough / augh sounding like 'saw'", "thought → thawt, caught → cawt, daughter → dawter", r_ought),
    ("ph", "ph → f", "phone → fone, photo → foto, graph → graf", r_ph),
    ("initial", "Silent letters at the start: kn, wr, gn, gh, rh", "write → rite, knife → nife, ghost → gost, rhythm → rythm", r_initial),
    ("ch", "ch sounding like k or sh", "school → skool, stomach → stomak, machine → mashine", r_ch),
    ("wh", "wh → w", "what → wat, when → wen, which → wich, white → wite", r_wh),
    ("wa", "a after w sounding like 'hot'", "what → wot, want → wont, watch → wotch, wash → wosh", r_wa),
    ("ui", "ui sounding like 'it'", "build → bild, guilt → gilt", r_ui),
    ("oo", "o / ou sounding like 'food'", "move → moov, soup → soop, shoe → shoo", r_oo),
    ("ow", "ow sounding like 'know'", "know → no, knowing → noing, own → oan, bowl → boal", r_ow),
    ("book", "oo sounding like 'book'", "book → buk, good → gud, look → luk", r_book),
    ("ere", "ere sounding like 'care'", "there → thare, where → whare", r_ere),
    ("cluster", "Long vowel before two consonants", "find → finde, child → childe, most → moste, ghost → ghoste", r_cluster_e),
    ("ve", "Short vowel + ve", "have → hav, give → giv", r_ve),
    ("ive", "The -ive ending", "active → activ, positive → positiv", r_ive),
    ("syncope", "Unpronounced vowels", "every → evry, different → diffrent", r_syncope),
]
# Levels kept in a fixed place regardless of their surprise score.
FIRST = ["sight"]
# (later, earlier): "initial" must follow "ow" so know -> kno -> no.
MUST_FOLLOW = [("initial", "ow"), ("wh", "ere")]   # where -> whare -> ware
LAST = ["ive", "syncope"]

# Very common words left alone by default. The extension's "common words"
# option respells them, consistently with the levels (oo = the vowel of food).
COMMON = {"to": "too", "do": "doo", "two": "too", "into": "intoo", "onto": "ontoo",
          "you": "yoo", "your": "yor", "yours": "yors", "yourself": "yorself",
          "yourselves": "yorselvz", "youth": "yooth"}
KEEP = set(COMMON) | {"i", "a", "the"}

# Dictionary entries too obscure to block a respelling as a "different word":
# wat (Scots for wet), wy (the letter y).
OBSCURE = {"wat", "wy"}

SAMPLE = ("I thought we should go out tonight, but my friend said she was too tired "
          "to leave the house. Maybe we could meet another time when the weather is "
          "nice and everyone feels better. She has some money, though, and we have "
          "enough to buy a phone. Look at that great school building over there!")


# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmudict")
    ap.add_argument("freq")
    ap.add_argument("uk")
    ap.add_argument("--top", type=int, default=20000)
    ap.add_argument("--wordlist", default="/usr/share/dict/words",
                    help="word list where proper nouns are capitalised")
    ap.add_argument("--json")
    ap.add_argument("--report")
    a = ap.parse_args()

    us, uk = load_cmudict(a.cmudict), load_ipa_uk(a.uk)
    lower, capital = set(), set()
    with open(a.wordlist) as f:
        for line in f:
            w = line.strip()
            (lower if w.islower() else capital).add(w.lower())
    proper = capital - lower
    words = [(w, c) for w, c in load_freq(a.freq)
             if w.isalpha() and w.isascii() and (w in us or w in uk)][:a.top]
    total = sum(c for _, c in words)
    pron_cache = {w: pronunciations(w, us, uk) for w, _ in words}
    # real words a respelling must not turn into (unless they sound the same):
    # dictionary words that people actually use. Archaic entries ("childe")
    # and subtitle slang or abbreviations ("wat", "wy") don't count.
    ranked = [w for w, _ in load_freq(a.freq)]
    in_use, top5k = set(ranked), set(ranked[:5000])
    real = {}
    for w in lower & in_use:
        if len(w) <= 2 and w not in top5k:
            continue                          # letter names, abbreviations: wy
        if w in OBSCURE:
            continue
        if w in us or w in uk:
            real[w] = set(pronunciations(w, us, uk))

    # P(sound | grapheme) for ordering by how surprising a spelling is
    gp = Counter()
    gcount = Counter()
    aligned = {}
    unaligned = []
    for w, c in words:
        als = []
        for p in pron_cache[w]:
            al = align(w, p)
            if al:
                als.append(al)
        aligned[w] = als
        if not als:
            unaligned.append((w, c))
            continue
        for g, p in als[0]:
            gp[(g, p)] += c
            gcount[g] += c

    def surprise(g, p):
        return -math.log2(gp[(g, p)] / gcount[g]) if gcount[g] and gp[(g, p)] else 10.0

    def run(levels):
        """Apply levels cumulatively. Returns (per-level stats, word history,
        word edits). An edit is (level_index, chunk_index, new_text) against
        the word's letter chunks, or chunk_index -1 for a whole-word
        replacement, so the extension can apply any subset of levels."""
        state = {w: [[[g, p, g] for g, p in al] for al in aligned[w]] for w, _ in words}
        current = {w: w for w, _ in words}
        history = defaultdict(list)          # word -> [(level_index, spelling)]
        edits = defaultdict(list)            # word -> [(level_index, chunk, text)]
        level_stats = []
        freq = dict(words)
        for li, (lid, name, desc, fn) in enumerate(levels):
            changed_words = []
            surprises = []
            if fn is None:
                # hand-picked words: applied whether or not they're in the
                # frequency list (couldn, as in couldn't, isn't)
                for w, new in SIGHT.items():
                    if w in KEEP or w == new:
                        continue
                    if w in state:
                        state[w] = [[[new, (), w]] for _ in state[w]]
                    current[w] = new
                    history[w].append((li, new))
                    edits[w].append((li, -1, new))
                    changed_words.append((w, freq.get(w, 0), new))
                    surprises.append((10.0, freq.get(w, 0)))
                tok = sum(c for _, c, _ in changed_words)
                level_stats.append((lid, name, desc, changed_words, tok, 10.0))
                continue
            for w, c in words:
                if w in KEEP or w in proper or not state[w]:
                    continue
                trial = [[list(x) for x in chunks] for chunks in state[w]]
                results = set()
                ok = True
                for chunks in trial:
                    before = text_of(chunks)
                    if not fn(chunks) or text_of(chunks) == before:
                        ok = False
                        break
                    results.add(text_of(chunks))
                if not ok or len(results) != 1:
                    continue
                new = results.pop()
                if new in real and not (real[new] & set(pron_cache[w])):
                    continue                      # would read as a different word
                for orig, tr in zip(state[w], trial):
                    diff = [x for x, y in zip(orig, tr) if x[0] != y[0]]
                    surprises += [(surprise(x[2], tuple(x[1])), c) for x in diff[:1]]
                edits[w] += [(li, k, y[0]) for k, (x, y) in enumerate(zip(state[w][0], trial[0]))
                             if x[0] != y[0]]
                state[w] = trial
                current[w] = new
                history[w].append((li, new))
                changed_words.append((w, c, new))
            tok = sum(c for _, c, _ in changed_words)
            mean_s = (sum(x * c for x, c in surprises) / sum(c for _, c in surprises)
                      if surprises else 0)
            level_stats.append((lid, name, desc, changed_words, tok, mean_s))
        base = {w: [g for g, _ in aligned[w][0]] for w in edits if aligned.get(w)}
        return level_stats, history, (edits, base)

    # Pass 1 scores each level; pass 2 runs them most-confusing first.
    first_stats, _, _ = run(LEVELS)
    score = {st[0]: st[5] for st in first_stats}
    def rank(lv):
        lid = lv[0]
        if lid in FIRST:
            return (0, FIRST.index(lid))
        if lid in LAST:
            return (2, LAST.index(lid))
        return (1, -score[lid])
    levels = sorted(LEVELS, key=rank)
    for later, earlier in MUST_FOLLOW:
        ids = [lv[0] for lv in levels]
        if ids.index(later) < ids.index(earlier):
            lv = levels.pop(ids.index(later))
            levels.insert([x[0] for x in levels].index(earlier) + 1, lv)
    level_stats, history, (edits, base) = run(levels)
    for li, (lid, _, _, cw, tok, sc) in enumerate(level_stats, 1):
        print(f"level {li} {lid}: {len(cw)} words, {tok/total:.2%} of tokens, "
              f"surprise {sc:.1f}", file=sys.stderr)

    def render(text, level):
        def f(m):
            w = m.group(0)
            sp = w.lower()
            for li, s2 in history.get(w.lower(), ()):
                if li < level:
                    sp = s2
            if w[0].isupper():
                sp = sp[:1].upper() + sp[1:]
            return sp
        return re.sub(r"[A-Za-z]+", f, text)

    if a.json:
        out = {
            "levels": [{"id": lid, "name": name, "examples": desc}
                       for lid, name, desc, *_ in level_stats],
            "common": COMMON,
            # c: the word's letter chunks; e: [level, chunk index (-1 = whole
            # word), new text] in level order
            "words": {w: {"c": base.get(w, []), "e": [[li + 1, k, t] for li, k, t in e]}
                      for w, e in edits.items()},
        }
        with open(a.json, "w") as f:
            json.dump(out, f, separators=(",", ":"), ensure_ascii=False)

    if a.report:
        lines = [f"# Spelling levels (top {len(words)} words)", "",
                 "| # | Level | Words changed | % of running text | Surprise (bits) | Most common |",
                 "|---|---|---|---|---|---|"]
        cum = 0
        for i, (lid, name, desc, cw, tok, s) in enumerate(level_stats, 1):
            cum += tok
            ex = ", ".join(f"{w} → {n}" for w, _, n in cw[:12])
            lines.append(f"| {i} | {name} | {len(cw)} | {tok/total:.1%} (cum. {cum/total:.1%}) | {s:.1f} | {ex} |")
        lines += ["", "## Sample text at each level", ""]
        for lv in range(0, len(level_stats) + 1, 1):
            label = "Level 0 (unchanged)" if lv == 0 else f"Level {lv}: {level_stats[lv-1][1]}"
            lines += [f"**{label}**", "", "> " + render(SAMPLE, lv), ""]
        lines += ["", f"Words that couldn't be aligned to a pronunciation (left unchanged): "
                  f"{len(unaligned)} — most common: " + ", ".join(w for w, _ in unaligned[:40])]
        with open(a.report, "w") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
