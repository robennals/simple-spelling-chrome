# Simplified Spelling Rules (draft)

**Summary.** Spelling fixes come as a sequence of **levels**. Each level is
one rule that turns a class of confusing spellings into a familiar, casual
spelling of the kind kids and texters already use: *tho, thru, nite, luv, hed,
skool, fone*. The extension has a single on/off switch that applies every
level, plus the very common words. Levels are listed with the most confusing
spellings first.

> I thawt we shud go out tonite, but my frend sed she wos too tired to leave
> the house. Maybe we cud meet anuther time wen the wether is nice and
> evrywun feels better. She has sum munney, tho, and we hav enuff to buy a
> fone. Luk at that grate skool bilding over thare!

With every level on, 18.4% of running text is respelled. Per-level counts,
examples and sample text are in [analysis/levels.md](analysis/levels.md).

## Principles

- **Only fix spellings that are actually odd.** Each word is split into
  letter-chunks matched to its sounds (*h|ea|d* = /h ɛ d/). A rule fires only
  on a chunk that makes an unusual sound, such as *ea* sounding like *bed*.
- **Any reasonable accent is enough to keep a spelling.** A rule fires only
  if *every* American and British pronunciation of the word agrees it's odd.
  So *what* stays as it is, because British says /wɒt/. A sound any accent
  pronounces is never dropped (the r in *car* stays), and words with two
  pronunciations, like *live*, are left alone.
- **One deliberate exception: *wh* becomes *w*** (*what → wat, when → wen*),
  even though Scottish, Irish and some American speakers still say "hw".
  It's rare enough not to be worth an extra spelling.
- **Spelling can depend on position, as long as it's consistent.** Results
  use the normal English patterns: silent e (*grate, nite*), doubled
  consonants after a short vowel (*reddy, hevvy*), *ck* (*stomak*).
- **Results must be instantly readable.** A respelling is rejected if it
  would read as a *different-sounding* real word (*dough → do* is blocked;
  *knew → new* is fine, because they sound the same). There's no
  offensive-word filter: *come → cum* and *country → cuntry* are the obvious
  casual spellings, so they're kept.
- **Endings and names are left alone.** *-ed* and *-s* keep their spelling.
  Names are skipped: words the dictionary only lists capitalised, and on the
  page, any capitalised word that doesn't start a sentence.

## Levels

Levels are ordered by how surprising the original spelling is. That's measured
as how rarely those letters make that sound across all English words, in bits:
higher means more confusing. The hand-picked common words come first, and the
two most aggressive levels come last.

| # | Level | Examples | Running text |
|---|---|---|---|
| 1 | Common irregular words | of → ov, said → sed, does → duz, one → wun, could → cud | 4.4% |
| 2 | a after w sounding like 'hot' | what → wot, want → wont, watch → wotch, wash → wosh | 2.2% |
| 3 | Unexpected silent letters | debt → det, island → iland, hour → our, answer → anser | 0.2% |
| 4 | ough/augh by sound | though → tho, through → thru, enough → enuff, laugh → laff | 0.2% |
| 5 | ch sounding like k or sh | school → skool, stomach → stomak, machine → mashine | 0.1% |
| 6 | o / ou sounding like 'cup' | love → luv, mother → muther, young → yung, blood → blud | 1.9% |
| 7 | ea that isn't 'ee' | head → hed, great → grate, learn → lern, heart → hart | 0.7% |
| 8 | o / ou sounding like 'food' | move → moov, soup → soop, shoe → shoo | 0.3% |
| 9 | ough / augh sounding like 'saw' | thought → thawt, caught → cawt, daughter → dawter | 0.2% |
| 10 | Short vowel + ve | have → hav, give → giv | 0.8% |
| 11 | ui sounding like 'it' | build → bild, guilt → gilt | <0.1% |
| 12 | ere sounding like 'care' | there → thare, where → whare | 0.7% |
| 13 | wh → w | what → wat, when → wen, which → wich, white → wite | 2.0% |
| 14 | ow sounding like 'know' | know → no, knowing → noing, own → oan, bowl → boal | 1.0% |
| 15 | Long vowel before two consonants | find → finde, child → childe, most → moste, ghost → ghoste | 0.3% |
| 16 | oo sounding like 'book' | book → buk, good → gud, look → luk | 0.7% |
| 17 | ei / ey / eigh sounding like 'day' | they → thay, eight → ate, weigh → way | 0.7% |
| 18 | Silent letters at the start: kn, wr, gn, gh, rh | write → rite, knife → nife, ghost → gost, rhythm → rythm | 0.8% |
| 19 | ph → f | phone → fone, photo → foto, graph → graf | 0.1% |
| 20 | igh → i | night → nite, light → lite, high → hi, height → hite | 0.7% |
| 21 | The -ive ending | active → activ, positive → positiv | 0.1% |
| 22 | Unpronounced vowels | every → evry, different → diffrent | 0.2% |

