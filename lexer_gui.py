

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import json
import os
import sys
import platform
import threading
import time

# ── Colour palette (dark, terminal-inspired) ──────────────────────────────
BG         = "#0d1117"
BG_PANEL   = "#161b22"
BG_HEADER  = "#21262d"
BG_ROW_A   = "#161b22"
BG_ROW_B   = "#1c2128"
ACCENT     = "#58a6ff"
ACCENT2    = "#3fb950"
ACCENT3    = "#f78166"
ACCENT4    = "#d2a8ff"
ACCENT5    = "#ffa657"
FG         = "#e6edf3"
FG_DIM     = "#8b949e"
FG_DARK    = "#484f58"
BORDER     = "#30363d"

# Token-type colour map
TOKEN_COLORS = {
    "KEYWORD":        "#ff7b72",
    "IDENTIFIER":     "#79c0ff",
    "INTEGER_LITERAL":"#79c0ff",
    "FLOAT_LITERAL":  "#79c0ff",
    "STRING_LITERAL": "#a5d6ff",
    "CHAR_LITERAL":   "#a5d6ff",
    "OPERATOR":       "#ffa657",
    "PUNCTUATION":    "#e6edf3",
    "PREPROCESSOR":   "#d2a8ff",
    "COMMENT":        "#8b949e",
    "UNKNOWN":        "#f85149",
}

CATEGORY_COLORS = {
    "function":      "#79c0ff",
    "variable":      "#3fb950",
    "type":          "#d2a8ff",
    "namespace":     "#ffa657",
    "template/type": "#d2a8ff",
    "unknown":       "#8b949e",
}

FONT_MONO  = ("Consolas", 11) if platform.system() == "Windows" else ("Menlo", 11)
FONT_MONO_S = (FONT_MONO[0], 10)
FONT_BOLD  = (FONT_MONO[0], 12, "bold")
FONT_TITLE = (FONT_MONO[0], 16, "bold")
FONT_SMALL = (FONT_MONO[0], 9)

# ══════════════════════════════════════════════════════════════════════════
#  Utility — locate the compiled backend next to this script
# ══════════════════════════════════════════════════════════════════════════
def find_backend():
    here   = os.path.dirname(os.path.abspath(__file__))
    names  = ["lexer_backend", "lexer_backend.exe"]
    for nm in names:
        p = os.path.join(here, nm)
        if os.path.isfile(p):
            return p
    return None

