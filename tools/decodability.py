#!/usr/bin/env python3
"""How well can you tell a word's pronunciation from its letters?

For the spelling at each level, every word is aligned to its pronunciations
(letter chunks <-> sounds). A "phonics rule" is learned for each chunk in
context: the sound it most often makes, weighted by word frequency. A word is
*decodable* if some pronunciation of it (any accent) follows those rules for
every chunk.

Context for a chunk = the letters, position in the word, and for single
vowel letters whether a silent-e / open syllable makes them long; for c and g
whether e/i/y follows. Unstressed vowels may reduce to schwa ("uh") without
counting as a miss, since stress isn't written.

Usage:
  decodability.py CMUDICT FREQLIST UK_IPA RESPELLINGS_JSON [--top N] [--report OUT.md]
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spelling_levels as sl  # noqa: E402
from phonetic_spelling import load_cmudict, load_freq, load_ipa_uk  # noqa: E402

SINGLE_VOWELS = set("aeiouy")
REDUCED_OK = {"AX", "IH", "ER"}   # an unstressed vowel may sound like "uh"


def context(chunks, i):
    """Phonics context for chunk i: (letters, position, detail)."""
    g = chunks[i][0]
    n = len(chunks)
    last_pron = n - 1
    while last_pron > 0 and chunks[last_pron][0] == "e" and not chunks[last_pron][1]:
        last_pron -= 1
    pos = "I" if i == 0 else ("F" if i >= last_pron else "M")
    prev = chunks[i - 1][0] if i else ""
    nxt = chunks[i + 1][0] if i + 1 < n else ""
    after = chunks[i + 2][0] if i + 2 < n else None
    vowel_chunks = [j for j, c in enumerate(chunks)
                    if c[0][:1] in SINGLE_VOWELS and not (j == n - 1 and c[0] == "e")]
    one_syllable = len(vowel_chunks) <= 1
    extra = ""
    if g == "e" and i == n - 1 and vowel_chunks and vowel_chunks != [i]:
        extra = "silent-e"                    # like, time, since
    elif g == "e" and i == n - 2 and nxt in ("d", "s") and len(vowel_chunks) > 1:
        extra = "ending"                      # happened, makes (not bed, yes)
    elif g in SINGLE_VOWELS:
        if not nxt:
            extra = "end-1syl" if one_syllable else "end"     # my / happy, go
        elif nxt[0] in SINGLE_VOWELS:
            extra = "hiatus"
        elif len(nxt) == 1 and after is not None and after[:1] in SINGLE_VOWELS:
            extra = "magic" if after == "e" and i + 2 == n - 1 else "open"
        elif (chunks[-1][0] == "e" and i < n - 2
              and all(not set(c[0]) & SINGLE_VOWELS for c in chunks[i + 1:-1])):
            extra = "magic"                   # final e across a cluster: paste, finde
        else:
            extra = "closed+" + nxt[:1]       # find / fin, old / doll
        if g == "a" and prev in ("w", "qu", "wh"):
            extra += ",after-w"               # was, want, what
    elif g in ("c", "g"):
        extra = "soft" if nxt[:1] in ("e", "i", "y") else "hard"
    elif g == "n":
        extra = "before-k" if nxt[:1] in ("k", "c", "g") else ""   # drink
    elif g in ("d", "s") and i == n - 1 and prev == "e":
        extra = "ending"
    return (g, pos, extra)


VOICING = {frozenset({("S",), ("Z",)}), frozenset({("TH",), ("DH",)})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmudict")
    ap.add_argument("freq")
    ap.add_argument("uk")
    ap.add_argument("respellings")
    ap.add_argument("--top", type=int, default=20000)
    ap.add_argument("--report")
    ap.add_argument("--common", action="store_true",
                    help="also respell the very common words (the extension option)")
    a = ap.parse_args()

    us, uk = load_cmudict(a.cmudict), load_ipa_uk(a.uk)
    table = json.load(open(a.respellings))
    n_levels = len(table["levels"])
    words = [(w, c) for w, c in load_freq(a.freq)
             if w.isalpha() and w.isascii() and (w in us or w in uk)][:a.top]
    prons = {w: sl.pronunciations(w, us, uk) for w, _ in words}
    total = sum(c for _, c in words)

    def spelling(w, level):
        """The word's spelling with levels 1..level on (same logic as the extension)."""
        if a.common and level > 0 and w in table.get("common", {}):
            return table["common"][w]
        entry = table["words"].get(w)
        if not entry:
            return w
        on = [e for e in entry["e"] if e[0] <= level]
        whole = [t for _, k, t in on if k == -1]
        if whole:
            return whole[-1]
        chunks = list(entry["c"])
        for _, k, t in on:
            chunks[k] = t
        return "".join(chunks) if on else w

    rows = []
    ambiguity_at = {}
    for level in [0] + list(range(1, n_levels + 1)):
        # align every word's current spelling to each of its pronunciations
        aligned = {}
        for w, c in words:
            sp = spelling(w, level)
            als = [al for al in (sl.align(sp, p) for p in prons[w]) if al]
            aligned[w] = als
        # learn the most common sound for each chunk-in-context
        counts = defaultdict(Counter)
        for w, c in words:
            for al in aligned[w]:
                for i in range(len(al)):
                    counts[context(al, i)][al[i][1]] += c / len(aligned[w])
        rule = {ctx: cnt.most_common(1)[0][0] for ctx, cnt in counts.items()}

        def ok(al):
            misses = []
            for i, (g, p) in enumerate(al):
                pred = rule[context(al, i)]
                if p == pred:
                    continue
                # stress isn't written: a vowel may be full or reduced to "uh"
                if (len(p) == 1 and len(pred) == 1 and p[0] in sl.VOWEL_PHONES
                        and pred[0] in sl.VOWEL_PHONES
                        and (p[0] in REDUCED_OK or pred[0] in REDUCED_OK)):
                    continue
                # o before l (old, told): close to the short o of "doll" in
                # London and southern England, so either reading fits an accent
                if (g == "o" and {p, pred} <= {("OW",), ("AA",), ("AO",)}
                        and i + 1 < len(al) and al[i + 1][0] in ("l", "ll")):
                    continue
                # -ed / -es endings follow the usual t/d/id, s/z/iz rule
                if context(al, i)[2] == "ending":
                    continue
                misses.append((context(al, i), p, pred))
            return misses

        dec_tok = dec_types = unal = near_tok = 0
        miss_by = defaultdict(lambda: [0, []])
        for w, c in words:
            if not aligned[w]:
                unal += c
                continue
            results = [ok(al) for al in aligned[w]]
            if any(not r for r in results):
                dec_tok += c
                dec_types += 1
            elif any(all(frozenset({p, pred}) in VOICING for _, p, pred in r) for r in results):
                near_tok += c                 # only s/z or th voicing differs
            else:
                best = min(results, key=len)
                ctx, p, pred = best[0]
                key = (ctx[0], " ".join(p) or "silent", " ".join(pred) or "silent")
                miss_by[key][0] += c
                if len(miss_by[key][1]) < 6:
                    miss_by[key][1].append(spelling(w, level))
        rows.append((level, dec_tok / total, dec_types / len(words), near_tok / total))
        ambiguity_at[level] = sorted(miss_by.items(), key=lambda kv: -kv[1][0])
        print(f"level {level}: decodable {dec_tok/total:.1%} of running text "
              f"(+{near_tok/total:.1%} voicing-only), {dec_types}/{len(words)} words",
              file=sys.stderr)

    if a.report:
        names = ["(normal spelling)"] + [lv["name"] for lv in table["levels"]]
        lines = ["# Decodability: can you tell the pronunciation from the letters?", "",
                 "| Level | | Running text readable from letters | + only s/z or th voicing off | Distinct words |",
                 "|---|---|---|---|---|"]
        for level, tok, typ, near in rows:
            lines.append(f"| {level} | {names[level]} | {tok:.1%} | {tok + near:.1%} | {typ:.1%} |")
        for level in (0, n_levels):
            lines += ["", f"## Biggest remaining misreadings at level {level}", "",
                      "| Letters | Actual sound | Usual sound | Running text | Examples |",
                      "|---|---|---|---|---|"]
            for (g, actual, usual), (tok, ex) in ambiguity_at[level][:25]:
                lines.append(f"| {g} | {actual} | {usual} | {tok/total:.2%} | {', '.join(ex)} |")
        Path(a.report).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
