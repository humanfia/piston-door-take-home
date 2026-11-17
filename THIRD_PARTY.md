# Third-party material

## vjeux/redstonepedia (MIT, Copyright (c) 2026 Christopher Chedeau)

https://github.com/vjeux/redstonepedia at commit 86a5e4843d8effe81bf7bf411a554cef8b58a1c9.
Its license is in `minecraft/bridge/LICENSE`.

| here | from there | changes |
|---|---|---|
| `minecraft/bridge/` | `bridge/src`, `bridge/resources/mctas-log4j2.xml` | none |
| `corpus/doors/*.txt` | `designs/piston-door-3x3/archive/*.txt`, `designs/piston-door-2x2/archive/classic6-20b.txt` (as `2x2-classic6-20b.txt`) | the 945 designs that use only blocks this task allows; line endings |
| `door.txt` | `designs/piston-door-3x3/archive/piston-door-3x3-v2-151b.txt` | header comment |
| `redsim/judge.py`, `docs/rules.md` | `crates/piston-door/src/lib.rs`, `docs/rules.md` | the judge rewritten in Python; the differences are listed in docs/rules.md |
| `redsim/design.py` | the design file format of `crates/mctas/src/design.rs` | a new parser for the same format |
| `minecraft/setup.py`, `minecraft/worker.py` | `crates/mctas/src/setup.rs`, `bridge.rs`, `sim.rs` | the same steps and JVM flags, rewritten in Python |
| `docs/mechanics.md`, `docs/prior-art.md` | `docs/mechanics.md`, `docs/history.md`, `LEADERBOARD.md`, archive tables | condensed and rewritten |

## Minecraft

Nothing from Minecraft is in this repository. `python -m minecraft.setup` downloads the official
26.3 server from Mojang and a JDK from adoptium.net onto your machine. Using the server is
subject to the Minecraft EULA (https://aka.ms/MinecraftEULA).
