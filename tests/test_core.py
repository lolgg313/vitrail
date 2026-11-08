# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Run with:  python -m pytest tests   (needs an OpenGL 3.3 capable EGL/GLX device)"""
import math
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))

from harness import Harness, vt, pygame  # noqa: E402

CTRL = pygame.KMOD_LCTRL
SHIFT = pygame.KMOD_LSHIFT


# ----------------------------------------------------------------------------- pure python
def test_expr():
    ev = vt.evaluate
    assert ev("2*pi") == pytest.approx(2 * math.pi)
    assert ev("10 % 3") == 1
    assert ev("sqrt(16) + 1") == 5
    assert ev("2^3") == 8
    assert ev("1,5") == 1.5
    assert ev("-(3)") == -3
    for bad in ("__import__('os')", "().__class__", "x", "1e308**2", "9**9**9", "", "open('f')", "[1]"):
        t0 = time.perf_counter()
        with pytest.raises(vt.ExprError):
            ev(bad)
        assert time.perf_counter() - t0 < 0.1


def test_fuzzy():
    modes = ["Opaque", "Alpha Clip", "Alpha Blend", "Additive", "Multiply", "Transform"]
    assert vt.fuzzy_filter("trnasform", modes)[0] == "Transform"
    assert vt.fuzzy_filter("alph bl", modes)[0] == "Alpha Blend"
    assert vt.fuzzy_filter("multipy", modes)[0] == "Multiply"
    assert vt.fuzzy_filter("zzz", modes) == []


def test_undo_stack():
    u = vt.UndoStack()
    box = [0]
    u.push("a", lambda: box.__setitem__(0, 0), lambda: box.__setitem__(0, 1))
    box[0] = 1
    assert u.undo() and box[0] == 0
    assert u.redo() and box[0] == 1
    assert not u.redo()


# ----------------------------------------------------------------------------- GPU + input
@pytest.fixture
def demo():
    import demo as demo_mod
    h = Harness()
    status = vt.Label("Ready")
    handles = demo_mod.build(h.root, status)
    h.root.add(status)
    h.frame()
    return h, handles


def test_render_runs_single_draw(demo):
    h, _ = demo
    assert h.ui.stats["instances"] > 200
    assert not h.ui.dirty
    data = h.fbo.read(components=3)
    assert len(set(data[::997])) > 10  # something non-uniform was drawn


def test_drag_scrub_is_one_undo_step(demo):
    h, w = demo
    f = w["rough"]
    v0 = f.value
    h.move(*h.center(f))
    h.down()
    for _ in range(10):
        h.move(h.mouse[0] + 10, h.mouse[1])
    h.up()
    assert f.value > v0 + 0.15
    assert not f.editing
    h.key(pygame.K_z, CTRL)
    assert f.value == pytest.approx(v0)
    h.key(pygame.K_z, CTRL | SHIFT)
    assert f.value > v0 + 0.15


def test_shift_drag_is_finer(demo):
    h, w = demo
    f = w["rough"]
    h.move(*h.center(f))
    h.down()
    for _ in range(10):
        h.move(h.mouse[0] + 10, h.mouse[1], mod=SHIFT)
    h.up()
    coarse_px = 100 / f.w
    assert 0 < f.value - 0.5 < coarse_px * 0.2


def test_click_to_type_expression(demo):
    h, w = demo
    f = w["samples"]
    h.click(*h.center(f))
    assert f.editing and h.ui.focus is f
    h.type("64*2+1")
    h.key(pygame.K_RETURN)
    assert f.value == 129 and not f.editing
    h.key(pygame.K_z, CTRL)
    assert f.value == 128


def test_bad_expression_keeps_value(demo):
    h, w = demo
    f = w["samples"]
    h.click(*h.center(f))
    h.type("hello(")
    h.key(pygame.K_RETURN)
    assert f.value == 128


