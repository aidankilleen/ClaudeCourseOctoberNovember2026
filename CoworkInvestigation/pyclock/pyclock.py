"""Analog clock with themes, resizing and a frameless/transparent mode (tkinter only).

Keys / mouse
  1-4            choose a theme
  F              cycle window mode: Normal -> Frameless round -> Frameless see-through
  Right-click    menu (themes, window mode, quit)
  Frameless:     drag to move, mouse wheel or +/- to resize, Esc to quit
"""
import json
import math
import re
import time
import tkinter as tk
from pathlib import Path

SIZE = 400  # default window size
MIN_W, MIN_H = 220, 260
SETTINGS_FILE = Path(__file__).with_name("pyclock_settings.json")
TRANSPARENT_KEY = "#ff00fe"  # colour that becomes see-through (must not be used by a theme)

MODES = ["Normal", "Frameless round", "Frameless see-through"]

THEMES = {
    "Midnight": dict(
        bg="#1e1e2e", rim="#585b70", major="#cdd6f4", minor="#6c7086", numbers="#cdd6f4",
        hour="#cdd6f4", minute="#89b4fa", second="#f38ba8", hub="#f38ba8", digital="#a6adc8",
        font="Helvetica", ui_bg="#181825", ui_fg="#cdd6f4", ui_active="#313244",
    ),
    "Classic": dict(
        bg="#fdfaf3", rim="#222222", major="#222222", minor="#888888", numbers="#222222",
        hour="#111111", minute="#111111", second="#c0392b", hub="#c0392b", digital="#555555",
        font="Times", ui_bg="#ece7da", ui_fg="#222222", ui_active="#d8d2c2",
    ),
    "Ocean": dict(
        bg="#0b3c5d", rim="#1d8fb5", major="#e0f7ff", minor="#5fb4d1", numbers="#e0f7ff",
        hour="#ffffff", minute="#7fe0ff", second="#ffb347", hub="#ffb347", digital="#9fd8ea",
        font="Helvetica", ui_bg="#082d47", ui_fg="#e0f7ff", ui_active="#14587f",
    ),
    "Retro": dict(
        bg="#000000", rim="#00aa33", major="#33ff66", minor="#007722", numbers="#33ff66",
        hour="#33ff66", minute="#33ff66", second="#ffee00", hub="#ffee00", digital="#00cc44",
        font="Courier", ui_bg="#0a0a0a", ui_fg="#33ff66", ui_active="#0f3d1a",
    ),
}