# ══════════════════════════════════════════════════════════════════════════
#  Main Application Window
# ══════════════════════════════════════════════════════════════════════════
class LexerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("C++ Lexical Analyzer")
        self.configure(bg=BG)
        self.geometry("1280x820")
        self.minsize(900, 600)

        # State
        self._cpp_path   = tk.StringVar()
        self._status_var = tk.StringVar(value="Ready — open a .cpp file to begin.")
        self._tokens_data  = []
        self._symbols_data = []
        self._filter_var   = tk.StringVar()
        self._filter_var.trace_add("write", self._on_filter)
        self._sym_filter   = tk.StringVar()
        self._sym_filter.trace_add("write", self._on_sym_filter)
        self._sort_col     = None
        self._sort_rev     = False

        self._build_ui()
        self._style_ttk()

    # ── TTK style ──────────────────────────────────────────────────────
    def _style_ttk(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        # Notebook
        s.configure("TNotebook",
                     background=BG, borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab",
                     background=BG_HEADER, foreground=FG_DIM,
                     font=FONT_MONO, padding=(18, 8),
                     borderwidth=0, focuscolor=BG)
        s.map("TNotebook.Tab",
              background=[("selected", BG_PANEL)],
              foreground=[("selected", FG)])

        # Treeview (token table)
        s.configure("Tokens.Treeview",
                     background=BG_ROW_A, foreground=FG,
                     fieldbackground=BG_ROW_A,
                     rowheight=26, font=FONT_MONO_S,
                     borderwidth=0)
        s.configure("Tokens.Treeview.Heading",
                     background=BG_HEADER, foreground=ACCENT,
                     font=(FONT_MONO[0], 10, "bold"),
                     relief="flat", borderwidth=0)
        s.map("Tokens.Treeview",
              background=[("selected", "#1f6feb")],
              foreground=[("selected", "#ffffff")])

        # Treeview (symbol table)
        s.configure("Sym.Treeview",
                     background=BG_ROW_A, foreground=FG,
                     fieldbackground=BG_ROW_A,
                     rowheight=26, font=FONT_MONO_S,
                     borderwidth=0)
        s.configure("Sym.Treeview.Heading",
                     background=BG_HEADER, foreground=ACCENT2,
                     font=(FONT_MONO[0], 10, "bold"),
                     relief="flat", borderwidth=0)
        s.map("Sym.Treeview",
              background=[("selected", "#1f6feb")],
              foreground=[("selected", "#ffffff")])

        # Scrollbar
        s.configure("Dark.Vertical.TScrollbar",
                     background=BG_HEADER, troughcolor=BG,
                     arrowcolor=FG_DIM, borderwidth=0, relief="flat")
        s.configure("Dark.Horizontal.TScrollbar",
                     background=BG_HEADER, troughcolor=BG,
                     arrowcolor=FG_DIM, borderwidth=0, relief="flat")

        # Progressbar
        s.configure("Blue.Horizontal.TProgressbar",
                     troughcolor=BG_HEADER, background=ACCENT,
                     borderwidth=0, thickness=3)

    # ── Build UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Top bar ─────────────────────────────────────────────────
        top = tk.Frame(self, bg=BG_HEADER, height=64)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tk.Label(top, text="⟨/⟩", font=(FONT_MONO[0], 22, "bold"),
                 bg=BG_HEADER, fg=ACCENT).pack(side="left", padx=(20, 6), pady=12)
        tk.Label(top, text="C++ Lexical Analyzer",
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG).pack(side="left", pady=12)
        tk.Label(top, text="powered by C++ backend",
                 font=FONT_SMALL, bg=BG_HEADER, fg=FG_DIM).pack(side="left", padx=(10, 0), pady=18)

        # Compile button (top-right)
        self._btn_compile = tk.Button(
            top, text="⚙  Compile Backend",
            font=FONT_MONO_S, bg=BG_PANEL, fg=ACCENT4,
            activebackground=BG_HEADER, activeforeground=ACCENT4,
            relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
            command=self._compile_backend)
        self._btn_compile.pack(side="right", padx=(6, 20), pady=14)

        # ── File picker bar ─────────────────────────────────────────
        bar = tk.Frame(self, bg=BG_PANEL, height=52)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        tk.Label(bar, text="Source file:", font=FONT_MONO_S,
                 bg=BG_PANEL, fg=FG_DIM).pack(side="left", padx=(20, 6), pady=12)

        self._path_entry = tk.Entry(bar, textvariable=self._cpp_path,
                                    font=FONT_MONO_S, bg=BG_HEADER, fg=FG,
                                    insertbackground=FG, relief="flat",
                                    highlightthickness=1,
                                    highlightbackground=BORDER,
                                    highlightcolor=ACCENT)
        self._path_entry.pack(side="left", fill="x", expand=True,
                               padx=(0, 8), pady=12, ipady=4)

        self._btn_browse = tk.Button(
            bar, text="Browse…",
            font=FONT_MONO_S, bg=BG_HEADER, fg=FG_DIM,
            activebackground=BG_PANEL, activeforeground=FG,
            relief="flat", bd=0, padx=14, pady=5, cursor="hand2",
            command=self._browse)
        self._btn_browse.pack(side="left", pady=12, padx=(0, 8))

        self._btn_analyze = tk.Button(
            bar, text="▶  Analyze",
            font=(FONT_MONO[0], 11, "bold"), bg=ACCENT, fg="#0d1117",
            activebackground="#79c0ff", activeforeground="#0d1117",
            relief="flat", bd=0, padx=20, pady=5, cursor="hand2",
            command=self._analyze)
        self._btn_analyze.pack(side="left", pady=12, padx=(0, 20))

        # ── Progress bar ────────────────────────────────────────────
        self._progress = ttk.Progressbar(self, style="Blue.Horizontal.TProgressbar",
                                          mode="indeterminate", length=200)
        # (packed dynamically when needed)

        # ── Notebook ────────────────────────────────────────────────
        self._nb = ttk.Notebook(self, style="TNotebook")
        self._nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_token_tab()
        self._build_symbol_tab()
        self._build_ast_tab()
        self._build_source_tab()
        self._build_stats_tab()

        # ── Status bar ──────────────────────────────────────────────
        sb = tk.Frame(self, bg=BG_HEADER, height=28)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self._status_lbl = tk.Label(sb, textvariable=self._status_var,
                                     font=FONT_SMALL, bg=BG_HEADER, fg=FG_DIM,
                                     anchor="w")
        self._status_lbl.pack(side="left", padx=16, pady=4)

        self._tok_count_lbl = tk.Label(sb, text="",
                                        font=FONT_SMALL, bg=BG_HEADER, fg=ACCENT,
                                        anchor="e")
        self._tok_count_lbl.pack(side="right", padx=16, pady=4)

    def _build_ast_tab(self):
        frame = tk.Frame(self._nb, bg=BG_PANEL)
        self._nb.add(frame, text="  Parse Tree (AST)  ")

        # Create Treeview with a single generic column
        self._ast_tree = ttk.Treeview(frame, style="Tokens.Treeview")
        self._ast_tree.heading("#0", text="Abstract Syntax Tree", anchor="w")
        
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._ast_tree.yview, style="Dark.Vertical.TScrollbar")
        self._ast_tree.configure(yscrollcommand=vsb.set)
        
        vsb.pack(side="right", fill="y")
        self._ast_tree.pack(fill="both", expand=True, padx=12, pady=10)

    # ── Token Tab ──────────────────────────────────────────────────────
    def _build_token_tab(self):
        frame = tk.Frame(self._nb, bg=BG_PANEL)
        self._nb.add(frame, text="  Token Stream  ")

        # Filter bar
        fbar = tk.Frame(frame, bg=BG_PANEL)
        fbar.pack(fill="x", padx=12, pady=(10, 0))

        tk.Label(fbar, text="Filter:", font=FONT_MONO_S,
                 bg=BG_PANEL, fg=FG_DIM).pack(side="left", padx=(4, 6))

        fentry = tk.Entry(fbar, textvariable=self._filter_var,
                          font=FONT_MONO_S, bg=BG_HEADER, fg=FG,
                          insertbackground=FG, relief="flat",
                          highlightthickness=1, highlightbackground=BORDER,
                          highlightcolor=ACCENT, width=30)
        fentry.pack(side="left", ipady=3)

        # Type filter buttons
        self._type_filter = tk.StringVar(value="ALL")
        types = ["ALL","KEYWORD","IDENTIFIER","OPERATOR",
                 "INTEGER_LITERAL","FLOAT_LITERAL",
                 "STRING_LITERAL","COMMENT","PREPROCESSOR"]
        for t in types:
            clr = TOKEN_COLORS.get(t, FG_DIM)
            rb = tk.Radiobutton(fbar, text=t, variable=self._type_filter,
                                value=t, font=FONT_SMALL,
                                bg=BG_PANEL, fg=clr,
                                selectcolor=BG_HEADER,
                                activebackground=BG_PANEL,
                                activeforeground=clr,
                                relief="flat", bd=0,
                                command=self._on_filter)
            rb.pack(side="left", padx=(8, 0))

        # Table
        cols = ("#", "Type", "Value", "Line", "Col")
        self._tok_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                       style="Tokens.Treeview",
                                       selectmode="browse")

        widths = {"#": 60, "Type": 170, "Value": 420, "Line": 70, "Col": 70}
        for c in cols:
            self._tok_tree.heading(c, text=c,
                                   command=lambda _c=c: self._sort_tokens(_c))
            self._tok_tree.column(c, width=widths[c], anchor="w",
                                  stretch=(c == "Value"))

        vsb = ttk.Scrollbar(frame, orient="vertical",
                             command=self._tok_tree.yview,
                             style="Dark.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(frame, orient="horizontal",
                             command=self._tok_tree.xview,
                             style="Dark.Horizontal.TScrollbar")
        self._tok_tree.configure(yscrollcommand=vsb.set,
                                  xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tok_tree.pack(fill="both", expand=True, padx=(12, 0), pady=(8, 0))

        # Tag colours per token type
        for ttype, colour in TOKEN_COLORS.items():
            self._tok_tree.tag_configure(ttype, foreground=colour)
        self._tok_tree.tag_configure("even", background=BG_ROW_B)

    # ── Symbol Table Tab ───────────────────────────────────────────────
    def _build_symbol_tab(self):
        frame = tk.Frame(self._nb, bg=BG_PANEL)
        self._nb.add(frame, text="  Symbol Table  ")

        # Filter
        fbar = tk.Frame(frame, bg=BG_PANEL)
        fbar.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(fbar, text="Filter:", font=FONT_MONO_S,
                 bg=BG_PANEL, fg=FG_DIM).pack(side="left", padx=(4, 6))
        fentry = tk.Entry(fbar, textvariable=self._sym_filter,
                          font=FONT_MONO_S, bg=BG_HEADER, fg=FG,
                          insertbackground=FG, relief="flat",
                          highlightthickness=1, highlightbackground=BORDER,
                          highlightcolor=ACCENT2, width=30)
        fentry.pack(side="left", ipady=3)

        # Category filter
        self._cat_filter = tk.StringVar(value="ALL")
        cats = ["ALL", "function", "variable", "type", "namespace"]
        for cat in cats:
            clr = CATEGORY_COLORS.get(cat, FG_DIM)
            rb = tk.Radiobutton(fbar, text=cat, variable=self._cat_filter,
                                value=cat, font=FONT_SMALL,
                                bg=BG_PANEL, fg=clr,
                                selectcolor=BG_HEADER,
                                activebackground=BG_PANEL,
                                activeforeground=clr, relief="flat", bd=0,
                                command=self._on_sym_filter)
            rb.pack(side="left", padx=(12, 0))

        # Table
        cols = ("#", "Name", "Category", "First Line", "Occurrences", "All Lines")
        self._sym_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                       style="Sym.Treeview",
                                       selectmode="browse")
        widths = {"#": 55, "Name": 200, "Category": 130,
                  "First Line": 100, "Occurrences": 110, "All Lines": 350}
        for c in cols:
            self._sym_tree.heading(c, text=c,
                                   command=lambda _c=c: self._sort_symbols(_c))
            self._sym_tree.column(c, width=widths[c], anchor="w",
                                  stretch=(c == "All Lines"))

        vsb = ttk.Scrollbar(frame, orient="vertical",
                             command=self._sym_tree.yview,
                             style="Dark.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(frame, orient="horizontal",
                             command=self._sym_tree.xview,
                             style="Dark.Horizontal.TScrollbar")
        self._sym_tree.configure(yscrollcommand=vsb.set,
                                  xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._sym_tree.pack(fill="both", expand=True, padx=(12, 0), pady=(8, 0))

        for cat, colour in CATEGORY_COLORS.items():
            self._sym_tree.tag_configure(cat, foreground=colour)
        self._sym_tree.tag_configure("even", background=BG_ROW_B)

    # ── Source View Tab ────────────────────────────────────────────────
    def _build_source_tab(self):
        frame = tk.Frame(self._nb, bg=BG_PANEL)
        self._nb.add(frame, text="  Source View  ")

        # line numbers + text side-by-side
        container = tk.Frame(frame, bg=BG_PANEL)
        container.pack(fill="both", expand=True, padx=12, pady=10)

        self._line_nums = tk.Text(container, width=5, state="disabled",
                                   bg=BG_HEADER, fg=FG_DARK,
                                   font=FONT_MONO_S, relief="flat",
                                   bd=0, padx=4, pady=4,
                                   selectbackground=BG_HEADER)
        self._line_nums.pack(side="left", fill="y")

        src_vsb = ttk.Scrollbar(container, orient="vertical",
                                 style="Dark.Vertical.TScrollbar")
        src_vsb.pack(side="right", fill="y")

        self._src_text = tk.Text(container, state="disabled",
                                  bg=BG_PANEL, fg=FG,
                                  font=FONT_MONO_S, relief="flat",
                                  bd=0, padx=8, pady=4,
                                  selectbackground="#1f6feb",
                                  insertbackground=FG,
                                  wrap="none",
                                  yscrollcommand=self._sync_scroll)
        self._src_text.pack(side="left", fill="both", expand=True)
        src_vsb.config(command=self._scroll_both)

        # Syntax highlight tags
        self._src_text.tag_configure("KEYWORD",      foreground="#ff7b72")
        self._src_text.tag_configure("IDENTIFIER",   foreground="#79c0ff")
        self._src_text.tag_configure("STRING",       foreground="#a5d6ff")
        self._src_text.tag_configure("CHAR",         foreground="#a5d6ff")
        self._src_text.tag_configure("NUMBER",       foreground="#79c0ff")
        self._src_text.tag_configure("OPERATOR",     foreground="#ffa657")
        self._src_text.tag_configure("PREPROCESSOR", foreground="#d2a8ff")
        self._src_text.tag_configure("COMMENT",      foreground="#8b949e")

    def _sync_scroll(self, *args):
        self._line_nums.yview_moveto(args[0])

    def _scroll_both(self, *args):
        self._src_text.yview(*args)
        self._line_nums.yview(*args)

    # ── Stats Tab ──────────────────────────────────────────────────────
    def _build_stats_tab(self):
        frame = tk.Frame(self._nb, bg=BG_PANEL)
        self._nb.add(frame, text="  Statistics  ")
        self._stats_frame = frame

    def _render_stats(self):
        for w in self._stats_frame.winfo_children():
            w.destroy()

        if not self._tokens_data:
            tk.Label(self._stats_frame, text="No data yet.",
                     font=FONT_MONO, bg=BG_PANEL, fg=FG_DIM).pack(pady=40)
            return

        # Count by type
        from collections import Counter
        type_counts = Counter(t["type"] for t in self._tokens_data)
        total = len(self._tokens_data)

        title = tk.Label(self._stats_frame, text="Token Distribution",
                         font=FONT_BOLD, bg=BG_PANEL, fg=FG)
        title.pack(pady=(24, 16))

        canvas_w, canvas_h = 700, 320
        canvas = tk.Canvas(self._stats_frame, width=canvas_w, height=canvas_h,
                            bg=BG_PANEL, highlightthickness=0)
        canvas.pack()

        items = sorted(type_counts.items(), key=lambda x: -x[1])
        bar_h = 28
        max_count = items[0][1] if items else 1
        x_start = 200
        bar_max_w = 420
        y = 20

        for ttype, cnt in items:
            clr  = TOKEN_COLORS.get(ttype, FG_DIM)
            bw   = max(4, int(bar_max_w * cnt / max_count))
            pct  = cnt / total * 100

            canvas.create_text(x_start - 10, y + bar_h//2,
                                text=ttype, anchor="e",
                                font=FONT_SMALL, fill=clr)
            canvas.create_rectangle(x_start, y, x_start + bw, y + bar_h,
                                     fill=clr, outline="")
            canvas.create_text(x_start + bw + 8, y + bar_h//2,
                                text=f"{cnt}  ({pct:.1f}%)", anchor="w",
                                font=FONT_SMALL, fill=FG_DIM)
            y += bar_h + 6

        # Summary numbers
        sym_count = len(self._symbols_data)
        lines = max((t["line"] for t in self._tokens_data), default=0)

        grid = tk.Frame(self._stats_frame, bg=BG_PANEL)
        grid.pack(pady=24)
        stats = [
            ("Total Tokens",     str(total),      ACCENT),
            ("Unique Symbols",   str(sym_count),  ACCENT2),
            ("Source Lines",     str(lines),      ACCENT4),
            ("Keywords",         str(type_counts.get("KEYWORD", 0)),     ACCENT3),
            ("Identifiers",      str(type_counts.get("IDENTIFIER", 0)),  ACCENT),
            ("String Literals",  str(type_counts.get("STRING_LITERAL",0)), "#a5d6ff"),
        ]
        for i, (label, val, clr) in enumerate(stats):
            card = tk.Frame(grid, bg=BG_HEADER, bd=0,
                             highlightthickness=1, highlightbackground=BORDER)
            card.grid(row=i//3, column=i%3, padx=12, pady=8, ipadx=20, ipady=10)
            tk.Label(card, text=val, font=(FONT_MONO[0], 22, "bold"),
                     bg=BG_HEADER, fg=clr).pack()
            tk.Label(card, text=label, font=FONT_SMALL,
                     bg=BG_HEADER, fg=FG_DIM).pack()

    # ── Actions ────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select C++ Source File",
            filetypes=[("C++ Source", "*.cpp *.cxx *.cc *.h *.hpp"),
                       ("All files",  "*.*")])
        if path:
            self._cpp_path.set(path)

    def _analyze(self):
        path = self._cpp_path.get().strip()
        if not path:
            messagebox.showwarning("No File", "Please select a .cpp file first.")
            return
        if not os.path.isfile(path):
            messagebox.showerror("File Not Found", f"Cannot find:\n{path}")
            return

        backend = find_backend()
        if backend is None:
            ans = messagebox.askyesno(
                "Backend Not Found",
                "lexer_backend executable not found.\n\n"
                "Would you like to compile it now?\n"
                "(Requires g++ to be installed)")
            if ans:
                self._compile_backend(then_analyze=path)
            return

        self._set_status("Analyzing…", busy=True)
        threading.Thread(target=self._run_backend,
                          args=(backend, path), daemon=True).start()

    def _run_backend(self, backend, path):
        try:
            result = subprocess.run(
                [backend, path],
                capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.after(0, lambda: self._on_error(
                    result.stderr or "Backend returned non-zero exit code."))
                return
            data = json.loads(result.stdout)
            self.after(0, lambda: self._on_data(data, path))
        except subprocess.TimeoutExpired:
            self.after(0, lambda: self._on_error("Analysis timed out."))
        except json.JSONDecodeError as e:
            self.after(0, lambda: self._on_error(f"JSON parse error: {e}"))
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _on_data(self, data, src_path):
        self._tokens_data  = data.get("tokens", [])
        self._symbols_data = data.get("symbol_table", [])
        ast_data           = data.get("ast", [])
        self._populate_token_table(self._tokens_data)
        self._populate_symbol_table(self._symbols_data)
        self._populate_ast_tree(ast_data)
        self._load_source(src_path)
        self._render_stats()

        tc = len(self._tokens_data)
        sc = len(self._symbols_data)
        self._set_status(
            f"Done — {tc} tokens, {sc} unique symbols in: {os.path.basename(src_path)}",
            busy=False)
        self._tok_count_lbl.config(
            text=f"Tokens: {tc}  |  Symbols: {sc}")

    def _on_error(self, msg):
        self._set_status(f"Error: {msg}", busy=False, error=True)
        messagebox.showerror("Analysis Error", msg)

    def _populate_ast_tree(self, ast_data):
        self._ast_tree.delete(*self._ast_tree.get_children())
        
        # Recursive function to map JSON nodes to Tkinter Tree items
        def insert_node(parent_id, node_data):
            if isinstance(node_data, dict):
                node_type = node_data.get("type", "Node")
                
                # Format a display string (e.g., "VarDecl: a (int)")
                display_text = f"[{node_type}]"
                if "identifier" in node_data:
                    display_text += f" {node_data['identifier']}"
                if "value" in node_data:
                    display_text += f" = {node_data['value']}"
                
                item_id = self._ast_tree.insert(parent_id, "end", text=display_text, open=True)
                
                # Recursively add children
                for key, val in node_data.items():
                    if key not in ["type", "identifier", "value"]: # skip flat strings we just printed
                        if isinstance(val, (dict, list)):
                            child_folder = self._ast_tree.insert(item_id, "end", text=f"{key}:", open=True)
                            insert_node(child_folder, val)
                            
            elif isinstance(node_data, list):
                for item in node_data:
                    insert_node(parent_id, item)

        # Insert the root
        insert_node("", ast_data)

    # ── Populate tables ────────────────────────────────────────────────
    def _populate_token_table(self, tokens):
        self._tok_tree.delete(*self._tok_tree.get_children())
        for i, tok in enumerate(tokens):
            tags = [tok["type"]]
            if i % 2 == 1: tags.append("even")
            self._tok_tree.insert("", "end",
                values=(i+1, tok["type"], tok["value"],
                        tok["line"], tok["col"]),
                tags=tags)

    def _populate_symbol_table(self, symbols):
        self._sym_tree.delete(*self._sym_tree.get_children())
        for i, sym in enumerate(symbols):
            lines_str = ", ".join(str(l) for l in sym.get("lines", []))
            tags = [sym.get("category", "unknown")]
            if i % 2 == 1: tags.append("even")
            self._sym_tree.insert("", "end",
                values=(i+1, sym["name"], sym.get("category","?"),
                        sym.get("first_line","?"),
                        sym.get("occurrences","?"),
                        lines_str),
                tags=tags)

    # ── Source view with syntax highlighting ───────────────────────────
    def _load_source(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                src = f.read()
        except Exception:
            return

        self._src_text.config(state="normal")
        self._src_text.delete("1.0", "end")
        self._src_text.insert("end", src)

        # Apply token-based syntax highlighting
        for tok in self._tokens_data:
            tag = {
                "KEYWORD":        "KEYWORD",
                "STRING_LITERAL": "STRING",
                "CHAR_LITERAL":   "CHAR",
                "INTEGER_LITERAL":"NUMBER",
                "FLOAT_LITERAL":  "NUMBER",
                "OPERATOR":       "OPERATOR",
                "PREPROCESSOR":   "PREPROCESSOR",
                "COMMENT":        "COMMENT",
            }.get(tok["type"])
            if tag is None:
                continue
            line = tok["line"]
            col  = tok["col"]
            val  = tok["value"]
            start = f"{line}.{col-1}"
            end   = f"{line}.{col-1+len(val)}"
            try:
                self._src_text.tag_add(tag, start, end)
            except Exception:
                pass

        self._src_text.config(state="disabled")

        # Line numbers
        self._line_nums.config(state="normal")
        self._line_nums.delete("1.0", "end")
        n_lines = src.count("\n") + 1
        self._line_nums.insert("end",
            "\n".join(str(i) for i in range(1, n_lines + 1)))
        self._line_nums.config(state="disabled")

    # ── Filter ─────────────────────────────────────────────────────────
    def _on_filter(self, *_):
        q     = self._filter_var.get().lower()
        ttype = self._type_filter.get()
        self._tok_tree.delete(*self._tok_tree.get_children())
        idx = 0
        for tok in self._tokens_data:
            if ttype != "ALL" and tok["type"] != ttype:
                continue
            if q and q not in tok["value"].lower() and q not in tok["type"].lower():
                continue
            tags = [tok["type"]]
            if idx % 2 == 1: tags.append("even")
            self._tok_tree.insert("", "end",
                values=(idx+1, tok["type"], tok["value"],
                        tok["line"], tok["col"]),
                tags=tags)
            idx += 1

    def _on_sym_filter(self, *_):
        q   = self._sym_filter.get().lower()
        cat = self._cat_filter.get()
        self._sym_tree.delete(*self._sym_tree.get_children())
        idx = 0
        for sym in self._symbols_data:
            if cat != "ALL" and sym.get("category") != cat:
                continue
            if q and q not in sym["name"].lower():
                continue
            lines_str = ", ".join(str(l) for l in sym.get("lines", []))
            tags = [sym.get("category", "unknown")]
            if idx % 2 == 1: tags.append("even")
            self._sym_tree.insert("", "end",
                values=(idx+1, sym["name"], sym.get("category","?"),
                        sym.get("first_line","?"),
                        sym.get("occurrences","?"),
                        lines_str),
                tags=tags)
            idx += 1

    # ── Sort ───────────────────────────────────────────────────────────
    def _sort_tokens(self, col):
        col_map = {"#": None, "Type": "type", "Value": "value",
                   "Line": "line", "Col": "col"}
        key = col_map.get(col)
        if not key or not self._tokens_data:
            return
        rev = (self._sort_col == col) and not self._sort_rev
        self._sort_col = col; self._sort_rev = rev
        self._tokens_data.sort(key=lambda t: t.get(key, ""), reverse=rev)
        self._populate_token_table(self._tokens_data)

    def _sort_symbols(self, col):
        col_map = {"#": None, "Name": "name", "Category": "category",
                   "First Line": "first_line", "Occurrences": "occurrences"}
        key = col_map.get(col)
        if not key or not self._symbols_data:
            return
        rev = (self._sort_col == col) and not self._sort_rev
        self._sort_col = col; self._sort_rev = rev
        self._symbols_data.sort(key=lambda s: s.get(key, ""), reverse=rev)
        self._populate_symbol_table(self._symbols_data)

    # ── Compile backend ────────────────────────────────────────────────
    def _compile_backend(self, then_analyze=None):
        here = os.path.dirname(os.path.abspath(__file__))
        src  = os.path.join(here, "main.cpp") # <--- Changed to main.cpp
        out  = os.path.join(here, "lexer_backend")

        if not os.path.isfile(src):
            messagebox.showerror("Source Not Found",
                f"main.cpp not found in:\n{here}\n\nMake sure main.cpp, lexer.h, and parser.h are in the same folder as this script.")
            return

        self._set_status("Compiling C++ backend…", busy=True)

        def do_compile():
            try:
                # We compile main.cpp. The headers (lexer.h, parser.h) will be included automatically by the compiler.
                result = subprocess.run(
                    ["g++", "-O2", "-std=c++17", src, "-o", out],
                    capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    self.after(0, lambda: self._set_status(
                        "Backend compiled successfully!", busy=False))
                    if then_analyze:
                        self.after(200, lambda: self._analyze())
                else:
                    err = result.stderr
                    self.after(0, lambda: self._on_error(
                        f"Compilation failed:\n{err}"))
            except FileNotFoundError:
                self.after(0, lambda: self._on_error(
                    "g++ not found. Please install GCC/MinGW and add it to PATH."))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=do_compile, daemon=True).start()
        self._set_status("Compiling C++ backend…", busy=True)

        def do_compile():
            try:
                result = subprocess.run(
                    ["g++", "-O2", "-std=c++17", src, "-o", out],
                    capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    self.after(0, lambda: self._set_status(
                        "Backend compiled successfully!", busy=False))
                    if then_analyze:
                        self.after(200, lambda: self._analyze())
                else:
                    err = result.stderr
                    self.after(0, lambda: self._on_error(
                        f"Compilation failed:\n{err}"))
            except FileNotFoundError:
                self.after(0, lambda: self._on_error(
                    "g++ not found. Please install GCC/MinGW and add it to PATH."))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=do_compile, daemon=True).start()

    # ── Status helpers ─────────────────────────────────────────────────
    def _set_status(self, msg, busy=False, error=False):
        self._status_var.set(msg)
        clr = ACCENT3 if error else (ACCENT if not busy else ACCENT5)
        self._status_lbl.config(fg=clr)
        if busy:
            self._progress.pack(side="bottom", fill="x")
            self._progress.start(12)
        else:
            self._progress.stop()
            self._progress.pack_forget()


# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = LexerApp()
    app.mainloop()
