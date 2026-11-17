"""A re-implementation of the parts of Minecraft: Java Edition that drive piston doors.

It follows the game's own structure rather than an abstract circuit model, because compact
doors depend on exactly the things an abstract model drops:

  * the game tick: scheduled block ticks, then block events, then block entities
  * the neighbour-update stack (depth first, updates raised inside a handler are deferred)
  * shape updates, which are what observers react to
  * scheduled-tick priorities and de-duplication
  * pistons as block events, moving blocks as block entities that take two ticks
  * quasi-connectivity, block dropping on short pulses, slime/honey structures, the push limit
  * redstone wire, including the HashSet iteration order that makes it position dependent

Block states are interned `St` objects, positions are (x, y, z) tuples. Supported blocks are
the usual door palette: solid blocks, glass, obsidian, glazed terracotta, pistons, slime,
honey, wire, repeaters, comparators, torches, redstone blocks, observers, targets, note
blocks and levers.
"""
import heapq

from .blockdata import INSTRUMENT, PLAIN as PLAIN_DATA

# ---------------------------------------------------------------- directions

DOWN, UP, NORTH, SOUTH, WEST, EAST = "down", "up", "north", "south", "west", "east"
VEC = {DOWN: (0, -1, 0), UP: (0, 1, 0), NORTH: (0, 0, -1), SOUTH: (0, 0, 1), WEST: (-1, 0, 0), EAST: (1, 0, 0)}
OPP = {DOWN: UP, UP: DOWN, NORTH: SOUTH, SOUTH: NORTH, WEST: EAST, EAST: WEST}
D6 = (DOWN, UP, NORTH, SOUTH, WEST, EAST)             # Direction.values()
HORIZONTAL = (NORTH, EAST, SOUTH, WEST)               # Direction.Plane.HORIZONTAL
UPDATE_ORDER = (WEST, EAST, DOWN, UP, NORTH, SOUTH)   # NeighborUpdater.UPDATE_ORDER
SHAPE_ORDER = (WEST, EAST, NORTH, SOUTH, DOWN, UP)    # BlockBehaviour.UPDATE_SHAPE_ORDER
CW = {NORTH: EAST, EAST: SOUTH, SOUTH: WEST, WEST: NORTH}
CCW = {v: k for k, v in CW.items()}
AXIS = {DOWN: "y", UP: "y", NORTH: "z", SOUTH: "z", WEST: "x", EAST: "x"}


def add(p, d, k=1):
    v = VEC[d]
    return (p[0] + v[0] * k, p[1] + v[1] * k, p[2] + v[2] * k)


# setBlock flags
F_NEIGHBORS, F_CLIENTS, F_INVISIBLE, F_KNOWN_SHAPE, F_NO_DROPS, F_MOVED = 1, 2, 4, 16, 32, 64
F_SKIP_WIRE_SHAPE, F_SKIP_ON_PLACE = 128, 512

# ---------------------------------------------------------------- block states


class St:
    __slots__ = ("id", "p", "_w")

    def __repr__(self):
        if not self.p:
            return self.id
        return self.id + "[" + ",".join(f"{k}={v}" for k, v in sorted(self.p.items())) + "]"


_INTERN = {}


def S(bid, **props):
    key = (bid, tuple(sorted(props.items())))
    st = _INTERN.get(key)
    if st is None:
        st = St()
        st.id, st.p, st._w = bid, props, {}
        _INTERN[key] = st
    return st


def W(st, **kw):
    """`st` with some properties replaced."""
    key = tuple(kw.items())
    r = st._w.get(key)
    if r is None:
        r = st._w[key] = S(st.id, **{**st.p, **kw})
    return r


AIR = S("air")

# Building blocks: full cubes with no behaviour (tools/gen_blocks.py reads them from the game).
PLAIN = set(PLAIN_DATA)

DEFAULTS = {
    "piston": {"facing": NORTH, "extended": "false"},
    "sticky_piston": {"facing": NORTH, "extended": "false"},
    "piston_head": {"facing": NORTH, "type": "normal", "short": "false"},
    "redstone_wire": {"north": "none", "south": "none", "east": "none", "west": "none", "power": "0"},
    "repeater": {"facing": NORTH, "delay": "1", "locked": "false", "powered": "false"},
    "comparator": {"facing": NORTH, "mode": "compare", "powered": "false"},
    "redstone_torch": {"lit": "true"},
    "redstone_wall_torch": {"facing": NORTH, "lit": "true"},
    "observer": {"facing": SOUTH, "powered": "false"},
    "target": {"power": "0"},
    "note_block": {"note": "0", "powered": "false", "instrument": "harp"},
    "lever": {"face": "wall", "facing": NORTH, "powered": "false"},
    "redstone_lamp": {"lit": "false"},
    "dropper": {"facing": NORTH, "triggered": "false"},
}
BULBS = ("waxed_copper_bulb", "waxed_exposed_copper_bulb", "waxed_weathered_copper_bulb", "waxed_oxidized_copper_bulb")
for _b in BULBS:
    DEFAULTS[_b] = {"lit": "false", "powered": "false"}
SIMPLE = {"redstone_block", "slime_block", "honey_block"}
KNOWN = PLAIN | SIMPLE | set(DEFAULTS)


def make_state(block_id, props=None):
    bid = block_id.split(":", 1)[-1]
    if bid == "air":
        return AIR
    if bid not in KNOWN:
        raise ValueError(f"unsupported block {block_id}")
    p = dict(PLAIN_DATA[bid][2] if bid in PLAIN_DATA else DEFAULTS.get(bid, {}))
    for k, v in (props or {}).items():
        if k not in p:
            raise ValueError(f"{bid} has no property {k}")
        p[k] = str(v).lower() if isinstance(v, bool) else str(v)
    return S(bid, **p)


