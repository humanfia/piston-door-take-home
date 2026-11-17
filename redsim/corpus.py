"""The validation corpus: door designs and what the real game says about each.

corpus/doors/ holds design files (from vjeux/redstonepedia's archive, MIT). corpus/verdicts.tsv
holds one row per case, written by tools/record_verdicts.py from the real game:

    file  mutation  works  volume  dims  blocks  open  close  reason

A case is a door file, or a door file with one mutation applied (`del x,y,z`, or
`set x,y,z <state>`): most mutants are broken doors, so the corpus also checks that the
simulator fails where the game fails, and for the same reason.
"""
import os
import random
import zlib

from . import judge
from .design import Design, block_name, format_state, parse_state

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "corpus")
DOORS = os.path.join(ROOT, "doors")
VERDICTS = os.path.join(ROOT, "verdicts.tsv")
COLUMNS = ("file", "mutation", "works", "volume", "dims", "blocks", "open", "close", "reason")
REASON_CHARS = 400


def apply_mutation(design, mutation):
    if not mutation:
        return design
    op, pos, *rest = mutation.split(" ", 2)
    p = tuple(int(v) for v in pos.split(","))
    d = design.translated((0, 0, 0))
    if op == "del":
        del d.blocks[p]
    elif op == "set":
        d.blocks[p] = rest[0]
    else:
        raise ValueError(f"bad mutation {mutation!r}")
    return d


def mutations(design, name, count=2):
    """`count` reproducible single-block changes of a design."""
    rng = random.Random(zlib.crc32(name.encode()))
    spec = judge.Spec(design)
    keep = set(spec.door_cells()) | {spec.lever}
    cells = [p for p in sorted(design.blocks) if p not in keep and block_name(design.blocks[p]) != "piston_head"]
    out = []
    for _ in range(count * 4):
        if len(out) == count or not cells:
            break
        p = rng.choice(cells)
        name_, props = parse_state(design.blocks[p])
        where = f"{p[0]},{p[1]},{p[2]}"
        choice = rng.random()
        m = None
        if name_ == "repeater" and choice < 0.7:
            delay = rng.choice([d for d in "1234" if d != props.get("delay", "1")])
            m = f"set {where} {format_state(name_, {**props, 'delay': delay})}"
        elif name_ in ("piston", "sticky_piston") and props.get("extended", "false") == "false" and choice < 0.5:
            other = "piston" if name_ == "sticky_piston" else "sticky_piston"
            m = f"set {where} {format_state(other, props)}"
        elif name_ == "observer" and choice < 0.5:
            facing = rng.choice([f for f in ("north", "south", "east", "west", "up", "down") if f != props.get("facing")])
            m = f"set {where} {format_state(name_, {**props, 'facing': facing})}"
        elif props.get("extended") != "true":
            m = f"del {where}"
        if m and m not in out:
            out.append(m)
    return out


def summarize(report):
    """A judge report as the verdict columns after file and mutation."""
    if not report.ok:
        return ("0", "", "", str(report.blocks), "", "", (report.reason or "")[:REASON_CHARS])
    return ("1", str(report.volume), "x".join(map(str, report.dims)), str(report.blocks),
            str(report.open_ticks), str(report.close_ticks), "")


def load_verdicts(path=VERDICTS):
    rows = []
    with open(path, encoding="utf8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            rows.append(dict(zip(COLUMNS, cols + [""] * (len(COLUMNS) - len(cols)))))
    return rows


def judge_case(world, file, mutation, positions=None):
    design = apply_mutation(Design.load(os.path.join(DOORS, file)), mutation)
    return summarize(judge.verify(world, design, positions))
