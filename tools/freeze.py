"""Copy the judge and the simulator into tests/frozen, the copy the submission tests score with.

    python tools/freeze.py           # refresh the frozen copy
    python tools/freeze.py --check   # exit 1 if it differs from redsim/
"""
import filecmp
import os
import shutil
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FILES = ("__init__.py", "blockdata.py", "design.py", "errors.py", "judge.py", "sim.py", "world.py")


def main():
    src, dst = os.path.join(ROOT, "redsim"), os.path.join(ROOT, "tests", "frozen", "redsim")
    if "--check" in sys.argv:
        stale = [f for f in FILES if not os.path.exists(os.path.join(dst, f))
                 or not filecmp.cmp(os.path.join(src, f), os.path.join(dst, f), shallow=False)]
        if stale:
            sys.exit(f"tests/frozen is out of date: {', '.join(stale)} (run python tools/freeze.py)")
        return
    os.makedirs(dst, exist_ok=True)
    for f in FILES:
        shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
    print(f"froze {len(FILES)} files into tests/frozen/redsim")


if __name__ == "__main__":
    main()
