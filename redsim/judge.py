"""The judge: does a design work as a piston door, and how big is it.

The rules are those of vjeux/redstonepedia (docs/rules.md there, docs/rules.md here), and this
file follows its `piston-door` crate check for check. The judge talks to a world through a small
interface, so the same code runs on the simulator (`redsim.world.SimWorld`) and on the real game
(`minecraft.worker.World`).

    report = verify(SimWorld(), Design.load("door.txt"))
    report.ok, report.reason, report.volume, report.dims, report.open_ticks, report.close_ticks
"""
from .design import block_name
from .errors import Unsupported

CYCLES = 3
MAX_TICKS = 400
MAX_PERIOD_EXTRA = 8
BASE_OFFSETS = [(0, 0, 0), (-7, 3, 5), (5, -11, -6), (-3, 40, 2)]

FORBIDDEN = {
    "command_block", "chain_command_block", "repeating_command_block", "structure_block", "structure_void",
    "jigsaw", "barrier", "light", "bedrock", "end_portal_frame", "end_portal", "end_gateway", "nether_portal",
    "spawner", "trial_spawner", "vault", "reinforced_deepslate", "budding_amethyst", "petrified_oak_slab",
    "moving_piston", "test_block", "test_instance_block", "frosted_ice", "bubble_column", "fire", "soul_fire",
}
MECHANISM = {
    "slime_block", "honey_block", "piston", "sticky_piston", "piston_head", "moving_piston", "observer",
    "redstone_block", "redstone_lamp", "target", "repeater", "comparator", "redstone_wire", "redstone_torch",
    "redstone_wall_torch", "lever", "dispenser", "dropper", "hopper", "note_block", "tnt",
}


def extra_offsets(n):
    """`n` more test positions, the same pseudo-random ones redstonepedia's judge uses."""
    seed = 0x9E3779B97F4A7C15
    mask = (1 << 64) - 1

    def nxt(m):
        nonlocal seed
        seed ^= (seed << 13) & mask
        seed ^= seed >> 7
        seed ^= (seed << 17) & mask
        return seed % (2 * m + 1) - m
    return [(nxt(13), nxt(40), nxt(13)) for _ in range(n)]


def offsets(extra=28):
    return BASE_OFFSETS + extra_offsets(extra)


class Spec:
    """Where the opening and the lever are."""

    def __init__(self, design):
        if "door" not in design.ports or "lever" not in design.ports:
            raise ValueError("a design needs 'port door: x y z' and 'port lever: x y z'")
        self.door, self.lever = design.ports["door"], design.ports["lever"]
        self.size = design.door_size()
        self.along_z = design.along_z()

    def _w(self, i):
        return (0, 0, i) if self.along_z else (i, 0, 0)

    def _d(self, i):
        return (i, 0, 0) if self.along_z else (0, 0, i)

    def door_cells(self):
        x, y, z = self.door
        return [(x + self._w(dw)[0], y + dy, z + self._w(dw)[2])
                for dy in reversed(range(self.size)) for dw in range(self.size)]

    def columns(self, depth):
        """The opening's columns in front of and behind the door, `depth` blocks each way."""
        x, y, z = self.door
        out = []
        for dd in range(-depth, depth + 1):
            if dd == 0:
                continue
            d = self._d(dd)
            for dy in range(self.size):
                for dw in range(self.size):
                    s = self._w(dw)
                    out.append((x + s[0] + d[0], y + dy, z + s[2] + d[2]))
        return out

    def walkway(self):
        return self.columns(3)


class Report:
    def __init__(self):
        self.ok = False
        self.reason = None          # why it failed
        self.position = None        # the offset it failed at
        self.blocks = 0             # blocks placed (piston heads not counted)
        self.volume = None          # bounding box of everything over rest and every tick, lever excluded
        self.dims = None            # (width, height, depth)
        self.open_ticks = None      # worst of the cycles at the first position
        self.close_ticks = None
        self.cycles = []            # (open_ticks, open_settle, close_ticks, close_settle) at the first position
        self.warnings = []
        self.frames = None          # with keep_frames: (rest, [open frames], [close frames]) of the first cycle

    def __repr__(self):
        if not self.ok:
            return f"<broken: {self.reason}>"
        return f"<works: volume {self.volume} {self.dims}, {self.blocks} blocks, open {self.open_ticks}, close {self.close_ticks}>"