def load_settings():
    """Return saved settings as a dict (empty if missing or invalid)."""
    try:
        data = json.loads(SETTINGS_FILE.read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    try:
        w, h = int(data["width"]), int(data["height"])
        if w >= MIN_W and h >= MIN_H:
            out["width"], out["height"] = w, h
    except (KeyError, TypeError, ValueError):
        pass
    try:
        out["x"], out["y"] = int(data["x"]), int(data["y"])
    except (KeyError, TypeError, ValueError):
        pass
    if data.get("mode") in range(len(MODES)):
        out["mode"] = data["mode"]
    return out


class AnalogClock:
    def __init__(self, root, theme="Midnight"):
        self.root = root
        root.title("PyClock")
        root.minsize(MIN_W, MIN_H)
        self.cx = self.cy = SIZE / 2
        self.radius = SIZE / 2 - 20
        self.name = theme
        self.mode = 0
        self.can_be_transparent = True  # set False if the platform refuses
        self.drag = (0, 0)

        self.bar = tk.Frame(root)
        self.canvas = tk.Canvas(root, width=SIZE, height=SIZE, highlightthickness=0)
        self.bar.pack(side="bottom", fill="x")
        self.canvas.pack(side="top", fill="both", expand=True)

        self.buttons = {}
        self.theme_var = tk.StringVar(value=theme)
        self.mode_var = tk.IntVar(value=0)
        for i, name in enumerate(THEMES, start=1):
            b = tk.Button(self.bar, text=f"{i}  {name}", relief="flat", bd=0, padx=8, pady=6,
                          command=lambda n=name: self.set_theme(n))
            b.pack(side="left", expand=True, fill="x")
            self.buttons[name] = b
            root.bind(str(i), lambda e, n=name: self.set_theme(n))

        self.build_menu()
        root.bind("f", lambda e: self.set_mode((self.mode + 1) % len(MODES)))
        root.bind("F", lambda e: self.set_mode((self.mode + 1) % len(MODES)))
        root.bind("<Escape>", lambda e: self.on_close() if self.mode else None)
        root.bind("<plus>", lambda e: self.resize_by(30))
        root.bind("<equal>", lambda e: self.resize_by(30))
        root.bind("<minus>", lambda e: self.resize_by(-30))
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        c = self.canvas
        c.bind("<Configure>", self.on_resize)
        c.bind("<ButtonPress-1>", self.drag_start)
        c.bind("<B1-Motion>", self.drag_move)
        c.bind("<MouseWheel>", lambda e: self.resize_by(30 if e.delta > 0 else -30))
        c.bind("<Button-4>", lambda e: self.resize_by(30))   # Linux scroll up
        c.bind("<Button-5>", lambda e: self.resize_by(-30))  # Linux scroll down
        c.bind("<ButtonRelease-3>", self.show_menu)
        c.bind("<Button-2>", self.show_menu)  # macOS secondary click

        settings = load_settings()
        self.apply_geometry(settings)
        self.set_theme(theme)
        self.set_mode(settings.get("mode", 0))
        self.tick()

    # ---------- window geometry, settings ----------
    def apply_geometry(self, s):
        r = self.root
        w = min(s.get("width", SIZE), r.winfo_screenwidth())
        h = min(s.get("height", SIZE + 40), r.winfo_screenheight())
        geo = f"{w}x{h}"
        if "x" in s:
            x = max(-w + 80, min(s["x"], r.winfo_screenwidth() - 80))
            y = max(0, min(s["y"], r.winfo_screenheight() - 80))
            geo += f"+{x}+{y}"
        r.geometry(geo)

    def on_close(self):
        """Save size, position and window mode, then quit."""
        self.root.update_idletasks()
        m = re.match(r"(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)", self.root.geometry())
        data = {"mode": self.mode}
        if m:
            data.update(width=int(m[1]), height=int(m[2]), x=int(m[3]), y=int(m[4]))
        try:
            SETTINGS_FILE.write_text(json.dumps(data))
        except OSError:
            pass  # e.g. read-only folder; just skip saving
        self.root.destroy()

    # ---------- window mode (normal / frameless) ----------
    def set_mode(self, mode):
        self.mode = mode
        self.mode_var.set(mode)
        root = self.root
        frameless = mode != 0
        # Toggling the frame works most reliably while the window is hidden.
        root.withdraw()
        root.overrideredirect(frameless)
        if self.can_be_transparent:
            try:
                root.attributes("-transparentcolor", TRANSPARENT_KEY if frameless else "")
            except tk.TclError:  # only Windows supports this
                self.can_be_transparent = False
        if frameless:
            self.bar.pack_forget()
        else:
            self.bar.pack(side="bottom", fill="x", before=self.canvas)
        root.deiconify()
        root.focus_force()
        self.redraw()

    def drag_start(self, e):
        self.drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def drag_move(self, e):
        if self.mode:
            self.root.geometry(f"+{e.x_root - self.drag[0]}+{e.y_root - self.drag[1]}")

    def resize_by(self, step):
        if not self.mode:
            return
        n = max(120, min(max(self.root.winfo_width(), self.root.winfo_height()) + step,
                         self.root.winfo_screenheight()))
        self.root.geometry(f"{n}x{n}")

    # ---------- menu ----------
    def build_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        for i, name in enumerate(THEMES, start=1):
            self.menu.add_radiobutton(label=f"{i}  {name}", variable=self.theme_var, value=name,
                                      command=lambda n=name: self.set_theme(n))
        self.menu.add_separator()
        for i, label in enumerate(MODES):
            self.menu.add_radiobutton(label=label, variable=self.mode_var, value=i,
                                      command=lambda i=i: self.set_mode(i))
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=self.on_close)

    def show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    # ---------- drawing ----------
    def point(self, angle_deg, length):
        """Convert a clock angle (0 = 12 o'clock, clockwise) to canvas x, y."""
        a = math.radians(angle_deg - 90)
        return self.cx + length * math.cos(a), self.cy + length * math.sin(a)

    def on_resize(self, event):
        self.cx, self.cy = event.width / 2, event.height / 2
        self.radius = max(40, min(event.width, event.height) / 2 - 20)
        self.redraw()

    def set_theme(self, name):
        self.name = name
        self.theme_var.set(name)
        t = THEMES[name]
        self.bar.configure(bg=t["ui_bg"])
        for n, b in self.buttons.items():
            b.configure(bg=t["ui_active"] if n == name else t["ui_bg"], fg=t["ui_fg"],
                        activebackground=t["ui_active"], activeforeground=t["ui_fg"])
        self.redraw()

    def redraw(self):
        """Rebuild the whole clock for the current theme, size and window mode."""
        t = self.t = THEMES[self.name]
        c, r, cx, cy = self.canvas, self.radius, self.cx, self.cy
        k = r / 180  # scale factor relative to the original 400px design
        c.delete("all")

        see_through = self.mode != 0 and self.can_be_transparent
        c.configure(bg=TRANSPARENT_KEY if see_through else t["bg"])
        face_fill = "" if (self.mode == 2 and see_through) else t["bg"]

        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=t["rim"], fill=face_fill,
                      width=max(2, 4 * k))
        for i in range(60):
            major = i % 5 == 0
            x1, y1 = self.point(i * 6, r - (16 if major else 8) * k)
            x2, y2 = self.point(i * 6, r - 2 * k)
            c.create_line(x1, y1, x2, y2, width=max(1, (3 if major else 1) * k),
                          fill=t["major"] if major else t["minor"])
        for h in range(1, 13):
            x, y = self.point(h * 30, r - 34 * k)
            c.create_text(x, y, text=str(h), fill=t["numbers"],
                          font=(t["font"], -max(8, int(18 * k)), "bold"))

        self.hour = c.create_line(cx, cy, cx, cy, width=max(3, 8 * k), fill=t["hour"], capstyle="round")
        self.minute = c.create_line(cx, cy, cx, cy, width=max(2, 5 * k), fill=t["minute"], capstyle="round")
        self.second = c.create_line(cx, cy, cx, cy, width=max(1, 2 * k), fill=t["second"], capstyle="round")
        hub = max(3, 7 * k)
        c.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill=t["hub"], outline="")
        self.digital = c.create_text(cx, cy + r * 0.55, fill=t["digital"],
                                     font=(t["font"], -max(8, int(14 * k))))
        self.update_hands()

    def update_hands(self):
        now = time.localtime()
        s = now.tm_sec
        m = now.tm_min + s / 60
        h = (now.tm_hour % 12) + m / 60
        for item, angle, length in (
            (self.hour, h * 30, self.radius * 0.5),
            (self.minute, m * 6, self.radius * 0.75),
            (self.second, s * 6, self.radius * 0.85),
        ):
            x, y = self.point(angle, length)
            self.canvas.coords(item, self.cx, self.cy, x, y)
        self.canvas.itemconfig(self.digital, text=time.strftime("%H:%M:%S", now))

    def tick(self):
        self.update_hands()
        self.root.after(200, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    AnalogClock(root)
    root.mainloop()
