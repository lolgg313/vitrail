# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Tests for animation (tracks, player, timeline, graph editor) and the asset browser."""
import json
import os
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))

from harness import Harness, vt, pygame  # noqa: E402
from vitrail.animation import AnimationPlayer, Clip, Track  # noqa: E402
from vitrail.assets import (Asset, AssetBrowser, MaterialEditor, create_material,  # noqa: E402
                            load_json, scan)

CTRL = pygame.KMOD_LCTRL
ALT = pygame.KMOD_LALT
SAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "sample_project")


def fill(w=1100, h=700):
    H = Harness(w, h)
    root = vt.Column(spacing=0)
    H.ui.set_root(root)
    return H, root


# ----------------------------------------------------------------------------- tracks
def test_track_interpolation():
    t = Track("x", [(0, 0.0), (10, 10.0), (20, 0.0)])
    assert t.evaluate(-5) == 0.0 and t.evaluate(25) == 0.0
    assert t.evaluate(10) == 10.0
    vals = [t.evaluate(f / 4) for f in range(81)]
    assert max(vals) <= 10.0 + 1e-9 and min(vals) >= -1e-9          # no overshoot at the peak
    t.keys[0].interp = "linear"
    assert t.evaluate(5) == pytest.approx(5.0)
    t.keys[0].interp = "constant"
    assert t.evaluate(9.9) == 0.0
    t.add_key(10, 3.0)
    assert len(t.keys) == 3 and t.keys[1].value == 3.0


def test_player_binding_playback_loop():
    H, root = fill()
    clip = Clip("c", start=1, end=25, fps=24)
    tr = clip.add_track("X", [(1, 0.0), (25, 24.0)])
    tr.keys[0].interp = "linear"
    p = AnimationPlayer(clip)
    f = vt.NumberField("X", 0.0, parent=root)
    p.bind(tr, f)
    p.attach(H.ui)
    p.set_frame(13)
    assert f.value == pytest.approx(12.0)
    p.play()
    t0 = time.perf_counter()
    p._last = t0
    H.ui.update(t0 + 0.5)                     # 12 frames at 24 fps
    assert p.frame == pytest.approx(25.0, abs=0.01) or p.frame < 13
    H.ui.update(t0 + 0.75)                    # wraps around (loop)
    assert 1 <= p.frame < 25
    p.pause()
    assert not p.playing and p.frame == round(p.frame)
    p.loop = False
    p.set_frame(20)
    p.play()
    p._last = time.perf_counter()
    H.ui.update(p._last + 5)
    assert p.frame == 25 and not p.playing


def test_insert_key_on_hover_and_undo():
    H, root = fill()
    clip = Clip("c", start=1, end=50)
    tr = clip.add_track("Y")
    p = AnimationPlayer(clip)
    f = vt.NumberField("Y", 2.5, parent=root)
    p.bind(tr, f)
    p.attach(H.ui)
    H.frame()
    p.set_frame(10)
    H.move(*H.center(f))
    H.key(pygame.K_i, unicode="i")
    assert [(k.frame, k.value) for k in tr.keys] == [(10.0, 2.5)]
    assert p.anim_state(f) == "keyed"
    p.set_frame(20)
    assert p.anim_state(f) == "animated"
    H.key(pygame.K_z, CTRL)
    assert tr.keys == []
    H.key(pygame.K_z, CTRL | pygame.KMOD_LSHIFT)
    p.set_frame(10)
    H.key(pygame.K_i, ALT)
    assert tr.keys == []


@pytest.fixture
def anim():
    import anim_page
    H, root = fill(1180, 720)
    h = anim_page.build_animation_page(root, H.ui)
    H.frame()
    H.frame()
    return H, h


def test_timeline_scrub_select_move_delete(anim):
    H, h = anim
    tl, p, clip = h["timeline"], h["player"], h["clip"]
    rh = tl.ruler_h(H.ui)
    H.click(int(tl.fx(40)), int(tl.y + rh / 2))           # scrub on the ruler
    assert p.frame == 40
    tx = clip.tracks[0]
    key = tx.keys[1]                                       # frame 48
    row_y = tl.row_y(H.ui, 1) + tl.rh(H.ui) / 2
    H.move(int(tl.fx(key.frame)), int(row_y))
    H.down()
    H.move(int(tl.fx(key.frame + 6)), int(row_y), steps=4)
    H.up()
    assert key.frame == 54 and key.selected
    H.key(pygame.K_z, CTRL)
    assert [k.frame for k in clip.tracks[0].keys] == [1, 48, 96]
    # box-select all Position Y keys between frames 10 and 40, then delete them
    y_row = tl.row_y(H.ui, 2) + tl.rh(H.ui) / 2
    H.move(int(tl.fx(10)), int(y_row - 4))
    H.down()
    H.move(int(tl.fx(40)), int(y_row + 4), steps=4)
    H.up()
    sel = clip.selected_keys()
    assert sel and all(t is clip.tracks[1] and 10 <= k.frame <= 40 for t, k in sel)
    n = len(clip.tracks[1].keys)
    H.key(pygame.K_DELETE)
    assert len(clip.tracks[1].keys) == n - len(sel)