class Broken(Exception):
    pass


def legality_problems(design):
    out = []
    for pos, state in sorted(design.blocks.items()):
        name = block_name(state)
        if name in FORBIDDEN:
            out.append(f"{name} at {list(pos)} is not something a survival player can place")
    return out


def _settled_from(flags):
    """1-based index of the first entry from which every entry is true."""
    first = None
    for i, ok in enumerate(flags):
        if ok:
            if first is None:
                first = i + 1
        else:
            first = None
    return first


def _closed_problems(world, cells, spec):
    out = []
    door = spec.door_cells()
    first = cells.get(door[0], "minecraft:air")
    for p in door:
        s = cells.get(p, "minecraft:air")
        if s != first:
            out.append(f"door cell {list(p)} is {s}, but the door must be {len(door)} identical blocks ({first})")
        if block_name(s) in MECHANISM:
            out.append(f"door cell {list(p)} is {s}, not a plain door block")
    for p in door:
        s = cells.get(p, "minecraft:air")
        if not world.flags(s)[1] or block_name(s) == "moving_piston":
            out.append(f"door cell {list(p)} is {s}")
    for p in spec.walkway():
        s = cells.get(p)
        if s and world.flags(s)[0]:
            out.append(f"walkway cell {list(p)} is blocked by {s}")
    return out


def _open_problems(world, cells, spec):
    out = []
    for p in spec.door_cells() + spec.walkway():
        s = cells.get(p)
        if s and (world.flags(s)[0] or block_name(s) == "moving_piston"):
            out.append(f"{list(p)} is {s}")
    return out


def watch_box(design, spec):
    lo, hi = design.bounds()
    lo, hi = list(lo), list(hi)
    for p in spec.door_cells() + spec.walkway():
        for i in range(3):
            lo[i] = min(lo[i], p[i])
            hi[i] = max(hi[i], p[i])
    return tuple(v - 2 for v in lo), tuple(v + 2 for v in hi)


def place(world, design):
    """Paste the design as written, work out the wire shapes, let every block look at its
    neighbours once (in x, y, z order), then run until nothing is pending."""
    blocks = design.block_list()
    world.clear()
    world.set_raw(blocks)
    world.update_shape([p for p, s in blocks if block_name(s) == "redstone_wire"])
    world.update_self([p for p, _ in blocks])


