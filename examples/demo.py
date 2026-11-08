# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Vitrail feature tour.  Run:  python examples/demo.py

Try: drag numbers (Shift fine, Ctrl snap), click to type "2*pi", Ctrl+Z,
Ctrl+wheel over a field, Backspace to reset, right-click a field, drag across
the checkboxes, type inside an open dropdown, hold Q for the pie menu.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame  # noqa: E402

import vitrail as vt  # noqa: E402

BLEND_MODES = ["Opaque", "Alpha Clip", "Alpha Hashed", "Alpha Blend", "Additive", "Multiply",
               "Screen", "Overlay", "Soft Light", "Hard Light", "Color Dodge", "Color Burn"]


def build(root, status=None):
    """Fill ``root`` (a Column) with the demo widgets. Returns a dict of handles."""
    h = {}

    def log(msg):
        if status is not None:
            status.text = msg

    with vt.Row(parent=root, spacing=10, expand=1):
        with vt.Column(spacing=8):
            with vt.Panel("Transform", icon="move"):
                h["loc"] = vt.VectorField("Location", (0.0, 1.25, -3.5), step=0.1, unit=" m",
                                          on_change=lambda v: log(f"location = {tuple(round(c, 3) for c in v)}"))
                vt.VectorField("Rotation", (0.0, 90.0, 0.0), step=1.0, precision=1, unit="°")
                vt.VectorField("Scale", (1.0, 1.0, 1.0), step=0.05, min=0.0)
            with vt.Panel("Material", icon="palette"):
                h["color"] = vt.ColorSwatch((0.86, 0.35, 0.18, 1.0), label="Base Color",
                                            on_change=lambda c: log(f"color = {vt.to_hex(c)}"))
                vt.ColorSwatch("#3b8eea80", label="Emission")
                h["rough"] = vt.NumberField("Roughness", 0.5, min=0.0, max=1.0, slider=True,
                                            tooltip="Microsurface roughness\nDrag, or click to type")
                vt.NumberField("Metallic", 0.0, min=0.0, max=1.0, slider=True)
                vt.NumberField("IOR", 1.45, min=1.0, max=4.0, step=0.01)
                h["blend"] = vt.Dropdown(BLEND_MODES, "Alpha Blend", label="Blend Mode",
                                         on_change=lambda v: log(f"blend = {v}"))
                with vt.Row():
                    vt.Checkbox("Backface Culling", True)
                    vt.Checkbox("Shadows", True)
            with vt.Panel("Object", icon="cube"):
                h["name"] = vt.TextField("Suzanne", label="Name", placeholder="object name",
                                         on_change=lambda v: log(f"name = {v!r}"))
                vt.TextField("", label="Tag", placeholder="type something")
                with vt.Row(align=True):
                    vt.Toggle("Visible", True)
                    vt.Toggle("Selectable", True)
                    vt.Toggle("Locked", False)

        with vt.Column(spacing=8):
            with vt.Panel("Render", icon="camera"):
                h["engine"] = vt.EnumRow(["Raster", "Path", "Hybrid"], "Path",
                                         on_change=lambda v: log(f"engine = {v}"))
                h["samples"] = vt.NumberField("Samples", 128, min=1, max=4096, step=1)
                vt.NumberField("Exposure", 0.0, soft_min=-5, soft_max=5, slider=True, step=0.1)
                h["progress"] = vt.ProgressBar(0.62)
                with vt.Row():
                    vt.Button("Preview", lambda: log("preview clicked"), icon="eye")
                    vt.Button("Render", lambda: log("render clicked"), primary=True, icon="play")
            with vt.Panel("Layers  (drag across the boxes)", icon="layers"):
                for row in range(3):
                    with vt.Row():
                        for col in range(4):
                            vt.Checkbox(f"L{row * 4 + col + 1}", (row + col) % 3 == 0)
            with vt.Panel("Advanced", collapsed=True, icon="settings"):
                vt.NumberField("Seed", 42, step=1)
                vt.NumberField("Clamp", 10.0, min=0.0)
                vt.Label("Collapsed by default", dim=True)
    return h


# =============================================================================== showcase app
SCENE = {
    "Scene": {
        "Camera": None, "Sun": None,
        "Characters": {"Hero": {"Armature": None, "Body": None, "Sword": None}, "Villain": {"Body": None}},
        "Environment": {"Terrain": None, "Trees": {f"Tree.{i:03d}": None for i in range(1, 25)}, "Water": None},
    }
}
_ICON_FOR = {"Camera": "camera", "Sun": "sun", "Armature": "move", "Water": "drop", "Terrain": "layers"}


