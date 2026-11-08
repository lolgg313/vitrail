# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Tests for icons, menus, tree view, dialogs, node editor, material widgets, logo."""
import os
import sys
import time
import xml.dom.minidom

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))

from harness import Harness, vt, pygame  # noqa: E402

CTRL = pygame.KMOD_LCTRL
SHIFT = pygame.KMOD_LSHIFT


def fill_harness(w=1100, h=700, theme=None):
    H = Harness(w, h, theme)
    root = vt.Column(spacing=0)
    H.ui.set_root(root)
    return H, root


# ----------------------------------------------------------------------------- icons
def test_every_icon_rasterises():
    H = Harness(200, 200)
    from vitrail.icons import rasterize
    for name, ops in vt.ICONS.items():
        for px in (16, 24):
            data = rasterize(ops, px)
            assert len(data) == px * px
            assert max(data) > 100, f"{name} rendered empty at {px}px"
    run = H.ui.icons.get("folder", 16)
    assert run is H.ui.icons.get("folder", 16)  # cached
    assert H.ui.icons.get("no-such-icon", 16) is None


def test_icon_draws_one_quad():
    H = Harness(100, 100)
    dl = vt.DrawList()
    H.ui.icon(dl, "settings", 10, 10, 16)
    assert dl.count == 1


# ----------------------------------------------------------------------------- menus
def _bar(H, root, log):
    MI = vt.MenuItem
    bar = vt.MenuBar([
        ("File", [MI("New", lambda: log.append("new"), shortcut="Ctrl+N", icon="file-plus"),
                  MI("Export", submenu=[MI("PNG Image", lambda: log.append("png")), MI("glTF", lambda: log.append("gltf"))]),
                  None, MI("Quit", lambda: log.append("quit"))]),
        ("Edit", [MI("Undo", lambda: log.append("undo")), MI("Grid", lambda: log.append("grid"), checked=True)]),
    ])
    root.add(bar)
    root.add(vt.Button("under", lambda: log.append("button")))
    H.frame()
    return bar


def test_menubar_open_hover_switch_submenu_pick():
    H, root = fill_harness()
    log = []
    bar = _bar(H, root, log)
    rects = bar._title_rects(H.ui)
    H.click(int(rects[0][0] + 5), int(rects[0][1] + 5))
    file_menu = H.ui.overlays[-1]
    assert isinstance(file_menu, vt.Menu) and len(file_menu.items) == 4
    H.frame()
    H.move(int(rects[1][0] + 5), int(rects[1][1] + 5))          # hover "Edit" switches menus
    assert H.ui.overlays[-1].items[0].label == "Undo"
    H.move(int(rects[0][0] + 5), int(rects[0][1] + 5))
    m = H.ui.overlays[-1]
    H.frame()
    r = m.row_rect(1)                                          # hover "Export" opens submenu
    H.move(int(r[0] + 30), int(r[1] + r[3] / 2))
    H.frame()
    sub = H.ui.overlays[-1]
    assert sub.parent_menu is m and sub.items[0].label == "PNG Image"
    sr = sub.row_rect(0)
    H.move(int(sr[0] + 30), int(sr[1] + sr[3] / 2), steps=3)
    H.click(*H.mouse)
    assert log == ["png"] and not H.ui.overlays


def test_menu_shortcut_and_search():
    H, root = fill_harness()
    log = []
    bar = _bar(H, root, log)
    H.key(pygame.K_n, CTRL)
    assert log == ["new"]
    rects = bar._title_rects(H.ui)
    H.click(int(rects[0][0] + 5), int(rects[0][1] + 5))
    H.type("gltf")                    # search reaches into submenus
    H.frame()
    m = H.ui.overlays[-1]
    assert m._view[0].path.endswith("glTF")
    H.key(pygame.K_RETURN)
    assert log == ["new", "gltf"]


def test_keyboard_menu_navigation():
    H, root = fill_harness()
    log = []
    bar = _bar(H, root, log)
    rects = bar._title_rects(H.ui)
    H.click(int(rects[0][0] + 5), int(rects[0][1] + 5))
    H.frame()
    H.key(pygame.K_DOWN)
    H.key(pygame.K_DOWN)          # Export
    H.key(pygame.K_RIGHT)         # into submenu
    H.frame()
    H.key(pygame.K_RETURN)
    assert log == ["png"]