def test_tab_moves_between_fields(demo):
    h, w = demo
    x, y, z = w["loc"].fields
    h.click(*h.center(x))
    assert x.editing
    h.type("5")
    h.key(pygame.K_TAB)
    assert x.value == 5.0 and not x.editing and y.editing
    h.key(pygame.K_TAB, SHIFT)
    assert x.editing
    h.key(pygame.K_ESCAPE)
    assert not x.editing and x.value == 5.0


def test_ctrl_wheel_reset_copy_paste(demo):
    h, w = demo
    s = w["samples"]
    h.move(*h.center(s))
    h.wheel(1, CTRL)
    h.wheel(1, CTRL)
    assert s.value == 130
    h.key(pygame.K_BACKSPACE)
    assert s.value == 128
    h.key(pygame.K_c, CTRL)
    h.move(*h.center(w["loc"].fields[0]))
    h.key(pygame.K_v, CTRL)
    assert w["loc"].fields[0].value == 128.0


def test_checkbox_drag_toggle(demo):
    h, _ = demo
    boxes = [c for c in h.ui.iter_widgets() if isinstance(c, vt.Checkbox) and c.text.startswith("L")]
    row0 = boxes[:4]  # L1 on, L2 off, L3 off, L4 on
    h.move(*h.center(row0[1]))
    h.down()
    for b in row0[2:]:
        h.move(*h.center(b), steps=4)
    h.up()
    assert [b.value for b in row0] == [True, True, True, True]


def test_dropdown_press_drag_release(demo):
    h, w = demo
    d = w["blend"]
    h.move(*h.center(d))
    h.down()
    menu = h.ui.overlays[-1]
    assert isinstance(menu, vt.Menu)
    h.frame()
    target = next(i for i, it in enumerate(menu._view) if it and it.label == "Opaque")
    ry, rh, _ = menu._rows[target]
    h.move(int(menu.x + 30), int(ry + rh / 2), steps=5)
    h.up()
    assert d.value == "Opaque" and not h.ui.overlays
    h.key(pygame.K_z, CTRL)
    assert d.value == "Alpha Blend"


def test_dropdown_click_then_typo_search(demo):
    h, w = demo
    d = w["blend"]
    h.click(*h.center(d))
    assert h.ui.overlays, "menu should stay open after a click"
    h.type("multipy")
    h.frame()
    h.key(pygame.K_RETURN)
    assert d.value == "Multiply" and not h.ui.overlays


def test_click_outside_closes_menu(demo):
    h, w = demo
    h.click(*h.center(w["blend"]))
    assert h.ui.overlays
    h.click(5, h.size[1] - 5)
    assert not h.ui.overlays and w["blend"].value == "Alpha Blend"


def test_text_field(demo):
    h, w = demo
    t = w["name"]
    h.click(*h.center(t))
    assert t.editing
    h.key(pygame.K_a, CTRL)
    h.type("Cube")
    h.key(pygame.K_RETURN)
    assert t.value == "Cube"
    h.click(*h.center(t))
    h.key(pygame.K_END)
    h.key(pygame.K_BACKSPACE, CTRL)
    h.type("Sphere")
    h.click(5, h.size[1] - 5)      # focus loss commits
    assert t.value == "Sphere"
    h.key(pygame.K_z, CTRL)
    assert t.value == "Cube"


def test_panel_collapse_relayout(demo):
    h, _ = demo
    panel = next(p for p in h.ui.iter_widgets() if isinstance(p, vt.Panel) and p.title == "Transform")
    tall = panel.h
    h.click(int(panel.x + 40), int(panel.y + 8))
    h.frame()
    assert panel.collapsed and panel.h < tall / 3