def _scene_items(d):
    out = []
    for name, sub in d.items():
        icon = _ICON_FOR.get(name, "folder" if isinstance(sub, dict) else "cube")
        out.append(vt.TreeItem(name, _scene_items(sub) if isinstance(sub, dict) else (), icon=icon,
                               expanded=name in ("Scene", "Characters")))
    return out


def _fs_item(path, name=None):
    def load(item):
        try:
            entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            return []
        return [_fs_item(e.path, e.name) if e.is_dir() else
                vt.TreeItem(e.name, icon=vt.dialogs.icon_for(e.name)) for e in entries if not e.name.startswith(".")]
    return vt.TreeItem(name or path, icon="folder", lazy=load, data=path)


def build_showcase(root, ui, project_root=None):
    """The full tour inside ``root`` (a window-sized Column). Returns handles."""
    from vitrail.material import (AppBar, Card, Chip, FAB, IconButton, MButton, OutlinedField, RadioGroup,
                                  Slider, Snackbar, Spinner, Switch)
    from vitrail.nodes import NodeEditor
    import blueprint_nodes

    h = {}
    status = vt.Label("Ready", dim=True, icon="info")
    themes = {"Editor Dark": vt.Theme.dark, "Editor Light": vt.Theme.light,
              "Material Dark": vt.Theme.material_dark, "Material Light": vt.Theme.material_light}
    current = {"theme": "Editor Dark"}

    def set_theme(name):
        current["theme"] = name
        ui.set_theme(themes[name]())
        status.text = f"Theme: {name}"

    def say(msg):
        status.text = msg

    def open_dialog():
        vt.FileDialog.open_file(ui, lambda p: say(f"Opened: {p}" if p else "Open cancelled"),
                                filters=[("All files", "*"), ("Images", "*.png;*.jpg;*.jpeg;*.gif"),
                                         ("Python", "*.py"), ("Scenes", "*.json;*.glb;*.gltf")])

    def save_dialog():
        vt.FileDialog.save_file(ui, lambda p: say(f"Saved as: {p}" if p else "Save cancelled"),
                                filters=[("JSON graph", "*.json"), ("All files", "*")], default_name="graph.json")

    # ---------------------------------------------------------------- menu bar
    MI = vt.MenuItem
    menubar = vt.MenuBar([
        ("File", [
            MI("New", lambda: say("New file"), icon="file-plus", shortcut="Ctrl+N"),
            MI("Open...", open_dialog, icon="folder-open", shortcut="Ctrl+O"),
            MI("Open Recent", submenu=[MI(f"project_{i}.vit", (lambda i=i: say(f"Recent {i}")), icon="file")
                                       for i in range(1, 6)]),
            None,
            MI("Save As...", save_dialog, icon="save", shortcut="Ctrl+Shift+S"),
            MI("Export", icon="upload", submenu=[MI("PNG Image", lambda: say("Export PNG"), icon="file-image"),
                                                 MI("glTF Scene", lambda: say("Export glTF"), icon="cube"),
                                                 MI("Graph JSON", save_dialog, icon="file-code")]),
            None,
            MI("Quit", lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)), icon="power", shortcut="Ctrl+Q"),
        ]),
        ("Edit", [
            MI("Undo", ui.undo.undo, icon="undo", shortcut="Ctrl+Z", enabled=lambda: ui.undo.can_undo),
            MI("Redo", ui.undo.redo, icon="redo", shortcut="Ctrl+Shift+Z", enabled=lambda: ui.undo.can_redo),
            None,
            MI("Find...", lambda: say("Find"), icon="search", shortcut="Ctrl+F"),
            MI("Preferences...", lambda: vt.MessageBox.ask(ui, "Preferences live in the Theme menu for now.",
                                                         title="Preferences", icon="settings"), icon="settings"),
        ]),
        ("View", [
            MI("Theme", icon="palette", submenu=[MI(n, (lambda n=n: set_theme(n)),
                                                    checked=(lambda n=n: current["theme"] == n)) for n in themes]),
            MI("Show Status Bar", lambda: setattr(status, "visible", not status.visible),
               checked=lambda: status.visible),
            None,
            MI("Properties", lambda: tabs.select(0), shortcut="Ctrl+1"),
            MI("Blueprint", lambda: tabs.select(1), shortcut="Ctrl+2"),
            MI("Material", lambda: tabs.select(2), shortcut="Ctrl+3"),
            MI("Tree & Files", lambda: tabs.select(3), shortcut="Ctrl+4"),
            MI("Icons", lambda: tabs.select(4), shortcut="Ctrl+5"),
            MI("Animation", lambda: tabs.select(5), shortcut="Ctrl+6"),
            MI("Assets", lambda: tabs.select(6), shortcut="Ctrl+7"),
        ]),
        ("Help", [
            MI("Keyboard Shortcuts", lambda: vt.MessageBox.ask(
                ui, "Drag numbers: Shift fine, Ctrl snap\nCtrl+Z / Ctrl+Shift+Z undo / redo\n"
                    "Ctrl+wheel steps the hovered value\nType in any open menu to search it\n"
                    "Hold Q for the pie menu", title="Shortcuts", icon="keyboard"), icon="keyboard"),
            MI("About Vitrail", lambda: AboutDialog().open(ui), icon="info"),
        ]),
    ])
    root.add(menubar)

    tabs = vt.Tabs(fill=True)
    root.add(tabs)
    h["tabs"] = tabs

    # ---------------------------------------------------------------- 1. properties
    props = tabs.add_tab("Properties", vt.Column(spacing=0), icon="sliders")
    sc = vt.ScrollArea(vt.Column(padding=10, spacing=8), fill=True, parent=props)
    h.update(build(sc.content, status))

    # ---------------------------------------------------------------- 2. blueprint
    bp = tabs.add_tab("Blueprint", vt.Column(spacing=0), icon="node")
    bar = vt.Row(spacing=6, padding=6, parent=bp)
    ed = NodeEditor(fill=True, parent=bp)
    blueprint_nodes.build_sample_graph(ed)
    h["editor"] = ed
    vt.Button("Add Node", lambda: ed.open_add_menu(ui, (ed.x + ed.w / 2, ed.y + 40)), icon="plus", expand=0, parent=bar)
    vt.Button("Frame All", ed.frame_all, icon="fullscreen", expand=0, parent=bar)
    vt.Button("Save Graph...", lambda: vt.FileDialog.save_file(
        ui, lambda p: p and (open(p, "w").write(__import__("json").dumps(ed.to_dict(), indent=1)), say(f"Graph saved: {p}")),
        filters=[("JSON graph", "*.json")], default_name="graph.json"), icon="save", expand=0, parent=bar)
    vt.Button("Load Graph...", lambda: vt.FileDialog.open_file(
        ui, lambda p: p and (ed.from_dict(__import__("json").load(open(p))), say(f"Graph loaded: {p}")),
        filters=[("JSON graph", "*.json")]), icon="folder-open", expand=0, parent=bar)
    vt.Label("Right-click: add  •  drag sockets  •  Ctrl+right-drag: cut  •  wheel: zoom",
             dim=True, parent=bar)

    # ---------------------------------------------------------------- 3. material
    mat = tabs.add_tab("Material", vt.Column(spacing=0), icon="shapes")
    AppBar("Material components", actions=[("search", lambda: say("Search")),
                                            ("bell", lambda: Snackbar.show(ui, "No new notifications")),
                                            ("dots-vertical", lambda: vt.open_context_menu(
                                                ui, [MI("Settings", lambda: say("Settings"), icon="settings"),
                                                     MI("Help", lambda: say("Help"), icon="help")]))],
           on_nav=lambda: say("Navigation"), parent=mat)
    msc = vt.ScrollArea(vt.Column(padding=16, spacing=14), fill=True, parent=mat)
    with msc.content:
        with vt.Row(spacing=14):
            with Card("Buttons", subtitle="Five emphasis levels"):
                MButton("Filled", lambda: Snackbar.show(ui, "Filled button pressed", ("Undo", lambda: say("Undone"))),
                        icon="check")
                MButton("Tonal", lambda: say("Tonal"), variant="tonal")
                MButton("Outlined", lambda: say("Outlined"), variant="outlined", icon="download")
                MButton("Elevated", lambda: say("Elevated"), variant="elevated")
                MButton("Text", lambda: say("Text"), variant="text")
            with Card("Selection", subtitle="Switches, chips, radios"):
                Switch("Wi-Fi", True)
                Switch("Bluetooth", False)
                with vt.Row(spacing=6):
                    Chip("Pets", True, icon="heart")
                    Chip("Music", False, icon="music")
                    Chip("Travel", False, icon="globe")
                h["radio"] = RadioGroup(["Small", "Medium", "Large"], "Medium")
            with Card("Inputs", subtitle="Outlined fields and sliders"):
                OutlinedField("Ada Lovelace", label="Full name")
                OutlinedField("", label="Email", supporting="We never share it")
                h["slider"] = Slider(0.4, label="Volume", fmt="{:.0%}")
                Slider(3, min=0, max=10, step=1, label="Stars", fmt="{:.0f}")
        with vt.Row(spacing=14):
            with Card("Progress", subtitle="Determinate and indeterminate"):
                with vt.Row(spacing=12):
                    Spinner(36, expand=0)
                    vt.ProgressBar(0.72, text="{value:.0%} uploaded")
            with Card("Actions", subtitle="Icon buttons and a FAB"):
                with vt.Row(spacing=4):
                    for ic in ("edit", "share", "bookmark", "trash"):
                        IconButton(ic, (lambda ic=ic: say(f"{ic} clicked")), expand=0, tooltip=ic.title())
                    vt.Spacer()
                    FAB("plus", lambda: Snackbar.show(ui, "Created a new item"), text="Create", expand=0)
            with Card("Tip", subtitle="Material look everywhere"):
                vt.Label("View › Theme › Material Dark", icon="palette")
                vt.Label("re-skins the whole app.", dim=True)

    # ---------------------------------------------------------------- 4. tree & files
    tf = tabs.add_tab("Tree & Files", vt.Row(spacing=10, padding=10), icon="list")
    with tf:
        with vt.Column(spacing=6):
            vt.Label("Outliner  (drag & drop to re-parent, Ctrl/Shift multi-select)", bold=True, icon="layers")
            outl = vt.TreeView(_scene_items(SCENE), drag_drop=True, fill=True)
            outl.selection_changed.connect(lambda sel: say("Selected: " + ", ".join(i.text for i in sel)))
            outl.moved.connect(lambda it, parent, idx: say(f"Moved {it.text} into {parent.text}"))
            h["outliner"] = outl
        with vt.Column(spacing=6):
            vt.Label("File browser  (lazy-loads folders, sortable columns)", bold=True, icon="folder")
            home = os.path.expanduser("~")
            fsv = vt.TreeView([_fs_item(home, home)], fill=True)
            fsv.items[0].expanded = True
            fsv.refresh()
            with vt.Row(spacing=6):
                vt.Button("Open File...", open_dialog, icon="folder-open")
                vt.Button("Open Multiple...", lambda: vt.FileDialog.open_file(
                    ui, lambda p: say(f"{len(p)} files" if p else "Cancelled"), multiple=True), icon="file")
            with vt.Row(spacing=6):
                vt.Button("Save As...", save_dialog, icon="save")
                vt.Button("Choose Folder...", lambda: vt.FileDialog.choose_folder(
                    ui, lambda p: say(f"Folder: {p}" if p else "Cancelled")), icon="folder")
            with vt.Row(spacing=6):
                vt.Button("Message Box", lambda: vt.MessageBox.ask(
                    ui, "Delete 3 selected objects?\nThis cannot be undone.", lambda r: say(f"Answer: {r}"),
                    title="Delete objects", buttons=("Cancel", "Delete"), icon="warning", default="Delete",
                    cancel="Cancel"), icon="warning")
                vt.Button("Input Dialog", lambda: vt.InputDialog.ask(
                    ui, "Rename", "New name", lambda r: say(f"Renamed to {r!r}" if r else "Cancelled"),
                    default="Cube.001"), icon="edit")

    # ---------------------------------------------------------------- 5. icons
    ic = tabs.add_tab("Icons", vt.Column(spacing=8, padding=10), icon="grid")
    search = vt.TextField("", placeholder="Filter icons...  (e.g. file, arrow, media)", parent=ic)
    gallery = IconGallery(fill=True, parent=ic)
    search.edited.connect(gallery.set_filter)
    search.changed.connect(gallery.set_filter)

    # ---------------------------------------------------------------- 6. animation
    import anim_page
    an = tabs.add_tab("Animation", vt.Column(spacing=0), icon="film")
    h.update(anim_page.build_animation_page(an, ui))

    # ---------------------------------------------------------------- 7. assets
    import assets_page
    ap = tabs.add_tab("Assets", vt.Row(spacing=0), icon="package")
    h.update(assets_page.build_assets_page(ap, ui, project_root))

    # ---------------------------------------------------------------- status bar
    sb = vt.Row(spacing=8, padding=4, parent=root)
    sb.add(status)
    stats = _StatsLabel(width=260)
    sb.add(stats)
    h["status"] = status
    h["stats"] = stats
    h["menubar"] = menubar
    return h