def test_context_menu():
    H, root = fill_harness()
    got = []
    vt.open_context_menu(H.ui, [("Copy", lambda: got.append(1)), None, vt.MenuItem("Paste", lambda: got.append(2))],
                         at=(100, 100))
    H.frame()
    m = H.ui.overlays[-1]
    r = m.row_rect(2)
    H.click(int(r[0] + 20), int(r[1] + 5))
    assert got == [2]


# ----------------------------------------------------------------------------- tree
def _tree_items():
    return [vt.TreeItem("Animals", [vt.TreeItem("Cat"), vt.TreeItem("Dog"), vt.TreeItem("Duck")], expanded=True),
            vt.TreeItem("Plants", [vt.TreeItem("Oak"), vt.TreeItem("Fern")]),
            vt.TreeItem("Zebra crossing")]


def test_tree_keyboard_and_typeahead():
    H, root = fill_harness()
    t = vt.TreeView(_tree_items(), fill=True, parent=root)
    H.frame()
    H.click(int(t.x + 60), int(t.y + 5))                 # row 0: Animals
    assert t.selection[0].text == "Animals" and H.ui.focus is t
    H.key(pygame.K_DOWN)
    H.key(pygame.K_DOWN)
    assert t.selection[0].text == "Dog"
    H.key(pygame.K_DOWN, SHIFT)
    assert [i.text for i in t.selection] == ["Dog", "Duck"]
    H.key(pygame.K_DOWN)
    H.key(pygame.K_RIGHT)                                 # expand Plants
    assert t.items[1].expanded
    H.type("z")
    assert t.selection[0].text == "Zebra crossing"
    H.key(pygame.K_HOME)
    H.key(pygame.K_LEFT)                                  # collapse Animals
    assert not t.items[0].expanded


def test_tree_drag_drop_into_and_before():
    H, root = fill_harness()
    t = vt.TreeView(_tree_items(), drag_drop=True, fill=True, parent=root)
    moved = []
    t.moved.connect(lambda it, p, i: moved.append((it.text, p.text, i)))
    H.frame()
    rh = t.rh(H.ui)
    rows = [r[0].text for r in t.rows()]
    cat_y = t.y + 1 + rows.index("Cat") * rh + rh / 2
    plants_y = t.y + 1 + rows.index("Plants") * rh + rh / 2
    H.move(int(t.x + 80), int(cat_y))
    H.down()
    H.move(int(t.x + 80), int(plants_y), steps=6)
    H.up()
    assert moved == [("Cat", "Plants", 2)]
    assert t.items[1].expanded and t.items[1].children[-1].text == "Cat"
    rows = [r[0].text for r in t.rows()]
    zebra_top = t.y + 1 + rows.index("Zebra crossing") * rh + 2
    dog_y = t.y + 1 + rows.index("Dog") * rh + rh / 2
    H.move(int(t.x + 80), int(dog_y))
    H.down()
    H.move(int(t.x + 80), int(zebra_top), steps=6)        # top edge -> "before"
    H.up()
    assert [i.text for i in t.items] == ["Animals", "Plants", "Dog", "Zebra crossing"]


def test_tree_cannot_drop_into_own_child():
    H, root = fill_harness()
    t = vt.TreeView(_tree_items(), drag_drop=True, fill=True, parent=root)
    H.frame()
    rh = t.rh(H.ui)
    H.move(int(t.x + 80), int(t.y + 1 + rh / 2))           # Animals
    H.down()
    H.move(int(t.x + 80), int(t.y + 1 + rh * 1.5), steps=5)  # onto Cat (its child)
    H.up()
    assert t.items[0].text == "Animals" and t.items[0].parent is t.root


def test_tree_lazy_columns_sort_and_scale():
    calls = []

    def load(item):
        calls.append(item.text)
        return [vt.TreeItem(f"child {i}", values=(str(i),), sort_keys=(f"child {i}", i)) for i in (3, 1, 2)]
    H, root = fill_harness()
    t = vt.TreeView([vt.TreeItem("lazy", lazy=load)], columns=[("Name", None), ("N", 60)], fill=True, parent=root)
    H.frame()
    assert calls == []
    t.set_expanded(t.items[0])
    assert calls == ["lazy"] and len(t.rows()) == 4
    t.sort_by(1)
    assert [c.values[0] for c in t.items[0].children] == ["1", "2", "3"]
    t.sort_by(1, descending=True)
    assert [c.values[0] for c in t.items[0].children] == ["3", "2", "1"]
    big = vt.TreeView([vt.TreeItem(f"item {i}") for i in range(100_000)], fill=True)
    root.clear()
    root.add(big)
    H.frame()
    t0 = time.perf_counter()
    big.scroll = 50_000 * big.rh(H.ui)
    big.invalidate()
    H.frame()
    assert time.perf_counter() - t0 < 0.5
    assert H.ui.stats["instances"] < 400


