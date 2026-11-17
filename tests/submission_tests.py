"""Score door.txt.

    python tests/submission_tests.py

The judge and the simulator used here are the frozen copies in tests/frozen, so changes you make
to redsim/ while exploring do not change your score. Do not edit anything under tests/.

A door must first work: 3 open/close cycles at each of 32 world positions (docs/rules.md). Then
its score is its volume, lower is better. The volume tests are milestones; each names a door
from the corpus that sits at that size.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "frozen"))
from redsim import Design, SimWorld, Unsupported, offsets, verify  # noqa: E402

DOOR = os.environ.get("DOOR", os.path.join(HERE, "..", "door.txt"))
START = 1440          # the door this repository starts with (12 x 10 x 12)
BEST_KNOWN = 56       # 7 x 8 x 1, the smallest door in corpus/doors


def judge_door():
    try:
        return verify(SimWorld(), Design.load(DOOR), offsets())
    except Unsupported as e:
        sys.exit(f"door.txt cannot be judged: {e}\nSee docs/rules.md for the blocks a door may use.")


REPORT = judge_door()


class Correctness(unittest.TestCase):
    def test_door_works(self):
        self.assertTrue(REPORT.ok, f"at offset {REPORT.position}: {REPORT.reason}")


class Volume(unittest.TestCase):
    def below(self, limit):
        self.assertTrue(REPORT.ok, "the door does not work")
        self.assertLess(REPORT.volume, limit)

    def test_smaller_than_the_starting_door(self):
        self.below(START)

    def test_below_1000(self):
        self.below(1000)

    def test_below_500(self):
        self.below(500)

    def test_38_block_record_253(self):
        # sf-holdA-b38: the fewest blocks placed (38), but 7 x 9 x 4 = 252
        self.below(253)

    def test_symmetric_control_145(self):
        # fc2: 8 x 9 x 2 = 144
        self.below(145)

    def test_flat_101(self):
        # one block thick, 10 x 10 x 1 = 100
        self.below(101)

    def test_flat_81(self):
        # 8 x 10 x 1 = 80
        self.below(81)

    def test_flat_64(self):
        # 7 x 9 x 1 = 63: more than half of the corpus sits here
        self.below(64)

    def test_ties_the_best_known_57(self):
        # 7 x 8 x 1 = 56: e78k-h4 and its relatives
        self.below(BEST_KNOWN + 1)

    def test_new_record(self):
        # smaller than every door in the corpus
        self.below(BEST_KNOWN)


if __name__ == "__main__":
    if REPORT.ok:
        w, h, d = REPORT.dims
        print(f"door.txt works: volume {REPORT.volume} ({w} wide x {h} high x {d} deep), {REPORT.blocks} blocks placed, "
              f"opens in {REPORT.open_ticks} ticks, closes in {REPORT.close_ticks}")
        print(f"volume: {START} at the start, {BEST_KNOWN} is the best known")
    else:
        print(f"door.txt is broken at offset {REPORT.position}: {REPORT.reason}")
    unittest.main(verbosity=1)