def test_timeline_context_interpolation(anim):
    H, h = anim
    tl, clip = h["timeline"], h["clip"]
    key = clip.tracks[0].keys[0]
    row_y = tl.row_y(H.ui, 1) + tl.rh(H.ui) / 2
    H.move(int(tl.fx(key.frame)), int(row_y))
    H.down(3)
    H.up(3)
    assert isinstance(H.ui.overlays[-1], vt.Menu)
    H.frame()
    H.type("constant")
    H.frame()
    H.key(pygame.K_RETURN)
    assert key.interp == "constant"


def test_curve_editor_drag_value_and_legend(anim):
    H, h = anim
    h["anim_tabs"].select(1)
    H.frame()
    H.frame()
    ce, clip = h["curves"], h["clip"]
    key = clip.tracks[2].keys[2]        # Scale @ 48 = 1.3
    x, y = ce.fx(key.frame), ce.vy(key.value)
    H.move(int(x), int(y))
    H.down()
    H.move(int(x), int(y - 40), steps=4)
    H.up()
    assert key.value > 1.3 + 30 / ce.ppv * 0.9
    assert key.frame == 48
    tr, (lx, ly, lw, lh) = ce._legend_rows(H.ui)[0]
    H.click(int(lx + 30), int(ly + lh / 2))
    assert tr.visible is False


def test_transport_bar(anim):
    H, h = anim
    tb, p = h["transport"], h["player"]
    H.click(*H.center(tb.play_btn))
    assert p.playing and tb.play_btn.icon == "pause"
    H.click(*H.center(tb.play_btn))
    assert not p.playing
    tb.frame_field.set_value(33)
    assert p.frame == 33
    p.jump("next")
    assert p.frame == 36


# ----------------------------------------------------------------------------- assets
@pytest.fixture
def project(tmp_path):
    dst = tmp_path / "proj"
    shutil.copytree(SAMPLE, dst)
    return str(dst)


@pytest.fixture
def browser(project):
    H, root = fill(1100, 700)
    b = AssetBrowser(project, fill=True, parent=root)
    H.frame()
    return H, b


def test_scan_kinds(project):
    kinds = {a.name: a.kind for a in scan(os.path.join(project, "Materials"))}
    assert kinds["Metals"] == "folder" and kinds["Jade.vmat"] == "material"
    assert Asset(os.path.join(project, "Prefabs", "Crate.prefab")).data["components"][0] == "Transform"
    assert Asset(os.path.join(project, "Textures", "bricks.png")).kind == "image"


def test_browser_navigate_search_filter(browser, project):
    H, b = browser
    g = b.grid
    mats = [a for a in g.assets if a.name == "Materials"][0]
    i = g.assets.index(mats)
    x, y, w, h = g._rect(H.ui, i)
    H.click(int(x + w / 2), int(y + h / 2))
    H.click(int(x + w / 2), int(y + h / 2))            # double click enters
    assert b.cwd == os.path.join(project, "Materials")
    H.key(pygame.K_BACKSPACE)                          # grid has focus -> up
    assert b.cwd == project
    b.search.set_value("gold")
    assert [a.name for a in g.assets][0] == "Gold.vmat"
    b.search.set_value("")
    b.filter.set_value("prefab")
    b.navigate(os.path.join(project, "Prefabs"))
    assert {a.kind for a in g.assets} == {"prefab"}


