# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Hamid Reza Jahanshahi (S.U.P.E)
"""Headless test harness: EGL ModernGL context + offscreen framebuffer +
synthetic pygame events.  Used by the tests and for screenshots."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import moderngl  # noqa: E402
import pygame  # noqa: E402

import vitrail as vt  # noqa: E402


class Harness:
    def __init__(self, w=980, h=680, theme=None):
        pygame.init()
        try:
            self.ctx = moderngl.create_standalone_context(backend="egl")
        except Exception:
            self.ctx = moderngl.create_standalone_context()
        self.size = (w, h)
        self.fbo = self.ctx.simple_framebuffer((w, h))
        self.ui = vt.UI(self.ctx, (w, h), theme or vt.Theme())
        self.root = vt.Column(padding=8, spacing=6)
        self.scroll = vt.ScrollArea(self.root)
        self.ui.set_root(self.scroll)
        self.mouse = (0, 0)

    def frame(self):
        self.fbo.use()
        c = self.ui.theme.background
        self.fbo.clear(c[0], c[1], c[2], 1.0)
        self.ui.update()
        self.ui.draw()

    def screenshot(self, path):
        self.frame()
        data = self.fbo.read(components=3)
        img = pygame.image.frombytes(data, self.size, "RGB", True)
        pygame.image.save(img, path)
        return path

    # -- synthetic input -----------------------------------------------------------------
    def move(self, x, y, mod=0, steps=1):
        x0, y0 = self.mouse
        for i in range(1, steps + 1):
            nx = round(x0 + (x - x0) * i / steps)
            ny = round(y0 + (y - y0) * i / steps)
            px, py = self.mouse
            self.ui.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(nx, ny), rel=(nx - px, ny - py),
                                                    buttons=(0, 0, 0), mod=mod))
            self.mouse = (nx, ny)

    def down(self, button=1, mod=0):
        return self.ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=self.mouse, button=button, mod=mod))

    def up(self, button=1, mod=0):
        return self.ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=self.mouse, button=button, mod=mod))

    def click(self, x, y, button=1, mod=0):
        self.move(x, y)
        self.down(button, mod)
        self.up(button, mod)

    def wheel(self, dy, mod=0):
        return self.ui.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=dy, mod=mod))

    def key(self, key, mod=0, unicode=""):
        self.ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode=unicode))
        self.ui.handle_event(pygame.event.Event(pygame.KEYUP, key=key, mod=mod))

    def type(self, text):
        for ch in text:
            self.ui.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=ch))

    @staticmethod
    def center(w):
        return (int(w.x + w.w / 2), int(w.y + w.h / 2))
