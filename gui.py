"""2026 Fluent-inspired desktop interface for the lexical analyzer."""

import csv
import re
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Iterable, Sequence

from languages import DISPLAY_LANGUAGES, LANGUAGES, detect_language
from lexer import AnalysisResult, Lexer


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def _mix(start: str, end: str, amount: float) -> str:
    first, second = _hex_to_rgb(start), _hex_to_rgb(end)
    values = [round(a + (b - a) * amount) for a, b in zip(first, second)]
    return "#" + "".join(f"{value:02x}" for value in values)


def rounded_rectangle(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    **kwargs,
) -> int:
    """Draw a smooth rounded polygon and return its canvas item id."""
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class IconFactory:
    """Creates scalable monochrome icons with Tk PhotoImage."""

    def __init__(self, master: tk.Misc, color: str, accent: str) -> None:
        self.master, self.color, self.accent = master, color, accent

    def create(self, name: str, size: int = 20) -> tk.PhotoImage:
        image = tk.PhotoImage(master=self.master, width=size, height=size)
        color = self.accent if name in {"analyze", "brand"} else self.color
        points: list[tuple[int, int]] = []

        if name in {"editor", "file"}:
            points += self._box(4, 2, 15, 17)
            points += [(7, y) for y in (7, 10, 13)]
            points += [(x, y) for y in (7, 10, 13) for x in range(9, 14)]
        elif name == "tokens":
            points += self._box(3, 4, 8, 9) + self._box(11, 4, 16, 9)
            points += self._box(3, 12, 8, 17) + self._box(11, 12, 16, 17)
        elif name == "symbols":
            points += [(4, y) for y in range(3, 18)]
            points += [(15, y) for y in range(3, 18)]
            points += [(x, y) for x in range(4, 16) for y in (7, 13)]
        elif name == "errors":
            points += [(10, 2), (3, 17), (17, 17)]
            points += [(x, 17) for x in range(3, 18)]
            points += [(10, y) for y in range(7, 13)] + [(10, 15)]
        elif name == "analytics":
            points += self._box(3, 11, 6, 17)
            points += self._box(8, 7, 11, 17)
            points += self._box(13, 3, 16, 17)
        elif name == "open":
            points += self._box(2, 7, 17, 16) + self._box(4, 4, 10, 8)
        elif name == "sample":
            points += self._box(3, 3, 16, 17)
            points += [(x, 7) for x in range(6, 14)]
            points += [(x, 11) for x in range(6, 14)]
        elif name == "analyze":
            for x in range(5, 15):
                half = max(0, 5 - abs(10 - x))
                points += [(x, y) for y in range(10 - half, 11 + half)]
        elif name == "clear":
            points += [(x, x) for x in range(5, 15)]
            points += [(x, 19 - x) for x in range(5, 15)]
        elif name == "export":
            points += [(10, y) for y in range(3, 13)]
            points += [(x, 9 + abs(10 - x)) for x in range(6, 15)]
            points += self._box(4, 14, 16, 18)
        elif name == "theme":
            points += self._circle(10, 10, 7)
            points = [(x, y) for x, y in points if x <= 10 or y >= 13]
        elif name == "search":
            points += self._circle(8, 8, 5)
            points += [(12 + i, 12 + i) for i in range(5)]
        elif name == "brand":
            points += [(4, 10), (7, 7), (7, 13), (16, 10), (13, 7), (13, 13)]
            points += [(11, y) for y in range(5, 16)]

        for x, y in set(points):
            if 0 <= x < size and 0 <= y < size:
                image.put(color, (x, y))
        return image

    @staticmethod
    def _box(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
        return (
            [(x, y1) for x in range(x1, x2 + 1)]
            + [(x, y2) for x in range(x1, x2 + 1)]
            + [(x1, y) for y in range(y1, y2 + 1)]
            + [(x2, y) for y in range(y1, y2 + 1)]
        )

    @staticmethod
    def _circle(cx: int, cy: int, radius: int) -> list[tuple[int, int]]:
        return [
            (x, y)
            for x in range(cx - radius, cx + radius + 1)
            for y in range(cy - radius, cy + radius + 1)
            if (radius - 1) ** 2 <= (x - cx) ** 2 + (y - cy) ** 2 <= radius**2 + radius
        ]


class FluentButton(tk.Canvas):
    """Rounded button with smooth hover color interpolation."""

    def __init__(
        self,
        master,
        text: str,
        command: Callable,
        font: tuple,
        icon: tk.PhotoImage | None = None,
        width: int = 132,
        height: int = 42,
        radius: int = 13,
        colors: dict | None = None,
        primary: bool = False,
        compact: bool = False,
    ) -> None:
        super().__init__(
            master, width=width, height=height, highlightthickness=0,
            borderwidth=0, cursor="hand2",
        )
        self.command, self.button_text, self.font = command, text, font
        self.icon, self.radius, self.primary = icon, radius, primary
        self.compact = compact
        self.palette = colors or {}
        self._hover = 0.0
        self._target = 0.0
        self.bind("<Enter>", lambda _event: self._animate_to(1.0))
        self.bind("<Leave>", lambda _event: self._animate_to(0.0))
        self.bind("<Button-1>", lambda _event: self.command())
        self.redraw()

    def set_palette(self, colors: dict) -> None:
        self.palette = colors
        self.configure(bg=colors["surface"])
        self.redraw()

    def set_icon(self, icon: tk.PhotoImage) -> None:
        self.icon = icon
        self.redraw()

    def _animate_to(self, target: float) -> None:
        self._target = target
        self._step()

    def _step(self) -> None:
        if abs(self._target - self._hover) < 0.03:
            self._hover = self._target
            self.redraw()
            return
        self._hover += (self._target - self._hover) * 0.28
        self.redraw()
        self.after(14, self._step)

    def redraw(self) -> None:
        if not self.palette:
            return
        self.delete("all")
        self.configure(bg=self.palette.get("surface", "#ffffff"))
        base = self.palette["accent"] if self.primary else self.palette["button"]
        hover = self.palette["accent_hover"] if self.primary else self.palette["button_hover"]
        fill = _mix(base, hover, self._hover)
        rounded_rectangle(
            self, 1, 1, int(self["width"]) - 1, int(self["height"]) - 1,
            self.radius, fill=fill, outline=self.palette["button_border"],
        )
        foreground = "#ffffff" if self.primary else self.palette["text"]
        width = int(self["width"])
        center = width / 2
        if self.icon:
            icon_x = center - (24 if not self.compact else 12)
            self.create_image(icon_x, int(self["height"]) / 2, image=self.icon)
            if self.button_text:
                self.create_text(
                    icon_x + 17, int(self["height"]) / 2,
                    text=self.button_text, anchor="w", fill=foreground,
                    font=self.font,
                )
        elif self.button_text:
            self.create_text(
                center, int(self["height"]) / 2, text=self.button_text,
                fill=foreground, font=self.font,
            )


class NavButton(tk.Canvas):
    """Sidebar navigation item with icon, active indicator, and animation."""

    def __init__(
        self,
        master,
        text: str,
        icon: tk.PhotoImage,
        command: Callable,
        font: tuple,
        palette: dict,
    ) -> None:
        super().__init__(
            master, width=206, height=48, highlightthickness=0,
            borderwidth=0, cursor="hand2", bg=palette["sidebar"],
        )
        self.label, self.icon, self.command = text, icon, command
        self.font, self.palette = font, palette
        self.active = False
        self.hover = 0.0
        self.target = 0.0
        self.bind("<Enter>", lambda _event: self.animate(1.0))
        self.bind("<Leave>", lambda _event: self.animate(0.0))
        self.bind("<Button-1>", lambda _event: command())
        self.redraw()

    def set_active(self, active: bool) -> None:
        self.active = active
        self.redraw()

    def set_palette(self, palette: dict, icon: tk.PhotoImage) -> None:
        self.palette, self.icon = palette, icon
        self.configure(bg=palette["sidebar"])
        self.redraw()

    def animate(self, target: float) -> None:
        self.target = target
        self._step()

    def _step(self) -> None:
        if abs(self.target - self.hover) < 0.03:
            self.hover = self.target
            self.redraw()
            return
        self.hover += (self.target - self.hover) * 0.3
        self.redraw()
        self.after(14, self._step)

    def redraw(self) -> None:
        self.delete("all")
        base = self.palette["nav_active"] if self.active else self.palette["sidebar"]
        hover = self.palette["nav_hover"]
        fill = base if self.active else _mix(base, hover, self.hover)
        rounded_rectangle(self, 4, 3, 202, 45, 13, fill=fill, outline="")
        if self.active:
            rounded_rectangle(
                self, 4, 13, 8, 35, 2, fill=self.palette["accent"], outline=""
            )
        self.create_image(29, 24, image=self.icon)
        self.create_text(
            51, 24, text=self.label, anchor="w",
            fill=self.palette["text"], font=self.font,
        )


class RoundedCard(tk.Canvas):
    """Rounded card with a soft layered shadow and embedded content frame."""

    def __init__(self, master, palette: dict, radius: int = 18, padding: int = 16):
        super().__init__(master, highlightthickness=0, borderwidth=0)
        self.palette, self.radius, self.padding = palette, radius, padding
        self.content = tk.Frame(self, bd=0, highlightthickness=0)
        self.window = self.create_window(
            padding, padding, anchor="nw", window=self.content
        )
        self.bind("<Configure>", self._redraw)

    def set_palette(self, palette: dict) -> None:
        self.palette = palette
        self._redraw()

    def _redraw(self, _event=None) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 2 or height <= 2:
            return
        self.delete("shape")
        self.configure(bg=self.palette["workspace"])
        rounded_rectangle(
            self, 7, 9, width - 3, height - 2, self.radius,
            fill=self.palette["shadow"], outline="", tags="shape",
        )
        rounded_rectangle(
            self, 2, 2, width - 8, height - 9, self.radius,
            fill=self.palette["surface"], outline=self.palette["card_border"],
            tags="shape",
        )
        self.tag_lower("shape")
        self.content.configure(bg=self.palette["surface"])
        self.coords(self.window, self.padding, self.padding)
        self.itemconfigure(
            self.window,
            width=max(1, width - self.padding * 2 - 8),
            height=max(1, height - self.padding * 2 - 10),
        )


class SampleDialog(tk.Toplevel):
    """Compact sample picker for every supported language."""

    FOLDERS = {
        "C": "c", "C++": "cpp", "Java": "java", "JavaScript": "javascript",
        "C#": "csharp", "Python": "Python",
    }

    def __init__(self, parent, palette: dict, font: str, on_load: Callable) -> None:
        super().__init__(parent)
        self.parent, self.palette, self.on_load = parent, palette, on_load
        self.title("Load sample")
        self.geometry("430x250")
        self.resizable(False, False)
        self.configure(bg=palette["workspace"])
        self.transient(parent)
        self.grab_set()

        card = RoundedCard(self, palette, radius=20, padding=22)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        content = card.content
        tk.Label(
            content, text="Load a language sample", bg=palette["surface"],
            fg=palette["text"], font=(font, 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            content, text="Choose a language and test type.",
            bg=palette["surface"], fg=palette["muted"], font=(font, 9),
        ).pack(anchor="w", pady=(3, 18))
        self.language = tk.StringVar(value="C")
        self.kind = tk.StringVar(value="valid")
        combo_style = ttk.Style(self)
        combo_style.configure("Sample.TCombobox", padding=7)
        ttk.Combobox(
            content, values=list(self.FOLDERS), textvariable=self.language,
            state="readonly", style="Sample.TCombobox",
        ).pack(fill="x", pady=(0, 10))
        ttk.Combobox(
            content, values=("valid", "invalid"), textvariable=self.kind,
            state="readonly", style="Sample.TCombobox",
        ).pack(fill="x")
        button = tk.Button(
            content, text="Load sample", command=self._load, relief="flat",
            bd=0, bg=palette["accent"], fg="#ffffff",
            activebackground=palette["accent_hover"], activeforeground="#ffffff",
            font=(font, 10, "bold"), cursor="hand2", padx=16, pady=8,
        )
        button.pack(anchor="e", pady=(18, 0))

    def _load(self) -> None:
        folder = self.FOLDERS[self.language.get()]
        profile = LANGUAGES[self.language.get()]
        extension = profile.extensions[0]
        path = (
            Path(__file__).parent / "examples" / folder
            / f"{self.kind.get()}{extension}"
        )
        self.on_load(path, self.language.get())
        self.destroy()


class LexicalAnalyzerGUI(tk.Tk):
    """Modern multi-language compiler workbench."""

    LIGHT = {
        "workspace": "#f3f6fb", "sidebar": "#edf2f9", "surface": "#ffffff",
        "glass": "#f8fbff", "surface_alt": "#f6f8fc", "text": "#152033",
        "muted": "#6b778c", "accent": "#6366f1", "accent_hover": "#4f46e5",
        "button": "#ffffff", "button_hover": "#eef2ff",
        "button_border": "#dce4f0", "card_border": "#e4eaf3",
        "shadow": "#dbe2ed", "nav_hover": "#e4eaf5", "nav_active": "#dfe5ff",
        "input": "#fbfcfe", "selection": "#dfe5ff", "error": "#ef476f",
        "success": "#22a06b", "warning": "#f59e0b",
        "chart": ["#6366f1", "#8b5cf6", "#06b6d4", "#f59e0b", "#22a06b"],
    }
    DARK = {
        "workspace": "#0b1020", "sidebar": "#10172a", "surface": "#151d31",
        "glass": "#182238", "surface_alt": "#1a2439", "text": "#f3f6fc",
        "muted": "#98a6bd", "accent": "#818cf8", "accent_hover": "#a5b4fc",
        "button": "#1c2840", "button_hover": "#273655",
        "button_border": "#2c3b57", "card_border": "#25334d",
        "shadow": "#070b14", "nav_hover": "#1a263e", "nav_active": "#29345d",
        "input": "#10182a", "selection": "#344374", "error": "#fb7185",
        "success": "#4ade80", "warning": "#fbbf24",
        "chart": ["#818cf8", "#a78bfa", "#22d3ee", "#fbbf24", "#4ade80"],
    }

    PAGE_INFO = {
        "editor": ("Source Editor", "Write, open, or load a sample program"),
        "tokens": ("Token Stream", "Explore recognized lexemes and token classes"),
        "symbols": ("Symbol Table", "Review inferred declarations and scopes"),
        "errors": ("Diagnostics", "Inspect lexical errors and recovery details"),
        "analytics": ("Analysis Dashboard", "Visualize token distribution and scan quality"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("NexaLex Compiler Studio")
        self.geometry("1280x820")
        self.minsize(1080, 700)
        families = set(tkfont.families(self))
        self.ui_font = "Inter" if "Inter" in families else "Segoe UI"
        self.mono_font = "Cascadia Code" if "Cascadia Code" in families else "Consolas"

        self.lexer = Lexer()
        self.result: AnalysisResult | None = None
        self.current_file: Path | None = None
        self.dark_mode = tk.BooleanVar(value=False)
        self.language_var = tk.StringVar(value="Auto Detect")
        self.detected_language = tk.StringVar(value="Language: Auto")
        self.file_text = tk.StringVar(value="Untitled source")
        self.status_text = tk.StringVar(value="Ready to analyze")
        self.search_text = tk.StringVar()
        self.line_count_text = tk.StringVar(value="1 line")
        self.stats_vars = {
            name: tk.StringVar(value="0")
            for name in (
                "Total Tokens", "Keywords", "Identifiers",
                "Numbers", "Operators", "Errors",
            )
        }
        self.palette = self.LIGHT
        self.icons: dict[str, tk.PhotoImage] = {}
        self.nav_buttons: dict[str, NavButton] = {}
        self.action_buttons: list[tuple[FluentButton, str]] = []
        self.cards: list[RoundedCard] = []
        self.pages: dict[str, tk.Frame] = {}
        self.active_page = "editor"

        self._configure_ttk()
        self._build_shell()
        self._bind_shortcuts()
        self._configure_highlighting()
        self._apply_theme()
        self.show_page("editor")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_shell(self) -> None:
        self.configure(bg=self.palette["workspace"])
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self.workspace = tk.Frame(self, bg=self.palette["workspace"])
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(1, weight=1)
        self._build_header()
        self.page_host = tk.Frame(self.workspace, bg=self.palette["workspace"])
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 14))
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)
        self._build_pages()
        self._build_status()

    def _build_sidebar(self) -> None:
        self.sidebar = tk.Frame(self, width=236, bg=self.palette["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        brand = tk.Frame(self.sidebar, bg=self.palette["sidebar"])
        brand.pack(fill="x", padx=20, pady=(24, 28))
        self.brand_icon = tk.Label(brand, bg=self.palette["sidebar"])
        self.brand_icon.pack(side="left")
        self.brand_title = tk.Label(
            brand, text="NexaLex", bg=self.palette["sidebar"],
            fg=self.palette["text"], font=(self.ui_font, 16, "bold"),
        )
        self.brand_title.pack(side="left", padx=(10, 0))
        self.brand_badge = tk.Label(
            brand, text="STUDIO", bg=self.palette["nav_active"],
            fg=self.palette["accent"], font=(self.ui_font, 7, "bold"),
            padx=6, pady=3,
        )
        self.brand_badge.pack(side="left", padx=(7, 0))

        nav = tk.Frame(self.sidebar, bg=self.palette["sidebar"])
        nav.pack(fill="x", padx=15)
        self.nav_holder = nav
        for page, label, icon in (
            ("editor", "Source Editor", "editor"),
            ("tokens", "Token Stream", "tokens"),
            ("symbols", "Symbol Table", "symbols"),
            ("errors", "Diagnostics", "errors"),
            ("analytics", "Analytics", "analytics"),
        ):
            button = NavButton(
                nav, label, tk.PhotoImage(width=1, height=1),
                lambda selected=page: self.show_page(selected),
                (self.ui_font, 10, "bold"), self.palette,
            )
            button.pack(fill="x", pady=3)
            self.nav_buttons[page] = button

        sidebar_bottom = tk.Frame(self.sidebar, bg=self.palette["sidebar"])
        sidebar_bottom.pack(side="bottom", fill="x", padx=18, pady=18)
        self.export_tokens_button = self._action_button(
            sidebar_bottom, "Export tokens", self.export_tokens, "export",
            width=196, height=39,
        )
        self.export_tokens_button.pack(pady=4)
        self.export_symbols_button = self._action_button(
            sidebar_bottom, "Export symbols", self.export_symbols, "export",
            width=196, height=39,
        )
        self.export_symbols_button.pack(pady=4)
        self.theme_button = self._action_button(
            sidebar_bottom, "Dark mode", self.toggle_theme, "theme",
            width=196, height=39,
        )
        self.theme_button.pack(pady=(12, 0))

    def _build_header(self) -> None:
        self.header = tk.Canvas(
            self.workspace, height=116, highlightthickness=0,
            bd=0, bg=self.palette["workspace"],
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        self.header.bind("<Configure>", self._draw_header)
        self.header_content = tk.Frame(self.header, bg=self.palette["glass"])
        self.header_window = self.header.create_window(
            24, 18, anchor="nw", window=self.header_content
        )
        self.header_content.grid_columnconfigure(0, weight=1)
        title_box = tk.Frame(self.header_content, bg=self.palette["glass"])
        title_box.grid(row=0, column=0, rowspan=2, sticky="w")
        self.page_title = tk.Label(
            title_box, text="", bg=self.palette["glass"], fg=self.palette["text"],
            font=(self.ui_font, 20, "bold"),
        )
        self.page_title.pack(anchor="w")
        self.page_subtitle = tk.Label(
            title_box, text="", bg=self.palette["glass"], fg=self.palette["muted"],
            font=(self.ui_font, 9),
        )
        self.page_subtitle.pack(anchor="w", pady=(3, 0))

        controls = tk.Frame(self.header_content, bg=self.palette["glass"])
        controls.grid(row=0, column=1, rowspan=2, sticky="e")
        self.language_combo = ttk.Combobox(
            controls, textvariable=self.language_var,
            values=DISPLAY_LANGUAGES, state="readonly", width=14,
            style="Modern.TCombobox",
        )
        self.language_combo.pack(side="left", ipady=5, padx=(0, 8))
        self.language_combo.bind("<<ComboboxSelected>>", self._on_language_selected)
        self.analyze_button = self._action_button(
            controls, "Analyze", self.analyze_source, "analyze",
            width=116, height=40, primary=True,
        )
        self.analyze_button.pack(side="left", padx=(4, 0))

    def _draw_header(self, _event=None) -> None:
        width, height = self.header.winfo_width(), self.header.winfo_height()
        if width < 20:
            return
        self.header.delete("glass")
        rounded_rectangle(
            self.header, 7, 9, width - 2, height - 2, 20,
            fill=self.palette["shadow"], outline="", tags="glass",
        )
        rounded_rectangle(
            self.header, 2, 2, width - 8, height - 9, 20,
            fill=self.palette["glass"], outline=self.palette["card_border"],
            tags="glass",
        )
        self.header.tag_lower("glass")
        self.header_content.configure(bg=self.palette["glass"])
        self.header.coords(self.header_window, 24, 19)
        self.header.itemconfigure(
            self.header_window, width=max(1, width - 52), height=72
        )

    def _build_pages(self) -> None:
        for name in self.PAGE_INFO:
            page = tk.Frame(self.page_host, bg=self.palette["workspace"])
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page
        self._build_editor_page(self.pages["editor"])
        self._build_tokens_page(self.pages["tokens"])
        self._build_symbols_page(self.pages["symbols"])
        self._build_errors_page(self.pages["errors"])
        self._build_analytics_page(self.pages["analytics"])

    def _new_card(self, parent, row=0, column=0, **grid) -> RoundedCard:
        card = RoundedCard(parent, self.palette)
        card.grid(row=row, column=column, sticky="nsew", **grid)
        self.cards.append(card)
        return card

    def _build_editor_page(self, page: tk.Frame) -> None:
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        card = self._new_card(page)
        content = card.content
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        top = tk.Frame(content, bg=self.palette["surface"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top.grid_columnconfigure(0, weight=1)
        self.editor_label = tk.Label(
            top, text="Source workspace", bg=self.palette["surface"],
            fg=self.palette["text"], font=(self.ui_font, 12, "bold"),
        )
        self.editor_label.grid(row=0, column=0, sticky="w")
        self.file_badge = tk.Label(
            top, textvariable=self.file_text, bg=self.palette["surface_alt"],
            fg=self.palette["muted"], font=(self.ui_font, 8, "bold"),
            padx=10, pady=5,
        )
        self.file_badge.grid(row=0, column=1, padx=(8, 4))
        self.detected_label = tk.Label(
            top, textvariable=self.detected_language, bg=self.palette["surface_alt"],
            fg=self.palette["accent"], font=(self.ui_font, 8, "bold"),
            padx=10, pady=5,
        )
        self.detected_label.grid(row=0, column=2, padx=4)
        self.line_label = tk.Label(
            top, textvariable=self.line_count_text, bg=self.palette["surface"],
            fg=self.palette["muted"], font=(self.ui_font, 9),
        )
        self.line_label.grid(row=0, column=3, sticky="e")
        self.open_button = self._action_button(
            top, "Open", self.open_file, "open", width=88, height=34
        )
        self.open_button.grid(row=0, column=4, padx=(10, 3))
        self.sample_button = self._action_button(
            top, "Sample", self.load_sample, "sample", width=98, height=34
        )
        self.sample_button.grid(row=0, column=5, padx=3)
        self.clear_button = self._action_button(
            top, "", self.clear_all, "clear", width=40, height=34, compact=True
        )
        self.clear_button.grid(row=0, column=6, padx=(3, 0))

        editor_shell = tk.Frame(
            content, bg=self.palette["input"], highlightthickness=1,
            highlightbackground=self.palette["card_border"],
        )
        editor_shell.grid(row=1, column=0, sticky="nsew")
        editor_shell.grid_columnconfigure(1, weight=1)
        editor_shell.grid_rowconfigure(0, weight=1)
        self.line_numbers = tk.Text(
            editor_shell, width=5, padx=9, pady=13, takefocus=0, border=0,
            state="disabled", wrap="none", font=(self.mono_font, 11),
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        self.source_text = tk.Text(
            editor_shell, undo=True, wrap="none", borderwidth=0, padx=15, pady=13,
            insertwidth=2, font=(self.mono_font, 11),
        )
        self.source_text.grid(row=0, column=1, sticky="nsew")
        y_scroll = ttk.Scrollbar(
            editor_shell, orient="vertical", command=self._scroll_source
        )
        x_scroll = ttk.Scrollbar(
            editor_shell, orient="horizontal", command=self.source_text.xview
        )
        y_scroll.grid(row=0, column=2, sticky="ns")
        x_scroll.grid(row=1, column=1, sticky="ew")
        self.source_text.configure(
            yscrollcommand=lambda *args: self._sync_scroll(y_scroll, *args),
            xscrollcommand=x_scroll.set,
        )
        self.source_text.bind("<KeyRelease>", self._on_source_changed)
        self._update_line_numbers()

    def _build_tokens_page(self, page: tk.Frame) -> None:
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        card = self._new_card(page)
        content = card.content
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        search = tk.Frame(content, bg=self.palette["surface"])
        search.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        search.grid_columnconfigure(1, weight=1)
        self.search_icon_label = tk.Label(search, bg=self.palette["surface"])
        self.search_icon_label.grid(row=0, column=0, padx=(0, 8))
        self.search_entry = tk.Entry(
            search, textvariable=self.search_text, bd=0,
            font=(self.ui_font, 10), relief="flat",
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", ipady=9)
        self.search_text.trace_add("write", lambda *_: self._filter_tokens())
        self.token_tree = self._create_tree(
            content, ("type", "lexeme", "line"),
            ("TOKEN TYPE", "LEXEME", "LINE"), (180, 600, 90), row=1,
        )

    def _build_symbols_page(self, page: tk.Frame) -> None:
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        card = self._new_card(page)
        content = card.content
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        self.symbol_tree = self._create_tree(
            content, ("name", "type", "scope", "line"),
            ("IDENTIFIER", "DATA TYPE", "SCOPE", "LINE"),
            (260, 180, 360, 80),
        )

    def _build_errors_page(self, page: tk.Frame) -> None:
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        card = self._new_card(page)
        content = card.content
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        self.error_tree = self._create_tree(
            content, ("type", "line", "description"),
            ("ERROR TYPE", "LINE", "DESCRIPTION"), (220, 80, 650),
        )

    def _build_analytics_page(self, page: tk.Frame) -> None:
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        self.stats_frame = tk.Frame(page, bg=self.palette["workspace"])
        self.stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for index, (name, variable) in enumerate(self.stats_vars.items()):
            self.stats_frame.grid_columnconfigure(index, weight=1)
            card = RoundedCard(self.stats_frame, self.palette, radius=17, padding=14)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 6, 6))
            card.configure(width=130, height=108)
            self.cards.append(card)
            label = tk.Label(
                card.content, text=name.upper(), bg=self.palette["surface"],
                fg=self.palette["muted"], font=(self.ui_font, 7, "bold"),
            )
            label.pack(anchor="w")
            value = tk.Label(
                card.content, textvariable=variable, bg=self.palette["surface"],
                fg=self.palette["accent"], font=(self.ui_font, 22, "bold"),
            )
            value.pack(anchor="w", pady=(5, 0))
            setattr(self, f"stat_label_{index}", label)
            setattr(self, f"stat_value_{index}", value)

        charts = tk.Frame(page, bg=self.palette["workspace"])
        charts.grid(row=1, column=0, sticky="nsew")
        charts.grid_columnconfigure(0, weight=3)
        charts.grid_columnconfigure(1, weight=2)
        charts.grid_rowconfigure(0, weight=1)
        bar_card = self._new_card(charts, 0, 0, padx=(0, 7))
        quality_card = self._new_card(charts, 0, 1, padx=(7, 0))
        for card, title in (
            (bar_card, "Token distribution"),
            (quality_card, "Scan quality"),
        ):
            card.content.grid_columnconfigure(0, weight=1)
            card.content.grid_rowconfigure(1, weight=1)
            label = tk.Label(
                card.content, text=title, bg=self.palette["surface"],
                fg=self.palette["text"], font=(self.ui_font, 12, "bold"),
            )
            label.grid(row=0, column=0, sticky="w", pady=(0, 8))
            setattr(self, f"{'bar' if card is bar_card else 'quality'}_title", label)
        self.bar_chart = tk.Canvas(bar_card.content, highlightthickness=0)
        self.bar_chart.grid(row=1, column=0, sticky="nsew")
        self.quality_chart = tk.Canvas(quality_card.content, highlightthickness=0)
        self.quality_chart.grid(row=1, column=0, sticky="nsew")
        self.bar_chart.bind("<Configure>", lambda _event: self._draw_charts())
        self.quality_chart.bind("<Configure>", lambda _event: self._draw_charts())

    def _build_status(self) -> None:
        self.status = tk.Frame(self.workspace, height=34, bg=self.palette["workspace"])
        self.status.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 12))
        self.status.grid_columnconfigure(1, weight=1)
        self.status_dot = tk.Label(
            self.status, text="●", bg=self.palette["workspace"],
            fg=self.palette["success"], font=(self.ui_font, 8),
        )
        self.status_dot.grid(row=0, column=0)
        self.status_label = tk.Label(
            self.status, textvariable=self.status_text, bg=self.palette["workspace"],
            fg=self.palette["muted"], font=(self.ui_font, 8),
        )
        self.status_label.grid(row=0, column=1, sticky="w", padx=(7, 0))
        self.shortcut_label = tk.Label(
            self.status, text="Ctrl+O Open  ·  F5 Analyze  ·  Ctrl+L Clear",
            bg=self.palette["workspace"], fg=self.palette["muted"],
            font=(self.ui_font, 8),
        )
        self.shortcut_label.grid(row=0, column=2)

    def _action_button(
        self, parent, text: str, command: Callable, icon_name: str,
        width=120, height=40, primary=False, compact=False,
    ) -> FluentButton:
        button = FluentButton(
            parent, text, command, (self.ui_font, 9, "bold"),
            width=width, height=height, colors=self.palette,
            primary=primary, compact=compact,
        )
        self.action_buttons.append((button, icon_name))
        return button

    def _create_tree(
        self, parent, columns: Sequence[str], headings: Sequence[str],
        widths: Sequence[int], row=0,
    ) -> ttk.Treeview:
        shell = tk.Frame(parent, bg=self.palette["card_border"])
        shell.grid(row=row, column=0, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(0, weight=1)
        tree = ttk.Treeview(
            shell, columns=columns, show="headings", selectmode="browse",
            style="Modern.Treeview",
        )
        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, minwidth=70, anchor="w")
        scroll = ttk.Scrollbar(shell, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        scroll.grid(row=0, column=1, sticky="ns", pady=1)
        return tree

    def show_page(self, page: str) -> None:
        self.active_page = page
        self.pages[page].tkraise()
        for name, button in self.nav_buttons.items():
            button.set_active(name == page)
        title, subtitle = self.PAGE_INFO[page]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        if page == "analytics":
            self.after(30, self._draw_charts)

    def open_file(self, _event=None) -> None:
        path = filedialog.askopenfilename(
            title="Open source file",
            filetypes=[
                ("Supported source", "*.c *.h *.cpp *.cc *.cxx *.hpp *.java *.js *.jsx *.mjs *.cs *.py *.pyw *.txt"),
                ("C", "*.c *.h"), ("C++", "*.cpp *.cc *.cxx *.hpp"),
                ("Java", "*.java"), ("JavaScript", "*.js *.jsx *.mjs"),
                ("C#", "*.cs"), ("Python", "*.py *.pyw"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._load_path(Path(path))

    def load_sample(self) -> None:
        SampleDialog(self, self.palette, self.ui_font, self._load_path)

    def _load_path(self, path: Path, language: str | None = None) -> None:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Open File", f"Could not open file:\n{error}")
            return
        self.current_file = path
        detected = language or detect_language(path, content)
        self.language_var.set(detected)
        self.detected_language.set(f"Language: {detected}")
        self.source_text.delete("1.0", "end")
        self.source_text.insert("1.0", content)
        self.file_text.set(path.name)
        self._on_source_changed()
        self.show_page("editor")
        self.status_text.set(f"Loaded {path.name} as {detected}")

    def _on_language_selected(self, _event=None) -> None:
        selected = self.language_var.get()
        if selected == "Auto Detect":
            detected = detect_language(
                self.current_file,
                self.source_text.get("1.0", "end-1c"),
            )
            self.detected_language.set(f"Auto: {detected}")
        else:
            self.detected_language.set(f"Language: {selected}")
        self._highlight_source()

    def analyze_source(self, _event=None) -> None:
        source = self.source_text.get("1.0", "end-1c")
        if not source.strip():
            messagebox.showinfo("Analyze", "Enter, open, or load source code first.")
            return
        self.result = self.lexer.analyze(
            source,
            language=self.language_var.get(),
            file_path=self.current_file,
        )
        self.detected_language.set(f"Language: {self.result.language}")
        self._populate_results()
        errors = len(self.result.errors)
        self.status_text.set(
            f"{self.result.language} analysis complete · "
            f"{len(self.result.tokens)} tokens · {len(self.result.symbols)} symbols · "
            f"{errors} errors"
        )
        self.show_page("errors" if errors else "tokens")

    def clear_all(self, _event=None) -> None:
        self.source_text.delete("1.0", "end")
        self.result = None
        self.current_file = None
        self.file_text.set("Untitled source")
        self.detected_language.set("Language: Auto")
        self.language_var.set("Auto Detect")
        self.search_text.set("")
        for tree in (self.token_tree, self.symbol_tree, self.error_tree):
            tree.delete(*tree.get_children())
        for value in self.stats_vars.values():
            value.set("0")
        self._on_source_changed()
        self._draw_charts()
        self.status_text.set("Workspace cleared")
        self.show_page("editor")

    def export_tokens(self) -> None:
        if not self.result:
            messagebox.showinfo("Export", "Analyze source code before exporting.")
            return
        self._export_csv(
            "token_stream.csv", ("Token Type", "Lexeme", "Line Number"),
            ((token.token_type, token.lexeme, token.line) for token in self.result.tokens),
        )

    def export_symbols(self) -> None:
        if not self.result:
            messagebox.showinfo("Export", "Analyze source code before exporting.")
            return
        self._export_csv(
            "symbol_table.csv",
            ("Identifier Name", "Data Type", "Scope", "Line Number"),
            ((symbol.name, symbol.data_type, symbol.scope, symbol.line) for symbol in self.result.symbols),
        )

    def _export_csv(
        self, default_name: str, headers: Sequence[str], rows: Iterable
    ) -> None:
        path = filedialog.asksaveasfilename(
            title="Export CSV", defaultextension=".csv", initialfile=default_name,
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerows(rows)
        except OSError as error:
            messagebox.showerror("Export", f"Could not export file:\n{error}")
            return
        self.status_text.set(f"Exported {Path(path).name}")

    def _populate_results(self) -> None:
        if not self.result:
            return
        self._filter_tokens()
        for tree in (self.symbol_tree, self.error_tree):
            tree.delete(*tree.get_children())
        for index, symbol in enumerate(self.result.symbols):
            self.symbol_tree.insert(
                "", "end", values=(
                    symbol.name, symbol.data_type, symbol.scope, symbol.line
                ), tags=("even" if index % 2 == 0 else "odd",),
            )
        for index, error in enumerate(self.result.errors):
            self.error_tree.insert(
                "", "end", values=(
                    error.error_type, error.line, error.description
                ), tags=("even" if index % 2 == 0 else "odd",),
            )
        for name, value in self.result.statistics.items():
            self.stats_vars[name].set(str(value))
        self._draw_charts()

    def _filter_tokens(self) -> None:
        self.token_tree.delete(*self.token_tree.get_children())
        if not self.result:
            return
        query = self.search_text.get().strip().lower()
        visible = 0
        for token in self.result.tokens:
            if (
                query and query not in token.token_type.lower()
                and query not in token.lexeme.lower()
            ):
                continue
            self.token_tree.insert(
                "", "end", values=(token.token_type, token.lexeme, token.line),
                tags=("even" if visible % 2 == 0 else "odd",),
            )
            visible += 1

    def _on_source_changed(self, _event=None) -> None:
        self._update_line_numbers()
        self._highlight_source()
        if self.language_var.get() == "Auto Detect":
            detected = detect_language(
                self.current_file, self.source_text.get("1.0", "end-1c")
            )
            self.detected_language.set(f"Auto: {detected}")

    def _configure_highlighting(self) -> None:
        for tag, color in (
            ("keyword", "#8b5cf6"), ("string", "#16a34a"),
            ("comment", "#64748b"), ("number", "#ea580c"),
            ("operator", "#0284c7"),
        ):
            self.source_text.tag_configure(tag, foreground=color)

    def _highlight_source(self) -> None:
        text = self.source_text.get("1.0", "end-1c")
        for tag in ("keyword", "string", "comment", "number", "operator"):
            self.source_text.tag_remove(tag, "1.0", "end")
        selected = self.language_var.get()
        language = (
            detect_language(self.current_file, text)
            if selected == "Auto Detect" else selected
        )
        profile = LANGUAGES.get(language, LANGUAGES["C"])
        comment_parts = [re.escape(marker) + r"[^\n]*" for marker in profile.line_comments]
        comment_parts += [
            re.escape(start) + r"[\s\S]*?(?:" + re.escape(end) + r"|$)"
            for start, end in profile.block_comments
        ]
        patterns = []
        if comment_parts:
            patterns.append(("comment", "|".join(comment_parts)))
        patterns += [
            ("string", r'"""[\s\S]*?(?:"""|$)|\'\'\'[\s\S]*?(?:\'\'\'|$)|`(?:\\.|[^`])*`|"(?:\\.|[^"\\\n])*"?|\'(?:\\.|[^\'\\\n])*\'?'),
            ("keyword", r"\b(?:" + "|".join(sorted(map(re.escape, profile.keywords), key=len, reverse=True)) + r")\b"),
            ("number", r"\b(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b"),
            ("operator", "|".join(sorted(map(re.escape, profile.operators), key=len, reverse=True))),
        ]
        for tag, pattern in patterns:
            if not pattern:
                continue
            for match in re.finditer(pattern, text):
                self.source_text.tag_add(
                    tag, f"1.0+{match.start()}c", f"1.0+{match.end()}c"
                )

    def _update_line_numbers(self) -> None:
        line_count = int(self.source_text.index("end-1c").split(".")[0])
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert(
            "1.0", "\n".join(str(number) for number in range(1, line_count + 1))
        )
        self.line_numbers.configure(state="disabled")
        self.line_count_text.set(f"{line_count} line{'s' if line_count != 1 else ''}")

    def _scroll_source(self, *args) -> None:
        self.source_text.yview(*args)
        self.line_numbers.yview(*args)

    def _sync_scroll(self, scrollbar: ttk.Scrollbar, first, last) -> None:
        scrollbar.set(first, last)
        self.line_numbers.yview_moveto(first)

    def _draw_charts(self) -> None:
        if not hasattr(self, "bar_chart"):
            return
        stats = self.result.statistics if self.result else {
            "Keywords": 0, "Identifiers": 0, "Numbers": 0,
            "Operators": 0, "Errors": 0, "Total Tokens": 0,
        }
        self._draw_bar_chart(stats)
        self._draw_quality_chart(stats)

    def _draw_bar_chart(self, stats: dict) -> None:
        canvas = self.bar_chart
        canvas.delete("all")
        canvas.configure(bg=self.palette["surface"])
        width, height = max(canvas.winfo_width(), 420), max(canvas.winfo_height(), 260)
        data = [
            ("Keywords", stats["Keywords"]), ("Identifiers", stats["Identifiers"]),
            ("Numbers", stats["Numbers"]), ("Operators", stats["Operators"]),
        ]
        maximum = max([value for _, value in data] + [1])
        left, right, top = 105, width - 48, 28
        gap = max(48, (height - 55) // len(data))
        for index, (label, value) in enumerate(data):
            y = top + index * gap
            canvas.create_text(
                8, y + 8, text=label, anchor="w", fill=self.palette["muted"],
                font=(self.ui_font, 9),
            )
            rounded_rectangle(
                canvas, left, y, right, y + 16, 8,
                fill=self.palette["surface_alt"], outline="",
            )
            bar_width = max(0, (right - left) * value / maximum)
            if bar_width:
                rounded_rectangle(
                    canvas, left, y, left + bar_width, y + 16, 8,
                    fill=self.palette["chart"][index], outline="",
                )
            canvas.create_text(
                right, y + 29, text=str(value), anchor="e",
                fill=self.palette["text"], font=(self.ui_font, 9, "bold"),
            )

    def _draw_quality_chart(self, stats: dict) -> None:
        canvas = self.quality_chart
        canvas.delete("all")
        canvas.configure(bg=self.palette["surface"])
        width, height = max(canvas.winfo_width(), 300), max(canvas.winfo_height(), 260)
        total, errors = stats["Total Tokens"], stats["Errors"]
        clean = max(total - errors, 0)
        denominator = max(clean + errors, 1)
        quality = 100 if total and not errors else round(clean / denominator * 100)
        size = min(width - 100, height - 85, 180)
        x1, y1 = (width - size) / 2, 20
        x2, y2 = x1 + size, y1 + size
        canvas.create_arc(
            x1, y1, x2, y2, start=90, extent=-359.9,
            style="arc", width=17, outline=self.palette["surface_alt"],
        )
        extent = -359.9 * quality / 100
        canvas.create_arc(
            x1, y1, x2, y2, start=90, extent=extent,
            style="arc", width=17, outline=self.palette["success"],
        )
        canvas.create_text(
            width / 2, y1 + size / 2 - 7, text=f"{quality}%",
            fill=self.palette["text"], font=(self.ui_font, 22, "bold"),
        )
        canvas.create_text(
            width / 2, y1 + size / 2 + 20, text="clean scan",
            fill=self.palette["muted"], font=(self.ui_font, 8),
        )
        canvas.create_text(
            width / 2, min(y2 + 30, height - 20),
            text=f"{clean} valid tokens  ·  {errors} diagnostics",
            fill=self.palette["muted"], font=(self.ui_font, 8),
        )

    def toggle_theme(self) -> None:
        self.dark_mode.set(not self.dark_mode.get())
        self._apply_theme()

    def _configure_ttk(self) -> None:
        self.style = ttk.Style(self)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

    def _apply_theme(self) -> None:
        self.palette = self.DARK if self.dark_mode.get() else self.LIGHT
        self.configure(bg=self.palette["workspace"])
        factory = IconFactory(self, self.palette["muted"], self.palette["accent"])
        names = {
            "editor", "tokens", "symbols", "errors", "analytics", "open",
            "sample", "analyze", "clear", "export", "theme", "search", "brand",
        }
        self.icons = {name: factory.create(name) for name in names}
        app_icon = tk.PhotoImage(master=self, width=32, height=32)
        app_icon.put(self.palette["accent"], to=(2, 2, 30, 30))
        app_icon.put("#ffffff", to=(7, 14, 12, 19))
        app_icon.put("#ffffff", to=(20, 14, 25, 19))
        self._app_icon = app_icon
        self.iconphoto(True, app_icon)

        self.sidebar.configure(bg=self.palette["sidebar"])
        self.brand_icon.configure(image=self.icons["brand"], bg=self.palette["sidebar"])
        self.brand_title.configure(bg=self.palette["sidebar"], fg=self.palette["text"])
        self.brand_badge.configure(
            bg=self.palette["nav_active"], fg=self.palette["accent"]
        )
        for child in self.sidebar.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=self.palette["sidebar"])
        for page, button in self.nav_buttons.items():
            button.set_palette(self.palette, self.icons[page])
        for button, icon_name in self.action_buttons:
            button.set_palette(self.palette)
            button.set_icon(self.icons[icon_name])

        self.workspace.configure(bg=self.palette["workspace"])
        self.page_host.configure(bg=self.palette["workspace"])
        for page in self.pages.values():
            page.configure(bg=self.palette["workspace"])
        self.header.configure(bg=self.palette["workspace"])
        for widget in (self.header_content,):
            widget.configure(bg=self.palette["glass"])
        for widget in self.header_content.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=self.palette["glass"])
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label) and child is not self.file_badge:
                        child.configure(bg=self.palette["glass"])
        self.page_title.configure(bg=self.palette["glass"], fg=self.palette["text"])
        self.page_subtitle.configure(bg=self.palette["glass"], fg=self.palette["muted"])
        self.file_badge.configure(bg=self.palette["surface_alt"], fg=self.palette["muted"])
        self._draw_header()

        for card in self.cards:
            card.set_palette(self.palette)
        self.editor_label.configure(bg=self.palette["surface"], fg=self.palette["text"])
        self.detected_label.configure(
            bg=self.palette["surface_alt"], fg=self.palette["accent"]
        )
        self.line_label.configure(bg=self.palette["surface"], fg=self.palette["muted"])
        self.source_text.configure(
            bg=self.palette["input"], fg=self.palette["text"],
            insertbackground=self.palette["text"],
            selectbackground=self.palette["selection"],
        )
        self.line_numbers.configure(
            bg=self.palette["surface_alt"], fg=self.palette["muted"],
            selectbackground=self.palette["surface_alt"],
        )
        self.search_icon_label.configure(
            image=self.icons["search"], bg=self.palette["surface"]
        )
        self.search_entry.configure(
            bg=self.palette["input"], fg=self.palette["text"],
            insertbackground=self.palette["text"],
            highlightthickness=1,
            highlightbackground=self.palette["card_border"],
            highlightcolor=self.palette["accent"],
        )
        for index in range(6):
            getattr(self, f"stat_label_{index}").configure(
                bg=self.palette["surface"], fg=self.palette["muted"]
            )
            getattr(self, f"stat_value_{index}").configure(
                bg=self.palette["surface"], fg=self.palette["accent"]
            )
        self.bar_title.configure(bg=self.palette["surface"], fg=self.palette["text"])
        self.quality_title.configure(bg=self.palette["surface"], fg=self.palette["text"])
        self.stats_frame.configure(bg=self.palette["workspace"])

        self.status.configure(bg=self.palette["workspace"])
        self.status_dot.configure(
            bg=self.palette["workspace"], fg=self.palette["success"]
        )
        self.status_label.configure(
            bg=self.palette["workspace"], fg=self.palette["muted"]
        )
        self.shortcut_label.configure(
            bg=self.palette["workspace"], fg=self.palette["muted"]
        )

        self.style.configure(
            "Modern.TCombobox", fieldbackground=self.palette["input"],
            background=self.palette["surface"], foreground=self.palette["text"],
            arrowcolor=self.palette["muted"], bordercolor=self.palette["card_border"],
            lightcolor=self.palette["card_border"], darkcolor=self.palette["card_border"],
            padding=7, font=(self.ui_font, 9),
        )
        self.style.map(
            "Modern.TCombobox",
            fieldbackground=[("readonly", self.palette["input"])],
            foreground=[("readonly", self.palette["text"])],
        )
        self.style.configure(
            "Modern.Treeview", background=self.palette["input"],
            fieldbackground=self.palette["input"], foreground=self.palette["text"],
            rowheight=34, borderwidth=0, font=(self.ui_font, 9),
        )
        self.style.configure(
            "Modern.Treeview.Heading", background=self.palette["surface_alt"],
            foreground=self.palette["muted"], borderwidth=0,
            font=(self.ui_font, 8, "bold"), padding=(8, 10),
        )
        self.style.map(
            "Modern.Treeview",
            background=[("selected", self.palette["selection"])],
            foreground=[("selected", self.palette["text"])],
        )
        for tree in (self.token_tree, self.symbol_tree, self.error_tree):
            tree.tag_configure("even", background=self.palette["input"])
            tree.tag_configure("odd", background=self.palette["surface_alt"])
        self._draw_charts()

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-o>", self.open_file)
        self.bind_all("<F5>", self.analyze_source)
        self.bind_all("<Control-l>", self.clear_all)
