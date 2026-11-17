"""Design files: a contraption as human-readable layers (the format of vjeux/redstonepedia).

    # comment
    name: tiny-demo
    port door: 0 0 0          # minimum corner of the 3x3 opening
    port lever: 2 1 0         # where the lever is
    origin: 0 0 0             # world position of row 0, column 0 of layer 0
    palette:
      S minecraft:stone
      P minecraft:sticky_piston[facing=up]
      L minecraft:lever[face=floor,facing=east]
    layer 0:
      S.
    layer 1:
      PL

A layer is one y level (origin.y + its number). Inside a layer, rows run north to south (z grows
downward) and columns west to east (x grows rightward). `.` and spaces are air. Palette lines and
rows are indented by two spaces. The opening lies in the plane z = door.z and spans x and y from
the door port to +2.
"""
import re

_STATE = re.compile(r"^(minecraft:)?([a-z0-9_]+)(\[(.*)\])?$")


def parse_state(text):
    """'minecraft:piston[facing=east]' -> ('piston', {'facing': 'east'})."""
    m = _STATE.match(text.strip())
    if not m:
        raise ValueError(f"bad block state {text!r}")
    props = {}
    if m.group(4):
        for kv in m.group(4).split(","):
            k, _, v = kv.partition("=")
            props[k.strip()] = v.strip()
    return m.group(2), props


def format_state(block, props):
    if not props:
        return "minecraft:" + block
    return "minecraft:" + block + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def block_name(state):
    return state.split("[", 1)[0].replace("minecraft:", "")


class Design:
    def __init__(self):
        self.name = ""
        self.ports = {}      # name -> (x, y, z)
        self.meta = {}       # other header lines
        self.blocks = {}     # (x, y, z) -> state string, as written

    # ------------------------------------------------------------ reading and writing

    @classmethod
    def parse(cls, text):
        d = cls()
        origin = (0, 0, 0)
        palette = {}
        section, layer, row = "header", 0, 0
        cells = []
        for n, raw in enumerate(text.splitlines(), 1):
            indented = raw.startswith("  ")
            in_layer = section == "layer"
            line = raw if (in_layer and indented) else raw.split("#", 1)[0]
            if not line.strip():
                if in_layer and indented and not raw.strip():
                    raise ValueError(f"line {n}: blank row inside a layer; write an empty row as '  .'")
                continue
            if not indented:
                text_ = line.strip()
                if text_ == "palette:":
                    section = "palette"
                    continue
                m = re.match(r"^layer\s+(-?\d+)\s*:$", text_)
                if m:
                    section, layer, row = "layer", int(m.group(1)), 0
                    continue
                key, sep, value = text_.partition(":")
                if not sep:
                    raise ValueError(f"line {n}: {raw!r}")
                key, value = key.strip(), value.strip()
                section = "header"
                if key == "name":
                    d.name = value
                elif key == "origin":
                    origin = tuple(int(v) for v in value.split())
                elif key.startswith("port "):
                    d.ports[key[5:].strip()] = tuple(int(v) for v in value.split())
                else:
                    d.meta[key] = value
                continue
            body = line[2:].rstrip()
            if section == "palette":
                ch, _, state = body.strip().partition(" ")
                if len(ch) != 1 or not state.strip():
                    raise ValueError(f"line {n}: palette lines are '  <char> <block state>'")
                palette[ch] = state.strip()
            elif section == "layer":
                for col, ch in enumerate(body):
                    if ch not in ". ":
                        cells.append((n, ch, col, layer, row))
                row += 1
            else:
                raise ValueError(f"line {n}: unexpected indented line")
        for n, ch, col, layer, row in cells:
            if ch not in palette:
                raise ValueError(f"line {n}: {ch!r} is not in the palette")
            state = palette[ch]
            if block_name(state) != "air":
                d.blocks[(origin[0] + col, origin[1] + layer, origin[2] + row)] = state
        return d

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf8") as f:
            return cls.parse(f.read())

    def to_text(self):
        (x0, y0, z0), (x1, y1, z1) = self.bounds()
        states = sorted(set(self.blocks.values()))
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@$%&*+=?/<>"
        if len(states) > len(chars):
            raise ValueError("too many distinct block states for one palette")
        key = dict(zip(states, chars))
        out = [f"name: {self.name}"]
        out += [f"{k}: {v}" for k, v in self.meta.items()]
        out += [f"port {k}: {v[0]} {v[1]} {v[2]}" for k, v in self.ports.items()]
        out += [f"origin: {x0} {y0} {z0}", "palette:"]
        out += [f"  {key[s]} {s}" for s in states]
        for y in range(y0, y1 + 1):
            out.append(f"layer {y - y0}:")
            for z in range(z0, z1 + 1):
                row = "".join(key.get(self.blocks.get((x, y, z)), ".") for x in range(x0, x1 + 1)).rstrip(".")
                out.append("  " + (row or "."))
        return "\n".join(out) + "\n"

    # ------------------------------------------------------------ geometry

    def bounds(self):
        ps = list(self.blocks)
        return (tuple(min(p[i] for p in ps) for i in range(3)), tuple(max(p[i] for p in ps) for i in range(3)))

    def block_list(self):
        """Blocks in (x, y, z) order: the order the judge updates them in."""
        return sorted(self.blocks.items())

    def translated(self, off):
        d = Design()
        d.name, d.meta = self.name, dict(self.meta)
        mv = lambda p: (p[0] + off[0], p[1] + off[1], p[2] + off[2])  # noqa: E731
        d.ports = {k: mv(p) for k, p in self.ports.items()}
        d.blocks = {mv(p): s for p, s in self.blocks.items()}
        return d

    def door_size(self):
        return int(self.meta.get("door-size", "3"))

    def along_z(self):
        return self.meta.get("door-axis", "").strip() == "z"

    def placed_blocks(self):
        """Blocks placed: every block except piston heads, which belong to their piston."""
        return sum(1 for s in self.blocks.values() if block_name(s) != "piston_head")