**Very common words.** The extension also respells the very common words
the levels leave alone. These use the same *oo* as level 7:
*to → too, do → doo, two → too, into → intoo, you → yoo, your → yor*.

Levels 18–20 come late because *kn*, *ph* and *igh* always make the same
sound: they look odd but don't make words hard to read. *ought* → *aw* uses
the usual spelling of that vowel (*saw, law*), so it reads right in every
accent. *thort* would add an r for anyone who pronounces r, and *thot* only
works where *cot* and *caught* sound the same.

## How phonetic is it?

The measure is whether you can tell how a word is pronounced (in at least
one accent) from its letters. To check, the letter-to-sound rules are learned
from the spelling system itself: the usual sound of each letter group in
context, such as silent e, soft c, or position in the word. A word counts as
readable if those usual sounds give its pronunciation. Unstressed vowels may
reduce to "uh", because English doesn't mark stress. Details are in
[analysis/decodability.md](analysis/decodability.md).

| | Running text readable from its letters | Also allowing *s*/*z* and *th* voicing |
|---|---|---|
| Normal English | 80.0% | 83.5% |
| All 22 levels | 86.6% | 90.4% |
| All 22 levels + common words | 88.9% | 92.8% |

*s* (/s/ or /z/) and *th* (*thin* or *this*) can each make either sound.
That's accepted rather than fixed.

The biggest remaining gaps:

- **A vowel + one consonant + a vowel can be long or short.** *over, baby,
  making* are long; *never, family, camera* are short. In English it's
  close to a coin flip.
- **Short vowels before two consonants + e**: *else, since, dance, twelve,
  solve*. Level 15 makes a final e lengthen the vowel even across two
  consonants (*finde, childe, moste*), so these are now the exceptions.
  *old, told, cold* keep their spelling: in London and much of southern
  England, *o* before *l* sounds close to the short *o* of *doll*.
- **The long tail**: *very, even, -ture*, and so on.

## Words deliberately left alone

*I, a* and *the* are always left alone. *to, do, two, into, onto, you,
your* aren't touched by the levels, but the extension respells them from a
separate list (*too, doo, yoo*).

## Regenerating

[tools/spelling_levels.py](../tools/spelling_levels.py) builds
`extension/respellings.json` and the report:

```bash
curl -LO https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict
curl -LO https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt
curl -LO https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_UK.txt
python3 tools/spelling_levels.py cmudict.dict en_50k.txt en_UK.txt --top 50000 \
  --json extension/respellings.json --report docs/analysis/levels.md
python3 tools/decodability.py cmudict.dict en_50k.txt en_UK.txt \
  extension/respellings.json --report docs/analysis/decodability.md
```

It uses three data files plus a word list:

- **CMUdict** for American pronunciations.
- **ipa-dict en_UK** for British pronunciations.
- **FrequencyWords en_50k** for word frequencies. It's built from film
  subtitles, so it leans towards conversation.
- **The macOS word list** `/usr/share/dict/words`, to spot proper nouns and
  real words.

[tools/phonetic_spelling.py](../tools/phonetic_spelling.py) is the earlier
experiment with a fully phonetic spelling (one spelling per sound). The new
builder reuses its dictionary loaders.
