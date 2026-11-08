# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Assets page for the showcase: project browser + inspector + drop targets."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import vitrail as vt  # noqa: E402
from vitrail.assets import (KINDS, AssetBrowser, MaterialEditor, MaterialSlot, draw_thumbnail,  # noqa: E402
                            human_size)
from vitrail.images import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def sample_project_path():
    path = os.path.join(HERE, "sample_project")
    if not os.path.isdir(path):
        import make_sample_project
        make_sample_project.main(path)
    return path


class _BigThumb(vt.Widget):
    """Large thumbnail of whatever asset is selected (prefabs, meshes, ...)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.asset = None

    def preferred_size(self, ui):
        return (160, 150 * ui.theme.scale)

    def draw(self, dl, ui):
        if self.asset is None:
            return
        d = min(self.w, self.h)
        if not draw_thumbnail(dl, ui, self.asset, self.x + (self.w - d) / 2, self.y, d):
            ui.request_repaint(self)


class Inspector(vt.Column):
    def __init__(self, browser, **kw):
        super().__init__(spacing=6, padding=10, **kw)
        self.browser = browser
        self.header = vt.Label("Nothing selected", bold=True, icon="info", parent=self)
        self.mat = MaterialEditor(parent=self)
        self.mat.changed.connect(lambda p: browser.grid.invalidate())
        self.mat.changed.connect(lambda p: [a.reload() for a in browser.grid.assets if a.path == p])
        self.image = Image(None, max_px=512, height=180, radius=6, parent=self)
        self.thumb = _BigThumb(parent=self)
        self.info = vt.Column(spacing=2, parent=self)
        browser.selection_changed.connect(self.show)
        self.show([])

    def show(self, assets):
        a = assets[0] if len(assets) == 1 else None
        for w in (self.mat, self.image, self.thumb):
            w.visible = False
        self.info.clear()
        if a is None:
            self.header.text = f"{len(assets)} assets selected" if assets else "Nothing selected"
            self.header.icon = "layers" if assets else "info"
            return
        icon, color, _ = KINDS.get(a.kind, KINDS["other"])
        self.header.text = a.name
        self.header.icon = icon
        if a.kind == "material":
            self.mat.load(a.path)
            self.mat.visible = True
        elif a.kind == "image":
            self.image.source = a.path
            self.image.visible = True
            self.image.invalidate(layout=True)
        else:
            self.thumb.asset = a
            self.thumb.visible = True
            self.thumb.invalidate()
        with self.info:
            vt.Label(f"Type: {a.kind.title()}", dim=True)
            if not a.is_dir:
                vt.Label(f"Size: {human_size(a.size)}", dim=True)
            vt.Label("Modified: " + time.strftime("%Y-%m-%d %H:%M", time.localtime(a.mtime)), dim=True)
            if a.kind == "prefab":
                vt.Label("Components", bold=True)
                for c in a.data.get("components", []):
                    vt.Label(c, icon="sliders", dim=True)
        self.invalidate(layout=True)


def build_assets_page(page, ui, root=None):
    """``page`` is a Row. Returns handles."""
    root = root or sample_project_path()
    left = vt.Column(spacing=0, padding=6, parent=page)
    browser = AssetBrowser(root, fill=True, parent=left)
    side = vt.Column(spacing=8, width=330, expand=0, parent=page)
    sc = vt.ScrollArea(vt.Column(spacing=8), fill=True, parent=side)
    with sc.content:
        inspector = Inspector(browser)
        vt.Separator()
        with vt.Column(spacing=6, padding=10):
            vt.Label("Scene  (drag prefabs & materials here)", bold=True, icon="scene")
            slot = MaterialSlot(label="Ground")
            scene = vt.TreeView([vt.TreeItem("Main Scene", [vt.TreeItem("Main Camera", icon="camera"),
                                                            vt.TreeItem("Sun", icon="sun")], expanded=True,
                                             icon="scene")], rows=7)
    scene.drop_filter = lambda p: isinstance(p, dict) and p.get("type") == "asset" and any(
        a.kind in ("prefab", "material", "mesh") for a in p["assets"])

    def dropped(payload, item, where):
        parent = scene.items[0] if item is None or where != "into" else item
        for a in payload["assets"]:
            if a.kind == "material" and item is not None:
                item.values = (a.stem,)
                item.text = item.text.split("  [")[0] + f"  [{a.stem}]"
            elif a.kind in ("prefab", "mesh"):
                icon, color, _ = KINDS[a.kind]
                new = vt.TreeItem(a.stem, icon=icon, icon_color=color)
                if where == "into" or item is None:
                    parent.add(new)
                    parent.expanded = True
                else:
                    idx = item.parent.children.index(item) + (1 if where == "after" else 0)
                    item.parent.add(new, idx)
        scene.refresh()
    scene.payload_dropped.connect(dropped)
    browser.activated.connect(lambda a: vt.material.Snackbar.show(ui, f"Opened {a.name}")
                              if hasattr(vt, "material") else None)
    return {"browser": browser, "inspector": inspector, "scene": scene, "slot": slot}