def test_color_picker(demo):
    h, w = demo
    sw = w["color"]
    c0 = sw.value
    h.click(*h.center(sw))
    picker = h.ui.overlays[-1]
    assert isinstance(picker, vt.ColorPicker)
    h.frame()
    plane = picker.children[0]
    h.move(int(plane.x + 5), int(plane.y + 5))
    h.down()
    h.move(int(plane.x + plane.w * 0.2), int(plane.y + plane.h * 0.1), steps=5)
    h.up()
    assert sw.value != c0
    h.key(pygame.K_ESCAPE)
    assert not h.ui.overlays
    h.key(pygame.K_z, CTRL)
    assert sw.value == pytest.approx(c0)


def test_pie_menu(demo):
    h, _ = demo
    got = []
    cx, cy = 400, 300
    h.move(cx, cy)
    vt.PieMenu.open(h.ui, ["Left", "Right", "Bottom", "Top"], got.append, at=(cx, cy))
    h.frame()
    h.move(cx + 80, cy + 5, steps=4)
    h.down()
    h.up()
    assert got == ["Right"] and not h.ui.overlays


def test_idle_does_not_rebuild(demo):
    h, w = demo
    builds = h.ui.stats["builds"]
    lbl = next(c for c in h.ui.iter_widgets() if isinstance(c, vt.Label) and c.text == "Location")
    h.move(int(lbl.x + 5), int(lbl.y + 5))
    h.frame()
    builds = h.ui.stats["builds"]
    for i in range(20):
        h.move(int(lbl.x + 5 + i), int(lbl.y + 5))
        h.frame()
    assert h.ui.stats["builds"] == builds


def test_scroll_area(demo):
    h, _ = demo
    sc = h.scroll
    h.move(400, 400)
    h.wheel(-3)
    h.frame()
    assert sc.scroll > 0 or sc.max_scroll == 0


def test_thousand_widgets_fast():
    h = Harness(1200, 800)
    with h.root:
        for i in range(250):
            with vt.Row():
                vt.NumberField(f"N{i}", i * 0.5, slider=True, min=0, max=200)
                vt.Checkbox(f"C{i}", i % 2 == 0)
                vt.Button(f"Button {i}")
                vt.Dropdown(["One", "Two", "Three"])
    h.frame()
    t0 = time.perf_counter()
    for _ in range(10):
        h.ui.invalidate(layout=True)
        h.frame()
    h.ctx.finish()
    per = (time.perf_counter() - t0) / 10 * 1000
    print(f"\n1000 widgets: full relayout+rebuild+draw {per:.2f} ms, instances={h.ui.stats['instances']}")
    t0 = time.perf_counter()
    for _ in range(50):
        h.frame()   # nothing changed: cached buffer, one draw call
    h.ctx.finish()
    cached = (time.perf_counter() - t0) / 50 * 1000
    print(f"cached frame: {cached:.3f} ms")
    assert per < 200


def test_canvas_passthrough_and_drag_panel():
    h = Harness(800, 600)
    canvas = vt.Canvas()
    h.ui.set_root(canvas)
    panel = vt.Panel("Floating", draggable=True, width=200)
    with panel:
        vt.Button("Hello")
    canvas.place(panel, 50, 50)
    h.frame()
    h.move(600, 500)
    assert h.down() is False          # empty canvas: the game gets the click
    h.up()
    h.move(100, 58)
    assert h.down() is True
    h.move(300, 258, steps=5)
    h.up()
    h.frame()
    assert panel.pos == (250, 250) and not panel.collapsed
    h.click(int(panel.x + 60), int(panel.y + 8))   # click without drag folds
    assert panel.collapsed


def test_with_block_building_and_signals():
    h = Harness(400, 300)
    got = []
    with h.root:
        with vt.Row(align=True):
            a = vt.Button("A", lambda: got.append("A"))
            b = vt.Button("B", lambda: got.append("B"))
    h.frame()
    assert a.parent is b.parent and a.corners == (True, False, False, True)
    h.click(*h.center(b))
    h.move(*h.center(a))
    h.key(pygame.K_RETURN)
    assert got == ["B", "A"]
