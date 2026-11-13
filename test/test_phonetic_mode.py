"""Tests for the fully phonetic spelling in tools/phonetic_mode.py.

Run: python3 -m unittest discover -s test
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import phonetic_mode as pm  # noqa: E402


def spell(us, uk=None):
    return pm.spell(tuple(us.split()), tuple(uk.split()) if uk else None)


class VowelSetTest(unittest.TestCase):
    def test_bath_vs_trap(self):
        self.assertEqual(spell("B AE1 TH", "B PALM1 TH"), "bahth")
        self.assertEqual(spell("K AE1 T", "K AE1 T"), "kat")

    def test_palm_lot_cloth_thought(self):
        self.assertEqual(spell("F AA1 DH ER0", "F PALM1 DH ER0"), "faather")
        self.assertEqual(spell("HH AA1 T", "HH AA1 T"), "hot")
        self.assertEqual(spell("D AO1 G", "D AA1 G"), "dog")      # cloth merges with lot
        self.assertEqual(spell("TH AO1 T", "TH AO1 T"), "thawt")

    def test_strut_vs_what(self):
        self.assertEqual(spell("K AH1 P", "K AH1 P"), "kup")
        self.assertEqual(spell("W AH1 T", "W AA1 T"), "wot")      # British lot vowel

    def test_r_and_yod_kept(self):
        self.assertEqual(spell("K AA1 R", "K AAR1"), "kaar")
        self.assertEqual(spell("N UW1", "N Y UW1"), "nyuu")
        self.assertEqual(spell("M Y UW1 Z IH0 K", "M Y UW1 Z IH0 K"), "myuuzik")

    def test_unstressed(self):
        self.assertEqual(spell("AH0 B AW1 T", "AH0 B AW1 T"), "abowt")
        self.assertEqual(spell("HH AE1 P IY0", "HH AE1 P IY0"), "hapy")

    def test_consonants(self):
        self.assertEqual(spell("DH IH1 S"), "this")             # th for both th sounds
        self.assertEqual(spell("TH IH1 NG K"), "thingk")
        self.assertEqual(spell("B AA1 K S", "B AA1 K S"), "boks")

    def test_american_only(self):
        self.assertEqual(spell("K AE1 N T"), "kant")


if __name__ == "__main__":
    unittest.main()
