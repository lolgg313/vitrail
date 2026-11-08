# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Vitrail on top of your own ModernGL scene.

A spinning triangle is drawn with a plain ModernGL program; a draggable
Vitrail panel floats over it and edits its parameters live.  Clicks that miss
the panel fall through to the game (see ``on_event``).
"""
import os
import sys
from array import array

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import moderngl  # noqa: E402
import pygame  # noqa: E402

import vitrail as vt  # noqa: E402

app = vt.App(1000, 650, "Vitrail over a ModernGL scene", continuous=True, root="canvas")
ctx = app.ctx

prog = ctx.program(
    vertex_shader="""
        #version 330
        uniform float u_angle; uniform float u_scale; uniform float u_aspect;
        in vec2 in_pos;
        void main() {
            float c = cos(u_angle), s = sin(u_angle);
            vec2 p = mat2(c, s, -s, c) * in_pos * u_scale;
            gl_Position = vec4(p.x / u_aspect, p.y, 0.0, 1.0);
        }""",
    fragment_shader="""
        #version 330
        uniform vec4 u_color; out vec4 f;
        void main() { f = u_color; }""",
)
vbo = ctx.buffer(array("f", [0.0, 0.8, -0.7, -0.45, 0.7, -0.45]).tobytes())
vao = ctx.vertex_array(prog, [(vbo, "2f", "in_pos")])

state = {"angle": 0.0, "clicks": 0}

panel = vt.Panel("Scene", padding=6, draggable=True, width=280)
with panel:
    speed = vt.NumberField("Speed", 1.0, soft_min=-5, soft_max=5, slider=True)
    scale = vt.NumberField("Scale", 0.6, min=0.05, max=1.5, slider=True)
    color = vt.ColorSwatch((0.95, 0.55, 0.2, 1.0), label="Color")
    paused = vt.Checkbox("Paused", False)
    info = vt.Label("Click the background", dim=True)
    vt.Button("Reset", lambda: (speed.reset(), scale.reset(), color.reset(), paused.reset()))
app.root.place(panel, 20, 20)

fps_label = vt.Label("", dim=True, width=140)
app.root.place(fps_label, 860, 620)


def on_frame(dt):
    if not paused.value:
        state["angle"] += dt * speed.value
    fps = 1.0 / dt if dt > 0 else 0.0
    fps_label.text = f"{fps:5.0f} fps  {app.ui.stats['instances']} quads"


def on_draw(ctx_):
    w, h = app.ui.size
    prog["u_angle"].value = state["angle"]
    prog["u_scale"].value = scale.value
    prog["u_aspect"].value = w / max(1, h)
    prog["u_color"].value = color.value
    ctx_.disable(moderngl.BLEND)
    vao.render(moderngl.TRIANGLES)


def on_event(e):  # only events the UI did not consume arrive here
    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        state["clicks"] += 1
        info.text = f"game got click #{state['clicks']} at {e.pos}"


app.on_frame.connect(on_frame)
app.on_draw.connect(on_draw)
app.on_event.connect(on_event)
app.run()
