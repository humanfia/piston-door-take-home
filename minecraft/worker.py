"""A real Minecraft world to run designs in.

`Worker` starts one JVM running the bridge (minecraft/bridge): the official server's own classes
with no network, no players and no clock of its own. Nothing advances unless asked. `World` is
one sandbox in it and has the same interface as `redsim.world.SimWorld`, so the judge and every
tool run unchanged on either.
"""
import base64
import json
import os
import shutil
import struct
import subprocess
import tempfile
import threading

from . import setup


class BridgeError(RuntimeError):
    pass


class Worker:
    def __init__(self, heap_mb=1024):
        cfg = setup.installed()
        if cfg is None:
            raise BridgeError("the real-game environment is not installed; run: python -m minecraft.setup")
        self.dir = tempfile.mkdtemp(prefix="universe-", dir=cfg["home"])
        self._stderr = open(os.path.join(self.dir, "server.log"), "wb")
        self.proc = subprocess.Popen(
            [cfg["java"], f"-Xmx{heap_mb}m", "-XX:+UseSerialGC", "-XX:-UsePerfData", "-XX:ActiveProcessorCount=2",
             "-XX:+IgnoreUnrecognizedVMOptions", "--enable-native-access=ALL-UNNAMED",
             "--sun-misc-unsafe-memory-access=allow", "--add-opens=java.base/java.util=ALL-UNNAMED",
             f"-Dlog4j2.configurationFile={cfg['log4j']}", "-Dmctas.loglevel=WARN",
             "-cp", cfg["classpath"], setup.MAIN_CLASS, "--universe", self.dir],
            cwd=self.dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr)
        self._id = 0
        self._lock = threading.Lock()
        ready = self._read()
        if ready.get("event") != "ready":
            raise BridgeError(f"unexpected first line from the bridge: {ready}")
        self.version = ready.get("version")

    def _read(self):
        while True:
            line = self.proc.stdout.readline()
            if not line:
                tail = ""
                try:
                    self._stderr.flush()
                    tail = open(os.path.join(self.dir, "server.log"), errors="replace").read()[-2000:]
                except OSError:
                    pass
                raise BridgeError("the bridge exited\n" + tail)
            line = line.strip()
            if line.startswith(b"{"):
                return json.loads(line)

    def request(self, op, **fields):
        with self._lock:
            self._id += 1
            msg = {"id": self._id, "op": op, **fields}
            self.proc.stdin.write((json.dumps(msg) + "\n").encode())
            self.proc.stdin.flush()
            res = self._read()
        if not res.get("ok", True):
            raise BridgeError(f"{op}: {res.get('error')}")
        return res

    def world(self):
        return World(self)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=20)
        except Exception:  # noqa: BLE001
            self.proc.kill()
        self._stderr.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class World:
    """One sandbox: its own level, clock and random."""
    name = "minecraft"

    def __init__(self, worker):
        self.w = worker
        self.sb = worker.request("create", chunks=[-4, -4, 3, 3], seed=0)["sandbox"]
        self._flags = {"minecraft:air": (False, False)}

    def flags(self, state):
        """(collides, full): has a collision shape, and that shape is a full cube."""
        if state not in self._flags:
            self.w.request("normalize_states", states=[state])      # fails on a state the game does not know
            r = self.w.request("blockinfo", sandbox=self.sb, states=[state], types=[])
            info = r["blocks"][0] if "blocks" in r else r["states"][0]
            self._flags[state] = (bool(info.get("collides", info.get("full_collision"))), bool(info["full_collision"]))
        return self._flags[state]

    def _seen(self, r):
        for s, f in zip(r["palette"], r["flags"]):
            self._flags[s] = (bool(f["collides"]), bool(f["full"]))

    def clear(self):
        self.w.request("clear", sandbox=self.sb)

    def set_raw(self, blocks):
        """Write exact states: no updates, no placement side effects."""
        self.w.request("set", sandbox=self.sb, blocks=[[*p, s] for p, s in blocks], mode="raw")

    def update_shape(self, positions):
        self.w.request("update", sandbox=self.sb, positions=[list(p) for p in positions], kind="shape")

    def update_self(self, positions):
        self.w.request("update", sandbox=self.sb, positions=[list(p) for p in positions], kind="self")

    def use(self, pos):
        """Flip the lever at `pos`. Anything else there is left alone (a real right click would
        retune a note block or change a repeater's delay)."""
        if not self.get(pos, pos).get(tuple(pos), "").startswith("minecraft:lever"):
            return "PASS"
        return self.w.request("use", sandbox=self.sb, pos=list(pos))["result"]

    def step(self, max_ticks, lo, hi):
        """Tick until idle (at most max_ticks). Returns (frames, idle): one frame per tick, each a
        dict {pos: state} of the non-air cells of the box lo..hi."""
        r = self.w.request("step", sandbox=self.sb, ticks=max_ticks, until_idle=True,
                           record={"from": list(lo), "to": list(hi)})["results"][0]
        self._seen(r)
        return _frames(r), bool(r.get("idle"))

    def get(self, lo, hi):
        r = self.w.request("get", sandbox=self.sb, **{"from": list(lo), "to": list(hi)})
        r["frames"] = [r["data"]]
        self._seen(r)
        return _frames(r)[0]

    def unsupported(self, lo, hi):
        """(cells whose block could not stand there, cells whose block takes random ticks)."""
        r = self.w.request("unsupported", sandbox=self.sb, **{"from": list(lo), "to": list(hi)})
        return [tuple(p) for p in r["positions"]], [tuple(p) for p in r["random"]]

    def entities(self):
        return self.w.request("status", sandbox=self.sb)["entities"]

    def rotate(self, states, turns):
        """Each state turned `turns` quarter turns clockwise, by the game's own BlockState.rotate."""
        return self.w.request("rotate", states=list(states), turns=turns)["states"]


def _frames(r):
    x0, y0, z0 = r["from"]
    dx, dy, dz = r["size"]
    palette = r["palette"]
    air = {i for i, s in enumerate(palette) if s.endswith(":air")}
    coords = [(x0 + x, y0 + y, z0 + z) for y in range(dy) for z in range(dz) for x in range(dx)]
    out = []
    n = dx * dy * dz
    for data in r["frames"]:
        ids = struct.unpack(f"<{n}H", base64.b64decode(data))
        out.append({coords[i]: palette[v] for i, v in enumerate(ids) if v not in air})
    return out
