# Rules

What counts as a working door and how it is scored. The code is `redsim/judge.py`; the frozen
copy the tests use is `tests/frozen/redsim/judge.py`. The rules are those of
[vjeux/redstonepedia](https://github.com/vjeux/redstonepedia/blob/main/docs/rules.md), and the
judge follows its `piston-door` crate check for check. Two things differ and are listed at the
end.

## The door

A design file (format: `redsim/design.py`) names two ports:

* `door`: the minimum corner of the 3x3 opening. The opening lies in the plane `z = door.z` and
  spans x and y from that corner to +2.
* `lever`: where the lever is. It may rest off or on. The first flip from rest opens the door,
  the second closes it.

The **walkway** is the opening extended 3 blocks in front of and 3 behind the door (54 cells).

## The judge

A door counts when this passes at each of 32 world positions:

1. **Legal blocks.** Only blocks a survival player can place. For this task that also means only
   blocks the simulator models (the list is below); anything else is refused, not guessed.
2. **It settles.** The design is pasted as written, with no updates. Then the shapes of the
   redstone dust are computed, every block looks at its neighbours once (in x, y, z order), and
   the build must go idle within 400 ticks. Idle means no scheduled tick, no block event and no
   moving block is pending.
3. **Every block can stand where it is.** In the settled state no lever, torch, dust, repeater
   or comparator is without its support.
4. **Closed at rest.** The 9 door cells hold 9 identical full blocks, and none is a mechanism
   block (slime, honey, pistons, observers, redstone blocks, lamps, targets, repeaters,
   comparators, dust, torches, levers, droppers, note blocks). The walkway has no collision. The
   `lever` port holds a lever.
5. **Nothing in front of or behind the door.** At rest the 3x3 columns in front of and behind the
   opening are air at any distance: no machine parts, no dust, no torches, no lever.
6. **Open.** The lever is flipped and the build runs until idle (at most 400 ticks). Then the 9
   door cells and the walkway have no collision and hold no moving block, and nothing has broken
   and dropped as an item.
7. **Close.** The lever is flipped back and the build runs until idle. Then the door cells hold
   their rest blocks, the walkway is clear, and nothing has dropped.
8. **Bouncing is allowed.** Only the settled state after each flip is judged, so the doorway may
   close and reopen on the way.
9. **It keeps working.** 3 cycles are run. The closed state after some cycle must equal a closed
   state seen before (the whole watched box: the design, the walkway and a 2-block margin), so
   the door repeats forever. If the internal state differs between cycles the judge runs up to 8
   more cycles to find the period.
10. **32 positions.** Redstone dust updates its neighbours in an order that depends on its
    absolute position, so a door can work in one place and fail in another. The positions are
    `(0,0,0)`, `(-7,3,5)`, `(5,-11,-6)`, `(-3,40,2)` and 28 pseudo-random offsets
    (`redsim.judge.offsets()`).

## Score

**Volume**: the bounding box of every cell that is ever not air, at rest and on every tick of
every cycle, the lever excluded. Width x height x depth, lower is better. Moving blocks and piston
heads count.

Reported as well, and useful as tie-breakers, but not scored:

* **blocks placed**: the blocks in the design file, piston heads not counted;
* **ticks**: open = the first tick after the flip from which the door cells and the walkway stay
  walkable; close = the first tick from which the 9 door cells hold their rest blocks. The worst
  of the 3 cycles at the first position.

## Blocks

Blocks with behaviour, modelled in `redsim/sim.py`:

`piston`, `sticky_piston`, `piston_head` (only in front of an extended piston), `slime_block`,
`honey_block`, `redstone_wire`, `repeater`, `comparator`, `redstone_torch`, `redstone_wall_torch`,
`redstone_block`, `observer`, `target`, `note_block`, `redstone_lamp`, `dropper` (empty),
`waxed_copper_bulb` and its three weathered waxed variants, `lever`.

Building blocks, 229 of them, listed in `redsim/blockdata.py`: stone and its variants, bricks,
planks, logs, wool, concrete, terracotta, glazed terracotta (a piston can push it but slime
cannot pull it), glass and stained glass (they do not conduct), obsidian and crying obsidian (a
piston cannot move them), metal blocks, and so on. The file is generated from the game by
`tools/gen_blocks.py`.

Not available: sculk sensors, sand and other falling blocks, trapdoors, slabs, hoppers, rails,
entities, container contents, and everything else not named above.

## Differences from redstonepedia's judge

* **Volume** here is the plain bounding box above. Redstonepedia's boards use the piston door
  community's definition, which leaves out the door blocks and the plain frame around the
  opening. For flat doors the two usually agree; the plain box is never smaller.
* **Blocks.** Redstonepedia allows every survival block and has separate boards for sculk,
  gravity and entity doors. This task is the solid board restricted to the blocks above.

Rotation safety (the door also works turned 90, 180 and 270 degrees) is not part of either
judge.
