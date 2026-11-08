# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""A small library of evaluable nodes used by the demos."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import vitrail as vt  # noqa: E402
from vitrail.nodes import Node  # noqa: E402


def _num(v):
    return float(v) if isinstance(v, (int, float)) else 0.0


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def register_all(ed):
    ed.register("Input/Value", lambda: Node("Value", category="input", icon="sliders",
                                            inputs=[("Value", "float", 1.0)], outputs=[("Out", "float")],
                                            compute=lambda i: {"Out": _num(i["Value"])}))
    ed.register("Input/Integer", lambda: Node("Integer", category="input",
                                              inputs=[("Value", "int", 3)], outputs=[("Out", "int")],
                                              compute=lambda i: {"Out": int(i["Value"] or 0)}))
    ed.register("Input/Color", lambda: Node("Color", category="color", icon="palette",
                                            inputs=[("Color", "color", (0.9, 0.4, 0.2, 1.0))], outputs=[("Out", "color")],
                                            compute=lambda i: {"Out": i["Color"]}))
    ed.register("Input/Text", lambda: Node("Text", category="input", icon="text",
                                           inputs=[("Text", "string", "hello")], outputs=[("Out", "string")],
                                           compute=lambda i: {"Out": str(i["Text"])}))
    for name, fn in (("Add", lambda a, b: a + b), ("Subtract", lambda a, b: a - b),
                     ("Multiply", lambda a, b: a * b), ("Divide", lambda a, b: a / b if b else 0.0),
                     ("Power", lambda a, b: math.copysign(abs(a) ** b, a) if a or b > 0 else 0.0),
                     ("Minimum", min), ("Maximum", max)):
        ed.register(f"Math/{name}", lambda name=name, fn=fn: Node(
            name, category="math", inputs=[("A", "float", 0.5), ("B", "float", 2.0)], outputs=[("Result", "float")],
            compute=lambda i, fn=fn: {"Result": fn(_num(i["A"]), _num(i["B"]))}))
    for name, fn in (("Sine", math.sin), ("Cosine", math.cos), ("Absolute", abs), ("Square Root", lambda v: math.sqrt(abs(v)))):
        ed.register(f"Math/Functions/{name}", lambda name=name, fn=fn: Node(
            name, category="math", inputs=[("Value", "float", 0.0)], outputs=[("Result", "float")],
            compute=lambda i, fn=fn: {"Result": fn(_num(i["Value"]))}))
    ed.register("Math/Clamp", lambda: Node("Clamp", category="math",
                                           inputs=[("Value", "float", 0.5), ("Min", "float", 0.0), ("Max", "float", 1.0)],
                                           outputs=[("Result", "float")],
                                           compute=lambda i: {"Result": max(_num(i["Min"]), min(_num(i["Max"]), _num(i["Value"])))}))
    ed.register("Vector/Combine XYZ", lambda: Node("Combine XYZ", category="vector", icon="move",
                                                   inputs=[("X", "float", 0.0), ("Y", "float", 0.0), ("Z", "float", 0.0)],
                                                   outputs=[("Vector", "vector")],
                                                   compute=lambda i: {"Vector": (_num(i["X"]), _num(i["Y"]), _num(i["Z"]))}))
    ed.register("Vector/Length", lambda: Node("Length", category="vector", inputs=[("Vector", "vector")],
                                              outputs=[("Length", "float")],
                                              compute=lambda i: {"Length": math.sqrt(sum(c * c for c in (i["Vector"] or (0, 0, 0))[:3]))}))
    ed.register("Color/Mix", lambda: Node("Mix Color", category="color", icon="palette",
                                          inputs=[("Factor", "float", 0.5), ("A", "color", (0.1, 0.4, 0.9, 1.0)),
                                                  ("B", "color", (0.95, 0.8, 0.2, 1.0))],
                                          outputs=[("Color", "color")],
                                          compute=lambda i: {"Color": _lerp(i["A"], i["B"], max(0.0, min(1.0, _num(i["Factor"]))))}))
    ed.register("Logic/Compare", lambda: Node("Greater Than", category="logic",
                                              inputs=[("A", "float", 1.0), ("B", "float", 0.0)], outputs=[("Result", "bool")],
                                              compute=lambda i: {"Result": _num(i["A"]) > _num(i["B"])}))
    ed.register("Events/On Start", lambda: Node("On Start", category="event", icon="play",
                                                outputs=[("Then", "exec")]))
    ed.register("Events/Print", lambda: Node("Print", category="event", icon="terminal",
                                             inputs=[("In", "exec"), ("Message", "any", 0.0)], outputs=[("Then", "exec")]))
    ed.register("Output/Viewer", make_viewer)


def make_viewer():
    n = Node("Viewer", category="output", icon="eye", inputs=[("Value", "any")], width=190)
    lbl = vt.Label("-", dim=True, parent=n)
    swatch = vt.ColorSwatch((0, 0, 0, 1), parent=n)
    swatch.visible = False

    def compute(i):
        v = i["Value"]
        if isinstance(v, tuple) and len(v) == 4:
            swatch.value = v
            swatch.visible = True
            lbl.text = vt.to_hex(v)
        else:
            swatch.visible = False
            if isinstance(v, float):
                lbl.text = f"= {v:.4f}"
            elif isinstance(v, tuple):
                lbl.text = "= (" + ", ".join(f"{c:.2f}" for c in v) + ")"
            else:
                lbl.text = f"= {v}"
        return {}
    n.compute = compute
    return n


def build_sample_graph(ed):
    register_all(ed)
    a = ed.add_node(ed.create("Input/Value"), (0, 0))
    b = ed.add_node(ed.create("Math/Functions/Sine"), (220, 10))
    c = ed.add_node(ed.create("Math/Multiply"), (420, 40))
    v = ed.add_node(ed.create("Output/Viewer"), (640, 60))
    col = ed.add_node(ed.create("Color/Mix"), (220, 190))
    v2 = ed.add_node(ed.create("Output/Viewer"), (460, 230))
    ev = ed.add_node(ed.create("Events/On Start"), (0, 330))
    pr = ed.add_node(ed.create("Events/Print"), (220, 360))
    ed.connect(a.socket("Out"), b.socket("Value"), undo=False)
    ed.connect(b.socket("Result"), c.socket("A"), undo=False)
    ed.connect(c.socket("Result"), v.socket("Value"), undo=False)
    ed.connect(a.socket("Out"), col.socket("Factor"), undo=False)
    ed.connect(col.socket("Color"), v2.socket("Value"), undo=False)
    ed.connect(ev.socket("Then"), pr.socket("In"), undo=False)
    ed.connect(c.socket("Result"), pr.socket("Message"), undo=False)
    viewers = [v, v2]

    def recompute():
        for n in ed.nodes:
            if n.title == "Viewer":
                ed.evaluate(n)
    ed.graph_changed.connect(recompute)
    recompute()
    return viewers
