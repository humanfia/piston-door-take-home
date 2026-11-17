"""Run designs on the simulator and on the real game and compare everything.

    python tools/both.py <design.txt | folder> ... [--extra N] [--quiet] [--require-same]

For each design: the verdict, the reason, the timings and the volume from both, and the first
tick on which any cell of the watched box differs. Needs the real-game environment
(python -m minecraft.setup).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from minecraft.worker import Worker  # noqa: E402
from redsim import judge  # noqa: E402
from redsim.design import Design  # noqa: E402
from redsim.world import SimWorld, Unsupported  # noqa: E402


class Recorder:
    """Wraps a world and keeps every frame it produced."""

    def __init__(self, world):
        self.world, self.log = world, []

    def __getattr__(self, name):
        return getattr(self.world, name)

    def clear(self):
        self.log.append(("clear", None))
        self.world.clear()

    def step(self, max_ticks, lo, hi):
        frames, idle = self.world.step(max_ticks, lo, hi)
        self.log.append(("step", frames, idle))
        return frames, idle

    def use(self, pos):
        r = self.world.use(pos)
        self.log.append(("use", r))
        return r


def first_difference(a, b):
    """Compare two recorder logs; None when identical."""
    for n, (x, y) in enumerate(zip(a, b)):
        if x[0] != y[0]:
            return f"step {n}: real did {x[0]}, sim did {y[0]}"
        if x[0] != "step":
            if x != y:
                return f"step {n}: {x} vs {y}"
            continue
        for t, (fa, fb) in enumerate(zip(x[1], y[1]), 1):
            if fa != fb:
                lines = [f"run {n}, tick {t}:"]
                for p in sorted(set(fa) | set(fb)):
                    if fa.get(p) != fb.get(p):
                        lines.append(f"  {list(p)} real {fa.get(p, 'air')}  sim {fb.get(p, 'air')}")
                        if len(lines) > 12:
                            break
                return "\n".join(lines)
        if len(x[1]) != len(y[1]) or x[2] != y[2]:
            return f"run {n}: real ran {len(x[1])} ticks (idle {x[2]}), sim {len(y[1])} (idle {y[2]})"
    if len(a) != len(b):
        return f"real made {len(a)} steps, sim {len(b)}"
    return None


def summary(r):
    return (r.ok, r.reason, r.volume, r.dims, tuple(r.cycles), r.blocks)


def compare(real_world, path, positions):
    design = Design.load(path)
    sim_rec = Recorder(SimWorld())
    try:
        mine = judge.verify(sim_rec, design, positions)
    except Unsupported as e:
        return "unsupported", str(e), None, None
    real_rec = Recorder(real_world)
    real = judge.verify(real_rec, design, positions)
    diff = first_difference(real_rec.log, sim_rec.log)
    same = summary(real) == summary(mine) and diff is None
    return ("same" if same else "DIFFERENT"), diff, real, mine


def main():
    args = sys.argv[1:]
    extra = int(args[args.index("--extra") + 1]) if "--extra" in args else 0
    quiet = "--quiet" in args
    paths = []
    for a in args:
        if os.path.isdir(a):
            paths += sorted(os.path.join(a, f) for f in os.listdir(a) if f.endswith(".txt"))
        elif a.endswith(".txt"):
            paths.append(a)
    positions = judge.BASE_OFFSETS + judge.extra_offsets(extra)
    count = {}
    with Worker() as worker:
        world = worker.world()
        for path in paths:
            status, diff, real, mine = compare(world, path, positions)
            count[status] = count.get(status, 0) + 1
            if status == "same" and quiet:
                continue
            print(f"{os.path.basename(path)}: {status}", flush=True)
            if status == "unsupported":
                print("  ", diff)
            else:
                print("   real", real)
                print("   sim ", mine)
                if diff:
                    print("  ", diff.replace("\n", "\n   "))
    print(count)
    if "--require-same" in args and set(count) != {"same"}:
        sys.exit(1)


if __name__ == "__main__":
    main()