PISTONS = ("piston", "sticky_piston")
DIODES = ("repeater", "comparator")
TORCHES = ("redstone_torch", "redstone_wall_torch")
FULL_CUBES = PLAIN | {"redstone_block", "slime_block", "observer", "target", "note_block", "redstone_lamp", "dropper"} | set(BULBS)
CONDUCTORS = {n for n, v in PLAIN_DATA.items() if v[0]} | {"slime_block", "target", "note_block", "redstone_lamp", "dropper"}
SIGNAL_SOURCES = {"redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch", "lever",
                  "redstone_block", "observer", "target"}
PUSH_DESTROY = {"redstone_wire", "repeater", "comparator", "redstone_torch", "redstone_wall_torch", "lever"}
PUSH_BLOCK = {n for n, v in PLAIN_DATA.items() if v[1] == "block"} | {"piston_head", "moving_piston", "dropper"}
PUSH_ONLY = {n for n, v in PLAIN_DATA.items() if v[1] == "push_only"}


def is_conductor(st):
    return st.id in CONDUCTORS      # pistons never conduct, even retracted


def sturdy(st, face, kind="full"):
    """BlockState.isFaceSturdy. `kind` is full (wire, wall torch, lever), rigid (diodes) or center (torch)."""
    i = st.id
    if i in FULL_CUBES:
        return True
    if i in PISTONS:
        if st.p["extended"] == "false":
            return True
        f = st.p["facing"]
        return face == OPP[f] or (kind == "center" and face != f)
    if i == "piston_head":
        return face == st.p["facing"]
    return False


def instrument_for(below):
    return INSTRUMENT.get(below.id, "harp")


def lever_attach(st):
    """Direction from the lever to the block it is attached to."""
    face = st.p["face"]
    return DOWN if face == "floor" else UP if face == "ceiling" else OPP[st.p["facing"]]


def _java_bucket(p):
    h = ((p[1] + p[2] * 31) * 31 + p[0]) & 0xFFFFFFFF
    return (h ^ (h >> 16)) & 15


# ---------------------------------------------------------------- moving blocks


class Moving:
    """PistonMovingBlockEntity."""
    __slots__ = ("pos", "moved", "direction", "extending", "source", "progress", "progress_o", "last_ticked", "removed")

    def __init__(self, pos, moved, direction, extending, source):
        self.pos, self.moved, self.direction, self.extending, self.source = pos, moved, direction, extending, source
        self.progress = self.progress_o = 0.0
        self.last_ticked = -1
        self.removed = False


