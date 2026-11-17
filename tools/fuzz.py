"""Differential fuzzing: random contraptions on the simulator and on the real game.

    python tools/fuzz.py [--seeds A B] [--profile dense|doors|logic|slime] [--wild] [--shift dx dy dz] [--save DIR]
    python tools/fuzz.py --shrink case.txt

A case is a small box packed with random components and one lever. Both worlds place it the way
the judge does, settle, and get the lever flipped six times; every block of the watched box must
be the same on every tick. `--wild` starts components in arbitrary states (powered repeaters,
unlit torches, dust with wrong shapes) and puts the lever on any face. `--shrink` removes blocks
from a differing case while it still differs. Needs python -m minecraft.setup.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from both import Recorder, first_difference  # noqa: E402
from minecraft.worker import Worker  # noqa: E402
from redsim import judge  # noqa: E402
from redsim.design import Design, format_state  # noqa: E402
from redsim.world import SimWorld  # noqa: E402

H4 = ("north", "south", "east", "west")
D6 = H4 + ("up", "down")
VEC = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
SOLID = ("stone", "stone", "smooth_stone", "iron_block", "white_wool", "oak_log", "target", "note_block", "redstone_block",
         "slime_block", "redstone_lamp", "dropper", "glass", "obsidian", "quartz_block", "waxed_copper_bulb")
NEEDS_FLOOR = ("redstone_wire", "repeater", "comparator", "redstone_torch")

PROFILES = {
    "dense": [("air", 30), ("stone", 12), ("redstone_wire", 14), ("repeater", 6), ("comparator", 3), ("redstone_torch", 3),
              ("redstone_wall_torch", 2), ("sticky_piston", 8), ("piston", 4), ("observer", 6), ("slime_block", 3),
              ("honey_block", 2), ("redstone_block", 2), ("target", 2), ("note_block", 2), ("glass", 2), ("obsidian", 1),
              ("white_glazed_terracotta", 1), ("redstone_lamp", 2), ("dropper", 2), ("white_wool", 1), ("oak_log", 1),
              ("waxed_copper_bulb", 2)],
    "doors": [("air", 34), ("stone", 18), ("redstone_wire", 10), ("repeater", 5), ("sticky_piston", 12), ("piston", 3),
              ("observer", 9), ("slime_block", 4), ("honey_block", 2), ("redstone_block", 2), ("target", 1), ("glass", 1),
              ("comparator", 1), ("redstone_torch", 1), ("dropper", 2), ("note_block", 1)],
    "logic": [("air", 28), ("stone", 20), ("redstone_wire", 22), ("repeater", 8), ("comparator", 6), ("redstone_torch", 6),
              ("redstone_wall_torch", 5), ("sticky_piston", 2), ("observer", 3), ("redstone_block", 1), ("target", 2),
              ("note_block", 2), ("glass", 2), ("slime_block", 1), ("redstone_lamp", 3), ("dropper", 3), ("waxed_copper_bulb", 4)],
    "slime": [("air", 40), ("stone", 8), ("sticky_piston", 14), ("piston", 6), ("observer", 12), ("slime_block", 9),
              ("honey_block", 6), ("redstone_block", 5), ("white_glazed_terracotta", 2), ("obsidian", 2), ("note_block", 2),
              ("glass", 1), ("target", 1), ("dropper", 1), ("crying_obsidian", 1)],
}


def make_case(seed, profile="dense", wild=False):
    rng = random.Random(seed)
    names, weights = zip(*PROFILES[profile])
    sx, sy, sz = rng.choice([(4, 3, 4), (5, 3, 3), (4, 4, 3), (6, 2, 4), (3, 5, 3), (5, 4, 4)])
    cells = {}
    for y in range(sy):
        for x in range(sx):
            for z in range(sz):
                bid = rng.choices(names, weights)[0]
                props = {}
                below = cells.get((x, y - 1, z))
                if bid in NEEDS_FLOOR:
                    if y > 0 and below is None:
                        cells[(x, y - 1, z)] = (rng.choice(SOLID[:6]), {})
                    elif y > 0 and below[0] not in SOLID:
                        bid = "stone"
                    if bid == "repeater":
                        props = {"facing": rng.choice(H4), "delay": str(rng.choice([1, 1, 1, 2, 3, 4]))}
                    elif bid == "comparator":
                        props = {"facing": rng.choice(H4), "mode": rng.choice(["compare", "subtract"])}
                elif bid == "redstone_wall_torch":
                    f = rng.choice(H4)
                    back = cells.get((x - VEC[f][0], y, z - VEC[f][2]))
                    if back is None or back[0] not in SOLID:
                        bid = "air"
                    props = {"facing": f}
                elif bid in ("sticky_piston", "piston", "observer", "dropper"):
                    props = {"facing": rng.choice(D6)}
                elif bid == "white_glazed_terracotta":
                    props = {"facing": rng.choice(H4)}
                elif bid == "oak_log":
                    props = {"axis": rng.choice("xyz")}
                if bid != "air":
                    cells[(x, y, z)] = (bid, props)
    for (x, y, z), (bid, _) in list(cells.items()):
        if bid in NEEDS_FLOOR and y == 0:
            cells[(x, -1, z)] = ("stone", {})
    spots = [(x, y, z) for (x, y, z), (bid, _) in cells.items() if bid in SOLID and (x, y + 1, z) not in cells]
    if not spots:
        cells[(0, 0, 0)] = ("stone", {})
        cells.pop((0, 1, 0), None)
        spots = [(0, 0, 0)]
    lx, ly, lz = rng.choice(spots)
    lever = (lx, ly + 1, lz)
    cells[lever] = ("lever", {"face": "floor", "facing": rng.choice(H4)})
    if wild:
        for p, (bid, props) in list(cells.items()):
            if rng.random() > 0.35:
                continue
            props = dict(props)
            if bid == "repeater":
                props.update(powered=rng.choice(["true", "false"]), locked=rng.choice(["true", "false", "false"]))
            elif bid in ("comparator", "observer", "note_block"):
                props["powered"] = "true"
            elif bid in ("redstone_torch", "redstone_wall_torch"):
                props["lit"] = "false"
            elif bid == "redstone_lamp":
                props["lit"] = "true"
            elif bid == "dropper":
                props["triggered"] = "true"
            elif bid == "waxed_copper_bulb":
                props.update(lit=rng.choice(["true", "false"]), powered=rng.choice(["true", "false"]))
            elif bid == "redstone_wire":
                props["power"] = str(rng.randrange(16))
                for d in H4:
                    props[d] = rng.choice(["none", "side", "up"])
            elif bid == "target":
                props["power"] = str(rng.choice([0, 0, 7, 15]))
            cells[p] = (bid, props)
        solid = [p for p, (bid, _) in cells.items() if bid in SOLID]
        rng.shuffle(solid)
        for p in solid:
            f = rng.choice(D6)
            q = (p[0] + VEC[f][0], p[1] + VEC[f][1], p[2] + VEC[f][2])
            if q in cells:
                continue
            del cells[lever]
            lever = q
            cells[q] = ("lever", {"face": "floor" if f == "up" else "ceiling" if f == "down" else "wall",
                                  "facing": f if f in H4 else rng.choice(H4), "powered": rng.choice(["false", "false", "true"])})
            break
    d = Design()
    d.name = f"fuzz-{profile}-{seed}{'-wild' if wild else ''}"
    d.blocks = {p: format_state(bid, props) for p, (bid, props) in cells.items()}
    d.ports = {"lever": lever, "door": (0, 0, 0)}
    return d


def run(world, design, flips=6):
    """Place like the judge, settle, flip the lever `flips` times; returns the recorded log."""
    rec = Recorder(world)
    lo, hi = design.bounds()
    lo, hi = tuple(v - 3 for v in lo), tuple(v + 3 for v in hi)
    judge.place(rec, design)
    rec.step(100, lo, hi)
    for _ in range(flips):
        rec.use(design.ports["lever"])
        rec.step(120, lo, hi)
    return rec.log


def differs(real_world, design):
    real = run(real_world, design)
    try:
        mine = run(SimWorld(), design)
    except Exception as e:  # noqa: BLE001  (a crash is a finding too)
        return f"the simulator crashed: {e!r}"
    return first_difference(real, mine)


def shrink(path):
    design = Design.load(path)
    with Worker() as worker:
        world = worker.world()
        changed = True
        while changed:
            changed = False
            for p in sorted(design.blocks):
                if p == design.ports["lever"]:
                    continue
                trial = design.translated((0, 0, 0))
                del trial.blocks[p]
                if differs(world, trial):
                    design, changed = trial, True
        out = path.replace(".txt", ".min.txt")
        with open(out, "w", encoding="utf8", newline="\n") as f:
            f.write(design.to_text())
        for p, s in design.block_list():
            print(list(p), s)
        print(differs(world, design))
        print("saved", out)


def main():
    args = sys.argv[1:]
    if "--shrink" in args:
        return shrink(args[args.index("--shrink") + 1])
    a, b = (int(args[args.index("--seeds") + 1]), int(args[args.index("--seeds") + 2])) if "--seeds" in args else (0, 200)
    profile = args[args.index("--profile") + 1] if "--profile" in args else "dense"
    save = args[args.index("--save") + 1] if "--save" in args else None
    shift = (0, 0, 0)
    if "--shift" in args:
        i = args.index("--shift")
        shift = tuple(int(args[i + 1 + j]) for j in range(3))
    wild = "--wild" in args
    same, bad = 0, []
    with Worker() as worker:
        world = worker.world()
        for seed in range(a, b):
            design = make_case(seed, profile, wild).translated(shift)
            diff = differs(world, design)
            if diff is None:
                same += 1
                continue
            bad.append(seed)
            print(f"seed {seed}: {diff.splitlines()[0]}", flush=True)
            if save:
                os.makedirs(save, exist_ok=True)
                with open(os.path.join(save, design.name + ".txt"), "w", encoding="utf8", newline="\n") as f:
                    f.write(design.to_text())
    print(f"{same} of {b - a} random contraptions are identical on every tick; differing seeds: {bad}")
    if bad and "--require-same" in args:
        sys.exit(1)


if __name__ == "__main__":
    main()