def test_browser_create_rename_duplicate_delete(browser, project):
    H, b = browser
    b.navigate(os.path.join(project, "Materials"))
    b.create_material()
    assert os.path.isfile(os.path.join(project, "Materials", "New Material.vmat"))
    assert b.grid.selection[0].name == "New Material.vmat"
    b.rename(b.grid.selection[0])
    H.frame()
    assert isinstance(H.ui.overlays[-1], vt.InputDialog)
    H.key(pygame.K_a, CTRL)
    H.type("Ruby")
    H.key(pygame.K_RETURN)
    assert os.path.isfile(os.path.join(project, "Materials", "Ruby.vmat")) and not H.ui.overlays
    b.duplicate(b.grid.selection)
    assert os.path.isfile(os.path.join(project, "Materials", "Ruby copy.vmat"))
    b.delete(b.grid.selection)
    H.frame()
    H.key(pygame.K_RETURN)                             # confirm (default = Delete)
    assert not os.path.exists(os.path.join(project, "Materials", "Ruby copy.vmat"))
    b.create_prefab()
    assert load_json(os.path.join(project, "Materials", "New Prefab.prefab"), {})["type"] == "prefab"
    b.create_folder()
    H.frame()
    H.type("Sub")
    H.key(pygame.K_RETURN)
    assert os.path.isdir(os.path.join(project, "Materials", "New FolderSub")) or \
        os.path.isdir(os.path.join(project, "Materials", "Sub"))


def test_drag_asset_into_folder_tile(browser, project):
    H, b = browser
    b.navigate(os.path.join(project, "Materials"))
    H.frame()
    g = b.grid
    idx = {a.name: i for i, a in enumerate(g.assets)}
    sx, sy, sw, sh = g._rect(H.ui, idx["Jade.vmat"])
    tx, ty, tw, th = g._rect(H.ui, idx["Metals"])
    H.move(int(sx + sw / 2), int(sy + sh / 2))
    H.down()
    H.move(int(tx + tw / 2), int(ty + th / 2), steps=8)
    assert H.ui.drag is not None and H.ui.drag.target is g
    H.up()
    assert os.path.isfile(os.path.join(project, "Materials", "Metals", "Jade.vmat"))
    assert H.ui.drag is None


def test_drag_material_onto_slot_and_prefab_onto_tree(project):
    import assets_page
    H = Harness(1180, 720)
    root = vt.Row(spacing=0)
    H.ui.set_root(root)
    h = assets_page.build_assets_page(root, H.ui, project)
    b, slot, scene = h["browser"], h["slot"], h["scene"]
    b.navigate(os.path.join(project, "Materials"))
    H.frame()
    g = b.grid
    i = [a.name for a in g.assets].index("Lava.vmat")
    x, y, w, hh = g._rect(H.ui, i)
    H.move(int(x + w / 2), int(y + hh / 2))
    H.down()
    H.frame()                     # selecting re-lays out the inspector; find the slot afterwards
    H.move(*H.center(slot), steps=8)
    H.up()
    assert slot.value == os.path.join(project, "Materials", "Lava.vmat")
    b.navigate(os.path.join(project, "Prefabs"))
    H.frame()
    i = [a.name for a in g.assets].index("Crate.prefab")
    x, y, w, hh = g._rect(H.ui, i)
    H.move(int(x + w / 2), int(y + hh / 2))
    H.down()
    H.frame()
    rows = scene.rows()
    H.move(int(scene.x + 60), int(scene.y + 1 + scene.rh(H.ui) * 0.5), steps=8)   # onto "Main Scene"
    H.up()
    assert "Crate" in [c.text for c in scene.items[0].children]
    assert len(scene.rows()) == len(rows) + 1


def test_material_editor_saves(project):
    H, root = fill()
    path = create_material(project, "Test")
    ed = MaterialEditor(path, parent=root)
    H.frame()
    ed.rough.set_value(0.9)
    ed.metal.set_value(1.0)
    data = json.load(open(path))
    assert data["roughness"] == 0.9 and data["metallic"] == 1.0
    assert ed.ball.material["roughness"] == 0.9


def test_thumbnails_load_and_list_mode(browser, project):
    H, b = browser
    b.navigate(os.path.join(project, "Textures"))
    for _ in range(10):
        H.frame()
        H.ui.update(time.perf_counter() + 1)
    loaded = [k for k in H.ui.images._entries if "Textures" in k[0]]
    assert len(loaded) >= 5
    b.size_slider.set_value(28)
    H.frame()
    assert b.grid.list_mode and H.ui.stats["instances"] > 20


def test_material_ball_and_image_are_single_quads():
    H = Harness(200, 200)
    dl = vt.DrawList()
    dl.material_ball(0, 0, 64, (1, 0, 0, 1), 0.3, 0.0)
    assert dl.count == 1
    surf = pygame.Surface((32, 16), pygame.SRCALPHA)
    surf.fill((255, 0, 0, 255))
    from vitrail.images import Image
    img = Image(surf)
    H.root.add(img)
    H.frame()
    assert H.ui.images._entries and img.h == 16   # columns stretch width; height is natural