class World:
    def __init__(self, origin=(0, 0, 0), repeater_unit=2, observer_delay=2, observer_pulse=2, push_limit=12):
        self.origin = origin
        self.repeater_unit, self.observer_delay, self.observer_pulse, self.push_limit = \
            repeater_unit, observer_delay, observer_pulse, push_limit
        self.blocks = {}
        self.now = 0
        self.handling_tick = False
        # scheduled ticks
        self._heap, self._order = [], 0
        self._pending, self._running = set(), set()
        # block events
        self._events, self._event_set = [], set()
        # block entities
        self.moving = {}
        self._tickers = []
        self.comparator_out = {}
        # neighbour updater
        self._stack, self._added, self._count = [], [], 0
        self._wire_signals = True
        self._toggles = []
        # reporting
        self.touched = set()
        self.drops = []

    # ------------------------------------------------------------ basics

    def get(self, pos):
        return self.blocks.get(pos, AIR)

    def raw_set(self, pos, st):
        """Silent placement: no hooks and no updates."""
        self.touched.add(pos)
        if st is AIR:
            self.blocks.pop(pos, None)
        else:
            self.blocks[pos] = st

    def set_block(self, pos, st, flags):
        old = self.blocks.get(pos, AIR)
        if old is st:
            return False
        self.raw_set(pos, st)
        changed = old.id != st.id
        moved = bool(flags & F_MOVED)
        if changed:
            if old.id == "moving_piston":
                be = self.moving.get(pos)
                if be is not None:
                    self._final_tick(be)
                    if self.blocks.get(pos, AIR) is not st:   # finalTick placed something; restore ours
                        self.raw_set(pos, st)
            elif old.id == "comparator":
                self.comparator_out.pop(pos, None)
            if (flags & F_NEIGHBORS) or moved:
                self._after_removal(pos, old, moved)
        if not flags & F_SKIP_ON_PLACE:
            self._on_place(pos, st, old, moved)
        if self.blocks.get(pos, AIR) is st:
            if flags & F_NEIGHBORS:
                self.update_neighbors_at(pos, old.id)
                if st.id in BULBS or st.id == "dropper":
                    self._update_comparators(pos, st.id)
            if not flags & F_KNOWN_SHAPE:
                f = flags & ~(F_NEIGHBORS | F_NO_DROPS)
                self._indirect_shapes(old, pos, f)
                self._neighbour_shapes(st, pos, f)
                self._indirect_shapes(st, pos, f)
        return True

    def _sturdy(self, pos, face, kind="full", st=None):
        """isFaceSturdy at a position. A moving block's shape comes from its block entity."""
        if st is None:
            st = self.blocks.get(pos, AIR)
        if st.id != "moving_piston":
            return sturdy(st, face, kind)
        be = self.moving.get(pos)
        if be is None:
            return False
        if be.source and not be.extending:      # a retracting piston keeps its extended base shape
            return sturdy(W(be.moved, extended="true"), face, kind)
        if be.progress >= 1.0:
            return sturdy(be.moved, face, kind)
        return False

    def _update_comparators(self, pos, src):
        """Level.updateNeighbourForOutputSignal: comparators beside a block they can read, or one
        solid block away from it, look again."""
        for d in HORIZONTAL:
            q = add(pos, d)
            b = self.get(q)
            if b.id == "comparator":
                self.neighbor_changed(q, src)
            elif is_conductor(b):
                q = add(q, d)
                if self.get(q).id == "comparator":
                    self.neighbor_changed(q, src)

    def _bulb_check(self, pos, st):
        on = self.has_neighbor_signal(pos)
        if on != (st.p["powered"] == "true"):
            new = st
            if st.p["powered"] == "false":      # a rising edge toggles the light
                new = W(st, lit="false" if st.p["lit"] == "true" else "true")
            self.set_block(pos, W(new, powered="true" if on else "false"), 3)

    def destroy(self, pos, drop=True):
        st = self.get(pos)
        if st is AIR:
            return
        if drop:
            self.drops.append((self.now, pos, st.id))
        self.set_block(pos, AIR, 3)

    # ------------------------------------------------------------ neighbour updater

    def _push(self, u):
        nested = self._count > 0
        self._count += 1
        if nested:
            self._added.append(u)
            return
        self._stack.append(u)
        stack, added = self._stack, self._added
        try:
            while stack or added:
                if added:
                    stack.extend(reversed(added))
                    added.clear()
                u = stack[-1]
                while not added:
                    if not self._run_update(u):
                        stack.pop()
                        break
        finally:
            stack.clear()
            added.clear()
            self._count = 0

    def _run_update(self, u):
        kind = u[0]
        if kind == 0:      # one block
            self._neighbor_changed(u[1], u[2])
            return False
        if kind == 1:      # the six neighbours of a block, one per call
            _, pos, src, skip, state = u
            i = state[0]
            self._neighbor_changed(add(pos, UPDATE_ORDER[i]), src)
            i += 1
            if i < 6 and UPDATE_ORDER[i] == skip:
                i += 1
            state[0] = i
            return i < 6
        _, direction, pos, npos, nstate, flags = u
        st = self.get(pos)
        if not (flags & F_SKIP_WIRE_SHAPE and st.id == "redstone_wire"):
            new = self._update_shape(st, pos, direction, npos, nstate)
            self._update_or_destroy(st, new, pos, flags)
        return False

    def neighbor_changed(self, pos, src):
        self._push((0, pos, src))

    def update_neighbors_at(self, pos, src, skip=None):
        self._push((1, pos, src, skip, [1 if UPDATE_ORDER[0] == skip else 0]))

    def _shape_changed(self, direction, pos, npos, nstate, flags):
        self._push((2, direction, pos, npos, nstate, flags))

    def _neighbour_shapes(self, st, pos, flags):
        for d in SHAPE_ORDER:
            self._shape_changed(OPP[d], add(pos, d), pos, st, flags)

    def _indirect_shapes(self, st, pos, flags):
        if st.id != "redstone_wire":
            return
        for d in HORIZONTAL:
            if st.p[d] == "none":
                continue
            side = add(pos, d)
            if self.get(side).id == "redstone_wire":
                continue
            for v in (DOWN, UP):
                q = add(side, v)
                if self.get(q).id == "redstone_wire":
                    back = add(q, OPP[d])
                    self._shape_changed(OPP[d], q, back, self.get(back), flags)

    def _update_or_destroy(self, old, new, pos, flags):
        if new is old:
            return
        if new is AIR:
            self.destroy(pos, not flags & F_NO_DROPS)
        else:
            self.set_block(pos, new, flags & ~F_NO_DROPS)

    def update_from_neighbour_shapes(self, st, pos):
        for d in SHAPE_ORDER:
            q = add(pos, d)
            st = self._update_shape(st, pos, d, q, self.get(q))
        return st

    # ------------------------------------------------------------ signals

    def _block_signal(self, st, pos, d):
        """BlockState.getSignal. `d` points from the asking block to this one."""
        i = st.id
        if i == "redstone_wire":
            if not self._wire_signals or d == DOWN:
                return 0
            power = int(st.p["power"])
            if power == 0 or d == UP:
                return power
            return power if self._wire_connections(st, pos).p[OPP[d]] != "none" else 0
        if i == "redstone_block":
            return 15
        if i == "repeater":
            return 15 if st.p["powered"] == "true" and st.p["facing"] == d else 0
        if i == "observer":
            return 15 if st.p["powered"] == "true" and st.p["facing"] == d else 0
        if i == "comparator":
            return self.comparator_out.get(pos, 0) if st.p["powered"] == "true" and st.p["facing"] == d else 0
        if i == "redstone_torch":
            return 15 if st.p["lit"] == "true" and d != UP else 0
        if i == "redstone_wall_torch":
            return 15 if st.p["lit"] == "true" and st.p["facing"] != d else 0
        if i == "lever":
            return 15 if st.p["powered"] == "true" else 0
        if i == "target":
            return int(st.p["power"])
        return 0

    def _block_direct(self, st, pos, d):
        i = st.id
        if i in ("redstone_wire", "repeater", "observer", "comparator"):
            return self._block_signal(st, pos, d)
        if i in TORCHES:
            return self._block_signal(st, pos, d) if d == DOWN else 0
        if i == "lever":
            return 15 if st.p["powered"] == "true" and OPP[lever_attach(st)] == d else 0
        return 0

    def direct_signal_to(self, pos):
        best = 0
        for d in D6:
            q = add(pos, d)
            st = self.blocks.get(q)
            if st is not None:
                v = self._block_direct(st, q, d)
                if v > best:
                    best = v
                    if best >= 15:
                        return best
        return best

    def signal(self, pos, d):
        """Level.getSignal."""
        st = self.blocks.get(pos)
        if st is None:
            return 0
        v = self._block_signal(st, pos, d)
        if v < 15 and is_conductor(st):
            v = max(v, self.direct_signal_to(pos))
        return v

    def has_neighbor_signal(self, pos):
        return any(self.signal(add(pos, d), d) > 0 for d in D6)

    def best_neighbor_signal(self, pos):
        best = 0
        for d in D6:
            v = self.signal(add(pos, d), d)
            if v >= 15:
                return 15
            best = max(best, v)
        return best

    # ------------------------------------------------------------ scheduled ticks and block events

    def schedule(self, pos, block, delay, priority=0):
        key = (pos, block)
        if key in self._pending:
            return
        self._pending.add(key)
        self._order += 1
        heapq.heappush(self._heap, (self.now + delay, priority, self._order, pos, block))

    def has_scheduled(self, pos, block):
        return (pos, block) in self._pending

    def will_tick_this_tick(self, pos, block):
        return (pos, block) in self._running

    def block_event(self, pos, block, kind, data):
        e = (pos, block, kind, data)
        if e not in self._event_set:
            self._event_set.add(e)
            self._events.append(e)

    def tick(self):
        """One ServerLevel.tick."""
        self.handling_tick = True
        self.now += 1
        due = []
        heap = self._heap
        while heap and heap[0][0] <= self.now:
            t = heapq.heappop(heap)
            due.append(t)
            key = (t[3], t[4])
            self._pending.discard(key)
            self._running.add(key)
        due.sort(key=lambda t: (t[1], t[2]))
        for _, _, _, pos, block in due:
            self._running.discard((pos, block))
            st = self.get(pos)
            if st.id == block:
                self._scheduled_tick(pos, st)
        i = 0
        events = self._events
        while i < len(events):
            e = events[i]
            i += 1
            self._event_set.discard(e)
            pos, block, kind, data = e
            st = self.get(pos)
            if st.id == block and block in PISTONS:
                self._piston_event(pos, st, kind)
        events.clear()
        self.handling_tick = False
        tickers = self._tickers
        self._tickers = []
        keep = []
        for be in tickers:
            if be.removed:
                continue
            self._tick_moving(be)
            if not be.removed:
                keep.append(be)
        self._tickers = keep + self._tickers

    def idle(self):
        return not self._heap and not self._events and not self.moving

    # ------------------------------------------------------------ per-block hooks

    def _neighbor_changed(self, pos, src):
        st = self.blocks.get(pos)
        if st is None:
            return
        i = st.id
        if i == "redstone_wire":
            if self._sturdy(add(pos, DOWN), UP):
                self._wire_update_power(pos, st)
            else:
                self.destroy(pos)
        elif i in PISTONS:
            self._check_if_extend(pos, st)
        elif i == "repeater" or i == "comparator":
            if self._sturdy(add(pos, DOWN), UP, "rigid"):
                if i == "repeater":
                    self._repeater_check(pos, st)
                else:
                    self._comparator_check(pos, st)
            else:
                self.destroy(pos)
                for d in D6:
                    self.update_neighbors_at(add(pos, d), i)
        elif i in TORCHES:
            if (st.p["lit"] == "true") == self._torch_input(pos, st) and not self.will_tick_this_tick(pos, i):
                self.schedule(pos, i, 2)
        elif i == "piston_head":
            if self._head_survives(pos, st):
                self.neighbor_changed(add(pos, OPP[st.p["facing"]]), src)
        elif i == "note_block":
            on = self.has_neighbor_signal(pos)
            if on != (st.p["powered"] == "true"):
                # Playing the note is a block event. It changes no block, but while it is queued
                # the world is not idle.
                if on and self.get(add(pos, UP)) is AIR:
                    self.block_event(pos, i, 0, 0)
                self.set_block(pos, W(st, powered="true" if on else "false"), 3)
        elif i in BULBS:
            self._bulb_check(pos, st)
        elif i == "dropper":
            on = self.has_neighbor_signal(pos) or self.has_neighbor_signal(add(pos, UP))
            triggered = st.p["triggered"] == "true"
            if on and not triggered:
                self.schedule(pos, i, 4)
                self.set_block(pos, W(st, triggered="true"), 2)
            elif not on and triggered:
                self.set_block(pos, W(st, triggered="false"), 2)
        elif i == "redstone_lamp":
            lit = st.p["lit"] == "true"
            if lit != self.has_neighbor_signal(pos):
                if lit:
                    self.schedule(pos, i, 4)
                else:
                    self.set_block(pos, W(st, lit="true"), 2)

    def _update_shape(self, st, pos, d, npos, nstate):
        i = st.id
        if i == "redstone_wire":
            if d == DOWN:
                return st if self._sturdy(npos, UP, "full", nstate) else AIR
            if d == UP:
                return self._wire_connections(st, pos)
            side = self._wire_side(pos, d)
            if (side != "none") == (st.p[d] != "none") and not _is_cross(st):
                return W(st, **{d: side})
            cross = S("redstone_wire", **{**{h: "side" for h in HORIZONTAL}, "power": st.p["power"], d: side})
            return self._wire_connections(cross, pos)
        if i == "observer":
            if st.p["facing"] == d and st.p["powered"] == "false" and not self.has_scheduled(pos, "observer"):
                self.schedule(pos, "observer", self.observer_delay)
            return st
        if i == "repeater":
            if d == DOWN and not self._sturdy(npos, UP, "rigid", nstate):
                return AIR
            if AXIS[d] != AXIS[st.p["facing"]]:
                return W(st, locked="true" if self._repeater_locked(pos, st) else "false")
            return st
        if i == "comparator":
            return AIR if d == DOWN and not self._sturdy(npos, UP, "rigid", nstate) else st
        if i == "redstone_torch":
            return AIR if d == DOWN and not self._sturdy(npos, UP, "center", nstate) else st
        if i == "redstone_wall_torch":
            return AIR if OPP[d] == st.p["facing"] and not self._sturdy(npos, st.p["facing"], "full", nstate) else st
        if i == "lever":
            a = lever_attach(st)
            return AIR if d == a and not self._sturdy(npos, OPP[a], "full", nstate) else st
        if i == "piston_head":
            return AIR if OPP[d] == st.p["facing"] and not self._head_survives(pos, st) else st
        if i == "note_block":
            if d == DOWN or d == UP:      # any vertical shape update re-reads the block below
                return W(st, instrument=instrument_for(self.get(add(pos, DOWN))))
            return st
        return st

    def _on_place(self, pos, st, old, moved):
        i = st.id
        if i == "repeater" or i == "comparator":
            self._update_in_front(pos, st)
        elif i in TORCHES:
            for d in D6:
                self.update_neighbors_at(add(pos, d), i)
        elif i == "observer":
            if old.id != i and st.p["powered"] == "true" and not self.has_scheduled(pos, i):
                off = W(st, powered="false")
                self.set_block(pos, off, 18)
                self._update_in_front(pos, off)
        elif i in PISTONS:
            if old.id != i and pos not in self.moving:
                self._check_if_extend(pos, st)
        elif i in BULBS:
            if old.id != i:
                self._bulb_check(pos, st)
        elif i == "target":
            # a target that arrives powered (it can only start that way) switches itself off
            if old.id != i and st.p["power"] != "0" and not self.has_scheduled(pos, i):
                self.set_block(pos, W(st, power="0"), 18)

    def _after_removal(self, pos, old, moved):
        i = old.id
        if i == "observer":
            if old.p["powered"] == "true" and self.has_scheduled(pos, i):
                self._update_in_front(pos, W(old, powered="false"))
        elif moved:
            return
        elif i in TORCHES:
            for d in D6:
                self.update_neighbors_at(add(pos, d), i)
        elif i == "redstone_wire":
            for d in D6:
                self.update_neighbors_at(add(pos, d), i)
            self._wire_update_power(pos, old)
            for d in HORIZONTAL:
                self._wire_corner(add(pos, d))
            for d in HORIZONTAL:
                q = add(pos, d)
                self._wire_corner(add(q, UP if is_conductor(self.get(q)) else DOWN))
        elif i in DIODES:
            self._update_in_front(pos, old)
        elif i == "lever":
            if old.p["powered"] == "true":
                self.update_neighbors_at(pos, i)
                self.update_neighbors_at(add(pos, lever_attach(old)), i)

    def _scheduled_tick(self, pos, st):
        i = st.id
        if i == "repeater":
            if self._repeater_locked(pos, st):
                return
            powered = st.p["powered"] == "true"
            should = self._diode_input(pos, st) > 0
            if powered and not should:
                self.set_block(pos, W(st, powered="false"), 2)
            elif not powered:
                self.set_block(pos, W(st, powered="true"), 2)
                if not should:
                    self.schedule(pos, i, int(st.p["delay"]) * self.repeater_unit, -2)
        elif i == "comparator":
            self._comparator_refresh(pos, st)
        elif i == "observer":
            if st.p["powered"] == "true":
                self.set_block(pos, W(st, powered="false"), 2)
            else:
                self.set_block(pos, W(st, powered="true"), 2)
                self.schedule(pos, i, self.observer_pulse)
            self._update_in_front(pos, st)
        elif i == "redstone_lamp":
            if st.p["lit"] == "true" and not self.has_neighbor_signal(pos):
                self.set_block(pos, W(st, lit="false"), 2)
        elif i in TORCHES:
            on = self._torch_input(pos, st)
            self._toggles = [t for t in self._toggles if self.now - t[1] <= 60]
            if st.p["lit"] == "true":
                if on:
                    self.set_block(pos, W(st, lit="false"), 3)
                    self._toggles.append((pos, self.now))
                    if sum(1 for t in self._toggles if t[0] == pos) >= 8:
                        self.schedule(pos, self.get(pos).id, 160)
            elif not on and sum(1 for t in self._toggles if t[0] == pos) < 8:
                self.set_block(pos, W(st, lit="true"), 3)

    # ------------------------------------------------------------ lever

    def pull_lever(self, pos):
        st = self.get(pos)
        if st.id != "lever":
            return False
        st = W(st, powered="false" if st.p["powered"] == "true" else "true")
        self.set_block(pos, st, 3)
        self.update_neighbors_at(pos, "lever")
        self.update_neighbors_at(add(pos, lever_attach(st)), "lever")
        return True

    # ------------------------------------------------------------ torches, diodes, observers

    def _torch_input(self, pos, st):
        d = DOWN if st.id == "redstone_torch" else OPP[st.p["facing"]]
        return self.signal(add(pos, d), d) > 0

    def _update_in_front(self, pos, st):
        f = st.p["facing"]
        front = add(pos, OPP[f])
        self.neighbor_changed(front, st.id)
        self.update_neighbors_at(front, st.id, f)

    def _diode_input(self, pos, st):
        f = st.p["facing"]
        q = add(pos, f)
        v = self.signal(q, f)
        if v >= 15:
            return v
        b = self.get(q)
        return max(v, int(b.p["power"]) if b.id == "redstone_wire" else 0)

    def _side_input(self, pos, st, diodes_only):
        best = 0
        for d in (CW[st.p["facing"]], CCW[st.p["facing"]]):
            q = add(pos, d)
            b = self.get(q)
            if diodes_only:
                v = self._block_direct(b, q, d) if b.id in DIODES else 0
            elif b.id == "redstone_block":
                v = 15
            elif b.id == "redstone_wire":
                v = int(b.p["power"])
            else:
                v = self._block_direct(b, q, d) if b.id in SIGNAL_SOURCES else 0
            best = max(best, v)
        return best

    def _repeater_locked(self, pos, st):
        return self._side_input(pos, st, True) > 0

    def _prioritize(self, pos, st):
        d = OPP[st.p["facing"]]
        b = self.get(add(pos, d))
        return b.id in DIODES and b.p["facing"] != d

    def _repeater_check(self, pos, st):
        if self._repeater_locked(pos, st):
            return
        powered = st.p["powered"] == "true"
        should = self._diode_input(pos, st) > 0
        if powered != should and not self.will_tick_this_tick(pos, "repeater"):
            priority = -3 if self._prioritize(pos, st) else -2 if powered else -1
            self.schedule(pos, "repeater", int(st.p["delay"]) * self.repeater_unit, priority)

    def _analog(self, st):
        """What a comparator reads from a block, or None if it is not readable. A dropper is a
        container, always empty here; a copper bulb reads 15 while lit."""
        if st.id == "dropper":
            return 0
        if st.id in BULBS:
            return 15 if st.p["lit"] == "true" else 0
        return None

    def _comparator_input(self, pos, st):
        """ComparatorBlock.getInputSignal: a readable block in front, or behind one solid block,
        replaces the redstone signal."""
        i = self._diode_input(pos, st)
        f = st.p["facing"]
        q = add(pos, f)
        b = self.get(q)
        a = self._analog(b)
        if a is not None:
            return a
        if i < 15 and is_conductor(b):
            a = self._analog(self.get(add(q, f)))
            if a is not None:
                return a
        return i

    def _comparator_levels(self, pos, st):
        i = self._comparator_input(pos, st)
        j = self._side_input(pos, st, False) if i else 0
        return i, j

    def _comparator_output(self, pos, st):
        i, j = self._comparator_levels(pos, st)
        if i == 0 or j > i:
            return 0
        return i - j if st.p["mode"] == "subtract" else i

    def _comparator_should(self, pos, st):
        i, j = self._comparator_levels(pos, st)
        if i == 0:
            return False
        return i > j or (i == j and st.p["mode"] == "compare")

    def _comparator_check(self, pos, st):
        if self.will_tick_this_tick(pos, "comparator"):
            return
        if self._comparator_output(pos, st) != self.comparator_out.get(pos, 0) \
                or (st.p["powered"] == "true") != self._comparator_should(pos, st):
            self.schedule(pos, "comparator", 2, -1 if self._prioritize(pos, st) else 0)

    def _comparator_refresh(self, pos, st):
        new = self._comparator_output(pos, st)
        old = self.comparator_out.get(pos, 0)
        self.comparator_out[pos] = new
        if old != new or st.p["mode"] == "compare":
            should = self._comparator_should(pos, st)
            powered = st.p["powered"] == "true"
            if powered and not should:
                self.set_block(pos, W(st, powered="false"), 2)
            elif not powered and should:
                self.set_block(pos, W(st, powered="true"), 2)
            self._update_in_front(pos, st)

    # ------------------------------------------------------------ redstone wire

    def _connects(self, st, d):
        i = st.id
        if i == "redstone_wire":
            return True
        if i == "repeater":
            return AXIS[st.p["facing"]] == AXIS[d]
        if i == "observer":
            return st.p["facing"] == d
        return i in SIGNAL_SOURCES

    def _wire_side(self, pos, d, open_above=None):
        if open_above is None:
            open_above = not is_conductor(self.get(add(pos, UP)))
        q = add(pos, d)
        b = self.get(q)
        if open_above and self._sturdy(q, UP, "full", b) and self.get(add(q, UP)).id == "redstone_wire":
            return "up" if self._sturdy(q, OPP[d], "full", b) else "side"
        if not self._connects(b, d) and (is_conductor(b) or self.get(add(q, DOWN)).id != "redstone_wire"):
            return "none"
        return "side"

    def _wire_connections(self, st, pos):
        """RedStoneWireBlock.getConnectionState."""
        was_dot = _is_dot(st)
        open_above = not is_conductor(self.get(add(pos, UP)))
        c = {d: self._wire_side(pos, d, open_above) for d in HORIZONTAL}
        n, s, e, w = (c[d] != "none" for d in (NORTH, SOUTH, EAST, WEST))
        if not (was_dot and not (n or s or e or w)):
            if not w and not n and not s:
                c[WEST] = "side"
            if not e and not n and not s:
                c[EAST] = "side"
            if not n and not e and not w:
                c[NORTH] = "side"
            if not s and not e and not w:
                c[SOUTH] = "side"
        return S("redstone_wire", power=st.p["power"], **c)

    def _wire_target(self, pos):
        self._wire_signals = False
        try:
            block = self.best_neighbor_signal(pos)
        finally:
            self._wire_signals = True
        if block == 15:
            return 15
        best = 0
        above_open = not is_conductor(self.get(add(pos, UP)))
        for d in HORIZONTAL:
            q = add(pos, d)
            b = self.get(q)
            if b.id == "redstone_wire":
                best = max(best, int(b.p["power"]))
            if is_conductor(b):
                if above_open:
                    u = self.get(add(q, UP))
                    if u.id == "redstone_wire":
                        best = max(best, int(u.p["power"]))
            else:
                u = self.get(add(q, DOWN))
                if u.id == "redstone_wire":
                    best = max(best, int(u.p["power"]))
        return max(block, best - 1)

    def _wire_update_power(self, pos, st):
        target = self._wire_target(pos)
        if int(st.p["power"]) == target:
            return
        if self.get(pos) is st:
            self.set_block(pos, W(st, power=str(target)), 2)
        # A java.util.HashSet of the wire and its six neighbours: the iteration order, and so
        # the update order, depends on the absolute position.
        o = self.origin
        cells = [pos] + [add(pos, d) for d in D6]
        buckets = sorted(range(7), key=lambda k: (_java_bucket((cells[k][0] + o[0], cells[k][1] + o[1], cells[k][2] + o[2])), k))
        for k in buckets:
            self.update_neighbors_at(cells[k], "redstone_wire")

    def _wire_corner(self, pos):
        if self.get(pos).id == "redstone_wire":
            self.update_neighbors_at(pos, "redstone_wire")
            for d in D6:
                self.update_neighbors_at(add(pos, d), "redstone_wire")

    # ------------------------------------------------------------ pistons

    def _piston_powered(self, pos, facing):
        for d in D6:
            if d != facing and self.signal(add(pos, d), d) > 0:
                return True
        if self.signal(pos, DOWN) > 0:
            return True
        above = add(pos, UP)
        for d in D6:
            if d != DOWN and self.signal(add(above, d), d) > 0:
                return True
        return False

    def _head_survives(self, pos, st):
        f = st.p["facing"]
        base = self.get(add(pos, OPP[f]))
        if base.id == "moving_piston":
            return base.p["facing"] == f
        want = "sticky_piston" if st.p["type"] == "sticky" else "piston"
        return base.id == want and base.p["extended"] == "true" and base.p["facing"] == f

    def _check_if_extend(self, pos, st):
        f = st.p["facing"]
        powered = self._piston_powered(pos, f)
        extended = st.p["extended"] == "true"
        if powered and not extended:
            if self._resolve(pos, f, True) is not None:
                self.block_event(pos, st.id, 0, f)
        elif not powered and extended:
            q = add(pos, f, 2)
            b = self.get(q)
            kind = 1
            if b.id == "moving_piston" and b.p["facing"] == f:
                be = self.moving.get(q)
                if be is not None and be.extending and (be.progress_o < 0.5 or self.now == be.last_ticked or self.handling_tick):
                    kind = 2
            self.block_event(pos, st.id, kind, f)

    def _piston_event(self, pos, st, kind):
        f = st.p["facing"]
        powered = self._piston_powered(pos, f)
        if powered and kind in (1, 2):
            self.set_block(pos, W(st, extended="true"), 2)
            return
        if not powered and kind == 0:
            return
        sticky = st.id == "sticky_piston"
        if kind == 0:
            if not self._move_blocks(pos, f, True, sticky):
                return
            self.set_block(pos, W(st, extended="true"), 67)
            return
        head = add(pos, f)
        be = self.moving.get(head)
        if be is not None:
            self._final_tick(be)
        moving = S("moving_piston", facing=f, type="sticky" if sticky else "normal")
        self.set_block(pos, moving, 276)
        self._add_moving(Moving(pos, S(st.id, facing=f, extended="false"), f, False, True))
        self.update_neighbors_at(pos, "moving_piston")
        self._neighbour_shapes(moving, pos, 2)
        if sticky:
            q = add(pos, f, 2)
            b = self.get(q)
            done = False
            if b.id == "moving_piston":
                be = self.moving.get(q)
                if be is not None and be.direction == f and be.extending:
                    self._final_tick(be)
                    done = True
            if not done:
                if kind != 1 or b is AIR or not self._pushable(b, q, OPP[f], False, f) \
                        or (self._reaction(b) != "normal" and b.id not in PISTONS):
                    self.set_block(head, AIR, 3)
                else:
                    self._move_blocks(pos, f, False, sticky)
        else:
            self.set_block(head, AIR, 3)

    @staticmethod
    def _reaction(st):
        i = st.id
        if i in PUSH_DESTROY:
            return "destroy"
        if i in PUSH_BLOCK:
            return "block"
        if i in PUSH_ONLY:
            return "push_only"
        return "normal"

    def _pushable(self, st, pos, move_dir, allow_destroy, piston_facing):
        if st is AIR:
            return True
        i = st.id
        if i in PISTONS:
            return st.p["extended"] == "false"
        r = self._reaction(st)
        if r == "block":
            return False
        if r == "destroy":
            return allow_destroy
        if r == "push_only":
            return move_dir == piston_facing
        return True

    def _resolve(self, piston, facing, extending):
        """PistonStructureResolver. Returns (to_push, to_destroy) or None if the move is blocked."""
        push_dir = facing if extending else OPP[facing]
        start = add(piston, facing) if extending else add(piston, facing, 2)
        to_push, to_destroy = [], []
        limit = self.push_limit
        get = self.get
        back = OPP[push_dir]

        def sticky(st):
            return st.id == "slime_block" or st.id == "honey_block"

        def stick(a, b):
            if a.id == "honey_block" and b.id == "slime_block":
                return False
            if a.id == "slime_block" and b.id == "honey_block":
                return False
            return sticky(a) or sticky(b)

        def add_line(origin, direction):
            st = get(origin)
            if st is AIR:
                return True
            if not self._pushable(st, origin, push_dir, False, direction):
                return True
            if origin == piston or origin in to_push:
                return True
            i = 1
            if i + len(to_push) > limit:
                return False
            while sticky(st):
                p = add(origin, back, i)
                prev = st
                st = get(p)
                if st is AIR or not stick(prev, st) or not self._pushable(st, p, push_dir, False, back) or p == piston:
                    break
                i += 1
                if i + len(to_push) > limit:
                    return False
            j = 0
            for k in range(i - 1, -1, -1):
                to_push.append(add(origin, back, k))
                j += 1
            k = 1
            while True:
                p = add(origin, push_dir, k)
                if p in to_push:
                    at = to_push.index(p)
                    a, b, c = to_push[:at], to_push[len(to_push) - j:], to_push[at:len(to_push) - j]
                    to_push[:] = a + b + c
                    for m in range(at + j + 1):
                        q = to_push[m]
                        if sticky(get(q)) and not add_branches(q):
                            return False
                    return True
                st = get(p)
                if st is AIR:
                    return True
                if not self._pushable(st, p, push_dir, True, push_dir) or p == piston:
                    return False
                if self._reaction(st) == "destroy":
                    to_destroy.append(p)
                    return True
                if len(to_push) >= limit:
                    return False
                to_push.append(p)
                j += 1
                k += 1

        def add_branches(origin):
            st = get(origin)
            for d in D6:
                if AXIS[d] != AXIS[push_dir]:
                    p = add(origin, d)
                    if stick(get(p), st) and not add_line(p, d):
                        return False
            return True

        st = get(start)
        if not self._pushable(st, start, push_dir, False, facing):
            if extending and self._reaction(st) == "destroy":
                return [], [start]
            return None
        if not add_line(start, push_dir):
            return None
        i = 0
        while i < len(to_push):
            p = to_push[i]
            if sticky(get(p)) and not add_branches(p):
                return None
            i += 1
        return to_push, to_destroy

    def _hash_order(self, cells, peak):
        """Iteration order of a java.util.HashMap that held `peak` keys and now holds `cells`."""
        n = 16
        while peak > n * 3 // 4:
            n *= 2
        o = self.origin

        def bucket(p):
            h = ((p[1] + o[1] + (p[2] + o[2]) * 31) * 31 + p[0] + o[0]) & 0xFFFFFFFF
            return (h ^ (h >> 16)) & (n - 1)
        return [c for _, _, c in sorted((bucket(c), k, c) for k, c in enumerate(cells))]

    def _add_moving(self, be):
        self.moving[be.pos] = be
        self._tickers.append(be)

    def _move_blocks(self, pos, facing, extending, sticky):
        head = add(pos, facing)
        if not extending and self.get(head).id == "piston_head":
            self.set_block(head, AIR, 276)
        res = self._resolve(pos, facing, extending)
        if res is None:
            return False
        to_push, to_destroy = res
        states = [self.get(p) for p in to_push]
        left = dict(zip(to_push, states))
        move_dir = facing if extending else OPP[facing]
        destroyed = []
        for p in reversed(to_destroy):
            st = self.get(p)
            self.drops.append((self.now, p, st.id))
            self.set_block(p, AIR, 18)
            destroyed.append((p, st))
        moving = S("moving_piston", facing=facing, type="normal")
        for k in range(len(to_push) - 1, -1, -1):
            dest = add(to_push[k], move_dir)
            left.pop(dest, None)
            self.set_block(dest, moving, 324)
            self._add_moving(Moving(dest, states[k], facing, extending, False))
        if extending:
            head_state = S("piston_head", facing=facing, type="sticky" if sticky else "normal", short="false")
            left.pop(head, None)
            self.set_block(head, S("moving_piston", facing=facing, type="sticky" if sticky else "normal"), 324)
            self._add_moving(Moving(head, head_state, facing, True, True))
        # `left` is a java.util.HashMap in the game, so vacated cells are visited in hash order.
        vacated = self._hash_order(list(left), len(to_push))
        for p in vacated:
            self.set_block(p, AIR, 82)
        for p in vacated:
            self._indirect_shapes(left[p], p, 2)
            self._neighbour_shapes(AIR, p, 2)
        for p, st in destroyed:
            self._after_removal(p, st, False)
            self._indirect_shapes(st, p, 2)
            self.update_neighbors_at(p, st.id)
        for k in range(len(to_push) - 1, -1, -1):
            self.update_neighbors_at(to_push[k], states[k].id)
        if extending:
            self.update_neighbors_at(head, "piston_head")
        return True

    def _tick_moving(self, be):
        be.last_ticked = self.now
        be.progress_o = be.progress
        if be.progress_o < 1.0:
            be.progress = min(1.0, be.progress + 0.5)
            return
        pos = be.pos
        be.removed = True
        if self.moving.get(pos) is be:
            del self.moving[pos]
        if self.get(pos).id != "moving_piston":
            return
        st = self.update_from_neighbour_shapes(be.moved, pos)
        if st is AIR:
            self.set_block(pos, be.moved, 84)
            self._update_or_destroy(be.moved, st, pos, 3)
        else:
            self.set_block(pos, st, 67)
            self.neighbor_changed(pos, st.id)

    def _final_tick(self, be):
        if be.removed or be.progress_o >= 1.0:
            return
        be.progress = be.progress_o = 1.0
        be.removed = True
        pos = be.pos
        if self.moving.get(pos) is be:
            del self.moving[pos]
        if self.get(pos).id != "moving_piston":
            return
        st = AIR if be.source else self.update_from_neighbour_shapes(be.moved, pos)
        self.set_block(pos, st, 3)
        self.neighbor_changed(pos, st.id)


def _is_dot(st):
    p = st.p
    return p["north"] == "none" and p["south"] == "none" and p["east"] == "none" and p["west"] == "none"


def _is_cross(st):
    p = st.p
    return p["north"] != "none" and p["south"] != "none" and p["east"] != "none" and p["west"] != "none"