class _StatsLabel(vt.Widget):
    """Shows the renderer stats of the previous frame (never forces extra frames)."""

    def preferred_size(self, ui):
        return (200, ui.theme.h)

    def paint(self, dl, ui):          # bypass the paint cache: always current
        s = ui.stats
        ui.text(dl, f"{s['instances']} quads \u2022 1 draw call \u2022 {s['build_ms']:.1f} ms build",
                self.x, self.y, self.w, self.h, ui.theme.text_dim, "right")


class IconGallery(vt.Widget):
    """Grid of every built-in icon; click one to copy its name."""

    hover_redraw = True

    def __init__(self, **kw):
        super().__init__(**kw)
        self.filter = ""
        self.scroll = 0.0
        self._hot = None

    def set_filter(self, text):
        self.filter = text.strip().lower()
        self.scroll = 0.0
        self.invalidate()

    def names(self):
        return [n for n in vt.icon_names() if self.filter in n and not n.startswith("vitrail-")]

    def preferred_size(self, ui):
        return (300, 200)

    def _cell(self, ui):
        return round(104 * ui.theme.scale), round(70 * ui.theme.scale)

    def draw(self, dl, ui):
        t = ui.theme
        cw, ch = self._cell(ui)
        cols = max(1, int(self.w // cw))
        dl.push_clip(self.x, self.y, self.w, self.h)
        for i, n in enumerate(self.names()):
            x = self.x + (i % cols) * cw
            y = self.y + (i // cols) * ch - self.scroll
            if y + ch < self.y or y > self.y + self.h:
                continue
            hot = i == self._hot
            dl.box(x + 3, y + 3, cw - 6, ch - 6, vt.with_alpha(t.accent, 0.18) if hot else t.panel,
                   border=t.accent if hot else t.outline, radius=t.radius * t.scale)
            ui.icon_centered(dl, n, x, y + 6, cw, ch - 28, 24, t.accent if hot else t.text)
            ui.text(dl, n, x + 4, y + ch - 26, cw - 8, 18, t.text_dim, "center", size=11)
        dl.pop_clip()

    def _index(self, ui, px, py):
        cw, ch = self._cell(ui)
        cols = max(1, int(self.w // cw))
        c, r = int((px - self.x) // cw), int((py - self.y + self.scroll) // ch)
        i = r * cols + c
        return i if 0 <= c < cols and 0 <= i < len(self.names()) else None

    def on_mouse_move(self, ui, ev):
        i = self._index(ui, ev.x, ev.y)
        if i != self._hot:
            self._hot = i
            self.invalidate()

    def on_wheel(self, ui, dx, dy):
        cw, ch = self._cell(ui)
        cols = max(1, int(self.w // cw))
        rows = (len(self.names()) + cols - 1) // cols
        self.scroll = max(0.0, min(rows * ch - self.h, self.scroll - dy * ch))
        self.invalidate()
        return True

    def on_mouse_down(self, ui, ev):
        i = self._index(ui, ev.x, ev.y)
        if i is not None:
            name = self.names()[i]
            ui.clipboard.put(name)
            from vitrail.material import Snackbar
            Snackbar.show(ui, f'Copied icon name "{name}"')
        return True


class AboutDialog(vt.Dialog):
    def __init__(self):
        super().__init__("About Vitrail", width=420)
        self.add(_LogoBanner())
        vt.Label(f"Vitrail {vt.__version__}", bold=True, size=16, parent=self, align="center")
        vt.Label("GPU UI toolkit for pygame + ModernGL", dim=True, parent=self, align="center")
        vt.Label("Apache License 2.0", dim=True, parent=self, align="center", icon="shield")
        self.add_buttons("Close", default="Close")


class _LogoBanner(vt.Widget):
    def preferred_size(self, ui):
        return (200, 112 * ui.theme.scale)

    def draw(self, dl, ui):
        from vitrail.logo import draw_logo
        sz = 96 * ui.theme.scale
        draw_logo(ui, dl, self.x + (self.w - sz) / 2, self.y + 8, 96)


def main():
    app = vt.App(1180, 760, "Vitrail — showcase", root="fill")
    h = build_showcase(app.root, app.ui)

    def on_event(e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_q and not app.ui.wants_keyboard:
            vt.PieMenu.open(app.ui, ["Left", "Right", "Bottom", "Top", "Front", "Back"],
                            lambda v: setattr(h["status"], "text", f"pie -> {v}"),
                            title="View", release_key=pygame.K_q)

    app.on_event.connect(on_event)
    app.run()


if __name__ == "__main__":
    main()
