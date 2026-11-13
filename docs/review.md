# Project review: before going public

**Summary.** The extension works, and its core principles hold up. Four
things need settling before a public launch:

1. **Who it's for.**
2. **Whether the rules' exceptions are part of the design.**
3. **Whether real readers find either mode easier to read.**
4. **A short list of open decisions**, including a licence for the code.

## What's working

- **Clear principles.** Every rule follows "keep a sound if any accent
  pronounces it", "don't change a vowel if some accent reads it as written"
  and "it should look like familiar casual spelling". That's why the simple
  mode still reads as English.
- **Two modes settle the tension** between keeping text familiar and making
  it fully phonetic, without forcing one compromise.
- **Mistakes found in review were fixed with tests.** *cot = caught*,
  *the → dha*, *st → street* and *ghost → ghoste* are all covered now.

## Risks

- **No stated audience.** Learners of English, people curious about spelling
  reform, teachers and dyslexic readers would each want different trade-offs:
  how much text may change, whether *wot* beats *what*, and whether a fully
  phonetic mode belongs in a browser at all. One sentence on who it's for
  would settle many open choices.
- **The rules have accumulated exceptions.** Each is defensible on its own:
  - ***wh → w*** overrides "keep any sound an accent pronounces".
  - ***old, told*** are exempt because southern British pronounces them close
    to the short *o*.
  - **Fully phonetic** writes both *th* sounds as *th*.
  - **Fully phonetic** writes unstressed "uh" with the same *a* as *cat*
    (*tha*, *kat*), so it isn't strictly one spelling per sound.

  Either document these as deliberate ("principles, except where a result
  reads badly") or decide which principle wins before the next case comes up.
- **No reader testing.** Every readability call so far is two people's
  judgement. Fully phonetic in particular may read much more slowly than
  expected.
- **The simple mode's benefit is modest.** With everything on, it changes
  18% of running text and raises the share readable from its letters from
  80% to about 87% ([analysis/decodability.md](analysis/decodability.md)).
  That metric is home-made and was refined along the way: it's good for
  comparing options, but not a figure to quote publicly.
- **Limited real-browser testing.** It has been tried by hand on a few pages
  and in a jsdom simulation, not across many sites.

## Open decisions

1. **Licence for the code.** The repository is public with no licence, so
   others can't legally reuse it. The word tables must stay CC BY-SA 4.0
   whichever licence is chosen ([THIRD_PARTY_NOTICES](../extension/THIRD_PARTY_NOTICES.txt)).
2. ***want → wont*.** It sounds the same as *wont* (habit), so the misreading
   check allows it, but readers will see *won't*. Recommended: exclude it.
3. ***was → wos* or *woz*.** *woz* is the familiar shorthand but spells that
   *s* as *z* in one word only.
4. **Long vowels inside words (option D).** Silent e would only work at the
   end of a word, and long vowels inside a word would use *ay/ee/oa/oo*
   (*oaver, payper, bayby*). This changes about 2% of running text.
5. **Fully phonetic at launch,** or keep it as an experimental option until
   it has been reader-tested.

## Suggested next steps

1. **Write down who it's for.** One sentence is enough; put it in the README.
2. **Run a reading test.** Five people read the same paragraph in each mode,
   timed. Ask what tripped them up.
3. **Make the open decisions above in one batch**, then submit to the store
   ([publishing.md](publishing.md)).
