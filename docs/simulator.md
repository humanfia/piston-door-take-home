# The simulator and how far to trust it

`redsim/sim.py` re-implements the redstone and piston rules of Minecraft Java 26.3 in Python.
This page says what it models, how it was checked against the real game, and where it stops.

## What it models

It follows the game's own structure instead of an abstract circuit model, because small doors
depend on exactly the things an abstract model drops.

| part | why a door needs it |
|---|---|
| The game tick in three phases: scheduled ticks, block events, block entities | pistons are block events and moving blocks are block entities; which runs first sets every timing |
| The neighbour-update stack (depth first; updates raised inside a handler wait until it returns) and shape updates | observers react to shape updates only |
| Scheduled-tick priorities and de-duplication | the order of repeaters and comparators that fire on the same tick |
| Pistons: quasi-connectivity, the 12-block push limit, slime and honey structures, block dropping on short pulses, 2 ticks of travel | most compact doors are built on these |
| Observers seeing a block start to move, not only arrive | observer chains |
| Redstone dust: connection shapes, dot and cross, and updates in the iteration order of a Java `HashSet` of positions | the order depends on absolute coordinates, so a door can work in one place and fail in another |
| Repeaters (locking, priorities), comparators (including reading droppers and copper bulbs), torches (burnout), observers, levers, redstone blocks, targets, note blocks, lamps, droppers, copper bulbs | |
| Blocks losing their support, and redstone components broken by a piston | this is where "something dropped" failures come from |

Building blocks have no behaviour, only four facts each (conducts or not, how a piston treats
it, note block instrument, state properties). `tools/gen_blocks.py` reads them from the game
into `redsim/blockdata.py`.

## How it was checked

The reference is always the real game, driven through the same judge (`minecraft/worker.py`).

**The corpus.** `corpus/doors` holds 945 doors from redstonepedia's archive that use only blocks
the simulator models. `tools/record_verdicts.py` judged each of them, and two one-block mutations
of each (a deleted block, a changed repeater delay, a plain piston for a sticky one, a turned
observer), in the real game: 2835 cases, of which 1043 work and 1792 are broken.
`tests/test_simulator.py` runs the same cases on the simulator and compares the verdict, the
text of the failure reason, the volume and its dimensions, the blocks placed and the open and
close ticks. All 2835 match.

**Tick by tick.** `tools/both.py` runs a design on both worlds and compares every block of the
watched box after every tick, from placement to the last cycle. All 945 corpus doors are
identical on every tick. The other 750 designs of redstonepedia's archive use blocks the
simulator does not model.

**Random contraptions.** `tools/fuzz.py` packs a small box with random components and a lever,
runs it on both worlds and compares every block on every tick. Four mixes of components
(`dense`, `logic`, `slime`, `doors`), with and without `--wild` (components starting in
arbitrary states, the lever on any face), at shifted world positions. With the final code:
27 000 contraptions, no difference. Earlier runs, about 10 000 more, are where items 5 to 7 of
the list below came from.

**Linux.** Setup from nothing, the real game, `both.py` and the fuzzer were run on Debian (WSL)
as well as on Windows. CI runs them on Ubuntu.

Differences these checks found and fixed along the way, for a sense of what they catch:

1. A retracted piston was treated as a conductor. Pistons never conduct.
2. A retracting piston's base still supports the dust on its back.
3. A lever needs a full face: it falls off the side of an extended piston base.
4. Breaking dust notifies the dust diagonally above and below it, which can update a piston.
5. A target block that starts powered switches itself off when a piston moves it.
6. A note block re-reads its instrument on any shape update from above or below, not only when
   the block below changes.
7. A note block playing is a block event: it changes no block, but the world is not idle while
   it is queued, which moves "ticks until idle" by one.

## Limits

* **Minecraft Java 26.3 only**, with experimental redstone off (the default). Not Bedrock.
* **Blocks outside the list are refused**, not approximated: sculk sensors, falling blocks,
  trapdoors, slabs, hoppers, rails, dispensers, and so on. Of redstonepedia's 1694 archived
  doors, 750 use at least one of them (631 of those a sculk sensor).
* **No entities.** A dropped item is detected as "a block broke"; inside the block list that is
  the same thing. Droppers are always empty.
* **Two rules are implemented but not pinned down by any test.** The deferred execution of
  neighbour updates (as opposed to plain recursion), and the `HashMap` order in which the cells
  a piston vacates send their shape updates. Replacing either with the simpler version changes
  no result in the corpus or in thousands of random cases, so the tests cannot tell whether they
  are right.
* **The corpus verdicts were recorded at the judge's 4 base positions**, not all 32. The
  submission test uses 32.
* The simulator earned its record on doors and door-like contraptions. A design far from that
  (large clocks, long comparator chains) is less well covered; check it with `--real`.

## Rerunning the checks

```
python -m minecraft.setup
python tools/record_verdicts.py --jobs 8            # rewrite corpus/verdicts.tsv from the real game
python -m unittest tests.test_simulator             # simulator against corpus/verdicts.tsv
python tools/both.py corpus/doors --quiet           # tick by tick, every corpus door
python tools/fuzz.py --seeds 0 1000 --profile logic --wild
python tools/fuzz.py --shrink some-case.txt         # cut a differing case down
python tools/gen_blocks.py                          # regenerate redsim/blockdata.py
python tools/freeze.py                              # refresh tests/frozen after changing redsim/
```