# ----------------------------------------------------------------------------- dialogs
@pytest.fixture
def tmpfs(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "inner.txt").write_text("x")
    (tmp_path / "a.png").write_bytes(b"1234")
    (tmp_path / "b.png").write_bytes(b"12")
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / ".secret").write_text("s")
    return tmp_path


def test_file_dialog_open_filter_navigate(tmpfs):
    H, root = fill_harness()
    got = []
    d = vt.FileDialog.open_file(H.ui, got.append, start_dir=str(tmpfs),
                                filters=[("Images", "*.png"), ("All files", "*")])
    H.frame()
    names = [i.text for i in d.files.items]
    assert names == ["docs", "a.png", "b.png"]          # folders first, filtered, no hidden
    d.filter_box.set_value(1)
    assert "notes.txt" in [i.text for i in d.files.items] and ".secret" not in [i.text for i in d.files.items]
    d.hidden_box.set_value(True)
    assert ".secret" in [i.text for i in d.files.items]
    docs = d.files.items[0]
    d.files.activated.emit(docs)                        # double-click a folder
    assert d.cwd == str(tmpfs / "docs") and [i.text for i in d.files.items] == ["inner.txt"]
    H.key(pygame.K_BACKSPACE)                           # parent folder
    assert d.cwd == str(tmpfs)
    d.go_back()
    assert d.cwd == str(tmpfs / "docs")
    d.go_forward()
    assert d.cwd == str(tmpfs)
    H.frame()
    item = [i for i in d.files.items if i.text == "a.png"][0]
    d.files.select([item])
    assert d.name_field.value == "a.png"
    d.accept()
    assert got == [str(tmpfs / "a.png")] and not H.ui.overlays


def test_file_dialog_multiple_and_cancel(tmpfs):
    H, root = fill_harness()
    got = []
    d = vt.FileDialog.open_file(H.ui, got.append, start_dir=str(tmpfs), multiple=True)
    H.frame()
    pngs = [i for i in d.files.items if i.text.endswith(".png")]
    d.files.select(pngs)
    assert d.name_field.value == '"a.png" "b.png"'
    d.accept()
    assert got == [[str(tmpfs / "a.png"), str(tmpfs / "b.png")]]
    vt.FileDialog.open_file(H.ui, got.append, start_dir=str(tmpfs))
    H.frame()
    H.key(pygame.K_ESCAPE)
    assert got[-1] is None and not H.ui.overlays


def test_file_dialog_save_overwrite_confirm(tmpfs):
    H, root = fill_harness()
    got = []
    d = vt.FileDialog.save_file(H.ui, got.append, start_dir=str(tmpfs), filters=[("Text", "*.txt")],
                                default_name="notes")
    H.frame()
    d.accept()                                           # "notes" -> notes.txt exists -> confirm
    box = H.ui.overlays[-1]
    assert isinstance(box, vt.MessageBox)
    H.frame()
    H.key(pygame.K_RETURN)                               # default button = Replace
    assert got == [str(tmpfs / "notes.txt")]
    d = vt.FileDialog.save_file(H.ui, got.append, start_dir=str(tmpfs), filters=[("Text", "*.txt")],
                                default_name="fresh")
    d.accept()
    assert got[-1] == str(tmpfs / "fresh.txt")


def test_file_dialog_folder_and_new_folder(tmpfs):
    H, root = fill_harness()
    got = []
    d = vt.FileDialog.choose_folder(H.ui, got.append, start_dir=str(tmpfs))
    H.frame()
    assert [i.text for i in d.files.items] == ["docs"]
    d._new_folder()
    H.frame()
    inp = H.ui.overlays[-1]
    assert isinstance(inp, vt.InputDialog) and inp.field.editing
    H.key(pygame.K_a, CTRL)
    H.type("assets")
    H.key(pygame.K_RETURN)
    assert (tmpfs / "assets").is_dir()
    assert [i.text for i in d.files.selection] == ["assets"]
    d.accept()
    assert got == [str(tmpfs / "assets")]


def test_modal_blocks_underlying_ui():
    H, root = fill_harness()
    hits = []
    b = vt.Button("under", lambda: hits.append(1), parent=root)
    H.frame()
    vt.MessageBox.ask(H.ui, "Hello", hits.append, buttons=("OK",))
    H.frame()
    H.click(*H.center(b))
    assert hits == [] and H.ui.overlays
    H.key(pygame.K_RETURN)
    assert hits == ["OK"]
    H.click(*H.center(b))
    assert hits == ["OK", 1]


