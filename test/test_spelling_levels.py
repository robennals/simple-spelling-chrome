"""Unit tests for the alignment and rules in tools/spelling_levels.py.

Run: python3 -m unittest discover -s test
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import spelling_levels as sl  # noqa: E402


def chunks(word, phones):
    al = sl.align(word, tuple(phones.split()))
    assert al, f"could not align {word}"
    return [[g, p, g] for g, p in al]


def apply(rule, word, phones):
    ch = chunks(word, phones)
    changed = rule(ch)
    return sl.text_of(ch) if changed else None


class AlignTest(unittest.TestCase):
    def test_prefers_multi_letter_graphemes(self):
        self.assertEqual(sl.align("night", ("N", "AY", "T")),
                         [("n", ("N",)), ("igh", ("AY",)), ("t", ("T",))])

    def test_silent_final_e(self):
        self.assertEqual(sl.align("make", ("M", "EY", "K"))[-1], ("e", ()))

    def test_unalignable_returns_none(self):
        self.assertIsNone(sl.align("cat", ("D", "AO", "G")))


class NormaliseTest(unittest.TestCase):
    def test_schwa_and_british_units(self):
        self.assertEqual(sl.normalise(("AH0", "AH1", "AAR1", "PALM1")),
                         (("AX", "AH", "AA", "R", "AA"), 3))

    def test_weak_forms_dropped(self):
        us = {"to": [("T", "UW1"), ("T", "AH0")]}
        self.assertEqual(sl.pronunciations("to", us, {}), [("T", "UW")])


class RuleTest(unittest.TestCase):
    def test_ough_by_sound(self):
        self.assertEqual(apply(sl.r_ough, "though", "DH OW"), "tho")
        self.assertEqual(apply(sl.r_ough, "through", "TH R UW"), "thru")
        self.assertEqual(apply(sl.r_ough, "enough", "IH N AH F"), "enuff")
        self.assertEqual(apply(sl.r_ough, "laughter", "L AE F T ER"), "lafter")
        self.assertIsNone(apply(sl.r_ough, "thought", "TH AO T"))   # regular

    def test_ea_short_doubles_next_consonant(self):
        self.assertEqual(apply(sl.r_ea, "head", "HH EH D"), "hed")
        self.assertEqual(apply(sl.r_ea, "ready", "R EH D IY"), "reddy")
        self.assertEqual(apply(sl.r_ea, "great", "G R EY T"), "grate")
        self.assertEqual(apply(sl.r_ea, "learn", "L ER N"), "lern")
        self.assertIsNone(apply(sl.r_ea, "seat", "S IY T"))

    def test_short_u_drops_misleading_e(self):
        self.assertEqual(apply(sl.r_short_u, "love", "L AH V"), "luv")
        self.assertEqual(apply(sl.r_short_u, "something", "S AH M TH IH NG"), "sumthing")
        self.assertEqual(apply(sl.r_short_u, "money", "M AH N IY"), "munney")

    def test_igh_and_magic_e(self):
        self.assertEqual(apply(sl.r_igh, "night", "N AY T"), "nite")
        self.assertEqual(apply(sl.r_igh, "high", "HH AY"), "hi")
        self.assertEqual(apply(sl.r_igh, "nights", "N AY T S"), "nites")
        self.assertIsNone(apply(sl.r_igh, "sighs", "S AY Z"))       # no "sise"

    def test_ey_uses_ay_in_open_syllables(self):
        self.assertEqual(apply(sl.r_ey, "they", "DH EY"), "thay")
        self.assertEqual(apply(sl.r_ey, "eight", "EY T"), "ate")
        self.assertEqual(apply(sl.r_ey, "neighbor", "N EY B ER"), "naybor")

    def test_silent_letters(self):
        self.assertEqual(apply(sl.r_silent, "debt", "D EH T"), "det")
        self.assertEqual(apply(sl.r_silent, "island", "AY L AX N D"), "iland")
        self.assertIsNone(apply(sl.r_silent, "talk", "T AO K"))     # regular 'alk'
        self.assertIsNone(apply(sl.r_silent, "listen", "L IH S AX N"))

    def test_initial_silent(self):
        self.assertEqual(apply(sl.r_initial, "write", "R AY T"), "rite")
        self.assertEqual(apply(sl.r_initial, "ghost", "G OW S T"), "gost")
        self.assertIsNone(apply(sl.r_initial, "ghetto", "G EH T OW"))    # keeps g hard
        self.assertEqual(apply(sl.r_initial, "rhythm", "R IH DH AX M"), "rythm")

    def test_wa(self):
        self.assertEqual(apply(sl.r_wa, "watch", "W AA CH"), "wotch")
        self.assertEqual(apply(sl.r_wa, "what", "W AH T"), "whot")
        self.assertIsNone(apply(sl.r_wa, "water", "W AO T ER"))       # saw vowel
        self.assertIsNone(apply(sl.r_wa, "war", "W AO R"))
        self.assertIsNone(apply(sl.r_wa, "walk", "W AO K"))
        self.assertEqual(apply(sl.r_wa, "want", "W AO N T"), "wont")
        self.assertEqual(apply(sl.r_wa, "wallet", "W AA L AX T"), "wollet")

    def test_wh(self):
        self.assertEqual(apply(sl.r_wh, "when", "W EH N"), "wen")
        self.assertEqual(apply(sl.r_wh, "when", "HH W EH N"), "wen")
        self.assertEqual(apply(sl.r_wh, "whole", "HH OW L"), "hole")
        self.assertIsNone(apply(sl.r_initial, "know", "N OW"))     # would read "now"

    def test_ought_becomes_aw(self):
        self.assertEqual(apply(sl.r_ought, "thought", "TH AO T"), "thawt")
        self.assertEqual(apply(sl.r_ought, "daughter", "D AO T ER"), "dawter")
        self.assertIsNone(apply(sl.r_ought, "though", "DH OW"))

    def test_ow_book_ere(self):
        self.assertEqual(apply(sl.r_ow, "know", "N OW"), "kno")
        self.assertEqual(apply(sl.r_ow, "shows", "SH OW Z"), "shos")
        self.assertEqual(apply(sl.r_ow, "grown", "G R OW N"), "groan")
        self.assertEqual(apply(sl.r_ow, "known", "N OW N"), "knoan")
        self.assertEqual(apply(sl.r_ow, "bowl", "B OW L"), "boal")
        self.assertEqual(apply(sl.r_ow, "knowing", "N OW IH NG"), "knoing")
        self.assertEqual(apply(sl.r_ow, "window", "W IH N D OW"), "windo")
        self.assertIsNone(apply(sl.r_ow, "now", "N AW"))
        self.assertEqual(apply(sl.r_book, "good", "G UH D"), "gud")
        self.assertIsNone(apply(sl.r_book, "food", "F UW D"))
        self.assertEqual(apply(sl.r_ere, "there", "DH EH R"), "thare")
        self.assertIsNone(apply(sl.r_ere, "here", "HH IY R"))

    def test_cluster_e(self):
        self.assertEqual(apply(sl.r_cluster_e, "find", "F AY N D"), "finde")
        self.assertIsNone(apply(sl.r_cluster_e, "old", "OW L D"))       # o before l
        self.assertEqual(apply(sl.r_cluster_e, "child", "CH AY L D"), "childe")
        self.assertEqual(apply(sl.r_cluster_e, "most", "M OW S T"), "moste")
        self.assertEqual(apply(sl.r_cluster_e, "kinds", "K AY N D Z"), "kindes")
        self.assertIsNone(apply(sl.r_cluster_e, "lost", "L AO S T"))     # short
        self.assertIsNone(apply(sl.r_cluster_e, "finding", "F AY N D IH NG"))
        self.assertIsNone(apply(sl.r_cluster_e, "rules", "R UW L Z"))
        self.assertIsNone(apply(sl.r_cluster_e, "rolls", "R OW L Z"))

    def test_ch_ph_ui_oo(self):
        self.assertEqual(apply(sl.r_ch, "school", "S K UW L"), "skool")
        self.assertEqual(apply(sl.r_ch, "machine", "M AX SH IY N"), "mashine")
        self.assertEqual(apply(sl.r_ph, "phone", "F OW N"), "fone")
        self.assertEqual(apply(sl.r_ui, "build", "B IH L D"), "bild")
        self.assertEqual(apply(sl.r_oo, "move", "M UW V"), "moov")
        self.assertEqual(apply(sl.r_oo, "lose", "L UW Z"), "looz")

    def test_ve_and_ive(self):
        self.assertEqual(apply(sl.r_ve, "have", "HH AE V"), "hav")
        self.assertIsNone(apply(sl.r_ve, "active", "AE K T IH V"))
        self.assertEqual(apply(sl.r_ive, "active", "AE K T IH V"), "activ")

    def test_syncope_keeps_endings_and_magic_e(self):
        self.assertEqual(apply(sl.r_syncope, "every", "EH V R IY"), "evry")
        self.assertIsNone(apply(sl.r_syncope, "called", "K AO L D"))
        self.assertIsNone(apply(sl.r_syncope, "useless", "Y UW S L AX S"))

    def test_doubling_variants(self):
        # a z-sound s doubles as zz, a k sound as ck
        self.assertEqual(apply(sl.r_short_u, "cousin", "K AH Z AX N"), "cuzzin")
        self.assertEqual(apply(sl.r_ch, "echo", "EH K OW"), "ecko")
        self.assertEqual(apply(sl.r_ch, "stomach", "S T AH M AX K"), "stomak")

    def test_silent_letter_exceptions(self):
        self.assertIsNone(apply(sl.r_silent, "oh", "OW"))           # h after a vowel
        self.assertIsNone(apply(sl.r_silent, "ballet", "B AE L EY"))  # French final t
        self.assertIsNone(apply(sl.r_silent, "sign", "S AY N"))     # gn
        self.assertEqual(apply(sl.r_silent, "autumn", "AO T AX M"), "autum")
        self.assertEqual(apply(sl.r_silent, "honest", "AA N AX S T"), "onest")

    def test_ea_r_variants(self):
        self.assertEqual(apply(sl.r_ea, "heart", "HH AA R T"), "hart")
        self.assertEqual(apply(sl.r_ea, "bear", "B EH R"), "bare")
        self.assertEqual(apply(sl.r_ea, "pears", "P EH R Z"), "pares")
        self.assertEqual(apply(sl.r_ea, "wearing", "W EH R IH NG"), "waring")
        self.assertEqual(apply(sl.r_ea, "bearded", "B IY R D IH D"), None)

    def test_make_long_refuses_awkward_shapes(self):
        # long vowel before a cluster: no silent-e spelling fits
        self.assertIsNone(apply(sl.r_igh, "nightmare", "N AY T M EH R"))

    def test_ive_needs_two_syllables_and_syncope_guard(self):
        self.assertIsNone(apply(sl.r_ive, "give", "G IH V"))
        self.assertIsNone(apply(sl.r_syncope, "basically", "B EY S IH K L IY"))


if __name__ == "__main__":
    unittest.main()
