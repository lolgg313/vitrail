# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Animation page for the showcase: stage + keyable properties + transport +
dope sheet + graph editor."""
import colorsys
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import vitrail as vt  # noqa: E402
from vitrail.animation import AnimationPlayer, Clip, CurveEditor, Timeline, TransportBar  # noqa: E402


class Stage(vt.Widget):
    """Tiny 2D viewport: a bouncing material ball with onion skin and motion path."""

    def __init__(self, player, props, **kw):
        super().__init__(**kw)
        self.player = player
        self.props = props
        player.add_view(self)

    def preferred_size(self, ui):
        return (360, 230)

    def _to_screen(self, x, y):
        s = self.w / 12.0
        return (self.x + self.w / 2 + x * s, self.y + self.h - 28 - y * s * 0.9)

    def _state(self, frame):
        p = self.props
        return tuple(p[n].anim_track.evaluate(frame) if p[n].anim_track.keys else p[n].value
                     for n in ("x", "y", "scale", "hue"))

    def draw(self, dl, ui):
        t = ui.theme
        s = t.scale
        dl.push_clip(self.x, self.y, self.w, self.h)
        dl.box(self.x, self.y, self.w, self.h, vt.shade(t.background, -0.1), border=t.outline, radius=t.radius * s)
        dl.grid(self.x, self.y, self.w, self.h, 24 * s, (self.x + self.w / 2, self.y + self.h - 28),
                vt.with_alpha(t.text, 0.03), vt.with_alpha(t.text, 0.07))
        gy = self.y + self.h - 28
        dl.box(self.x + 8, gy, self.w - 16, 2, vt.with_alpha(t.text, 0.25))
        c = self.player.clip
        # motion path
        for fr in range(int(c.start), int(c.end) + 1):
            px, py = self._to_screen(*self._state(fr)[:2])
            d = (3.0 if fr % 12 == 1 else 1.8) * s
            dl.box(px - d / 2, py - 18 * s - d / 2, d, d, vt.with_alpha(t.accent, 0.55 if fr % 12 == 1 else 0.35),
                   radius=d / 2)
        # onion skin
        f = self.player.frame
        for off, alpha in ((-8, 0.10), (-4, 0.18), (4, 0.18), (8, 0.10)):
            x, y, sc, hue = self._state(max(c.start, min(c.end, f + off)))
            r = 18 * sc * s
            sx, sy = self._to_screen(x, y)
            col = colorsys.hsv_to_rgb(hue % 1.0, 0.75, 0.95)
            dl.box(sx - r, sy - 2 * r, 2 * r, 2 * r, (col[0], col[1], col[2], alpha), radius=r)
        x, y, sc, hue = self._state(f)
        r = 18 * sc * s
        sx, sy = self._to_screen(x, y)
        sh = max(0.25, 1 - y / 6)
        dl.shadow(sx - r * sh, gy - 4 * s, 2 * r * sh, 8 * s, (0, 0, 0, 0.55 * sh), 4 * s, 6 * s)
        col = colorsys.hsv_to_rgb(hue % 1.0, 0.75, 0.95)
        dl.material_ball(sx - r, sy - 2 * r, 2 * r, (col[0], col[1], col[2], 1.0), 0.3, 0.0)
        ui.text(dl, f"frame {f:5.1f}", self.x + 10 * s, self.y + 6 * s, 140 * s, 18 * s, t.text_dim, size=11)
        dl.pop_clip()


def build_animation_page(page, ui):
    """``page`` is a Column. Returns handles."""
    clip = Clip("Bounce", start=1, end=96, fps=24)
    player = AnimationPlayer(clip)
    tx = clip.add_track("Position X", [(1, -4.0), (48, 4.0), (96, -4.0)])
    ty = clip.add_track("Position Y", [(1, 0.0), (12, 3.2), (24, 0.0), (36, 2.0), (48, 0.0), (60, 2.6),
                                       (72, 0.0), (84, 1.4), (96, 0.0)])
    ts = clip.add_track("Scale", [(1, 1.0), (24, 0.8), (48, 1.3), (72, 0.8), (96, 1.0)])
    th = clip.add_track("Hue", [(1, 0.02), (48, 0.55), (96, 1.02)])
    ty.keys[0].interp = "bezier"
    for k in ty.keys[::2]:
        k.interp = "bezier"

    top = vt.Row(spacing=10, padding=8, parent=page)
    props = {}
    side = vt.Column(spacing=4, width=300, expand=0)
    stage = Stage(player, props, height=230)
    top.add(stage)
    top.add(side)
    with side:
        vt.Label("Animated properties", bold=True, icon="film")
        props["x"] = vt.NumberField("Position X", 0.0, step=0.1, soft_min=-5, soft_max=5, slider=True)
        props["y"] = vt.NumberField("Position Y", 0.0, step=0.1, soft_min=0, soft_max=4, slider=True)
        props["scale"] = vt.NumberField("Scale", 1.0, min=0.1, max=3, step=0.05)
        props["hue"] = vt.NumberField("Hue", 0.0, step=0.01, soft_min=0, soft_max=1, slider=True)
        vt.Label("Hover a field + I: insert key  •  Alt+I: delete", dim=True, size=11)
        vt.Label("Yellow = on a key, green = animated", dim=True, size=11)
        with vt.Row(spacing=4):
            vt.Button("Key All", player.key_all, icon="diamond")
            vt.Button("Frame All", lambda: (timeline.frame_all(), curves.frame_all()), icon="fullscreen")
    for name, tr in (("x", tx), ("y", ty), ("scale", ts), ("hue", th)):
        player.bind(tr, props[name])
        props[name].changed.connect(lambda _v: stage.invalidate())

    transport = TransportBar(player, parent=page)
    tabs = vt.Tabs(style="underline", fill=True, parent=page)
    timeline = Timeline(player, fill=True)
    curves = CurveEditor(player, fill=True)
    ds = tabs.add_tab("Dope Sheet", vt.Column(spacing=0), icon="diamond")
    ds.add(timeline)
    ge = tabs.add_tab("Graph Editor", vt.Column(spacing=0), icon="chart-line")
    ge.add(curves)
    player.attach(ui)
    player.set_frame(1)
    return {"player": player, "clip": clip, "timeline": timeline, "curves": curves, "stage": stage,
            "props": props, "transport": transport, "anim_tabs": tabs}
