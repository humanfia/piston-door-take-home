"""Judge a design file.

    python -m redsim door.txt              # the simulator, 32 world positions
    python -m redsim door.txt --quick      # 4 positions
    python -m redsim door.txt --real       # the real game (needs: python -m minecraft.setup)
    python -m redsim door.txt --trace      # also print the doorway tick by tick
"""
import argparse
import sys

from . import judge
from .design import Design
from .errors import Unsupported
from .world import SimWorld


def print_report(path, r, where):
    if not r.ok:
        at = f" at offset {list(r.position)}" if r.position and tuple(r.position) != (0, 0, 0) else ""
        print(f"{path}: BROKEN on {where}{at}")
        print(f"  {r.reason}")
        return
    w, h, d = r.dims
    print(f"{path}: WORKS on {where}")
    print(f"  volume {r.volume} ({w} wide x {h} high x {d} deep), {r.blocks} blocks placed")
    print(f"  opens in {r.open_ticks} ticks, closes in {r.close_ticks}")
    for line in r.warnings[:5]:
        print("  note:", line)


def trace(r, design):
    """The door's plane, one picture per tick: # door block, m moving, o other block, . air."""
    spec = judge.Spec(design)
    x, y, z = spec.door
    rest, opening, closing = r.frames
    door_state = rest.get(spec.door_cells()[0])

    def picture(cells):
        rows = []
        for dy in range(spec.size + 1, -2, -1):
            row = ""
            for dw in range(-2, spec.size + 2):
                p = (x, y + dy, z + dw) if spec.along_z else (x + dw, y + dy, z)
                s = cells.get(p)
                row += "." if s is None else "#" if s == door_state else "m" if "moving_piston" in s else "o"
            rows.append(row)
        return rows

    for label, frames in (("opening", opening), ("closing", closing)):
        last = None
        shown = []
        for t, f in enumerate(frames, 1):
            pic = picture(f)
            if pic != last:
                shown.append((t, pic))
                last = pic
        print(f"  {label} (ticks where the door plane changes):")
        for i in range(0, len(shown), 8):
            chunk = shown[i:i + 8]
            print("    " + "  ".join(f"t{t:<{len(pic[0]) - 1}}" for t, pic in chunk))
            for row in range(len(chunk[0][1])):
                print("    " + "  ".join(pic[row] for _, pic in chunk))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="redsim", description="Judge a piston door design.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--quick", action="store_true", help="4 world positions instead of 32")
    ap.add_argument("--real", action="store_true", help="run on the real game instead of the simulator")
    ap.add_argument("--trace", action="store_true", help="print the doorway tick by tick")
    a = ap.parse_args(argv)
    positions = judge.BASE_OFFSETS if a.quick else judge.offsets()
    where = f"{'the real game' if a.real else 'the simulator'}, {len(positions)} positions"
    worker = None
    if a.real:
        from minecraft.worker import Worker
        worker = Worker()
        world = worker.world()
    else:
        world = SimWorld()
    ok = True
    try:
        for path in a.files:
            design = Design.load(path)
            try:
                r = judge.verify(world, design, positions, keep_frames=a.trace)
            except Unsupported as e:
                print(f"{path}: NOT JUDGED: {e}")
                ok = False
                continue
            print_report(path, r, where)
            if a.trace and r.frames:
                trace(r, design)
            ok = ok and r.ok
    finally:
        if worker:
            worker.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
