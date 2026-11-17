"""Write corpus/verdicts.tsv: what the real game says about every corpus door and its mutants.

    python tools/record_verdicts.py [--jobs 8] [--mutants 2]

Each door in corpus/doors and `--mutants` single-block mutations of it are judged on the real
game at the judge's 4 base positions. One JVM per job. Needs python -m minecraft.setup.
"""
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from minecraft.worker import Worker  # noqa: E402
from redsim import corpus  # noqa: E402
from redsim.design import Design  # noqa: E402


def main():
    args = sys.argv[1:]
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 8
    mutants = int(args[args.index("--mutants") + 1]) if "--mutants" in args else 2
    cases = []
    for file in sorted(os.listdir(corpus.DOORS)):
        if not file.endswith(".txt"):
            continue
        design = Design.load(os.path.join(corpus.DOORS, file))
        cases.append((file, ""))
        cases += [(file, m) for m in corpus.mutations(design, file, mutants)]
    local = threading.local()
    workers = []

    def run(case):
        if not hasattr(local, "world"):
            w = Worker()
            workers.append(w)
            local.world = w.world()
        return (*case, *corpus.judge_case(local.world, *case))

    done = 0
    rows = []
    with ThreadPoolExecutor(jobs) as pool:
        for row in pool.map(run, cases):
            rows.append(row)
            done += 1
            if done % 200 == 0:
                print(f"{done}/{len(cases)}", flush=True)
    for w in workers:
        w.close()
    with open(corpus.VERDICTS, "w", encoding="utf8", newline="\n") as f:
        f.write("# Verdicts of the real game (Minecraft Java 26.3), written by tools/record_verdicts.py.\n")
        f.write("# " + "\t".join(corpus.COLUMNS) + "\n")
        for row in rows:
            f.write("\t".join(c.replace("\t", " ").replace("\n", " ") for c in row) + "\n")
    works = sum(r[2] == "1" for r in rows)
    print(f"{len(rows)} cases: {works} work, {len(rows) - works} are broken")


if __name__ == "__main__":
    main()
