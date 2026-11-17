# Prior art: small 3x3 piston doors

This file is distilled from the redstonepedia repository (MIT license, Christopher Chedeau, commit
86a5e48): the story in
[docs/history.md](https://github.com/vjeux/redstonepedia/blob/main/docs/history.md), the rankings
in [LEADERBOARD.md](https://github.com/vjeux/redstonepedia/blob/main/designs/piston-door-3x3/LEADERBOARD.md),
plus `docs/rules.md` and the archive's `records.tsv`, `captions.tsv`, `README.md` and design
files. It only repeats what those files state; where a number was read from a design file's header
or from the archive catalog, that is said. Mechanics referred to here are explained in
[mechanics.md](mechanics.md). Times are UTC. Coordinates: the opening is x, y in {0,1,2}, z = 0;
TL/T/TR, ML/C/MR, BL/M/BR are the door blocks by row; "36 / 19" means opens in 36 gt, closes in 19.

The source's rules allow every survival-placeable block. Many of its doors therefore use blocks
outside this challenge's palette (droppers, sculk sensors, copper bulbs, trapdoors, sand). The
tables below say which doors stay inside the palette.

**Palette note.** This summary was written for the blocks named above. The task also allows
empty droppers, waxed copper bulbs and 229 building blocks ([rules.md](rules.md#blocks)), so a few
doors marked "outside the palette" below are in fact allowed: anything whose only extra blocks
are droppers, copper bulbs, wool or logs. For what the source says about droppers and copper
bulbs, read its own file.

## 1. How the source measures a door

* **Size = volume** (since 2026-10-18): the bounding box of the build over every state of a cycle
  (at rest, every tick of the opening and the closing, open), the lever excluded. `80b (8x10x1)`
  means 8 wide x 10 high x 1 deep. A community door labelled "140b" is 10 x 14 x 1 with about 87
  placed blocks. (rules.md points to `tracks/props/NOTES.md` for the exact definition; that file
  is not part of the checkout this summary was made from.)
* **Blocks placed** (non-air blocks, piston heads excluded) is what records counted before
  2026-10-18. It now only breaks ties, followed by open + close ticks. Archive file names keep
  the placed-block count (`fc2-40b`): they are IDs, not sizes.
* **Ticks:** open = the first tick from which the door cells and the walkway stay walkable (a
  moving block blocks); close = the first tick from which the 9 cells hold their rest blocks;
  worst of 3 cycles at the first position. Other positions can differ by a few ticks.
* **The judge:** 3 open/close cycles at 32 world positions; 9 identical plain full door blocks;
  the walkway (the opening extended 3 blocks in front and behind) clear when open; since
  2026-10-18 16:40Z nothing at all in the 3x3 columns in front of or behind the door; after each
  close the watched box identical to the rest state with nothing dropped; no floating blocks; no
  randomly ticking blocks; bouncing mid-cycle allowed (only settled states are judged); the lever
  may rest on or off.
* **Boards** rank only rotation-safe designs (working turned 90, 180, 270 degrees) with a FULL
  FRAME: when open, the 12 frame cells around the opening (3 above, 3 below, 3 on each side, in
  the door plane) hold the same block as the 9 door blocks. Three extra blocks may move around
  as long as they are in place when the door is open and when it is closed.
* **The owner's target** (vjeux, 2026-10-19): 1 wide (flat), nothing in front or behind, no slime
  or honey, full frame; no piston resting in a quasi-connected armed state.

## 2. Current leaders (LEADERBOARD.md at the commit)

| board | leader | volume | blocks placed | open / close | inside this palette? |
|---|---|---|---|---|---|
| Solid (main); also no slime or honey; flat; in a 3-thick wall; entities allowed | e78k-h5-41b | 56 (7x8x1) | 41 | 36 / 19 | no: 2 droppers |
| Sculk | e78st-56b-38-1s-fill-37b-1 (track c77) | 56 (7x8x1) | 37 | 46 / 14 | no: sculk sensor |
| Solid, on the ground | none | - | - | - | - |
| Gravity | none listed under the full-frame rule | - | - | - | - |
| Seamless; seamless flat; record-eligible | satwire-63b-49-49b | 63 (7x9x1) | 49 | 15 / 15 | no: dropper, iron trapdoor, oak-log door |
| Not rotation-safe | e78-f41-fill-40b-1 (breaks at 90 degrees) | 56 (7x8x1) | 40 | 45 / 56 | no: sculk |
| Frame not full when open | e78k-h3-38b (frame 9/12) | 56 (7x8x1) | 38 | 36 / 19 | yes |
| Fastest open, any category | gravity2-g33-33b | 126 (7x9x2) | 33 | 5 / 16 | no: sand door |
| Fastest open; fastest open + close (solid) | fast-clean-c1r-107b | 720 (9x10x8) | 107 | 9 / 7 | no: a waxed copper bulb |
| Fastest close (any, solid) | fast-clean-s4c-90b | 405 (9x9x5) | 90 | 12 / 7 | yes |
| Fastest open + close, any category | gravity-g8-48b | 280 (7x10x4) | 48 | 5 / 11 | no: sand door |

The top of the Solid board, all 56 = 7x8x1 (palette column read from the archived design files):

| # | design | blocks | open / close | blocks used |
|---|---|---|---|---|
| 1 | e78k-h5-41b | 41 | 36 / 19 | stone, sticky pistons, observers, note blocks, lamp, dust, lever, droppers |
| 2 | e78k-h6-42b | 42 | 29 / 15 | the same kinds, with droppers |
| 3 | e78k-h4-42b | 42 | 36 / 19 | stone, sticky pistons, observers, note blocks, lamp, target, dust, lever: **all inside this palette** |
| 4 | e78s-56b-43-43b | 43 | 29 / 15 | with a dropper |
| 6 | e78s-56b-44-44b | 44 | 44 / 15 | inside this palette (stone, sticky pistons, observers, note blocks, lamp, target, dust, lever) |
| - | e78k-h2-45b | 45 | 44 / 15 | inside this palette; the first solid 7x8 |
| - | community-56b-47-elig-47b | 47 | 42 / 38 | comparator, dropper, lamps, obsidian, repeaters (community 7x8 by SacredRedstone, reproduced) |

Solid-only Pareto frontier (open, close, volume):

| volume | blocks | open | close | design | note |
|---|---|---|---|---|---|
| 56 (7x8x1) | 42 | 29 | 15 | e78k-h6-42b | slime-free |
| 63 (7x9x1) | 50 | 14 | 14 | pocket2-set0-50b | slime-free; uses a dropper |
| 126 (7x9x2) | 46 | 14 | 13 | exotic-pm46-trap-46b | slime; iron trapdoor |
| 144 (8x9x2) | 41 | 22 | 9 | fc2f-41b | slime |
| 252 (7x9x4) | 50 | 14 | 11 | exotic-pm50-trap-50b | slime; trapdoor |
| 405 (9x9x5) | 90 | 12 | 7 | fast-clean-s4c-90b | slime-free |
| 630 (9x10x7) | 103 | 9 | 7 | fast-clean-c1r-103b | breaks at 180 degrees |

Other sizes worth knowing (archive catalog): the best 7x9 = 63 solid doors are t7b-ob40-40b (40
blocks, 41 / 29), t7b-pw42-42b (42, 37 / 25) and e88-t7b-43b (43, 43 / 31), all built from stone,
sticky and normal pistons, observers, repeaters, dust and a lever (e88-t7b also note blocks): all
inside this palette. The best 8x8 = 64 solid door is s27-tlp50-50b (50 blocks, 39 / 45; it uses a
waxed copper bulb). The best 8x9 = 72 is flat-seam-e89b-49b (49, 34 / 34; stone, sticky pistons,
observers, repeaters, dust, lever), now listed under "Frame not full when open" (9/12).

### The smallest door inside this palette: e78k-h4-42b (7x8x1 = 56, 42 blocks, 36 / 19)

From the archived design file (one row per y level, x = -2..4 left to right; the lever on top is
excluded from the volume and is ON at rest):

```
 y   x: -2 -1  0  1  2  3  4
 5              L                 L  lever (floor, powered at rest) on the top-middle puller
 4           D  D  D              D  sticky piston facing down, extended at rest
 3    r  o>  P  P  P  <B N        P  its head (stuck to the top door row); r dust; N note block
 2    E  E   #  #  #  E  A^       #  door (stone); E stone; A^ observer facing up
 1    S> .   #  #  #  .  <C       S> / <C  sticky pistons facing the door, retracted, one-cell gap
 0    S> .   #  #  #  .  <C
-1    A^ .   E  .  .  <C A^       <C at (3,-1): the corner piston K
-2    E  R   <B s^ Ov T  r        R lamp; s^ sticky piston facing up; Ov observer facing down; T target
-3    .  s^  o> s^ o> n  E        n note block; o> / <B observers facing east / west
```

How it works, as far as the captions say (e78-56b-45, e78k-h2, e78k-h4 and history.md "What the
56 door uses"):

* **Top row:** one lever, ON at rest, stands on the top-middle puller; it powers that piston
  directly and the two beside it by quasi-connectivity, so one lever holds all three ceiling
  pistons extended. Flipping the lever pulls the whole top row up with no wiring.
* **Sides:** each side is a 2-piston stack of pull-type pulse pistons (ML/BL and MR/BR), fired by
  observers that watch the ceiling: a source above the stack feeds the upper piston directly and
  the lower one by QC (a powered stone on the left, an observer on the right). The frame stones
  at (-1,2), (3,2) and (0,-1) are kept so the open frame is 12/12.
* **Top-to-bottom crossing:** observers at (-2,-1) and (4,-1) watch the lower side pistons; that
  is how the wiring below the door learns that the lever was flipped.
* **Bottom-middle and centre:** a two-piston elevator below the door (A' on B', the two sticky
  pistons facing up in column x = 1) plus the corner piston K at (3,-1) that parks the
  bottom-middle block. In h2, K is driven by the right pullers delayed 2 gt plus the BR watcher
  through dust and a target, and B' gets its first pulse (B1, at t13) from an observer on a note
  block under K's target, with a "gate" observer at (2,-2) on it giving A's second pulse. In h4
  the bottom-left loop is a sticky piston at (-1,-3) that pushes the lamp up and back; the
  observer on the lamp fires on the moves (B' late by QC, then A's third pulse); the lamp is lit
  through the stone (-2,-2) from a BL-puller watcher at (-2,-1).

e78k-h3-38b (design file compared cell by cell) is the same door with the stones at (0,-1) and
(3,2) and the dust at (-2,3) removed, and the observer of (-1,3) standing at (-1,2) in place of
that frame stone: 38 blocks, same ticks, but only 9 of the 12 frame cells are full when open, so
the source keeps it off its size boards.

## 3. Record progression by blocks placed (solid category)

Volumes and ticks are from the archive catalog; times are from history.md.

| blocks | design | volume | open / close | time (2026-10-18) | what changed |
|---|---|---|---|---|---|
| 151 | v2-151b | 1440 (12x10x12) | 26 / 42 | before the night | first valid design: all-stone door, "UP dance" |
| 147 -> 115 | v2-147b ... v2-115b | 840 (12x10x7) at 115 | 24 / 36 at 115 | before the night | greedy removals, router-laid wires, a unified late chain, R_B stretching the B pulse; 94 of the 115 blocks are wiring |
| 109 | search-tool-v2-min | 770 (11x10x7) | 24 / 36 | 05:35 | local search + net re-synthesis |
| 96 | v2u2 | 700 (10x10x7) | 24 / 31 | 05:48 | sides PUSHED out by pistons that are off at rest (no NOT lines), two pushers sharing one obsidian block, a honey carrier for M, redstone blocks riding the side groups |
| 91, 88, 87 | mechanics-ta, search-tool-center-mech, v3c | 480, 600, 594 | 22 / 34, 24 / 31, 26 / 43 | 05:48-50 | A's torch next to its observer; side pistons high |
| 73 | rb1 | 630 (7x10x9) | 22 / 29 | 05:51 | movable power: one shuttled redstone block powers A, then the right piston, whose structure drags T aside (no P_T) |
| 57 | rb2 | 504 (7x9x8) | 22 / 29 | 05:53 | rb1 with short nets |
| 53, 51, 50, 48 | mechanics-rb2-hold, rb5-bchain, rb5-hold / rb6 | 288, 288, 378, 441 | 22 / 29 ... 22 / 25 | 06:00-10 | Q's 24 gt late hold re-laid, then replaced by a 7-block BUD "silent hold"; a pulse bridge into R_B |
| 47 | rb6-bmobs | 288 (8x9x4) | 22 / 25 | 06:44 | bottom-middle piston retracted at rest, fired by an observer watching the bottom-right door block |
| 46 | fresh-b mp6 | 126 (7x9x2) | 16 / 16 | 08:08 | new family: mirrored pump |
| 42 | fc1 | 189 (7x9x3) | 24 / 14 | 08:09 | new family: symmetric control, no hold |
| 40 | fc2 | 144 (8x9x2) | 24 / 9 | 08:10 | fc1 with a pull-type pulse piston for the left side |
| 40 (ties) | riders-fx1; m05-21b-sym | 189 (7x9x3); 162 (9x9x2) | 24 / 26; 40 / 38 | 10:03; 11:25 | fc2's left piston toggled by X's 3 pulses; the 21-block pulse-only mechanism |
| 39 | sf-holdA-b39 | 252 (7x9x4) | 40 / 36 | 15:15 | the 19-block slime-free mechanism, both top corners toggled by X's 3 pulses |
| 38 | sf-holdA-b38 | 252 (7x9x4) | 36 / 32 | 15:15 | b39 with the lever on an observer next to a note block |

Phases as history.md tells them: 05:14-06:10 the wiring collapses (115 -> 48: pushed sides and
movable power delete whole subsystems); 06:10-08:08 a plateau at 47-48 (every search called it a
local minimum; Q's 7-block hold could not be made cheaper); 08:08-08:14 two new families (46, 42,
40); 08:14-15:00 no 39, but three different 40s (fc2 = 25 mechanism + 15 control, fx1 = 27 + 13,
m05 = 21 + 19); 15:15 the slime-free mechanism wins (39, then 38). Searches on b38 found nothing
smaller.

Other boards that night, by blocks placed: slime-free 89 -> 58 -> 53 -> 50 -> 48 -> 45 -> 44 ->
43 -> 42 -> 41 -> 38; flat (opened 10:56) 60 -> 57 -> 55 -> 54 -> 49 -> 48 -> 47 -> 46 -> 45 ->
44 -> 43; fastest solid 16 / 17 -> 16 / 16 -> 12 / 7 (161 blocks, then 109) -> 11 / 7 (137, 119)
-> 10 / 7 (125, then 107) -> 9 / 7 (113, 112, 109), and open 4 / close 15 at 229 blocks.

## 4. Volume ranking since 2026-10-18 (flat doors, 1 deep)

Archive times are from the design files' headers.

| archived | volume | design | blocks | open / close | what it is |
|---|---|---|---|---|---|
| 10-18 22:54 | 72 (8x9x1) | flat-seam-e89b | 49 | 34 / 34 | flat-b's centre-down machine with TR sent right; later found to have frame 9/12 |
| 10-19 05:34 | 63 (7x9x1) | c79-community-63b | 51 | 14 / 14 | the community 7x9 door reproduced from a screenshot |
| 10-19 05:33 to 08:23 | 63 | pockets-63b-50, satwire-63b-49, c79-49-bl5-br3, pocket2-set0 | 50, 49, 49, 50 | 15 / 15 (pocket2: 14 / 14) | the community mechanism with its wiring re-found or re-synthesized |
| 10-19 09:55 | 63 | e88-t7a | 45 | 47 / 35 | a new 10-piston 7x9 mechanism with a lever-held ceiling |
| 10-19 10:01 to 13:16 | 63 | e88-t7b, t7b-rwfast, t7b-nb2, t7b-pw42, t7b-ob40 | 43, 43, 43, 42, 40 | 43 / 31, 39 / 27, 37 / 25, 37 / 25, 41 / 29 | wiring shrunk region by region |
| 10-19 10:51 to 13:16 | 64 (8x8x1) | c88-s26, c88-s27, s27-bl52, s27-trbl51, s27-tlp50 | 54, 53, 52, 51, 50 | 34 / 34 (tlp50: 39 / 45) | the community 7x9 mechanism in an 8x8 box |
| 10-19 15:11 | 56 (7x8x1) | e78-56b-45 | 45 | 105 / 111 | the first 7x8 door; sculk sensors, wool door |
| 10-19 16:52 | 56 | e78k-h2 | 45 | 44 / 15 | the first SOLID 7x8: every sensor replaced |
| 10-19 16:57, 17:04 | 56 | e78s-56b-44, e78s-56b-43 | 44, 43 | 44 / 15, 29 / 15 | corners re-wired by a fill search |
| 10-19 17:14 | 56 | e78k-h4 | 42 | 36 / 19 | new bottom-left loop (a piston moving a lamp) |
| 10-19 17:22 | 56 | e78k-h5 | 41 | 36 / 19 | new bottom-right with droppers: the board leader |
| 10-19 17:36 | 56 | e78k-h6 | 42 | 29 / 15 | the fast sibling |
| 10-19 17:56, 18:06 | 56 | community-7x8-rep4, community-56b-47-elig | 48, 47 | 42 / 38 | the community 7x8 (SacredRedstone) reproduced |
| 10-19 19:51 | 56 | e78k-h3 | 38 | 36 / 19 | frame 9/12 |

From 2026-10-19 20:00Z to 10-21 the source's team tried every box under 56 and wired none
(section 8). history.md also records, as community existence statements without designs, that
flat doors of 7 wide x 8 tall = 56 and 7 wide x 9 tall = 63 exist.

## 5. The door families

**UP dance (v2; best v2-min, 115 blocks).** The side columns ride slime backbones pulled by
pistons on NOT lines; M is pulled down; the centre piston A (above T) lifts T and a piston P_T
pulls T aside; the centre C then climbs on A, which rides the elevator piston B. Timing came from
torches, NOT gates and delay lines, which is where most of its blocks went.

**rb, movable power (best rb6-bmobs 47; riders-r3 43).** The sides are pushed out by pistons
that are off at rest. One sticky piston Q shuttles a redstone block: it powers A at rest; pushed
away, A loses power at once (lifting T) and the block lands next to the right piston P_R 2 gt
later, whose slime structure drags T aside. The centre uses the same A-on-B elevator. The cost
is a hold: on close the whole B dance runs backwards before T may come back, so Q must stay
extended 16 gt after the lever goes off (a 7-block silent hold in rb6; a redstone block riding
the left structure in riders-r2).

**Mirrored pump (fresh-b; best mp8, 43 blocks, 16 / 16).** The bottom door row is glued to a
slime row and pumped from below the door; the centre exits upward. Every piston fires once per
edge, and the moves are triggered by flags (blocks glued to the moving side structures, watched
by observers) instead of delay lines.

**Symmetric control (fresh-c; fc2 40, fx1 40).** The same signals at the same delays on both
lever edges, so no hold. Walk-through in section 6.

**Pulse-only 21 (mech-synth, wire21; m05, 40 blocks, 40 / 38).** Every piston is retracted at
rest and fired by 2 gt pulses; one 9-pulse train, identical on both edges (P_L, A, P_T, B on, A,
B off, A, M, P_R): no shuttle, no hold, no torch. T leaves north, above the walkway. A redstone
lamp makes the right piston's last pulse late.

**Slime-free 19 (mech-synth; sf-holdA b38 38 blocks, flat43 43 blocks).** Every edge block sits
on its own pull-type sticky piston, plus the A/B elevator for the centre and a T piston: 19
mechanism blocks, the floor of this family. One piston must fire after A's last pull: M at the
bottom (t >= 22 on close in w43), or, with the elevator below the door (flat-b), the top pullers.
sf-holdA holds A extended at rest (symmetric control's close), so M may fire early; both top
corners are pulled up and toggled by X's three pulses, the B window and the T piston share one
observer chain, and the lever hangs on an observer next to a note block (a zero-delay relay that
keeps power out of the T piston's quasi cell).

**Slime-free shuttle (s7q 44, fresh-d s4 45).** fc2's close without slime: A held by a shuttled
redstone block, side columns on pulse pistons.

**Flat versions of the 19 (flat, flat-b, lamp-sweep, flat-seam).** The same mechanism with every
block in the door plane: observer chains instead of dust (repeaters cannot be locked in one
plane). flat-b turns it upside down: the centre goes DOWN to an elevator below the door and the
top pair is pulled up (flat-b-v7: 44 blocks, 80 = 8x10x1, 30 / 26). flat-seam's e89b sends the
top-right block RIGHT so no ceiling puller needs a 10th row (8x9); the right top and middle fire
off an observer watching the top-middle puller, its double pulse merged into one by a delay-2
repeater; the right bottom is fed from below.

**Community 7x9 (c79 and its re-wirings; 63).** Rests closed with the lever ON; the right
pullers are held by the lever; an observer on the top elevator piston drives a hidden dust line
over the top; the bottom is sequenced by droppers read by observers and a normal piston pushed
into an empty cell; the centre goes down, pushed through the top-middle; a corner piston parks
the bottom-middle block in the floor corner. (Its wiring uses droppers.)

**Lever-held ceiling, 7x9 (e88 t7a/t7b; best t7b-ob40, 40 blocks).** One lever, ON at rest,
standing on the top-middle puller holds all three ceiling pullers (TL/TR by QC), so the whole
top row goes up with zero wiring and gives clean single pulses to both walls; the walls are
wired with 6 blocks; a bottom-right merger gives the elevator's A its first pulse; B is driven
for 8 gt by a delay-4 repeater standing on row -4, watched by a gate observer that fires at A's
landing on both of its edges. Later variants shrink the bottom-right route with a normal piston
used as a watched relay (pw42) and with a moving observer (ob40).

**7x8 (e78 line; 56).** Section 2. The lever-held top trio takes the top row out of the side
columns, so each side stack is only 2 pistons and can carry the signal from above the door to
below it; two spare rows below hold the elevator.

**Speed (speed, speed-2, lamp-sweep, fast-clean; 9 / 7 at 107-112 blocks).** T leaves first into
its exit cell; a pusher shoves a sticky puller into that exit; two quick pulls take C out; a
piston F waits armed (a BUD) to close in 7. Open 11 came from a 0-tick inside one block-event
phase, open 10 from an odd-tick pulse (a repeater reading a moved redstone block + a note block +
an observer), open 9 from Q spitting the puller at k5 off an odd pulse.

**Open-4 machine (tick-study, tick-door; 4 / 15 at 229 blocks, 1820 = 10x13x14).** 0-ticked
reach-through pullers take T out through its corner and C out through the top cell; see
mechanics.md section 12.

## 6. fc2 (40 blocks, 144 = 8x9x2, 24 / 9), the symmetric-control door

Layout (z = 0 unless noted): door stone at x 0..2, y 0..2. Left structure: 3 slime at (-1, 0..2).
Right structure: 6 slime at (3, 0..4) and (2,3); the slime at (2,3) drags T. P_L: sticky piston
facing east, retracted, at (-3,2), one cell from the left backbone (pull-type pulse piston). P_R:
sticky piston facing east, retracted, at (2,4). A: sticky piston facing down, extended, at (1,4),
head on T. B: sticky piston facing down, retracted, at (1,5). P_M: sticky piston facing up,
retracted, at (1,-2), one cell below M. Q: sticky piston facing east at (0,4,1) with the redstone
block RB at (1,4,1): RB powers A at rest; pushed to (2,4,1) it powers P_R. Lever at (-2,4,0) on
a stone at (-2,4,1).

Control (15 blocks): R_q, a delay-2 repeater at (-1,4,1) on a floor (Q = the lever 4 gt later, on
both edges); O_a, an observer watching the lever at (-1,4,0) (a 2 gt pulse into X 2 gt after each
flip); X, an east-west dust at (0,4,0) on a floor block (powers A directly, and A one cell lower
through its floor); O_b at (-1,5,0) watching O_a, into a stone at (-1,6,0) (a pulse at t4 into
R_B); R_B, a delay-4 repeater at (0,6,0) (the B window t12-20 into B's quasi cell (1,6,0)); O at
(0,5,0) watching R_B (A's two dance pulses into X at t14 and t22); two observers at (-3,4,0) and
(-3,3,0) (a pulse into P_L at t4); O_m watching the bottom-right door block from (2,-1,0) with a
smooth stone at (2,-2,0) (a pulse into P_M 2 gt after that block moves).

| t | opening | closing |
|---|---|---|
| 2 | O_a pulses X; A is still powered by RB, nothing moves | O_a pulses X; A extends and pushes C from (1,3) down into (1,2) |
| 4 | Q pushes RB east; A loses power at once, retracts, lifts T to (1,3); P_L reaches into its gap | the pulse ends while C is moving: A leaves it at (1,2) (a spit); Q pulls RB back; P_R loses power and pulls the right structure home, bringing T back to (1,3); P_L pushes the left structure home and spits it |
| 6 | P_L retracts and pulls the left structure west; T lands; RB lands next to P_R | everything lands, RB is next to A again; P_M pushes M up and spits it |
| 7 | P_R pushes the right structure east; its slime at (2,3) drags T to (2,3) | A extends and pushes T and C down together |
| 9-11 | O_m saw the bottom-right block leave; P_M pulls M down to (1,-1) | 9: they land, **closed at 9** |
| 12 | the B window starts; B pushes A down into (1,3) | 12-24: the B window fires again but B's push fails against the extended A; O's pulses reach an A that is already powered; idle at 24 |
| 14-16 | O pulses X; A extends and pulls C up into (1,2) | |
| 20 | the window ends; B lifts A back to (1,4) | |
| 22-24 | O pulses X again; A pulls C up into (1,3): **open at 24** | |

Constraints that shaped it: Q must be steady (a pulse-driven Q spits RB, P_R then fires before T
has landed, and a moving block is not dragged); the lever must feed both Q's repeater and the
early-pulse observer (RB and A's pulse dust cannot share a side of A); X must be dust (a solid
block there would power Q and would not update A in its lower position); the pull-type P_L costs
3 blocks against 5 for fc1's push-type piston under the walkway. The scheme works for any Q
delay from 2 to 7 as long as the A pulse comes at least 2 ticks before Q. Speed: open = b + 12
where b is the tick B fires, b >= d + 6 (T aside before B) and d (Q's delay in gt) >= 4, so 22
is the family's floor, reached by fc2f (41 blocks, 22 / 9) with the B window fed straight off
the lever.

## 7. Main discoveries

* **Pulse-driven pistons:** a retracted sticky piston one cell from its block, given one 2 gt
  pulse per edge, is a toggle (pull on open, push and let go on close); three pulses toggle it
  too, so a piston can reuse a source that fires three times per flip.
* **Movable power:** a shuttled redstone block switches one piston off at once and another on
  2 gt later; a redstone block or an observer riding a structure is a timing element.
* **Asymmetry for free:** a lamp lights at once and goes dark 4 gt after its power ends; a
  push-type and a pull-type pulse piston fed the same pulse act in opposite orders on the two
  edges; a weakly powered note block next to the lever is a zero-delay watch target that
  conducts nothing.
* **Quasi-connectivity:** a piston is quasi-powered through the head of the piston above it; a
  quasi-powered piston waits for an update, but a piston head forwards neighbour updates to its
  base (which is why fc2's Q cannot wait silently next to A).
* **Observer chains** cost 1 block per 2 gt; the tick at which a chain can fire a given cell is
  fixed mod 4 (aim at the quasi cell to shift it by 2); an observer watching a pulse-pulled door
  block fires 2 gt earlier on close than on open; a dust under a strongly powered block lights.
* **One lever can hold a whole ceiling** (e88): the top row needs no wiring, and the parked
  corner blocks give each side one clean pulse.
* **Speed:** a piston 0-ticks when the redstone block powering it is shoved away in the same
  block-event phase; odd ticks come only from pistons; the floors for solid doors are open >= 4
  and close >= 1.
* **What search does and does not find:** re-synthesized nets are shorter than nets laid one
  connection at a time (v2 113 -> 109, v2u2 96 -> 88); dust + its floor often becomes one
  strongly powered block; exact re-synthesis of small wiring groups found slack the local search
  missed (flat 49 -> 43, w42 -> 41, the fastest solid door 123 -> 107, with lamps, note blocks
  and targets in the palette); local search never invents a mechanism (fc2 40, mp8 43, rb6-bmobs
  47 were all local minima). Mechanism synthesis did find the 21-block pulse-only and the
  19-block slime-free mechanisms, but its automatic wiring is about 12 blocks worse than hand
  wiring (53 against m05's 40). Search with pistons in the wiring palette found the piston
  relay and the moving observer.

## 8. Dead ends

**Fewer than 38 blocks placed.** b38 is a local minimum of the minimizer with plateaus (30k
neutral edits), of re-synthesis of groups up to 5 blocks (with note blocks) and of regrowing 3
blocks (1.42M candidates). fc2 and its variants were local minima of every search (255 neutral
designs at depth 2; 24.3M size-3 candidates screened, none passed). By analysis each fc2 control
pair is pinned: X must reach A in both positions, which fixes the early-pulse observer and so
the lever; Q must sit at (0,4,+-1); P_L only accepts 2 gt pulses or a push from the east; P_M's
2 blocks are minimal; a "free" Q delay fails on close because Q's head passes the A pulse's
update to Q. With fc2-style slime sides and M fixed there is no mechanism below 21 blocks
(19,967 combinations); without slime, 19 is the floor of its family.

**Slime-free before b38.** The crux was M, which had to move at t >= 22 on close (after A's last
pull); a lamp only delays 4 gt, and a redstone block south of A cost 46 or more. Holding A
extended at rest removed the constraint.

**Flat, elevator on top.** The late left chain is geometrically minimal (9 observers), and every
flat slime-free pulse-only mechanism found needs one late piston.

**Faster.** Wired solid doors: 9 / 7; open 4 only at 229 blocks with close 15; open 8 works with
scripted inputs only.

**Below 72 (flat), evening of 2026-10-18.** e89b is minimal for its own mechanism and exact
timing (28 wiring blocks proven UNSAT in 8x9 for the palette block, dust, repeater, observer,
torch). 5-tall strips (11x5, 12x5) cannot be wired with fixed parts: every row mechanism fires
twice from the inner door column and once from the ring column beside it, and the corner cell
would need both roles. In 7-wide boxes row y = 1 is blocked end to end, so each side's top and
middle pistons are fed only from above and the bottom one only from below; a real observer
watching a double-firing piston fires into A's fatal window. SUPER seamless is impossible for
solid doors (emptying the centre needs a head or sticky face in the tunnel). The source warns
that every such "cannot be wired" verdict is relative to the plan and bounds given to the tool.

**Below 56 (2026-10-19 to 10-21).** Mechanisms that work with ideal (scripted) inputs exist at
42, 48, 49 and 54, in almost every box; none could be wired by any tool or gadget. The 56 door
uses two things, not proven necessary: a top-to-bottom crossing (the lever-held trio + 2-piston
side stacks, which needs a spare column on EACH side and a spare row above: width >= 7) and
room for the centre's 2-cell move (two spare rows for an elevator: height >= 5 + 1 + 2 = 8).

| box | volume | crossing | elevator room | mechanism with ideal inputs? | what stopped it |
|---|---|---|---|---|---|
| 7x5 .. 10x5 and turned | 35-50 | no | no | no | no row mechanism at any width <= 10 (exhaustive in the strip model) |
| 11x5, 5x11 | 55 | no | no | yes | the corner cell would need two roles: not wirable with fixed parts |
| 5x5x2 (2 deep) | 50 | - | - | no | by argument: no block can change plane inside the box |
| 6x6 | 36 | no | no | no (bounded) | no mechanism with <= 2 two-move blocks |
| 7x6 | 42 | yes | no | yes | BM must leave through the centre column (a 3-move path); a piston fires inside the opening |
| 6x7 | 42 | no | yes | yes | 2-4 pistons fire from inside the door square; two pistons have no feed inside the box |
| 8x6 | 48 | yes | no | yes | one cell would need 8 distinct ticks |
| 6x8, 6x9 | 48, 54 | no | yes | yes | the 6-wide walls below |
| 7x7 | 49 | yes | yes, but not both with an elevator | yes (trio7: C leaves through a middle frame cell) | a 2-cell bottom-left area and a 4-cell top-left area cannot make their pulses with real blocks |
| 9x6 | 54 | yes | no | yes | a piston fed only from a 2-cell pocket, which drives it 0 times over every filling; 9x7 = 63 would fix it |

* **6-wide boxes** have no spare column on one side: that side frame holds the 3 extra blocks,
  so it has no stack, and the other side's stack is 3 pistons tall; a source reaches only 2 of
  them from either end, so it cannot carry a crossing, and a top trio does not fit. The box-edge
  column's middle block also needs an elevator whose pistons can only be fed from the corner at
  the box edge, and that corner drives at most ONE action per edge where the column needs about
  five.
* **Load.** The small mechanisms need 20-30 pulses per edge, many pistons pulse 3-9 times per
  edge, and the free areas are 1-4 cells. A wirable door needs about 1-2 actions per piston per
  edge.
* **Closest approaches:** bf16 (the trio7 family, 7x7 = 49, slime-free): a complete schedule
  under every rule of the source's SAT model that replays in its simulator and in the game (open
  156 / close 154) with scripted inputs, but real blocks fail in its bottom-left and (0,-2)
  areas. q69c-sh0p (6x9, slime): every piston fed, one blind cell on one edge (the bottom-right
  must start a shuttle by tick 23 of the open and nothing it touches moves before tick 24).
* **What is proven** (each within its stated model): 5-tall boxes up to 10 wide and their turns;
  6x6 with <= 2 two-move blocks; for 7x7 at one action per piston per edge only that none of the
  1.57M decided candidates works (0.53M of 2.1M undecided); the SAT results are bounded by their
  horizon and rules. A working 7x7 mechanism needs 20 steps even in the permissive model, so
  short-horizon results do not rule 7x7 out.
* **Gadgets that helped but did not finish the job:** a lever outside the box on a never-moved
  piston's back face (holds that piston and the one below by QC); timing-free lever-held side
  stacks; carried and shuttled observers and redstone blocks (feeds for pistons with no free
  neighbour); QC through an empty cell; a slime column as a crossing (solid board only). They
  fixed starts and boxed-in pistons, not loads: areas of 1-4 cells must make 3-10 distinct ticks
  per edge.
