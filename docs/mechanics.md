# Mechanics for 3x3 piston doors (Minecraft Java 26.3)

This file is distilled from redstonepedia's `docs/mechanics.md` (MIT license, Christopher Chedeau,
commit 86a5e48): <https://github.com/vjeux/redstonepedia/blob/main/docs/mechanics.md>. A few items
come from the same repository's `docs/history.md` and `docs/rules.md` and are marked as such. It is
restricted to this challenge's block palette: plain solid blocks (stone, smooth stone, iron block,
concrete), glass, obsidian, glazed terracotta, piston, sticky piston, slime block, honey block,
redstone dust, repeater, comparator, redstone torch (floor and wall), redstone block, observer,
target, note block, redstone lamp, lever. Everything about other blocks (sculk, droppers, hoppers,
rails, gravity blocks, copper bulbs, trapdoors, leaves, scaffolding, entities) is left out, and
nothing is added that the source does not state.

**Palette note.** This summary was written for the blocks named above. The task also allows
empty droppers, waxed copper bulbs and 229 building blocks ([rules.md](rules.md#blocks)), so a few
doors marked "outside the palette" below are in fact allowed: anything whose only extra blocks
are droppers, copper bulbs, wool or logs. For what the source says about droppers and copper
bulbs, read its own file.

**Where the claims come from.** The source says every rule was read in the decompiled 26.3 game
(class names and line numbers below are those of its listing) and checked in its simulator; every
effect a door relies on is proven by a "gadget" (a small design plus a drive script with
expectations, section 13), and the whole gadget library was replayed in the unmodified official
26.3 server with identical results (section 14). "Measured" below means measured by the source's
tools, not by this file.

**Conventions.** Ticks are game ticks (gt, 1/20 s). "k" or "t" = ticks after the lever flip; the
flip happens between ticks, so the first tick after it is k1 (t1). The redstone community's
"1-tick" usually means one redstone tick (2 gt); this file uses game ticks throughout. Repeater
"delay d" is the repeater's setting 1..4; it delays 2 x d gt.

**Coordinates and names** (used by the tricks and the floors): the opening is x, y in {0,1,2} in
the plane z = 0, x growing to the right, y up; the walkway is the same x, y for |z| <= 3. Door
blocks: TL, T (or TM), TR in row y = 2; ML, C (centre, (1,1)), MR in row y = 1; BL, M (or BM), BR
in row y = 0. E = the cell outside T, (1,3). Recurring piston names: A = the piston that moves the
centre, B = the "elevator" piston that moves A one cell and back, P_T = the piston that takes T
aside, P_L / P_R / P_M = left, right, bottom-middle pistons, Q = a piston that shuttles a redstone
block (RB), R_B = the repeater that makes B's window, X = the dust that pulses A.

Contents: 1. one tick, 2. neighbour updates and shape updates, 3. pistons, 4. redstone dust,
5. the other components, 6. conductors and supports, 7. timing of every component, 8. what a
component does to a pulse train, 9. what happens in 0 gt, 10. odd ticks, 11. techniques,
12. floors for the fastest door, 13. gadget catalog, 14. vanilla confirmation.

## 1. One tick (`ServerLevel.tick`, 358-460)

| order | phase | source line | what runs there |
|---|---|---|---|
| between ticks | player actions | `LeverBlock.pull` | the lever's state and its neighbour updates happen at once: dust re-powers, pistons QUEUE block events, observers / repeaters / torches SCHEDULE ticks, lamps light |
| 1 | `handlingTick = true` | 360 | used by `PistonBaseBlock.checkIfExtend` (section 3) |
| 2 | game time + 1 | 387 | |
| 3 | scheduled block ticks | 394 `blockTicks.tick` | repeaters, comparators, observers, torches, lamps (turning off), ordered by (time, priority, insertion) |
| 4 | block events | 409 `runBlockEvents` (1267-1292) | pistons (`triggerEvent`), note block sounds; FIFO (`removeFirst`) until the queue is EMPTY, events added meanwhile run in the same phase; the queue is an `ObjectLinkedOpenHashSet` (215), so an identical pending event is dropped |
| 5 | `handlingTick = false` | 412 | |
| 6 | block entities | 459 `tickBlockEntities` | `PistonMovingBlockEntity.tick`: progress of moving blocks and their landing |

(Fluid ticks, chunk random ticks and entities run between these phases and do not matter for this
palette.) Consequences used everywhere below:

* Nothing moves before tick 1: a lever flip only queues piston events, which run in tick 1's
  block-event phase.
* The scheduled-tick phase comes BEFORE the block-event phase of the same tick, and the
  block-entity phase (landings) comes AFTER it. A piston powered between ticks, in the scheduled
  phase or in the block-event phase acts in that tick's block-event phase; a piston powered by a
  landing (block-entity phase) acts in the next tick.
* Scheduled ticks are collected first, then run, per-chunk queues merged by (trigger time,
  priority, sub-tick order) (`LevelTicks.tick` 81, `collectTicks` 93, `runCollectedTicks` 182).

## 2. Neighbour updates and shape updates

* **Neighbour updates** go out in the fixed order `WEST, EAST, DOWN, UP, NORTH, SOUTH`
  (`NeighborUpdater.UPDATE_ORDER`, through `CollectingNeighborUpdater`: a FIFO that runs nested
  updates after the current one; `addAndRun` 68, `runUpdates` 87). Pistons powered by one change
  therefore queue their events in that order (gadget `event-order`).
* **Shape updates** are a separate kind of update. Observers react only to shape updates of the
  block they face, never to neighbour updates. `setBlock` (`Level.setBlock` 216) does, as side
  effects: `onPlace` / removal, neighbour updates (flag 1), and shape updates with `flags & -34`,
  so changes made BY shape updates notify no neighbours.
* **Some state changes send no neighbour updates at all:** a lamp's lit state uses flag 2 (section
  5), and a repeater switching a solid block updates only that block's neighbours (section 5).
  These "quiet" changes are what makes silent holds and silent arming possible.
* **Dust is the exception to the fixed order.** When a wire's power changes it updates itself, its
  6 neighbours and their neighbours in `HashSet<BlockPos>` order, which depends on the world
  position (`DefaultRedstoneWireEvaluator.updatePowerStrength` 18). The source gives the hash:
  `hash = (y + 31z) * 31 + x`, bucket `(h ^ h >>> 16) & 15`.
* **Why a door can work at one position and fail at another.** If two pistons (or a piston and
  the component that should stop it) are updated by the same dust change, which one is updated
  first depends on where the door stands. The source's judge therefore runs every design for 3
  open/close cycles at 32 world positions (4 by default plus `--extra-offsets 28`). To make an
  order position independent, do not let dust decide it: feed the piston that must go first
  separately (the W,E,D,U,N,S order is fixed), or chain the pistons through their own moves.
* **Why a door can work facing one way only.** The W,E,D,U,N,S order is fixed in world
  directions, so turning a design 90 degrees changes which of two neighbours is updated first.
  Gadget `landing-race`: a powered piston Q whose push is blocked by a moving block queues nothing
  until that block lands; the landing block's update (W, E, D, U, N, S) then queues Q and any
  piston A the block powers in that order. With Q west of the landing cell, Q takes the redstone
  block away before A acts; turned 90 degrees, A fires first and is 0-ticked, spitting its block.
  The source's boards rank only rotation-safe designs (run turned 90, 180 and 270 degrees too).
* **Orientation-based update order is off.** 26.3 ships `ExperimentalRedstoneWireEvaluator` and
  passes an `Orientation` through `CollectingNeighborUpdater` (149-155) and
  `PistonBaseBlock.moveBlocks` (336), but `ExperimentalRedstoneUtils.initialOrientation` (9-22)
  returns null and `RedstoneWireBlock.updatePowerStrength` (271-275) uses the default evaluator
  unless the world has the `redstone_experiments` feature flag. Default worlds keep the fixed
  order and the position-dependent dust order.
* **How the source's judge places a design:** raw writes with no updates, then a shape update of
  every wire, then one `self` update of every block; the build must then go idle. A
  quasi-powered piston that has "not noticed yet" (a BUD-armed piston) therefore cannot exist in
  the rest state.

## 3. Pistons (`PistonBaseBlock`, `PistonStructureResolver`, `PistonMovingBlockEntity`)

### Power, quasi-connectivity and budding

* **Power** (`getNeighborSignal` 116-136): any neighbour except the front gives signal into the
  piston, OR any neighbour of the cell *above* the piston (except the piston itself) gives signal
  into that cell: **quasi-connectivity (QC)**. The cell above is called the piston's quasi cell.
* **Budding.** The piston only re-checks its power when it gets a neighbour update, so a
  QC-powered piston can sit unextended (or an unpowered one extended) until something updates it
  (a BUD). Gadgets `qc-bud`, `silent-hold`.
* A piston is also quasi-powered through the HEAD of an extended piston above it (gadget
  `head-qc`), and through an empty quasi cell that something emits into.
* **What updates a piston:** an emitter pointing INTO its quasi cell updates that cell's
  neighbours, the piston included. Powering a solid block NEXT to the quasi cell updates only that
  block's neighbours, so the piston stays put. A powered plain block (conductor) in or above the
  quasi position arms the piston without updating it. A dust changing power updates the neighbours
  of its neighbours (2 cells deep): a held piston at dust, block, piston re-checks (gadget
  `dust-reach`). A lever updates only its own neighbours and its support's. A placed redstone
  block updates only its own neighbours.
* **Piston heads forward updates:** `PistonHeadBlock.neighborChanged` passes every neighbour
  update to its base, so an extended piston also re-checks when a cell next to its head changes
  (gadget `head-forward`).

### Events and timing

| rule | source |
|---|---|
| A power change only QUEUES a block event (type 0 extend, 1 retract-and-pull, 2 retract-and-drop); the event re-checks power when it runs: an extend whose power is gone is dropped (a pulse that ends before the block-event phase is cancelled), a retract whose power is back just re-sets `extended` | `checkIfExtend` 93-114, `triggerEvent` 143-151 |
| An extend is only queued if the push resolves at that moment. There is no retry later (gadget `no-retry`): a powered piston whose push line holds a moving block queues nothing and sits powered and retracted until a neighbour update | 96-98 |
| Moved blocks become `moving_piston` at the destination at once; their old cells are air at once (the head cell holds the moving head) | `moveBlocks` 299-326 |
| A moving block's entity goes progress 0 -> 0.5 -> 1.0 in the block-entity phases of t and t+1 and the real block is placed in the block-entity phase of t+2. A piston action started at tick t is finished in the block-entity phase of t+2 | `PistonMovingBlockEntity.tick` 294-327 |
| Retract while extending: the head's moving entity is finalTick'd (to air: it is the source piston) | `triggerEvent` 164-166, `finalTick` 270-271 |
| Sticky only: if the block two ahead is a moving block this piston pushed (extending, same direction), it is finalTick'd: PLACED NOW, not pulled. Normal pistons only remove their head (the block keeps moving and lands at t+2) | 180-190, 204-205 |
| Retract type 2 (drop) when the block two ahead is moving and (progress < 0.5, or this tick's entity tick already ran, or the unpower happens in the scheduled / block-event phases); else type 1 (pull) | 101-110 |
| Type 1 with a plain block two ahead pulls it, also when the front cell was EMPTY ("reach-through": the retract resolver starts at pos+2) | 192-202, `PistonStructureResolver` |
| A pull is never finalized early: pulled and dragged blocks always land at t+2 | finalTick needs `isExtending` |
| The retracting base is itself a `moving_piston` (immovable, cannot act, cannot be pushed or pulled) until t+2; it lands with `setBlock(..,67)` + `neighborChanged`, so a powered piston re-extends at t+3 at the earliest | 168-179, `PistonMovingBlockEntity.tick` 313-314 |
| A piston placed by `finalTick` or by a landing runs `onPlace` and queues an extend if it is powered there: in the same phase when placed by a 0-tick, next tick when placed by a landing (gadgets `zero-tick-onplace`, `landing-fire`) | `onPlace` 80-86 |
| A moving block's entity is also finalTick'd when its cell is overwritten (`preRemoveSideEffects`), which no piston action does (moving pistons are immovable) | `PistonMovingBlockEntity` 286-288 |
| Extended pistons, moving pistons, obsidian and blocks with block entities are immovable; a push line holds at most 12 blocks | `isPushable` 215-257 |

How long a moved block takes to arrive (source section 7):

| move | arrives after | condition |
|---|---|---|
| pushed, 0-tick | 0 gt (placed in the same block-event phase) | its sticky pusher extends and retracts in one phase |
| pushed, spit at t+1 | 1 gt | its sticky pusher is unpowered in the next tick's scheduled or block-event phase |
| pushed, spit at t+2 | 2 gt, block-event phase | sticky pusher unpowered 2 gt later (a 2 gt pulse) |
| pushed, plain | 2 gt, block-entity phase | landing |
| pulled or dragged | always 2 gt, block-entity phase | landing |

### Short pulses on sticky pistons (block dropping, "spitting")

* If power drops while the block two in front is still a `moving_piston` being pushed by this
  piston, the retract event is type 2: the moving block is finished in place and **not pulled**.
  The source states this for any progress as long as the block has not landed ("sticky retract
  during a push finalizes, never pulls", seen in door rb9: B pushes A down at t4 and retracts at
  t6; A stays down).
* So a 2 gt pulse (an observer pulse) makes a sticky piston push its block one cell and leave it
  there (gadget `spit`). The spit block is placed in the block-event phase of the retract tick,
  so pistons it powers act in THAT tick, one tick earlier than after a landing (gadget
  `spit-saves-tick`, `checkIfExtend` 108 `isHandlingTick`).
* A 3+ gt pulse (for example 4 gt from a delay-2 repeater) on a sticky piston pushing a 2-block
  line pushes the line one cell and pulls back only the first block: the far block advances one
  cell with no piston touching it (gadget `pump`). A 2 gt pulse spits the whole line instead.
* A 1 gt pulse: the retraction comes at X+1 and the landing at X+3. A 1-tick sticky retraction
  still pulls the block two cells ahead on open; on close the push is spit (source, s79 notes).

### What can be moved

* **Immovable:** extended pistons, piston heads and moving pistons (`PushReaction.BLOCK`),
  obsidian (`getDestroySpeed == -1` class with bedrock), blocks with block entities.
* **Push-only:** glazed terracotta (`PUSH_ONLY`) can be pushed but not pulled, and is never
  dragged by slime.
* **Destroyed when pushed** (`POPPED` / push reaction DESTROY): the source names dust,
  repeaters, levers and torches. A block of this kind in the movement path is broken and drops
  as an item (which fails the source's judge: nothing may break or drop).
* **12 blocks** is the maximum a piston moves, slime/honey-dragged blocks included.
* A piston whose push line starts with an extended piston does nothing; it pushes that piston
  once it has retracted (gadget `blocked-push`). A piston whose front became a moving block
  meanwhile does nothing (`moveBlocks` returns false).

### Slime and honey

* A moved slime or honey block drags every adjacent movable block, except that slime and honey
  never stick to each other: two touching structures move independently (gadget `honey-slime`).
* Slime drags stone but not glazed terracotta or obsidian (gadget `slime-nonstick`). A
  slime-dragged neighbour that is immovable (extended piston, piston head) is skipped.
* Non-sticky moved blocks drag nothing: moving a piston that sits under a slime block leaves the
  slime behind.
* DESTROY blocks (dust, repeaters, levers, torches) next to a moving slime block are left in
  place, not dragged or broken; only a DESTROY block in the movement path breaks. Their floors
  are normal blocks and DO get dragged, so floors next to moving slime are made of glazed
  terracotta (never dragged).
* A retracted sticky piston right under a slime row rides it: pushed down when another piston
  pulls the row down, dragged back up when the row is pushed back, so it can pump the row from
  either spot (gadget `slime-rider`).
* Slime is a conductor and a valid floor; honey conducts nothing and holds nothing (source
  section 12, fixtures `slime-is-a-conductor`, `leaves-honey-hold-nothing`).

## 4. Redstone dust (`RedstoneWireBlock`, `DefaultRedstoneWireEvaluator`)

* **Delay 0.** A dust change takes effect where and when the change happens; it updates 2 cells
  deep (the neighbours of its neighbours), in the position-dependent order of section 2.
* **What dust powers:** the block below it and the blocks it points into, weakly. A weakly
  powered block powers components (pistons, repeaters, torches, lamps), never other dust.
* **Dust never feeds dust through a block.** While a wire computes its own input it turns off
  every wire's signal (`shouldSignal=false`). So dust does not pick up a block powered only by
  other dust. To tap one dust net one-way into another, put a repeater (or a block strongly
  powered by a repeater) between them.
* **Strong power back-feeds dust.** A block strongly powered by a repeater, a lever, an observer
  or a torch below it powers every dust touching it, including dust on top of it; and a dust
  directly UNDER a block strongly powered by an observer lights, because dust reads all six
  neighbours (gadget `dust-below`: a one-way tap from an observer chain into a dust net).
* **Shape: dot versus cross.** The default `redstone_wire` state is a dot, and a dot stays a dot
  (`getConnectionState` 117: `wasDot && isDot`), powering only the block below. To make an
  isolated dust point sideways, write it as a cross
  (`redstone_wire[north=side,east=side,south=side,west=side]`): it stays a cross after the shape
  update and powers all four neighbours. A dust with one connection becomes a line through it
  and points both ways.
* **What dust connects to:** other dust, levers, and targets (a target is a signal source, so a
  dust line beside it bends into it and powers it, where a plain block there would not be
  powered: gadget `target-tap`). A repeater whose back faces the source reads it.
* **Steps:** a wire connects up a step only if the block above it is not a conductor
  (`RedstoneWireBlock` 150, `canConnectUp = !above.isRedstoneConductor`); step connections are
  cut by a conductor above or beside. Pushing or pulling a conductor off a dust step connects
  the step at once (gadget `instant-on`).
* **OR in one dust:** a dust sandwiched between the output block of one repeater (above it) and
  of another (below it, its floor) is lit by either, and a cross dust powers the block it points
  into: a 2-input OR feeding a torch with 1 dust.
* **Stack feed** (gadget `stack-feed`): a cross dust behind a stack of 3 retracted sticky pistons
  at the top level points into the top piston, its floor powers the middle one and quasi-powers
  the bottom one. One pulse fires the whole stack.
* **Glass under dust:** a stone under a dust is powered by it and QC-arms any piston whose quasi
  cell it touches; glass carries the dust without powering anything.

## 5. The other components

### Lever
* Flipped between ticks; delay 0. Strongly powers the block it is attached to, weakly every
  neighbour. It is a signal source for adjacent components (dust connects to it, a repeater whose
  back faces it reads it), but an adjacent solid block other than its attachment is not powered:
  a repeater reading the lever is a one-way tap that the lever's block cannot back-feed (gadget
  `lever-tap`).
* The lever updates only its own neighbours and its support's neighbours. A lever next to a
  piston's quasi cell arms that piston silently.
* The block a lever hangs on is strongly powered, so it QC-arms a piston whose quasi cell touches
  it ("a lever arms the pistons two cells below its block").
* In a flat (one-plane) build a lever powers its neighbours, so it must stay off every piston
  and quasi cell it should not drive.

### Observer (`ObserverBlock.updateShape` 57/67, `tick` 45, `startSignal` 74)
* Reacts to *shape updates* of the block it faces, not to neighbour updates. It schedules a 2 gt
  tick, turns on, schedules 2 gt more, turns off: a 2 gt pulse starting 2 gt after the change,
  output from its back (strong power into the block behind it).
* It ignores changes while it is powered or has a tick pending (a 4 gt "busy window"), and it
  sees 0-ticks (a cell that changed twice inside one phase gives one pulse 2 gt later).
* An observer watching a lever pulses 2 gt, 2 gt after BOTH flips (gadget `dual-edge`). The
  lever's support can be an observer facing up that watches it and fires out of its back (gadget
  `lever-observer`).
* A chain of observers watching each other delays a pulse 2 gt per observer, needs no floors and
  goes around corners (gadget `observer-delay`): 1 block per 2 gt. The tick at which a chain can
  fire a given cell is fixed mod 4; aiming at the piston's quasi cell instead of the piston
  shifts it by 2.
* **Observers and pistons.** The source states: "a piston (or its head cell) changes state at
  the event, 2 gt later and again 2 gt after that, so an observer watching it pulses twice per
  motion. Watch a block that moves once, the lever, or another observer." The individual
  measurements it reports:
  * an observer watching a cell that a lever-fired (k1) piston changes fires k3..k5, a chained
    one at k5; the head landing 2 gt later does not re-trigger it because it is powered then
    (gadget `odd-observer`);
  * an observer watching a sticky piston given a 2 gt pulse fires at its extension (X+2) AND at
    its retraction's landing (X+4 -> X+6); a pull-type pulse piston gives its watcher two pulses
    4 gt apart (start of the extension, end of the spit retraction);
  * with a 1 gt pulse (retract at X+1, landing at X+3 inside the busy window) it fires once;
  * a piston firing twice exactly 6 gt apart gives its watcher 3 pulses, and an observer on a
    door block's PARKING cell can see 3 changes per edge, so links are not always even;
  * a LEVEL-held piston (held extended, released once per lever edge) moves once per edge and
    its watcher fires exactly ONE pulse per edge ("a parity-clean link").
* An observer watching a pulse-pulled door block fires 2 gt earlier on close than on open.
* An observer carried by a moving structure fires 2 gt after EVERY landing, out of its back
  wherever it landed (gadget `rider-observer`).
* An observer sees a block that starts moving: watching the cell a block leaves works as well as
  watching the cell it moves into (gadget `flag-observer`: a plain block glued to a moving slime
  structure, watched by an observer that touches no slime so it is never dragged, gives one 2 gt
  pulse after each move, out and back).

### Repeater (`DiodeBlock.tick` 50-63, `checkTickOnNeighbor` 84, `RepeaterBlock.isLocked` 84)
* Delay 2 x d gt (d = 1..4), in the scheduled-tick phase.
* **Tick priorities** (`shouldPrioritize` 196): EXTREMELY_HIGH (-3) if it feeds another diode,
  VERY_HIGH (-2) when turning off, HIGH (-1) when turning on. A repeater's turn-off tick
  therefore outranks another repeater's turn-on tick in the same game tick.
* **Pulse stretching:** a pulse shorter than the delay, even a 0-tick one, comes out exactly as
  long as the delay (2 gt -> 8 gt at d4); a second pulse while it is on is swallowed (gadget
  `pulse-stretch`). On a 0-tick power pulse the repeater turns on 2 gt later for its full delay
  (it turns on, then schedules its own turn-off).
* **Locking:** a repeater with another repeater pointing into its side keeps its output whatever
  its input does and follows the input again once unlocked (gadget `repeater-lock`). Locking is
  instant (read in `updateShape`). In one plane repeaters cannot be locked (their sides face out
  of the plane).
* **Repeaters update quietly:** a repeater switching a solid block in front of it updates that
  block's neighbours only (`updateNeighborsInFront`), not their neighbours. A piston powered
  through that block by quasi-connectivity is not updated: it neither extends nor retracts until
  something next to it changes (silent hold).

### Comparator (`ComparatorBlock` 64, 90, 140, 145-146, 151)
* Delay 2 gt, scheduled; priority HIGH if it feeds a diode, else NORMAL.
* The output is recomputed in its tick: a change undone before then (a 0-tick pulse) is
  swallowed; it also swallows a 1 gt pulse.
* Subtraction keeps the parity of its inputs. Gadget `comparator-odd`: rear = a redstone block,
  side = a redstone block that a lever piston moves; the output follows 2 gt after each input
  change: off at k5 (side block landed k3), back on at k3 after the off flip (pulled away at k1).
* Compare mode updates its front on every tick it runs, even with an unchanged output (a BUD
  source). It reads an analog source through one conductor.
* In one plane a comparator has no side inputs (they need a diode at z+-1).

### Redstone torch (`RedstoneTorchBlock` 61, 74, 83, 87, 126)
* Inverts with a 2 gt delay, scheduled. Powers every neighbour except its attachment, strongly
  the block above. A lit/unlit change also updates the neighbours of its neighbours.
* **Burnout:** 8 toggles in 60 gt -> off for 160 gt (the list is kept per position).
* Gadget `torch-delay`: wall lever, block, wall torch, sticky piston: the torch is off at tick 2
  after the lever, the piston it holds retracts in tick 2; relit and extending at tick 2 after
  the lever goes off.
* A wall torch hung on the outer face of a static frame stone powers the side puller below it
  directly and the one under that by QC (a level-held 2-stack), and is switched off by powering
  the stone.

### Redstone block
* A constant source. Moved by a piston it becomes a `moving_piston` at once: its dust line goes
  dark in the same phase and pistons on that line queue retracts that run in the same phase
  (gadget `instant-off`; a torch inverter would take 2 gt). It powers again when it lands (t+2,
  block-entity phase) or when it is placed by a spit or a 0-tick (block-event phase).
* A placed redstone block updates only its own neighbours: placed next to a quasi cell it arms
  the piston silently.

### Redstone lamp (`RedstoneLampBlock` 29, 36, 45)
* Lights in the tick it is powered (delay 0) and goes dark 4 gt after its power ends (a NORMAL
  scheduled tick from the first unpowered update, never rescheduled). Observers see both changes.
* Lamp state changes use flag 2 (no neighbour updates): a lamp next to a piston's quasi cell,
  fed through a conductor, never updates that piston.
* A lamp is a conductor. A lamp whose power ends exactly 4 gt before a new power pulse turns off
  and on in ONE tick (its off tick was scheduled first), so an observer watching it fires once.

### Note block (`NoteBlock.neighborChanged` 81)
* A plain conductor whose `powered` state follows `hasNeighborSignal` in the same tick, on both
  edges, with neighbour updates (`setBlockAndUpdate`). An observer watching it pulses on both
  edges of its power with no lamp-style fall delay. Its `instrument` follows the block below (an
  observer sees that change too). Its sound is a block event in the same tick.
* A weakly powered note block passes nothing on: next to a lever it is a zero-delay,
  non-conducting watch target.

### Target
* A conductor and a signal source (power 0 unless hit by a projectile), so dust always connects
  to it and powers it. A torch on a target reads a dust line running past it (gadget
  `target-tap`): one block where stone + dust + floor were needed.

## 6. Conductors and supports

What the source states per block ("-" = the source does not say):

| block | conductor (can be powered) | floor for dust / diodes / torches | moved by pistons |
|---|---|---|---|
| stone-like plain blocks (stone, smooth stone, iron block, concrete) | yes | yes | pushed, pulled, dragged by slime |
| note block | yes ("a plain conductor") | - | - |
| target | yes, and a signal source | - | - |
| redstone lamp | yes (used as a level conductor) | - | yes (one door pushes a lamp up and back) |
| glass | no: never powered, so it stops leaks into neighbouring pistons and quasi cells | yes (sturdy) | - |
| slime block | yes | yes ("a floor") | yes; drags its neighbours, never honey |
| honey block | no ("conducts nothing") | no ("holds nothing") | yes; drags its neighbours, never slime |
| glazed terracotta | - | yes (the floors beside moving slime) | push-only: pushed, never pulled, never dragged |
| obsidian | - | - | immovable |
| redstone block | a power source | - | yes (shuttles, riders) |
| piston, sticky piston, retracted | - | - | yes (carried pistons); a retracting base is immovable for 2 gt |
| extended piston, piston head, moving piston | - | an extended piston's top face stays full | immovable |
| observer | emits strong power into the block behind it | - | yes (carried and shuttled observers) |

The source's simulator groups plain blocks into classes whose members are interchangeable (3000
random circuits against the same circuit with every plain block replaced by a random member of
its class, 0 differ): stone-like conductors, obsidian (immovable), glass-like non-conductors,
slime, honey, glazed terracotta (push-only), and others outside this palette. Note-block
instruments matter only directly above / below a note block.