def test_drives_and_places():
    from vitrail.dialogs import list_drives, user_places, _parent
    assert list_drives() == ["/"] if os.name != "nt" else list_drives()
    assert user_places()[0][0] == "Home"
    assert _parent("/") == "/" and _parent("/a/b") == "/a"


# ----------------------------------------------------------------------------- node editor
@pytest.fixture
def graph():
    import blueprint_nodes
    H, root = fill_harness()
    from vitrail.nodes import NodeEditor
    ed = NodeEditor(fill=True, parent=root)
    blueprint_nodes.register_all(ed)
    H.frame()
    return H, ed


def test_node_link_by_drag_and_evaluate(graph):
    H, ed = graph
    a = ed.add_node(ed.create("Input/Value"), (20, 20))
    m = ed.add_node(ed.create("Math/Multiply"), (300, 20))
    H.frame()
    m.socket("B", False).slot.field.value = 3.0
    a.socket("Value", False).slot.field.value = 2.5
    H.move(*map(int, a.socket_pos(a.socket("Out"))))
    H.down()
    H.move(*map(int, m.socket_pos(m.socket("A", False))), steps=8)
    H.up()
    assert len(ed.links) == 1
    assert ed.evaluate(m)["Result"] == pytest.approx(7.5)
    H.frame()
    assert not m.socket("A", False).slot.field._visible or m.socket("A", False).slot.shown() is not m.socket("A", False).slot.field
    H.key(pygame.K_z, CTRL)
    assert ed.links == []


def test_node_type_rules_and_cycles(graph):
    H, ed = graph
    ev = ed.add_node(ed.create("Events/On Start"))
    add = ed.add_node(ed.create("Math/Add"), (200, 0))
    add2 = ed.add_node(ed.create("Math/Add"), (400, 0))
    assert ed.connect(ev.socket("Then"), add.socket("A", False)) is None       # exec -> float refused
    assert ed.connect(add.socket("Result"), add2.socket("A", False)) is not None
    assert ed.connect(add2.socket("Result"), add.socket("B", False)) is None   # would be a cycle
    assert ed.connect(add.socket("Result"), add2.socket("B", False)) is not None  # outputs fan out
    v = ed.add_node(ed.create("Input/Value"))
    ed.connect(v.socket("Out"), add2.socket("A", False))                       # replaces old input link
    assert [lk.out.node for lk in add2.socket("A", False).links] == [v]


def test_node_detach_by_dragging_input(graph):
    H, ed = graph
    a = ed.add_node(ed.create("Input/Value"), (20, 20))
    b = ed.add_node(ed.create("Output/Viewer"), (300, 40))
    ed.connect(a.socket("Out"), b.socket("Value"))
    H.frame()
    H.move(*map(int, b.socket_pos(b.socket("Value"))))
    H.down()
    H.move(int(b.x - 120), int(b.y + 200), steps=6)
    H.up()
    assert ed.links == []


def test_node_select_move_delete_undo(graph):
    H, ed = graph
    n1 = ed.add_node(ed.create("Math/Add"), (40, 40))
    n2 = ed.add_node(ed.create("Math/Add"), (300, 40))
    ed.connect(n1.socket("Result"), n2.socket("A", False))
    H.frame()
    H.move(int(n1.x + 30), int(n1.y + 8))
    H.down()
    H.move(int(n1.x + 130), int(n1.y + 58), steps=4)
    H.up()
    assert n1.gpos[0] == pytest.approx(140, abs=2) and n1.selected
    H.key(pygame.K_z, CTRL)
    assert n1.gpos == (40.0, 40.0)
    H.frame()
    H.move(int(ed.x + 5), int(ed.y + 5))                  # box select both
    H.down()
    H.move(int(ed.x + ed.w - 5), int(ed.y + ed.h - 5), steps=4)
    H.up()
    assert len(ed.selected) == 2
    H.key(pygame.K_x)
    assert ed.nodes == [] and ed.links == []
    H.key(pygame.K_z, CTRL)
    assert len(ed.nodes) == 2 and len(ed.links) == 1


