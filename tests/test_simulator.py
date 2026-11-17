"""The simulator must reproduce every verdict the real game gave (corpus/verdicts.tsv).

No Minecraft needed.   python -m unittest tests.test_simulator
"""
import os
import sys
import unittest
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from redsim import SimWorld, corpus  # noqa: E402
from redsim.design import Design  # noqa: E402
from redsim import judge  # noqa: E402


def run(row):
    got = corpus.judge_case(SimWorld(), row["file"], row["mutation"])
    want = tuple(row[c] for c in corpus.COLUMNS[2:])
    return row["file"], row["mutation"], got, want


class Corpus(unittest.TestCase):
    def test_matches_the_real_game(self):
        rows = corpus.load_verdicts()
        self.assertGreater(len(rows), 1000)
        with ProcessPoolExecutor() as pool:
            results = list(pool.map(run, rows, chunksize=16))
        wrong = [r for r in results if r[2] != r[3]]
        self.assertEqual(wrong[:5], [], f"{len(wrong)} of {len(results)} cases differ from the real game")


class DesignFiles(unittest.TestCase):
    def test_round_trip(self):
        for file in sorted(os.listdir(corpus.DOORS))[:60]:
            d = Design.load(os.path.join(corpus.DOORS, file))
            again = Design.parse(d.to_text())
            self.assertEqual((again.blocks, again.ports), (d.blocks, d.ports), file)

    def test_positions(self):
        # the first pseudo-random offsets of redstonepedia's judge (extra_offsets in its lib.rs)
        self.assertEqual(len(judge.offsets()), 32)
        self.assertEqual(len(set(judge.offsets())), 32)
        for x, y, z in judge.extra_offsets(28):
            self.assertTrue(-13 <= x <= 13 and -40 <= y <= 40 and -13 <= z <= 13)


if __name__ == "__main__":
    unittest.main()