Support rules the source states:

* In the settled rest state every block must pass the game's own `canSurvive`: no lever, torch,
  dust or repeater on air (the source's judge rejects floating blocks).
* Glass is sturdy (it holds dust, diodes and torches); slime is a floor; honey holds nothing.
* A DESTROY-class component (dust, repeater, lever, torch) is broken when a block is pushed into
  its cell. Next to moving slime it is left in place, but its floor, a normal block, is dragged.
  The source does not spell out what then happens to the component; its routers avoid the case
  by using glazed terracotta floors there ("floors next to moving slime must not be dragged").
* A retracting piston base keeps its extended box as support during the retraction; a piston
  head popped by `updateShape` drops nothing (source section 12).
* An extended piston's top face stays full, so a lever standing on top of an extended
  downward-facing piston survives (history.md, door e88).
* The source's judge requires that after each close the whole watched box is identical to the
  rest state and no item entity exists: anything that pops off fails the door.

## 7. Timing of every component

| component | input -> output | delay (gt) | phase / priority | notes | gadget |
|---|---|---|---|---|---|
| lever | click -> powered | 0 (between ticks) | - | strong power into its support, signal to adjacent components | all |
| redstone dust | any change | 0 | where the change happens | updates 2 cells deep, `HashSet` order | `instant-off`, `dust-reach` |
| repeater | input change | 2 x delay setting | scheduled; EXTREMELY_HIGH if it feeds another diode, VERY_HIGH turning off, HIGH turning on | a shorter pulse, even a 0-tick one, is stretched to the delay; locking is instant | `pulse-stretch`, `zero-tick-pulse`, `repeater-lock`, `early-window` |
| comparator | input change | 2 | scheduled; HIGH if it feeds a diode, else NORMAL | a 0-tick pulse is swallowed; subtraction keeps parity | `zero-tick-pulse`, `comparator-odd` |
| redstone torch | input change | 2 | scheduled | burnout: 8 toggles in 60 gt -> off 160 gt | `torch-delay` |
| observer | shape update from its face | on +2, off +2 more | scheduled | ignores changes while powered or pending; sees 0-ticks | `observer-delay`, `zero-tick-observer`, `odd-observer` |
| redstone lamp | power | on 0, off +4 | off scheduled (NORMAL) | visible to observers; no neighbour updates | `lamp-fall-delay` |
| note block | power edge | `powered` 0; sound = block event, same tick | in the update / block-event phase | watchable on both edges | `odd-pulse`, `note-watch` |
| target | (power 0 unless hit by a projectile) | - | - | a signal source: dust next to it bends into it and powers it | `target-tap` |
| redstone block (moved) | leaves / arrives | off 0, on at landing (+2, block-entity phase) or at a spit / 0-tick placement | - | | `instant-off`, `landing-next-tick` |
| piston | power | acts in the block-event phase of the tick in which it was powered if that was between ticks (lever: tick 1), in the scheduled phase or in the block-event phase; next tick if powered in the block-entity phase (a landing) | block-event phase | moved blocks land at t+2 (section 3) | all |

Every redstone component in this palette delays by an even number of game ticks. Odd ticks come
only from pistons (section 10).

**Pulse generators** the source lists:

* 0-tick pulse on a piston (extend and retract in one phase): power it, and have its own move
  update a silently armed partner that moves its power source away (gadget `zero-tick`).
* 0 gt power edges: `instant-off` (moved source), `instant-on` (conductor off a dust step); 0 gt
  power pulse: `zero-tick-pulse` (a redstone block placed and shoved away in one phase).
* 2 gt pulse: an observer (`dual-edge`, `spit`). Any 2d: a repeater.
* Odd pulses: k3..k5 from an observer on a k1 piston (`odd-observer`); k5..k7 / k7..k9 from a
  repeater reading a k1-moved redstone block + note block + observer (`odd-pulse`).

## 8. What each component does to a pulse train (link table)

Measured in the source's simulator and replayed in the game (112/112 identical). Input: a floor
lever toggled between ticks ("pulse k" = on before tick 1, off k ticks later). Cells: the
component's output windows as first tick on - first tick off ("1.." = stays on).

| component | pulse 1 | pulse 2 | pulse 4 | pulse 8 | 2x pulse 2, gap 1 | 2x pulse 2, gap 2 | 2x pulse 2, gap 4 | 2x pulse 2, gap 8 |
|---|---|---|---|---|---|---|---|---|
| repeater d1 | 2-4 | 2-4 | 2-6 | 2-10 | 2-7 | 2-4 6-8 | 2-4 8-10 | 2-4 12-14 |
| repeater d2 | 4-8 | 4-8 | 4-8 | 4-12 | 4-9 | 4-8 | 4-12 | 4-8 14-18 |
| repeater d4 | 8-16 | 8-16 | 8-16 | 8-16 | 8-16 | 8-16 | 8-16 | 8-16 |
| comparator | - | 2-4 | 2-6 | 2-10 | 2-7 | 2-4 6-8 | 2-4 8-10 | 2-4 12-14 |
| torch (inverts) | 0.. | 0-2 4.. | 0-2 6.. | 0-2 10.. | 0-2 7.. | 0-2 4-6 8.. | 0-2 4-8 10.. | 0-2 4-12 14.. |
| lamp | 1-5 | 1-6 | 1-8 | 1-12 | 1-6 | 1-10 | 1-6 7-12 | 1-6 11-16 |
| note block | 1-2 | 1-3 | 1-5 | 1-9 | 1-3 4-6 | 1-3 5-7 | 1-3 7-9 | 1-3 11-13 |
| observer on the lever | 2-4 | 2-4 | 2-4 6-8 | 2-4 10-12 | 2-4 7-9 | 2-4 6-8 | 2-4 8-10 | 2-4 12-14 |
| observer on a lamp | 2-4 7-9 | 2-4 8-10 | 2-4 10-12 | 2-4 14-16 | 2-4 8-10 | 2-4 12-14 | 2-4 8-10 14-16 | 2-4 8-10 12-14 18-20 |
| observer on a note block | 2-4 | 2-4 | 2-4 6-8 | 2-4 10-12 | 2-4 7-9 | 2-4 6-8 | 2-4 8-10 | 2-4 12-14 |

(The torch row starts lit: "0-2 4.." = lit, off from tick 2 to 4, lit again. The note block's
`powered` follows the lever with no delay, so the observer watching it behaves like one watching
the lever.)

Pulse COUNTS change along a chain: an observer merges changes inside its 4 gt busy window (one
pulse for a 1-2 gt input pulse); an observer watching a level (lamp, note block) emits two pulses
per window; a lamp merges pulses closer than its 4 gt fall; a comparator swallows a 1 gt pulse;
repeaters stretch to their delay and merge gaps shorter than it. A planner should take its link
rules from this table rather than assume every change is one pulse.

## 9. What happens in 0 gt (inside one block-event phase)

Block events run FIFO until the queue is empty, so any number of piston actions can chain in one
tick as long as every link is triggered by something that happens inside the phase. All rows are
reported PASS in the official server.

| effect | why (source) | gadget |
|---|---|---|
| **0-tick piston:** a sticky piston extends and retracts in one phase; the block it pushed is PLACED in that tick | 180-190 (finalTick two ahead) | `zero-tick` |
| a 0-ticked NORMAL piston's block still lands at t+2 | 204-205 | `zero-tick-normal` |
| **reach-through:** a 0-ticked sticky piston with an empty front cell pulls the block two cells away; the pulled block lands 2 gt later | 101-110 (type 1: nothing it pushed is moving); the retract resolver starts at pos+2 | `zero-tick-reach` |
| a piston placed by a 0-tick fires in the same phase; chains of placed pistons all act in one tick | `onPlace` 80-86 | `zero-tick-onplace` |
| one block, two placed moves, one tick | finalTick's `setBlockAndUpdate` updates the next (armed) piston, which is 0-ticked in turn | `double-move` |
| power LOSS: a moved redstone block (or any moved conductor) cuts power at once; pistons on that line queue retracts that run in the same phase | `moveBlocks` (the source becomes `moving_piston`) | `instant-off` |
| power GAIN without a moved source: a conductor pushed (or pulled) off a dust step connects the step at once; the piston it feeds extends in tick 1 | `RedstoneWireBlock` 150 | `instant-on` |
| power GAIN from a placed source: a redstone block finalTick'd by a sticky retract powers its neighbours in the block-event phase (their events run in the same phase) | 180-190 + `finalTick` 276 | `zero-tick-onplace`, `spit-saves-tick` |
| an observer SEES a 0-tick (the cell changed twice inside the phase): one pulse 2 gt later | `ObserverBlock.updateShape` 67-68 | `zero-tick-observer` |
| a 0-tick POWER pulse (source placed and removed inside one phase): a lamp is lit 0..4 gt, a repeater stretches it to its delay (on 2 gt later), a comparator swallows it; a piston next to the source moves only if its event is queued before the one that removes the source (it is then 0-ticked itself) | `DiodeBlock.tick` 50-63, `ComparatorBlock` 145-146, `RedstoneLampBlock` 36 | `zero-tick-pulse` |
| event order = update order (W,E,D,U,N,S), FIFO: of two pistons powered by one redstone block that both want the same stone, the west one moves it and the north one, finding a moving head in front, does nothing | `runBlockEvents` 1270-1271 | `event-order` |
| a powered piston carried onto a powered spot by a LANDING fires next tick (landing is in the block-entity phase) | `onPlace` | `landing-fire` |
| a quasi-powered piston ignores its source until any neighbour update; arming one silently is how 0-tick partners wait | `getNeighborSignal` 116-136 | `qc-bud`, `silent-hold` |

**How a 0-tick is made.** The piston P is powered by a redstone block. A partner piston X sits
silently armed (quasi-powered, not yet updated) so that P's own move updates it; X then shoves
P's redstone block away in the same block-event phase, P's retract event runs in that phase, and
the block P pushed is finalTick'd. The speed doors' "F 0-ticks" use the same pattern with landed
redstone blocks.

**Constraint for doors.** A BUD-armed piston cannot exist in the REST state (the judge's
placement updates every block). Partners and armed pullers must be armed after the flip: by the
lever itself (it only updates its own neighbours and its support's: a lever next to a piston's
quasi cell arms it silently), by dust feeding a conductor next to the quasi cell from 3+ cells
away (dust updates reach 2), or by a redstone block placed next to the quasi cell (its updates
reach only its own neighbours).

**FIFO interleaving.** Two chains of events started together interleave in the queue, one event
per chain per round (each event appends its follow-ups at the end). If chain B needs chain A's
result, start B from A's last action (a relay), start it one tick later, or pad it with an extra
piston so it runs one round later. A piston whose push fails when its event runs never retries.

## 10. Odd ticks (1 gt)

| source of odd timing | when | gadget |
|---|---|---|
| pistons the lever powers directly move at k1 | lever between ticks, events in tick 1 | every lever gadget |
| a block pushed at t lands at t+2 in the block-entity phase, after that tick's block events: pistons it powers act at t+3 (k1 push -> k4); components it feeds schedule from t+2 (repeater delay 1: on at k5) | `ServerLevel.tick` 409 vs 459 | `landing-next-tick` |
| a spit block is placed in the block-event phase of the retract tick: pistons it powers act THAT tick (k4 instead of k5 in the gadget) | `checkIfExtend` 108 | `spit-saves-tick`, `spit` |
| an observer watching a cell a k1 piston changes fires k3..k5; chains stay odd (k5, k7...) | observer 2 gt from the block-event phase | `odd-observer` |
| a repeater reading a redstone block that a k1 piston moves changes at k1+2d; a note block next to its output turns that edge into a state change an observer sees: pulse k5..k7 on the on flip, k7..k9 on the off flip | `DiodeBlock` 84-99 | `odd-pulse` |
| comparator subtraction keeps its inputs' parity: side input from a redstone block a k1 piston pushes (lands k3) -> output off at k5; pulled away at k1 -> output back at k3 | `ComparatorBlock` 145-146 | `comparator-odd` |

Asymmetric delays from a redstone block riding a moving structure (m = the tick of the move):

| element | on the move out | on the move back | source name |
|---|---|---|---|
| lamp next to the cell the block moves INTO (lit when it lands at m+2, dark 4 gt after it leaves at m), watched by an observer | observer pulse m+4 | m+6 | gadget `rb-lamp` |
| lamp at the block's rest cell | the other way round | | `rb-lamp` |
| dust next to the cell the block moves INTO (lit at m+2, dark the moment it leaves), watched by an observer | m+4 | m+2 | `rb-dust` (no gadget) |
| lever + delay-1 repeater -> sticky piston -> redstone block -> repeater of delay d: the piston pushes the block next to the repeater at t2, it lands at t4; closing, it pulls it away at t2 and the repeater's input drops at once | on at 4 + 2d | off at 2 + 2d | `shuttle` (no gadget): a lever level whose falling edge comes 2 gt early |

## 11. Techniques

### Holding and releasing pistons

* **Silent hold** (gadget `silent-hold`): a piston kept extended by a quasi source that later
  turns off WITHOUT updating it stays extended, unpowered, until any later neighbour update (a
  block landing next to its head counts, because heads forward updates). Feed the piston's quasi
  cell through a solid block switched by a repeater to drop the hold silently. The rb doors'
  7-block hold is built this way; gadget `head-forward` shows the release (an extended piston
  held unpowered retracts when a block is placed next to its HEAD).
* **Conductor feeds do not update:** a powered plain block above a piston quasi-arms it without
  updating it, so it fires only where something else updates it.
* **Fire a QC-only piston with an update, or deliberately without one:** an emitter INTO the
  quasi cell fires the piston; powering a solid block NEXT to the quasi cell does not. One door
  (c88 s25) uses the second on purpose: a stone powered from the side fires the piston that is
  its direct neighbour but leaves the piston below (QC-powered, never updated) alone on close.
* **Level-held pistons.** A piston held extended at rest by a level (the lever through dust or a
  conductor, or a torch on the lever's block) moves once per lever edge. Gadget `torch-link`: a
  torch on the lever's block holds a sticky piston extended, head stuck to its block; lever on:
  torch off 2 gt later, the piston retracts and pulls its block; lever off: it pushes it back.
* **One lever holds a whole ceiling** (history.md, e88): a lever ON at rest standing on top of
  the downward-facing T puller powers it directly and the TL / TR pullers beside it by QC (the
  lever is a neighbour of their quasi cells and its `updateNeighbours` reaches them). The whole
  top row goes up with zero wiring, and observers watching the TL / TR parking cells give one
  clean pulse each at t3 to both sides. Only the lever is excluded from the source's volume
  measure, so it may hang outside the box on a box cell.
* **Lever outside the box on a never-moved piston's back face:** holds that piston directly and
  the one below by QC: two levels for free. A lever-held stack works with each level switching
  anywhere 0..40 ticks after its flip ("timing-free side stacks").
* **Stopper** (gadget `stopper-release`): a piston head held extended at rest blocks another
  piston P's push line, so an early pulse on P does nothing; when a puller takes the block out
  of P's line during the pulse, its departure updates P, which fires at that tick.
* **A parked door block as a gate:** a door block that sits in a frame cell only while the door
  is open relays a repeater's strong power into the piston next to it only on open; on close the
  same pulse does nothing. Door blocks and ring stones also relay power into the opening's quasi
  cells: a strongly powered plain block in a ring cell gives signal into the opening cell next
  to it, which QC-powers a piston facing up just below that cell.

### Pulse-driven pistons

* **Push-type pulse piston** (gadget `pulse-toggle`): a sticky piston retracted at rest, one
  cell from its block, given one 2 gt observer pulse per lever edge. The on pulse reaches across
  the gap and pulls the block (a normal pull); the off pulse pushes it back and spits it. No
  torch, no steady line. Measured windows (source tool `door ideal`, v2 door): side / bottom
  pistons accept the pulse at any tick on both edges; A needs one pulse 0..4 gt after the flip
  plus the two B-edge pulses.
* **Three pulses toggle it too:** one net move, timed by the last pulse, so a piston can reuse a
  source that fires three times per flip (the doorway bounces before it settles; the source's
  judge only checks settled states).
* **Pull-type pulse piston:** a sticky piston two cells from a structure (one-cell gap) pulls it
  on the first 2 gt pulse and pushes + spits it back on the second, so a side column can be
  pulled open from OUTSIDE its backbone.
* **Order flip** (gadget `order-flip`): a push-type and a pull-type pulse piston fed the same
  pulse act in opposite orders on the two lever edges.
* **Pitfall:** an observer next to a pull-type piston fires twice per pulse, 4 gt apart. Use the
  mergers below, a 1 gt pulse, or a level-held piston as the link.
* Observers fire on both lever edges, so every observer-driven input of the open also fires on
  the close and vice versa: make those runs no-ops (`blocked-push`, `order-flip`) or route the
  two edges apart.

### Moving the centre: the A-on-B elevator (two-piston extender)

From history.md's walk-through of door fc2. A is a sticky piston facing the door (down, at
(1,4), head on T at rest); B is a sticky piston behind it ((1,5), retracted at rest).

| step | what happens |
|---|---|
| A unpowered | A retracts and lifts T one cell, to (1,3); T is then taken aside |
| B window starts | B pushes A one cell toward the door, into the cell T left |
| pulse on A | A (powered through a block that still reaches it in its lower position) extends and pulls C up one cell |
| B window ends | B lifts A back |
| second pulse on A | A pulls C up again: C is out of the opening |

On close the same door spits C down one cell with one early pulse on A, brings T back, and A
pushes T and C home together (2-block push). In fc2 the B window is an observer pulse into a
delay-4 repeater (t12-20), and A's two dance pulses come from an observer watching that repeater
(t14, t22); see `early-window` below for a faster window.

* **Symmetric control** (needs no hold): with an A-on-B elevator, T dragged out by the right
  structure and one shuttled redstone block (A off then P_R on / P_R off then A on), no hold is
  needed if (1) A gets one pulse BEFORE the shuttle moves, on both edges (open: A is still
  powered, the pulse is swallowed; close: A spits C down one cell, freeing T's cell), (2) the
  shuttle piston is the lever through one repeater (>= 2 gt after that pulse), and (3) the B
  window comes at the same delay on both edges: on close A is extended again and B's push fails
  (`blocked-push`).
* **Pump** (gadget `pump`): the 3+ gt pulse of section 3 moves the far block of a 2-block line
  one cell per stroke.
* **Carried puller** (a middle-row side block leaves vertically in 2 rows instead of an
  elevator's 3): a sticky piston facing UP resting in the corner (-1,-1) is pushed into the ring
  cell (0,-1) by a piston at (-2,-1) (1 gt pulse: spit), pulls ML (pos+2 = (0,1)) to (0,0), is
  pulled back by the same piston (now a pull-type, its front empty), and a puller at (0,-2)
  finishes ML to (0,-1); anything already lowered into row -1 (BL, BM) rides one cell right with
  it. It is drivable in-plane only facing up: its quasi cell is (0,0), fed by a plain stone in
  the ring cell (-1,0) that a component at (-2,0) powers strongly. The top mirror (facing down)
  has its quasi cell at the finishing puller, so it cannot fire without that puller.

### Movable power

* **Redstone block shuttle:** a sticky piston pushing a redstone block from next to piston A to
  next to piston B switches A off at once (the block is a moving piston that tick) and B on 2 gt
  later (when it lands): one actuator, ordered "A then B"; pulled back it gives "B off then A
  on". Keep the shuttle piston on a steady level: a 2 gt pulse spits the redstone block, which is
  then placed in the block-event phase, the piston it powers fires in that same phase, before a
  block lifted 2 ticks earlier has landed, and a moving block is not dragged.
* **Riders:** a redstone block carried by a slime structure powers a piston at rest and lets it
  go when the structure moves. It must touch the piston itself: in a quasi-only position its
  return never updates the piston, which then stays retracted (gadget `rider-hold`). Two pushers
  can share one powered block. An observer carried by a structure fires 2 gt after every landing
  (`rider-observer`); a plain block glued to a structure and watched by a fixed observer is a
  motion trigger, a **flag** (`flag-observer`). A stone set on top of a slime column is dragged
  on every slime move, and an observer watching its rest cell fires on each, on both edges; the
  cell the stone is dragged into must stay empty.
* **A moving observer as merger + router:** a double pulse (an observer on a pulse-pulled
  piston) into a sticky piston that faces an observer: pulse 1 pushes the observer next to
  target A (2 gt: spit, it stays) and it fires A on landing; pulse 2 pulls it home and it fires
  again on landing, into a different cell (for example the empty quasi cell of a normal piston).
  One pulse per edge into A plus a second, later signal elsewhere, from 2 blocks.
* **A normal piston as a 1-block watched relay:** an observer fires a normal piston whose head
  pops into the cell another observer watches: one block where a conductor + a watched note
  block took two.

### Shaping pulses

* **Pulse merger** (gadgets `pulse-merge`, `merger-gap`): observer -> delay-2 repeater ->
  observer turns a double pulse (two 2 gt pulses up to 4 gt apart) into ONE 2 gt pulse: the
  repeater is on for exactly 4 gt and its off edge comes while the observer watching it is still
  on (the repeater's tick has the higher priority). Two pulses 8 gt apart stay two.
* **Lamp merger:** an observer watching a lamp fires once per lamp edge; with the pulses spaced
  so the lamp turns off and on in one tick (power ends exactly 4 gt before the next pulse) the
  observer fires once.
* **Lamp as merger input + delay:** two pulses (t9, t13) light a lamp that is also the input of
  a merger repeater (one pulse at t15); observers on the lamp fire on both lamp edges (the
  off-edge copy when it goes dark at t19).
* **Lamp as an asymmetric element:** a lamp next to a strongly powered input cell lights at once
  and goes dark 4 gt after; an observer on the lamp gives one pulse at the window's start and
  one 4 gt after its end. A lamp under the lever's dust acts as a level conductor that holds the
  pullers below it but goes dark 4 gt after the lever drops, so an observer watching it fires at
  t6 on one edge and t2 on the other (source: "t6 on open and t2 on close" for a lever that is
  on at rest).
* **Note-block window** (gadget `window-watch`): a note block under a cross dust carries the
  dust's window into the piston below it (a lift piston held extended for the window; its sticky
  retract pulls the lifted piece back), and an observer watching the note block fires once at
  each edge of the window, 2 gt later.
* **Note block next to the lever:** the lever hangs on an observer next to a note block; the
  lever weakly powers the note block, which another observer watches: a zero-delay relay that
  keeps power out of a neighbouring piston's quasi cell (door sf-holdA b38).
* **Early window** (gadget `early-window`): a delay-1 repeater reading a block fed by an
  observer pulse and by a delay-2 repeater from a SECOND observer gives a window at t+4..6 and
  t+8..12 (a 2 gt hole: a repeater's turn-off tick outranks another's turn-on tick), against
  t+10..18 for the plain pulse stretcher.
* **Two pulses 8 gt apart from one pull-type puller:** observer watching the puller -> stone ->
  delay-4 repeater -> observer watching the repeater: the puller's extend and pull retract give
  two output pulses (t13, t21 after a t0 pulse, on both edges).
* **Odd-parity reshaper:** an observer on a once-pulsed sticky piston fires twice (extend, then
  landing 4 gt later). Feed that double pulse into the empty quasi cell of a NORMAL piston and
  watch the normal piston with an observer: the downstream train is odd on both edges (3 on
  open), and three pulses toggle a pulsed sticky piston.
* **Pulse bridge** (gadget `pulse-bridge`): block, cross dust, block: an observer pulse moved
  one cell sideways into a repeater's back with 4 blocks.
* **Dust + its floor -> one block:** an observer's or repeater's output strongly powers a plain
  block, which feeds the next part directly (history.md, found by the local search).

### In one plane (flat doors)

* Repeaters cannot be locked and comparators have no side inputs (both need a diode at z+-1).
* A lever powers its neighbours: keep it off every piston and quasi cell it should not drive.
* Non-conducting full blocks (glass) hold dust, diodes and torches but are never powered, so
  they stop leaks into neighbouring pistons and quasi cells.
* Corner pistons of a 2-row bottom take no observer pulse: a corner piston K at (-1,-1) facing
  east is fed only from (-2,-1) (an east-pointing emitter) or (-1,-2) (an up-pointing one); an
  observer pointing into K would watch (-3,-1) or (-1,-3), outside a 7-wide, 2-row bottom, and
  repeaters and comparators have no floor there. K can only get dust on a powered (-2,-2), a
  conductor at (-1,-2) powered by an observer at (0,-2), or a torch (inverted).
* A piston fed only through another piston's cell can never fire alone (gadget `qc-shared`,
  history.md).
* A 7-wide flat box is cut into regions: row y = 1 is blocked end to end (side pistons, their
  gaps, the door), so each side's top and middle pistons are fed only from above and the bottom
  one only from below. Links between regions must be things one region moves and the other can
  watch (a level-held piston, a parked door block, a flag).

### Notes for fast doors

* Pistons react to a landing one tick late (block-entity phase): spit (2 gt pulse) or 0-tick to
  place blocks in the block-event phase instead.
* A reach-through puller (sticky, empty front, 0-ticked) moves a block two cells away without
  ever having its head next to it at rest: the cheapest way to pull C or T out of a cell that
  was full at rest.
* Arm 0-tick partners after the flip (section 9), and give each one a power source it can shove
  away.
* Use one update to order several pistons (W,E,D,U,N,S), or chain them through their own moves:
  every piston action updates its base's and front cell's neighbours.

## 12. Floors for the fastest 3x3 door

A door is open when no cell of the opening or walkway blocks (moving blocks block) from that tick
on; closed when the 9 cells hold their rest blocks (placed) from that tick on.

**Floors (solid doors): open >= 4 gt, close >= 1 gt; open + close >= 5.**

| door | open / close | blocks | note |
|---|---|---|---|
| ideal-input machine (`open-4-close3`) | 4 / 3 | - | scripted inputs, identical in the official server |
| tick-door (`tick-door-open4-229b`) | 4 / 15 | 229 | the open-4 machine wired to a lever |
| speed-2 | 9 / 7 | 112 (c1) | best wired open + close |
| speed track's topology bound | 7 / 6 | - | T leaves through the centre's exit cell |
| symmetric-control family (fc2f) | 22 / 9 | 41 | family floor for open: 22 |

### Open >= 4 (the source's proof)

1. Nothing moves before tick 1 (section 1).
2. C is 2 cells from the outside of the 3x3 x 7 box in every direction (4 along z), and a piston
   moves a block 1 cell per move: C needs 2 moves, the second one taking it out.
3. A cell a block moves out of is air at once, so "open" is the tick in which C's last move
   STARTS (if everything else is out by then).
4. C can only move again once it is a placed block. After a pull, a drag or a plain push it is
   placed in the block-entity phase of t+2, so the next move is at t+3. The only early placement
   is `finalTick` by a sticky piston retracting while C is the block two ahead of it, i.e. C was
   the FIRST block of that piston's push: the piston's base is then adjacent to C's start cell,
   and all six cells next to the centre are in the opening or the walkway. That base is a
   `moving_piston` for 2 gt after the retract and can be moved out at t'+3 at the earliest.
5. Either way open >= t + 3 with t >= 1: open >= 4.

### An open-4 schedule (gadget `open-4`, ideal inputs)

T must leave its cell before C's first move, and not through E (C's puller sits there): it goes
sideways through its corner, which costs it 2 moves too (k1 into the corner, k4 out).

| tick | moves | gadget |
|---|---|---|
| k1 | the lever's piston shoves the redstone block feeding the pullers' dust line: the 6 side / bottom pullers (extended at rest, heads touching their blocks) retract in the same phase: ML, BL, MR, BR, TR, B out; TL pulled up into (0,3) | `instant-off` |
| k1 | TL's departure updates P_T at (-1,2) (armed after the flip): it extends into TL's empty cell and is 0-ticked by its partner X_T (in P_T's quasi cell): reach-through, T pulled into (0,2) (lands k3) | `zero-tick-reach` |
| k1 | T's departure updates A' at E (quasi-powered through F's cell): it extends into T's cell, its partner X_A shoves that source up: reach-through, C pulled into T's cell (lands k3); the shoved redstone block lands next to F's quasi cell at k3 and arms F silently | `center-exit` |
| k4 | an observer chain off the lever (2 observers: k4) unpowers the two aside pullers: A' pulled out of E, P_T pulled out of (-1,2) | `observer-delay` |
| k4 | E's emptying updates F (above E): F extends into E, its partner X_F shoves its quasi source, F retracts: reach-through, C pulled into E: C out | `center-exit` |
| k4 | the same at (-2,2): G_T reach-pulls T out of TL's cell into (-1,2): T out, open at 4 | `center-exit` |

The gadget has 9 stone door blocks, 7 plain pullers, the 4 reach-through pullers with their
partners and the 2 aside pullers. The opening is full at k3 (T and C sit in the top edge cells)
and clear from k4 on.

### Close

Close is measured on placed blocks, so a 0-tick placement counts in the tick it happens. C needs
2 moves in (E -> T's cell -> centre) and T must enter its cell after C went through.

| close | how |
|---|---|
| 1-3 (same-tick relays) | C pushed E -> T's cell by a 0-ticked piston above E (`zero-tick`); a piston carried into E by a 0-tick fires in the same phase (`zero-tick-onplace`) and 0-ticks C into the centre: gadget `center-return` places C in the edge cell at k1 and in the centre at k2. T returns through its corner: gadget `corner-return` places T in the corner at k1, in its own cell at k2, the corner block at k3. The carried pistons must be ordered AFTER the cell they enter is emptied: a relay (a piston next to the cell that pushes a conductor off a dust step feeding the pusher, `instant-on`) does it in the same tick, the tick boundary in the next. The 6 other blocks only need plain pushes at k1 (landing k3) |
| 3 (built, `open-4-close3`) | both carried-piston chains start at the k1/k2 boundary, A''s first; T's chain is padded with one piston so P_T's push comes one round after A' left T's cell: C and T placed at k2, TL at k3 (5 more padding pistons would bring TL into k2: close 2) |
| 4 (built, `open-4-cycle`) | k1 F 0-ticks C into T's cell and G_T 0-ticks T into TL's cell, the 6 plain pullers push their blocks home (land k3); k2 A' is 0-ticked back into E, fires as it is placed and 0-ticks C into the centre; k3 the same for P_T and T; k4 TL's puller 0-ticks TL home. One carried-piston chain per tick |
| 6 (speed track) | C pushed into T's cell at k1 (spit), T pushed into E, F re-extends at k4 pushing [T, C] together; C is the second block, not finalized: lands k6 (the boards show 7) |

### What a lever-driven open-4 must provide

| when | input | what can provide it |
|---|---|---|
| open k0 | power off at the 7 plain pullers, TL's first (TL's puller must run before B's) | one lever-fired piston shoving the redstone block of a dust net feeding them (`instant-off`); the dust order is position dependent, so feed TL's puller separately and first |
| open k0 | arm the k1 partners and P_T silently | the lever itself next to a quasi cell, or dust -> conductor -> quasi cell from 3+ cells away |
| open k3->k4 | the aside pullers retract at k4 | an observer pair off the lever (k4) firing a piston that shoves their redstone block |
| open k3->k4 | arm the k4 partners | the same k4 pulse, or a redstone block's own landing |
| open, idle | disarm the 4 partners | any time while open |
| close k0 | the 6 plain pullers' power back at k1 | an instant-on on the lever-off edge (a conductor pulled off a dust step); a redstone block merely pulled back lands at k3 and the pushes would land at k6 |
| close k0 | the F and G_T 0-ticks | the lever-off edge reaching the pistons before their partners (update order), partners armed after the open |
| close k1->k2 | A' carried back into E, fires, C home at k2 | an observer pulse at k2 off the lever-off edge |
| close k2->k3 | P_T carried back, fires, T home at k3 | a k2 observer + 1 more link (odd: k3 comes from a k1 piston's observer) |
| close k3->k4 | TL home at k4 | an observer pair at k4 |

The source's speed-track topology (T pulled into E at k1, lands k3; a pusher shoves [A', T] at k4
so a puller takes E; C into T's cell at k4, out at k7) has floor 7; its best wired door opens at
9 with an odd-tick pulse.

## 13. Gadget catalog (palette-only gadgets)

Each is a small design with a drive script in the source repository's `designs/gadgets/`; the
descriptions give enough to rebuild them.

| gadget | blocks | what it proves |
|---|---|---|
| `dual-edge` | observer | an observer watching a lever pulses 2 gt, 2 gt after both flips |
| `lever-observer` | observer under the lever | the lever's support is an observer facing up that watches it and fires out of its back |
| `lever-tap` | repeater | a repeater reading the lever feeds a net that the lever's block cannot back-feed |
| `observer-delay` | 3 observers | a chain of observers delays 2 gt per observer, no floors, around corners |
| `pulse-stretch` | repeater | a short pulse comes out exactly the repeater's delay long (2 gt -> 8 gt); a second pulse while on is swallowed |
| `pulse-merge` | observer + delay-2 repeater + observer | a double pulse (two 2 gt pulses up to 4 gt apart) becomes exactly one 2 gt pulse |
| `merger-gap` | delay-2 repeater + observer | two pulses 4 gt apart come out as one, two pulses 8 gt apart as two |
| `early-window` | 2 observers + repeaters | a window at t+4..6 and t+8..12 instead of t+10..18 |
| `repeater-lock` | 2 repeaters | a latch: a locked repeater keeps its output, follows its input again once unlocked |
| `pulse-bridge` | block, cross dust, block | an observer pulse moved one cell sideways into a repeater's back with 4 blocks |
| `torch-delay` | wall lever, block, wall torch, sticky piston | a torch inverts with 2 gt |
| `torch-link` | lever, block, torch, sticky piston (extended at rest), observer | a level-driven piston moves once per edge, so its watcher pulses exactly once per edge |
| `lamp-fall-delay` | lamp + observer | lamp: rise 0 gt, fall 4 gt |
| `rb-lamp` | redstone block on a moving structure + lamp + observer | asymmetric even delay: m+4 on the move out, m+6 on the move back |
| `target-tap` | target block | a target beside a straight dust line is powered by it; a torch on the target reads the line |
| `window-watch` | note block + cross dust + observer | the note block carries the dust's window into the piston below; the observer fires at both window edges, 2 gt later |
| `note-watch` | note block + observer | (variant; the source only says its drive script states what it proves) |
| `dust-below` | observer + stone + dust | a dust directly under a block strongly powered by an observer lights |
| `dust-reach` | dust | a dust changing power updates the neighbours of its neighbours: a held piston two cells away re-checks and retracts |
| `stack-feed` | cross dust + floor + observer | one pulse fires a stack of 3 retracted sticky pistons |
| `qc-bud` | repeater, piston | a piston is powered by anything powering the cell above it, but only acts when updated |
| `head-qc` | piston head | a piston is quasi-powered through the head of the piston above it |
| `qc-shared` | (history.md) | a piston fed only through another piston's cell can never fire alone |
| `silent-hold` | block + repeater | a quasi-powered piston ignores its source switching on and off until a neighbour update (variants `silent-hold-rb`, `hold-2rep`) |
| `head-forward` | piston head | an extended piston held unpowered retracts when a block is placed next to its head |
| `spit` | observer + sticky piston | a 2 gt pulse makes a sticky piston push its block and leave it (retract type 2) |
| `pulse-toggle` | observer + retracted sticky piston | one 2 gt pulse per lever edge: the on pulse pulls the block, the off pulse pushes it back and spits it |
| `order-flip` | push-type + pull-type pulse pistons | the two act in opposite orders on the two lever edges when fed the same pulse |
| `pump` | observer + repeater + sticky piston | a 3+ gt pulse (repeater delay 2 = 4 gt) pushes a 2-block line one cell and pulls back only the first block |
| `blocked-push` | 2 sticky pistons | a piston whose push line starts with an extended piston does nothing; it pushes that piston once it has retracted |
| `stopper-release` | held-extended sticky piston + observer + puller | an early pulse is blocked by a held head; the piston fires when a puller removes the block from its line |
| `no-retry` | piston, moving block | a powered piston whose push line holds a moving block queues nothing and never retries when it lands |
| `landing-fire` | piston moved onto a powered spot | a piston pushed onto a powered cell extends as it lands, no neighbour update needed |
| `landing-next-tick` | lever, piston, redstone block, piston, repeater | a pushed block lands in the block-entity phase of t+2: a piston it powers acts at t+3 (k4 for a lever piston), a delay-1 repeater reading it turns on at k5 |
| `spit-saves-tick` | observer, sticky piston, redstone block, piston | a spit block is placed in the block-event phase of the retract tick, so the piston it powers extends in that tick (k4 instead of k5) |
| `event-order` | 2 pistons | block events are FIFO in update order W, E, D, U, N, S |
| `landing-race` | 2 sticky pistons, redstone block (+ a sculk sensor in the source's build) | `no-retry` + `event-order`: which of two pistons a landing block triggers first depends on orientation (section 2) |
| `instant-off` | lever, piston, redstone block, dust, sticky piston | a moved redstone block darkens its dust line in the same phase; the extended piston at the far end retracts in tick 1 |
| `instant-on` | lever, piston, conductor on a dust step | pushing a conductor off a dust step lights the upper line in the same phase; the piston it feeds extends in tick 1 |
| `odd-observer` | lever, piston, 2 observers | an observer watching a cell a lever-fired piston changes fires at k3, a chained one at k5 |
| `odd-pulse` | piston + redstone block + repeater + note block + observer | pulse k5..k7 on the on flip, k7..k9 on the off flip |
| `comparator-odd` | lever, sticky piston, 2 redstone blocks, comparator | output off at k5, back on at k3 after the off flip |
| `zero-tick` | 2 pistons (ideal inputs) | a sticky piston that extends and retracts inside one block-event phase places the block it pushed in that tick; the 0-tick comes from a silently armed partner updated by the push that shoves the redstone block powering it |
| `zero-tick-normal` | 2 pistons | the same with a normal piston: the block lands at tick 3 |
| `zero-tick-reach` | 2 pistons | a 0-ticked sticky piston with an empty front cell pulls the block two cells away; it lands 2 gt later |
| `zero-tick-onplace` | 3 pistons | a piston carried into place by a 0-tick extends in the same phase |
| `zero-tick-observer` | zero-tick + observer | an observer watching a 0-ticked piston's head cell fires once, 2 gt later |
| `zero-tick-pulse` | zero-tick + a second partner + repeater, comparator, lamp | a 0-tick power pulse: lamp lit at once and dark 4 gt later, repeater on 2 gt later for its full delay, comparator never changes |
| `double-move` | 2 sticky pistons + 2 partners (ideal inputs) | one block, two moves, both placed, in one tick |
| `center-exit` | 4 pistons + 2 partners (ideal inputs) | the centre's two-move exit at the floor: out of the opening at t4 |
| `center-return` | 4 pistons + 3 partners (ideal inputs) | C placed in the edge cell at k1 and in the centre at k2 |
| `corner-return` | 4 pistons + 4 partners (ideal inputs) | T placed in the corner at k1, in its cell at k2, the corner block at k3 |
| `open-4` | 9 door blocks + 13 pistons + 4 partners (ideal inputs) | a whole 3x3 opening clear at tick 4; `open-4-cycle` closes it in 4, `open-4-close3` in 3 |
| `killer-chain` | pistons + partners (ideal inputs) | two BUD-triggered reach-through 0-ticks in one tick: when TR's puller pulls TR up, W (quasi-powered at rest, its push blocked by the door row) extends into the emptied corner and its base update fires its killer; the chain tick-door's open 4 is built from |
| `slime-nonstick` | slime, glazed terracotta, obsidian | slime drags stone but not glazed terracotta or obsidian |
| `honey-slime` | slime + honey | slime and honey never stick to each other |
| `slime-rider` | retracted sticky piston | a retracted sticky piston right under a slime row rides it |
| `rider-observer` | observer on a slime structure | fires 2 gt after every landing, out of its back wherever it landed |
| `rider-hold` | redstone block on a slime structure | powers a piston only in one position; the piston ignores every update until the structure comes back |
| `flag-observer` | stone + observer | a block glued to a moving slime structure, watched by a fixed observer: one 2 gt pulse after each move |

## 14. Vanilla confirmation

The source replays each gadget in the official 26.3 server (rest state placed with
`setblock ... strict`, the lever used by a bot player) and compares a watch box after every action
and every tick, at 4 positions. It reports PASS, identical at 4 positions, for: the zero-tick
family, `instant-off`, `instant-on`, `landing-next-tick`, `spit-saves-tick`, `odd-observer`,
`comparator-odd`, `center-exit`, `double-move`, `open-4`, `open-4-cycle`, `open-4-close3`,
`center-return`, `corner-return`, `event-order`, `torch-delay`; and for the older lever-only
gadgets (`dual-edge`, `dust-below`, `early-window`, `flag-observer`, `head-qc`, `hold-2rep`,
`lamp-fall-delay`, `landing-fire`, `lever-observer`, `note-watch`, `observer-delay`, `odd-pulse`,
`order-flip`, `pulse-bridge`, `pulse-stretch`, `pulse-toggle`, `pump`, `repeater-lock`,
`slime-rider`, `spit`, `target-tap`) and those replayed with `/setblock` (`blocked-push`,
`dust-reach`, `head-forward`, `honey-slime`, `lever-tap`, `no-retry`, `qc-bud`, `rider-hold`,
`rider-observer`, `silent-hold`, `silent-hold-rb`, `slime-nonstick`, `stack-feed`). Its summary:
"the whole gadget library behaves identically in the official server". For its simulator
(redsim) it reports 0 differences from the game in 100,000 random circuits and in 100,000 random
piston cases, plus 328 of 328 archived doors and 72 of 72 gadgets identical.
