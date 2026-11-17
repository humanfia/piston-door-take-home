"""The simulator behind the interface the judge uses.

`SimWorld` has the same methods as `minecraft.worker.World`, the real game: place raw blocks,
send updates, flip a lever, tick until idle while recording every tick. Block states go in and
out as the game writes them, e.g. `minecraft:sticky_piston[extended=false,facing=east]`.
"""
from . import sim
from .design import parse_state
from .errors import Unsupported
from .sim import AIR, add

_NO_COLLISION = {"redstone_wire", "redstone_torch", "redstone_wall_torch", "lever"}


_STATES = {}


def to_state(text):
    st = _STATES.get(text)
    if st is None:
        name, props = parse_state(text)
        if name not in sim.KNOWN:
            raise Unsupported(f"{name} is not modelled by the simulator")
        try:
            st = _STATES[text] = sim.make_state(name, props)
        except ValueError as e:
            raise Unsupported(str(e)) from None
    return st


def to_text(st):
    return "minecraft:" + repr(st)


def flags(state):
    """(collides, full): has a collision shape, and that shape is a full cube."""
    name = state.split("[", 1)[0].replace("minecraft:", "")
    if name in _NO_COLLISION or name == "air":
        return False, False
    if name == "moving_piston":
        return True, False
    if name in sim.FULL_CUBES:
        return True, True
    if name in sim.PISTONS:
        return True, "extended=false" in state
    return True, False


class SimWorld:
    name = "redsim"

    def __init__(self):
        self.w = sim.World()

    def clear(self):
        self.w = sim.World()

    def flags(self, state):
        return flags(state)

    def set_raw(self, blocks):
        for pos, state in blocks:
            self.w.raw_set(tuple(pos), to_state(state))

    def update_shape(self, positions):
        w = self.w
        for pos in positions:
            st = w.get(pos)
            new = w.update_from_neighbour_shapes(st, pos)
            if new is not st:
                w.raw_set(pos, new)

    def update_self(self, positions):
        for pos in positions:
            self.w.neighbor_changed(tuple(pos), self.w.get(tuple(pos)).id)

    def use(self, pos):
        return "lever" if self.w.pull_lever(tuple(pos)) else "PASS"

    def _box(self, lo, hi):
        return {p: to_text(st) for p, st in self.w.blocks.items()
                if lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1] and lo[2] <= p[2] <= hi[2]}

    def get(self, lo, hi):
        return self._box(lo, hi)

    def idle(self):
        return self.w.idle()

    def step(self, max_ticks, lo, hi):
        w = self.w
        cur = self._box(lo, hi)
        w.touched.clear()
        frames, idle = [], False
        for _ in range(max_ticks):
            w.tick()
            if w.touched:
                cur = dict(cur)
                for p in w.touched:
                    if lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1] and lo[2] <= p[2] <= hi[2]:
                        st = w.blocks.get(p)
                        if st is None:
                            cur.pop(p, None)
                        else:
                            cur[p] = to_text(st)
                w.touched.clear()
            frames.append(cur)
            if w.idle():
                idle = True
                break
        return frames, idle

    def unsupported(self, lo, hi):
        w = self.w
        out = []
        for p, st in w.blocks.items():
            if not (lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1] and lo[2] <= p[2] <= hi[2]):
                continue
            i = st.id
            if i == "redstone_wire":
                ok = w._sturdy(add(p, sim.DOWN), sim.UP)
            elif i in sim.DIODES:
                ok = w._sturdy(add(p, sim.DOWN), sim.UP, "rigid")
            elif i == "redstone_torch":
                ok = w._sturdy(add(p, sim.DOWN), sim.UP, "center")
            elif i == "redstone_wall_torch":
                ok = w._sturdy(add(p, sim.OPP[st.p["facing"]]), st.p["facing"])
            elif i == "lever":
                a = sim.lever_attach(st)
                ok = w._sturdy(add(p, a), sim.OPP[a])
            elif i == "piston_head":
                ok = w._head_survives(p, st)
            else:
                ok = True
            if not ok:
                out.append(p)
        return sorted(out), []

    def entities(self):
        """Item entities: every block that broke and dropped."""
        return len(self.w.drops)
