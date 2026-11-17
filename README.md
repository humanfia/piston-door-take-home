# Piston door take-home

Build the smallest 3x3 piston door in Minecraft Java 26.3.

A piston door is a wall of 9 blocks that a redstone machine pulls out of the way when a lever is
flipped and puts back when it is flipped again. `door.txt` holds a door that works and is huge:
volume 1440. The smallest doors known have volume 56. Your job is to make `door.txt` smaller.

```
python tests/submission_tests.py
```

```
door.txt works: volume 1440 (12 wide x 10 high x 12 deep), 151 blocks placed, opens in 26 ticks, closes in 42
volume: 1440 at the start, 56 is the best known
```

No install step: the scoring needs Python 3.9 or later and nothing else.

## The task

Edit `door.txt` (format: [redsim/design.py](redsim/design.py)) so that:

1. **It works.** 3 open/close cycles at each of 32 world positions, nothing breaks, nothing
   stands in the walkway. The full rules are in [docs/rules.md](docs/rules.md).
2. **Its volume is as small as you can make it.** Volume is the bounding box of everything the
   machine ever occupies, moving blocks included, the lever excluded.

The milestones in `tests/submission_tests.py`:

| volume below | what sits there |
|---|---|
| 1440 | the starting door |
| 1000, 500 | |
| 253 | `sf-holdA-b38`: the fewest blocks placed (38), 7 x 9 x 4 |
| 145 | `fc2`: 8 x 9 x 2 |
| 101, 81 | flat doors, one block thick: 10 x 10 x 1 and 8 x 10 x 1 |
| 64 | 7 x 9 x 1, where more than half of the known doors sit |
| 57 | 7 x 8 x 1 = 56, the best known |
| 56 | a new record |

`corpus/doors` holds 945 doors, down to volume 56. They are there to prove the simulator right
and to be studied. Copying one into `door.txt` passes every milestone but the last and shows
nothing; the interesting result is a door you can explain, and the open problem is the last
line of the table.

Do not edit anything under `tests/`. The tests score with a frozen copy of the judge and the
simulator, so you are free to change `redsim/` while you explore.

## Tools

```
python -m redsim door.txt            # judge it: 32 positions, about half a second
python -m redsim door.txt --trace    # and print the doorway tick by tick
python -m redsim door.txt --real     # judge it in the real game
```

`--trace` draws the door's plane on every tick where it changes (`#` door block, `m` moving
block, `o` other block, `.` air):

```
opening (ticks where the door plane changes):
  t1       t3       t5       t7       t9
  ..mmm..  ..ooo..  ..ooo..  ..ooo..  ..ooo..
  oommmoo  oo###oo  oo###oo  oo###oo  oo###oo
  ##...#o  ##...#o  ##...#o  ##...#o  ##...#o
  o.###.o  om###.o  mm.##mo  o#.#.mm  o#.#.#o
  o.###.o  om###.o  mm.##mo  o#.#.mm  o#...#o
  o.#..oo  o.#..oo  o.#..oo  o.#mmoo  o.#m.mo
```

Reading:

* [docs/rules.md](docs/rules.md): the judge, the score, the blocks you may use.
* [docs/mechanics.md](docs/mechanics.md): how pistons, dust, observers and repeaters behave, with
  exact tick numbers, and a catalog of proven tricks.
* [docs/prior-art.md](docs/prior-art.md): how the record went from 151 blocks to 38 and from
  volume 1440 to 56, the door families, and what did not work.

## Two worlds, one judge

The judge ([redsim/judge.py](redsim/judge.py)) talks to a world through six calls: paste blocks,
update them, flip the lever, tick until idle, read blocks, count dropped items. Two worlds
answer them.

**The simulator** ([redsim/sim.py](redsim/sim.py)) is a Python re-implementation of the parts of
the game a door touches: the three phases of a game tick, the neighbour-update stack, shape
updates, scheduled-tick priorities, pistons as block events, moving blocks as block entities,
quasi-connectivity, slime and honey, and redstone dust down to the hash-set iteration order that
makes it depend on world position. It judges a door at 32 positions in about half a second.

**The real game** ([minecraft/](minecraft)) is the official 26.3 server, run headless and
stepped one tick at a time through the bridge from
[vjeux/redstonepedia](https://github.com/vjeux/redstonepedia). Nothing in it is re-implemented.

```
python -m minecraft.setup      # once: Java 25, the server from Mojang, the bridge; about 400 MB
```

Everything it downloads goes to `~/.cache/piston-door-take-home` (or `$PISTON_DOOR_HOME`). It
runs on Linux, macOS and Windows.

The score comes from the simulator, because it is fast and needs nothing installed. The real
game is the reference: if the two ever disagree about a door, the game is right and the
simulator has a bug. Please report it.

How closely they agree, measured against the real game:

| check | result |
|---|---|
| 945 corpus doors and 1890 one-block mutations of them (1792 of the 2835 are broken): verdict, failure reason, volume, ticks | 2835 of 2835 the same |
| the 945 corpus doors run tick by tick: every block of the watched box on every tick | 945 of 945 the same |
| random contraptions, every block on every tick | 27 000 of 27 000 the same |

[docs/simulator.md](docs/simulator.md) has the details, the limits, and how to rerun each check.

```
python -m unittest tests.test_simulator      # the corpus check, no game needed, about 10 seconds
python tools/both.py door.txt                # your door on both worlds, first differing tick
python tools/fuzz.py --seeds 0 500           # random contraptions on both worlds
```

## Layout

| path | what |
|---|---|
| `door.txt` | your door |
| `tests/submission_tests.py` | the score |
| `tests/frozen/` | the frozen judge and simulator the score uses |
| `redsim/` | the simulator, the judge, the design file format |
| `minecraft/` | the real game: setup, the worker, the Java bridge |
| `corpus/` | 945 doors and what the real game says about each |
| `tools/` | both worlds side by side, fuzzing, corpus recording, block data generation |
| `docs/` | rules, mechanics, prior art, simulator fidelity |

## Credits

The rules, the bridge, the door archive and most of what the docs know come from
[vjeux/redstonepedia](https://github.com/vjeux/redstonepedia) by Christopher Chedeau (MIT).
[THIRD_PARTY.md](THIRD_PARTY.md) lists what was taken and how it was changed. The shape of this
repository follows Anthropic's
[original performance take-home](https://github.com/anthropics/original_performance_takehome).