def _verify_at(world, design, spec, report, first, keep_frames):
    place(world, design)
    lo, hi = watch_box(design, spec)
    _, idle = world.step(MAX_TICKS, lo, hi)
    if not idle:
        raise Broken(f"the build never settles after placement ({MAX_TICKS} ticks)")
    rest = world.get(lo, hi)
    floating, ticking = world.unsupported(lo, hi)
    if floating:
        raise Broken("unsupported blocks (they could not stand there in survival): "
                     + "; ".join(f"{list(p)} {rest.get(p, '?')}" for p in floating))
    if ticking:
        raise Broken("blocks that change by themselves over time (random ticks): "
                     + "; ".join(f"{list(p)} {rest.get(p, '?')}" for p in ticking))
    if first:
        for p, s in design.block_list():
            if rest.get(p, "minecraft:air") != s:
                report.warnings.append(f"not at rest as written: {list(p)} {s} became {rest.get(p, 'minecraft:air')}")
    problems = _closed_problems(world, rest, spec)
    if problems:
        raise Broken("not closed at rest: " + "; ".join(problems))
    reach = max(hi[0] - lo[0], hi[2] - lo[2]) + 1
    clutter = [f"{list(p)} {rest[p]}" for p in spec.columns(reach) if p in rest]
    if clutter:
        raise Broken("blocks in front of or behind the door (the 3x3 columns in front of and behind the opening "
                     "must be empty at rest, at any distance): " + "; ".join(clutter))
    if block_name(rest.get(spec.lever, "minecraft:air")) != "lever":
        raise Broken(f"port lever {list(spec.lever)} is {rest.get(spec.lever, 'minecraft:air')}, expected a lever")
    door = spec.door_cells()
    closed_door = [rest.get(p) for p in door]

    swept = None
    if first:
        swept = set(p for p in rest if p != spec.lever)

    seen_closed = [rest]
    periodic = False
    for cycle in range(CYCLES + MAX_PERIOD_EXTRA):
        if cycle >= CYCLES and periodic:
            break
        if world.use(spec.lever) != "lever":
            raise Broken(f"cycle {cycle}: the lever is gone")
        frames, idle = world.step(MAX_TICKS, lo, hi)
        if not idle:
            raise Broken(f"cycle {cycle}: still moving {len(frames)} ticks after opening")
        problems = _open_problems(world, frames[-1], spec)
        if problems:
            raise Broken(f"cycle {cycle}: not open after the lever was switched on: " + "; ".join(problems))
        open_ticks = _settled_from([not _open_problems(world, f, spec) for f in frames])
        if world.entities():
            raise Broken(f"cycle {cycle}: entities appeared while opening (something broke and dropped)")
        open_frames = frames

        if world.use(spec.lever) != "lever":
            raise Broken(f"cycle {cycle}: the lever is gone")
        frames, idle = world.step(MAX_TICKS, lo, hi)
        if not idle:
            raise Broken(f"cycle {cycle}: still moving {len(frames)} ticks after closing")
        last = frames[-1]
        now = [last.get(p) for p in door]
        if now != closed_door:
            raise Broken(f"cycle {cycle}: door not restored: " + "; ".join(
                f"{list(p)} is {a or 'minecraft:air'}, was {b}" for p, a, b in zip(door, now, closed_door) if a != b))
        problems = _closed_problems(world, last, spec)
        if problems:
            raise Broken(f"cycle {cycle}: not closed after the lever was switched back: " + "; ".join(problems))
        if any(s == last for s in seen_closed):
            periodic = True
        else:
            seen_closed.append(last)
        if world.entities():
            raise Broken(f"cycle {cycle}: entities appeared while closing (something broke and dropped)")
        close_ticks = _settled_from([[f.get(p) for p in door] == closed_door for f in frames])
        if first:
            report.cycles.append((open_ticks, len(open_frames), close_ticks, len(frames)))
            for f in open_frames + frames:
                swept.update(f)
            if keep_frames and cycle == 0:
                report.frames = (rest, open_frames, frames)
    if not periodic:
        raise Broken(f"the build never comes back to a closed state it had before within {CYCLES + MAX_PERIOD_EXTRA} "
                     "cycles (its internal state drifts, so it may stop working)")
    if first:
        swept.discard(spec.lever)
        w_axis, d_axis = (2, 0) if spec.along_z else (0, 2)
        dims = tuple(max(p[a] for p in swept) - min(p[a] for p in swept) + 1 for a in (w_axis, 1, d_axis))
        report.dims = dims
        report.volume = dims[0] * dims[1] * dims[2]


def verify(world, design, positions=None, keep_frames=False):
    """Judge `design` in `world` at every offset in `positions` (default: the 4 base positions).

    A record needs `positions=offsets()`: 32 positions. Dust updates its neighbours in an order
    that depends on where it stands, so a door can work in one place and fail in another.
    """
    report = Report()
    report.blocks = design.placed_blocks()
    try:
        illegal = legality_problems(design)
        if illegal:
            raise Broken("illegal design: " + "; ".join(illegal))
        if not design.blocks:
            raise Broken("empty design")
        for key in ("entity", "nbt", "relay"):
            if key in design.meta:
                raise Unsupported(f"'{key}:' lines (entity doors, container contents, tile modules) are outside this judge")
        spec = Spec(design)
        if spec.size not in (2, 3):
            raise Broken("door-size must be 2 or 3")
        for i, off in enumerate(positions or BASE_OFFSETS):
            report.position = off
            d = design.translated(off)
            _verify_at(world, d, Spec(d), report, i == 0, keep_frames)
    except Broken as e:
        report.reason = str(e)
        return report
    except Unsupported:
        raise
    except ValueError as e:
        report.reason = f"cannot judge: {e}"
        return report
    report.ok = True
    report.position = None
    report.open_ticks = max(c[0] for c in report.cycles[:CYCLES])
    report.close_ticks = max(c[2] for c in report.cycles[:CYCLES])
    return report