def test_node_zoom_and_scaled_widgets(graph):
    H, ed = graph
    n = ed.add_node(ed.create("Input/Value"), (40, 40))
    H.frame()
    w0 = n.w
    H.move(int(ed.x + 300), int(ed.y + 200))
    g_before = ed.to_graph(*H.mouse)
    for _ in range(4):
        H.wheel(1)
    H.frame()
    assert ed.content_zoom > 1.4 and n.w > w0 * 1.4
    g_after = ed.to_graph(*H.mouse)
    assert g_before[0] == pytest.approx(g_after[0], abs=1) and g_before[1] == pytest.approx(g_after[1], abs=1)
    f = n.socket("Value", False).slot.field
    H.click(*H.center(f))                                # click to type, at zoom
    assert f.editing
    H.type("4.25")
    H.key(pygame.K_RETURN)
    assert f.value == 4.25
    assert H.ui.theme.scale == 1.0                        # scale restored after dispatch


def test_node_serialise_roundtrip(graph):
    H, ed = graph
    a = ed.add_node(ed.create("Input/Value"), (0, 0))
    b = ed.add_node(ed.create("Math/Functions/Sine"), (200, 0))
    a.socket("Value", False).slot.field.value = 0.5
    ed.connect(a.socket("Out"), b.socket("Value", False))
    data = ed.to_dict()
    ed.from_dict(data)
    assert len(ed.nodes) == 2 and len(ed.links) == 1
    import math
    sine = [n for n in ed.nodes if n.title == "Sine"][0]
    assert ed.evaluate(sine)["Result"] == pytest.approx(math.sin(0.5))


def test_add_node_menu_search(graph):
    H, ed = graph
    H.move(int(ed.x + 200), int(ed.y + 150))
    H.down(3)
    H.up(3)
    menu = H.ui.overlays[-1]
    assert menu.title == "Add Node"
    H.type("sine")
    H.frame()
    H.key(pygame.K_RETURN)
    assert [n.title for n in ed.nodes] == ["Sine"]


def test_knife_cuts_wires(graph):
    H, ed = graph
    a = ed.add_node(ed.create("Input/Value"), (20, 40))
    b = ed.add_node(ed.create("Output/Viewer"), (400, 40))
    ed.connect(a.socket("Out"), b.socket("Value"))
    H.frame()
    xm = int((a.x + a.w + b.x) / 2)
    H.move(xm, int(ed.y + 5))
    H.down(3, CTRL)
    H.move(xm, int(ed.y + 400), steps=5)
    H.up(3)
    assert ed.links == []


# ----------------------------------------------------------------------------- material
def test_material_widgets():
    from vitrail.material import MButton, RadioGroup, Slider, Snackbar, Switch, Chip
    H, root = fill_harness(theme=vt.Theme.material_dark())
    got = []
    with root:
        b = MButton("Go", lambda: got.append("go"))
        sw = Switch("Wifi", False)
        r = RadioGroup(["a", "b", "c"], "a")
        sl = Slider(0.0)
        ch = Chip("Tag")
        under = vt.Button("under", lambda: got.append("under"))
    H.frame()
    H.click(*H.center(b))
    assert got == ["go"] and H.ui.animating
    H.click(*H.center(sw))
    assert sw.value is True
    H.ui.update(time.perf_counter() + 5)
    assert not H.ui.animating
    H.click(int(r.x + 20), int(r.y + r.h * 5 / 6))
    assert r.value == "c"
    x, cy, w = sl._track(H.ui)
    H.move(int(x), int(cy))
    H.down()
    H.move(int(x + w * 0.75), int(cy), steps=4)
    H.up()
    assert sl.value == pytest.approx(0.75, abs=0.02)
    H.key(pygame.K_z, CTRL)
    assert sl.value == 0.0
    H.click(*H.center(ch))
    assert ch.value
    sb = Snackbar.show(H.ui, "Saved")
    H.frame()
    H.click(*H.center(under))                              # snackbar does not block
    assert got[-1] == "under" and sb in H.ui.overlays
    H.ui.update(time.perf_counter() + 10)
    assert sb not in H.ui.overlays


# ----------------------------------------------------------------------------- showcase / logo
@pytest.mark.parametrize("theme", ["dark", "light", "material_dark", "material_light"])
def test_showcase_all_tabs_all_themes(theme):
    import demo
    H, root = fill_harness(1180, 760, getattr(vt.Theme, theme)())
    h = demo.build_showcase(root, H.ui)
    for i in range(len(h["tabs"].children)):
        h["tabs"].select(i)
        H.frame()
        assert H.ui.stats["instances"] > 50


def test_logo():
    from vitrail.logo import logo_surface, logo_svg
    pygame.init()
    s = logo_surface(48)
    assert s.get_size() == (48, 48)
    assert s.get_at((24, 30))[3] == 255 and s.get_at((1, 1))[3] < 40
    xml.dom.minidom.parseString(logo_svg())
