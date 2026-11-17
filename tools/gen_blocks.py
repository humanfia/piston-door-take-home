"""Generate redsim/blockdata.py from the real game.

The simulator models a few dozen blocks with behaviour by hand (sim.py). Building blocks need no
behaviour, only four facts each: does it conduct redstone, how does a piston treat it, which
note block instrument does it give, and which properties does its state carry. This script asks
the real game for those facts, for a hand-written list of candidate blocks, and keeps the ones
that really are plain: a full cube, sturdy on every face, no block entity, no signal, no random
ticks. Run it again after changing the list or the game version.

    python tools/gen_blocks.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from minecraft.worker import Worker  # noqa: E402
from redsim.design import parse_state  # noqa: E402

COLOURS = ("white orange magenta light_blue yellow lime pink gray light_gray cyan purple blue brown green red black").split()
WOODS = "oak spruce birch jungle acacia dark_oak mangrove cherry pale_oak".split()

CANDIDATES = (
    "stone smooth_stone cobblestone mossy_cobblestone stone_bricks mossy_stone_bricks cracked_stone_bricks "
    "chiseled_stone_bricks granite polished_granite diorite polished_diorite andesite polished_andesite "
    "deepslate cobbled_deepslate polished_deepslate deepslate_bricks deepslate_tiles chiseled_deepslate "
    "tuff polished_tuff tuff_bricks chiseled_tuff calcite dripstone_block smooth_basalt basalt polished_basalt "
    "blackstone polished_blackstone polished_blackstone_bricks chiseled_polished_blackstone gilded_blackstone "
    "bricks mud_bricks packed_mud nether_bricks red_nether_bricks cracked_nether_bricks chiseled_nether_bricks "
    "netherrack end_stone end_stone_bricks purpur_block purpur_pillar prismarine prismarine_bricks dark_prismarine "
    "sandstone chiseled_sandstone cut_sandstone smooth_sandstone red_sandstone chiseled_red_sandstone "
    "cut_red_sandstone smooth_red_sandstone quartz_block chiseled_quartz_block quartz_bricks quartz_pillar "
    "smooth_quartz terracotta clay dirt coarse_dirt snow_block packed_ice blue_ice moss_block sculk "
    "iron_block gold_block diamond_block emerald_block lapis_block netherite_block coal_block "
    "raw_iron_block raw_gold_block raw_copper_block amethyst_block "
    "waxed_copper_block waxed_cut_copper waxed_chiseled_copper waxed_exposed_copper waxed_weathered_copper "
    "waxed_oxidized_copper "
    "bookshelf glowstone sea_lantern shroomlight ochre_froglight verdant_froglight pearlescent_froglight "
    "melon pumpkin hay_block bone_block honeycomb_block dried_kelp_block nether_wart_block warped_wart_block "
    "obsidian crying_obsidian glass tinted_glass "
).split()
CANDIDATES += [f"{c}_{kind}" for c in COLOURS for kind in ("concrete", "wool", "terracotta", "glazed_terracotta", "stained_glass")]
CANDIDATES += [f"{w}_{kind}" for w in WOODS for kind in ("planks", "log", "wood")]
CANDIDATES += [f"stripped_{w}_{kind}" for w in WOODS for kind in ("log", "wood")]

# Blocks sim.py models by hand: only their instrument is needed here.
SPECIAL = ("piston sticky_piston slime_block honey_block redstone_block observer target note_block redstone_lamp "
           "dropper piston_head redstone_wire repeater comparator redstone_torch redstone_wall_torch lever "
           "waxed_copper_bulb waxed_exposed_copper_bulb waxed_weathered_copper_bulb waxed_oxidized_copper_bulb").split()

PUSH = {"PUSH_PULL": "normal", "IMMOVEABLE": "block", "PUSH": "push_only"}   # POPPED (breaks) is left out


def main():
    plain, instrument, rejected = {}, {}, []
    with Worker() as worker:
        world = worker.world()
        for name in CANDIDATES + SPECIAL:
            try:
                state = worker.request("normalize_states", states=["minecraft:" + name])["states"][0]
            except Exception as e:  # noqa: BLE001  (not a block in this version)
                rejected.append((name, "unknown block"))
                continue
            info = worker.request("blockinfo", sandbox=world.sb, states=[state], types=[])["states"][0]
            world.clear()
            world.set_raw([((0, 0, 0), state), ((0, 1, 0), "minecraft:note_block")])
            world.update_shape([(0, 1, 0)])
            note = world.get((0, 1, 0), (0, 1, 0))[(0, 1, 0)]
            instrument[name] = parse_state(note)[1]["instrument"]
            if name in SPECIAL:
                continue
            why = [k for k, bad in (("not a full cube", not info["full_collision"]), ("not sturdy", "0" in info["sturdy"]),
                                    ("block entity", info["block_entity"]), ("signal source", info["signal"]),
                                    ("random ticks", info["random_ticking"]),
                                    ("breaks when pushed", info["push"] not in PUSH)) if bad]
            if why:
                rejected.append((name, ", ".join(why)))
                continue
            plain[name] = (bool(info["conductor"]), PUSH[info["push"]], parse_state(state)[1])
    out = ['"""Generated by tools/gen_blocks.py from Minecraft 26.3. Do not edit by hand."""', "",
           "# name: (conducts redstone, piston push reaction, default properties)", "PLAIN = {"]
    out += [f"    {n!r}: {v!r}," for n, v in sorted(plain.items())]
    out += ["}", "", "# the note block instrument a block gives the note block standing on it (harp when absent)", "INSTRUMENT = {"]
    out += [f"    {n!r}: {v!r}," for n, v in sorted(instrument.items()) if v != "harp"]
    out += ["}", ""]
    path = os.path.join(os.path.dirname(__file__), "..", "redsim", "blockdata.py")
    with open(path, "w", encoding="utf8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"{len(plain)} plain blocks, {len(instrument)} instruments")
    for name, why in rejected:
        print("  left out:", name, "-", why)


if __name__ == "__main__":
    main()
