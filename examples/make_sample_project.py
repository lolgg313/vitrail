# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Generate examples/sample_project (materials, prefabs, textures, models...)."""
import json
import math
import os
import random
import struct
import sys
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame  # noqa: E402

from vitrail.assets import create_material, create_prefab  # noqa: E402
from vitrail.logo import logo_surface  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def mk(*parts):
    p = os.path.join(*parts)
    os.makedirs(p, exist_ok=True)
    return p


def textures(folder):
    rnd = random.Random(7)
    s = pygame.Surface((256, 256))
    for y in range(0, 256, 32):
        for x in range(0, 256, 32):
            s.fill((235, 235, 240) if (x + y) // 32 % 2 == 0 else (60, 62, 70), (x, y, 32, 32))
    pygame.image.save(s, os.path.join(folder, "checker.png"))
    s = pygame.Surface((256, 256))
    for y in range(256):
        t = y / 255
        pygame.draw.line(s, (int(30 + 200 * t), int(60 + 120 * (1 - t)), int(160 + 80 * (1 - t))), (0, y), (255, y))
    pygame.image.save(s, os.path.join(folder, "sky_gradient.png"))
    s = pygame.Surface((256, 256))
    s.fill((70, 30, 24))
    for row in range(0, 256, 32):
        off = 0 if row // 32 % 2 == 0 else 32
        for col in range(-64, 256, 64):
            c = rnd.randint(140, 185)
            pygame.draw.rect(s, (c, int(c * 0.42), int(c * 0.3)), (col + off + 3, row + 3, 58, 26), border_radius=3)
    pygame.image.save(s, os.path.join(folder, "bricks.png"))
    s = pygame.Surface((128, 128))
    for y in range(128):
        for x in range(128):
            v = int(128 + 60 * math.sin(x * 0.11) * math.cos(y * 0.09) + rnd.randint(-40, 40))
            v = max(0, min(255, v))
            s.set_at((x, y), (v // 3, v // 2 + 40, v // 4 + 20))
    pygame.image.save(s, os.path.join(folder, "grass_noise.png"))
    s = pygame.Surface((256, 128), pygame.SRCALPHA)
    for i in range(12):
        pygame.draw.circle(s, (255, 200 - i * 12, 80 + i * 14, 200), (20 + i * 20, 64), 30 - i)
    pygame.image.save(s, os.path.join(folder, "sprite_sheet.png"))
    pygame.image.save(logo_surface(256), os.path.join(folder, "vitrail_logo.png"))


def wav(path, freq=660, dur=0.25):
    rate = 22050
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * (i / rate) * (1 + i / rate))
                                                * (1 - i / (rate * dur)))) for i in range(int(rate * dur)))
        w.writeframes(frames)


def main(root=os.path.join(HERE, "sample_project")):
    pygame.init()
    if os.path.isdir(root):
        print("already exists:", root)
        return root
    mats = mk(root, "Materials")
    metals = mk(mats, "Metals")
    for name, kw in [
        ("Brick Red", dict(base_color=[0.72, 0.22, 0.14, 1], roughness=0.75)),
        ("Plastic Blue", dict(base_color=[0.1, 0.42, 0.95, 1], roughness=0.3)),
        ("Rubber Black", dict(base_color=[0.06, 0.06, 0.07, 1], roughness=0.85)),
        ("Marble", dict(base_color=[0.92, 0.9, 0.86, 1], roughness=0.15)),
        ("Jade", dict(base_color=[0.2, 0.7, 0.45, 1], roughness=0.25)),
        ("Neon Cyan", dict(base_color=[0.05, 0.08, 0.1, 1], roughness=0.4, emission=[0.2, 0.9, 1.0],
                           emission_strength=1.2)),
        ("Lava", dict(base_color=[0.15, 0.04, 0.02, 1], roughness=0.6, emission=[1.0, 0.35, 0.05],
                      emission_strength=0.9)),
    ]:
        create_material(mats, name, **kw)
    for name, kw in [
        ("Gold", dict(base_color=[1.0, 0.77, 0.34, 1], roughness=0.22, metallic=1.0)),
        ("Chrome", dict(base_color=[0.85, 0.86, 0.88, 1], roughness=0.06, metallic=1.0)),
        ("Copper", dict(base_color=[0.95, 0.55, 0.38, 1], roughness=0.35, metallic=1.0)),
        ("Brushed Steel", dict(base_color=[0.7, 0.72, 0.75, 1], roughness=0.5, metallic=1.0)),
    ]:
        create_material(metals, name, **kw)
    pre = mk(root, "Prefabs")
    for name, col, comps in [("Player", [0.36, 0.66, 1.0, 1], ["Transform", "Character Controller", "Animator"]),
                             ("Enemy", [1.0, 0.42, 0.38, 1], ["Transform", "AI Agent", "Health"]),
                             ("Crate", [0.85, 0.62, 0.3, 1], ["Transform", "Mesh Renderer", "Rigidbody"]),
                             ("Tree", [0.4, 0.8, 0.45, 1], ["Transform", "Mesh Renderer", "Wind Zone"]),
                             ("Street Lamp", [0.95, 0.85, 0.4, 1], ["Transform", "Point Light"])]:
        create_prefab(pre, name, color=col, components=comps)
    textures(mk(root, "Textures"))
    models = mk(root, "Models")
    with open(os.path.join(models, "crate.obj"), "w") as f:
        f.write("o Crate\n" + "".join(f"v {x} {y} {z}\n" for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)) +
                "f 1 2 4 3\nf 5 6 8 7\nf 1 2 6 5\nf 3 4 8 7\nf 1 3 7 5\nf 2 4 8 6\n")
    with open(os.path.join(models, "tree.gltf"), "w") as f:
        json.dump({"asset": {"version": "2.0", "generator": "vitrail sample"}, "scenes": [{"nodes": []}]}, f)
    with open(os.path.join(models, "rock.stl"), "w") as f:
        f.write("solid rock\nendsolid rock\n")
    scripts = mk(root, "Scripts")
    with open(os.path.join(scripts, "player.py"), "w") as f:
        f.write("class Player:\n    speed = 5.0\n\n    def update(self, dt):\n        pass\n")
    with open(os.path.join(scripts, "enemy_ai.py"), "w") as f:
        f.write("def think(agent):\n    return 'patrol'\n")
    shaders = mk(scripts, "Shaders")
    with open(os.path.join(shaders, "water.frag"), "w") as f:
        f.write("#version 330\nout vec4 c;\nvoid main(){ c = vec4(0.1, 0.4, 0.8, 1.0); }\n")
    audio = mk(root, "Audio")
    wav(os.path.join(audio, "jump.wav"), 520)
    wav(os.path.join(audio, "coin.wav"), 980, 0.15)
    scenes = mk(root, "Scenes")
    with open(os.path.join(scenes, "Main.vscene"), "w") as f:
        json.dump({"type": "scene", "objects": ["Player", "Crate", "Tree"]}, f, indent=2)
    with open(os.path.join(root, "README.txt"), "w") as f:
        f.write("Sample project for the Vitrail asset browser.\n")
    print("created", root)
    return root


if __name__ == "__main__":
    main(*sys.argv[1:])
