"""gui/pages/_tab_code.py — Code analysis tab for the Dashboard (IDE mode)."""

import re
import subprocess
import sys
import tempfile
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QScrollArea, QFrame, QComboBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QRegularExpression
from PyQt6.QtGui import (
    QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QTextDocument, QKeySequence, QShortcut
)


# ── Universal syntax highlighter ─────────────────────────────────────────────

def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:   f.setFontWeight(700)
    if italic: f.setFontItalic(True)
    return f

# VS Code Dark+ palette
_C = {
    "kw":      _fmt("#569cd6", bold=True),   # blue   — keywords
    "fn":      _fmt("#dcdcaa"),              # yellow — functions/builtins
    "str":     _fmt("#ce9178"),              # orange — strings
    "com":     _fmt("#6a9955", italic=True), # green  — comments
    "num":     _fmt("#b5cea8"),              # light green — numbers
    "dec":     _fmt("#c586c0"),              # purple — decorators/annotations
    "cls":     _fmt("#4ec9b0", bold=True),   # teal   — class names
    "self":    _fmt("#9cdcfe"),              # light blue — self/this
    "tag":     _fmt("#569cd6"),              # blue   — HTML tags
    "attr":    _fmt("#9cdcfe"),              # light blue — HTML attributes
    "prop":    _fmt("#9cdcfe"),              # light blue — CSS properties
    "val":     _fmt("#ce9178"),              # orange — CSS values
    "type":    _fmt("#4ec9b0"),              # teal   — types
    "op":      _fmt("#d4d4d4"),              # default — operators
}

def _rules_for_lang(lang: str) -> list[tuple[str, QTextCharFormat]]:
    """Return (pattern, format) rules for the given language family."""

    # ── C-family (JS, TS, Java, C, C++, Kotlin, Swift, Dart, Go, Rust, PHP) ──
    C_KW = (
        "abstract|as|async|await|break|case|catch|class|const|continue|"
        "debugger|default|delete|do|else|enum|export|extends|false|finally|"
        "for|from|function|if|implements|import|in|instanceof|interface|"
        "let|new|null|of|override|package|private|protected|public|"
        "return|static|super|switch|this|throw|true|try|typeof|"
        "undefined|var|void|while|with|yield|"
        # Java/Kotlin/Swift/Dart extras
        "fun|val|var|when|where|init|companion|object|data|sealed|"
        "open|internal|inline|reified|suspend|operator|infix|"
        "guard|defer|struct|protocol|extension|typealias|"
        "final|abstract|native|synchronized|transient|volatile|"
        # Go/Rust extras
        "chan|go|goroutine|map|range|select|type|package|"
        "fn|let|mut|impl|trait|use|mod|pub|crate|self|super|"
        "match|loop|move|ref|where|dyn|unsafe|extern|"
        # PHP extras
        "echo|print|include|require|namespace|use|trait|yield|"
        "array|list|foreach|endforeach|endfor|endwhile|endif|"
        "elseif|declare|enddeclare|endswitch"
    )
    C_BUILTIN = (
        "console|Math|JSON|Object|Array|String|Number|Boolean|"
        "Promise|setTimeout|setInterval|fetch|document|window|"
        "parseInt|parseFloat|isNaN|isFinite|encodeURI|decodeURI|"
        "print|println|printf|sprintf|strlen|count|array_map|"
        "System|println|print|fmt|Println|Printf|Sprintf|"
        "println!|vec!|format!|panic!|assert!|todo!|unimplemented!"
    )
    c_rules = [
        (r"//[^\n]*",                          _C["com"]),   # // comment
        (r"/\*.*?\*/",                         _C["com"]),   # /* block */
        (r"#[^\n]*",                           _C["com"]),   # # comment (PHP/Swift)
        (rf"\b({C_KW})\b",                     _C["kw"]),
        (rf"\b({C_BUILTIN})\b",                _C["fn"]),
        (r"\b(this|self|super)\b",             _C["self"]),
        (r"\bclass\s+(\w+)",                   _C["cls"]),
        (r"\bfun\s+(\w+)",                     _C["fn"]),
        (r"\bfn\s+(\w+)",                      _C["fn"]),
        (r"\bfunction\s+(\w+)",                _C["fn"]),
        (r"\bdef\s+(\w+)",                     _C["fn"]),
        (r"@\w+",                              _C["dec"]),   # annotations
        (r"\b\d+\.?\d*([eE][+-]?\d+)?\b",     _C["num"]),
        (r'"[^"\\]*(\\.[^"\\]*)*"',            _C["str"]),
        (r"'[^'\\]*(\\.[^'\\]*)*'",            _C["str"]),
        (r"`[^`]*`",                           _C["str"]),   # template literals
    ]

    # ── Python ────────────────────────────────────────────────────────────────
    PY_KW = (
        "False|None|True|and|as|assert|async|await|break|class|continue|"
        "def|del|elif|else|except|finally|for|from|global|if|import|in|is|"
        "lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield"
    )
    PY_BI = (
        "print|len|range|type|int|str|float|list|dict|set|tuple|bool|"
        "open|input|super|enumerate|zip|map|filter|sorted|reversed|"
        "any|all|min|max|sum|abs|round|isinstance|hasattr|getattr|"
        "setattr|staticmethod|classmethod|property|object"
    )
    py_rules = [
        (r"#[^\n]*",                           _C["com"]),
        (r'""".*?"""',                         _C["str"]),
        (r"'''.*?'''",                         _C["str"]),
        (rf"\b({PY_KW})\b",                    _C["kw"]),
        (r"\b(self|cls)\b",                    _C["self"]),
        (r"\bclass\s+(\w+)",                   _C["cls"]),
        (r"\bdef\s+(\w+)",                     _C["fn"]),
        (rf"\b({PY_BI})\b",                    _C["fn"]),
        (r"@\w+",                              _C["dec"]),
        (r"\b\d+\.?\d*([eE][+-]?\d+)?\b",     _C["num"]),
        (r'"[^"\\]*(\\.[^"\\]*)*"',            _C["str"]),
        (r"'[^'\\]*(\\.[^'\\]*)*'",            _C["str"]),
    ]

    # ── HTML ──────────────────────────────────────────────────────────────────
    html_rules = [
        (r"<!--.*?-->",                        _C["com"]),
        (r"</?(\w[\w.-]*)",                    _C["tag"]),
        (r'\b(\w+)\s*=',                       _C["attr"]),
        (r'"[^"]*"',                           _C["str"]),
        (r"'[^']*'",                           _C["str"]),
        (r"&\w+;",                             _C["dec"]),
    ]

    # ── CSS ───────────────────────────────────────────────────────────────────
    css_rules = [
        (r"/\*.*?\*/",                         _C["com"]),
        (r"[.#][\w-]+",                        _C["cls"]),
        (r"[\w-]+\s*:",                        _C["prop"]),
        (r":\s*[^;{]+",                        _C["val"]),
        (r'"[^"]*"',                           _C["str"]),
        (r"'[^']*'",                           _C["str"]),
        (r"#[0-9a-fA-F]{3,8}\b",              _C["num"]),
        (r"\b\d+\.?\d*(px|em|rem|%|vh|vw|pt|s|ms)?\b", _C["num"]),
    ]

    # ── SQL ───────────────────────────────────────────────────────────────────
    SQL_KW = (
        "SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|"
        "CREATE|TABLE|DROP|ALTER|ADD|COLUMN|INDEX|PRIMARY|KEY|"
        "FOREIGN|REFERENCES|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AS|"
        "GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|DISTINCT|ALL|UNION|"
        "AND|OR|NOT|IN|LIKE|BETWEEN|IS|NULL|EXISTS|CASE|WHEN|"
        "THEN|ELSE|END|BEGIN|COMMIT|ROLLBACK|TRANSACTION|"
        "DATABASE|USE|SHOW|DESCRIBE|EXPLAIN|GRANT|REVOKE"
    )
    sql_rules = [
        (r"--[^\n]*",                          _C["com"]),
        (r"/\*.*?\*/",                         _C["com"]),
        (rf"\b({SQL_KW})\b",                   _C["kw"]),
        (r"'[^']*'",                           _C["str"]),
        (r'"[^"]*"',                           _C["str"]),
        (r"\b\d+\.?\d*\b",                     _C["num"]),
        (r"\b\w+\s*\(",                        _C["fn"]),
    ]

    # ── Dispatch ──────────────────────────────────────────────────────────────
    lang_lower = lang.lower()
    if any(x in lang_lower for x in ("python", "django", "fastapi")):
        return py_rules
    if "html" in lang_lower:
        return html_rules
    if "css" in lang_lower:
        return css_rules
    if any(x in lang_lower for x in ("sql", "nosql", "mongo", "mysql")):
        return sql_rules
    # Everything else (JS, TS, Java, C, C++, Kotlin, Swift, Dart, Go, Rust,
    # PHP, Ruby, React, Vue, Angular, Flutter, Laravel, Next, Spring, ASP…)
    return c_rules


class _CodeHighlighter(QSyntaxHighlighter):
    """Universal VS Code-style syntax highlighter — adapts to any language."""

    def __init__(self, document: QTextDocument, lang: str = "Python"):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = [
            (QRegularExpression(p), f) for p, f in _rules_for_lang(lang)
        ]

    def set_language(self, lang: str):
        self._rules = [
            (QRegularExpression(p), f) for p, f in _rules_for_lang(lang)
        ]
        self.rehighlight()

    def highlightBlock(self, text: str):
        for regex, fmt in self._rules:
            it = regex.globalMatch(text)
            while it.hasNext():
                m = it.next()
                start  = m.capturedStart(1) if m.lastCapturedIndex() >= 1 else m.capturedStart()
                length = m.capturedLength(1) if m.lastCapturedIndex() >= 1 else m.capturedLength()
                if start >= 0:
                    self.setFormat(start, length, fmt)


# Keep old name working
_PythonHighlighter = _CodeHighlighter


# ── Background runner ─────────────────────────────────────────────────────────

class _RunSignals(QObject):
    finished = pyqtSignal(str, str)   # stdout, stderr


class _RunThread(QThread):
    def __init__(self, code: str, lang: str, signals: _RunSignals):
        super().__init__()
        self._code    = code
        self._lang    = lang
        self._signals = signals

    def run(self):
        stdout, stderr = _execute_code(self._code, self._lang)
        self._signals.finished.emit(stdout, stderr)


def _execute_code(code: str, lang: str) -> tuple[str, str]:
    """Run code locally in a temp file. Returns (stdout, stderr)."""
    lang_lower = lang.lower()
    tmp_path = None
    exe_path = None
    try:
        # ── HTML — write to temp file and open in browser ─────────────────
        if "html" in lang_lower:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name
            import webbrowser
            webbrowser.open(f"file://{tmp_path}")
            return "✓ Opened in your default browser.", ""

        # ── CSS — wrap in a minimal HTML page and open in browser ─────────
        if "css" in lang_lower:
            html_wrapper = (
                "<!DOCTYPE html><html><head><style>\n"
                + code +
                "\n</style></head><body>"
                "<h1 style='font-family:sans-serif'>CSS Preview</h1>"
                "<p class='sample'>Sample paragraph</p>"
                "<button class='sample'>Sample button</button>"
                "</body></html>"
            )
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as f:
                f.write(html_wrapper)
                tmp_path = f.name
            import webbrowser
            webbrowser.open(f"file://{tmp_path}")
            return "✓ CSS preview opened in your default browser.", ""

        # ── C / C++ — compile then run ────────────────────────────────────
        if lang_lower in ("c", "c++"):
            suffix   = ".c" if lang_lower == "c" else ".cpp"
            compiler = "gcc" if lang_lower == "c" else "g++"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name

            exe_path = tmp_path + ".out"
            compile_result = subprocess.run(
                [compiler, tmp_path, "-o", exe_path],
                capture_output=True, text=True, timeout=15
            )
            if compile_result.returncode != 0:
                return "", f"Compile error:\n{compile_result.stderr}"
            run_result = subprocess.run(
                [exe_path], capture_output=True, text=True, timeout=10
            )
            return run_result.stdout, run_result.stderr

        # ── Java — compile with javac then run ────────────────────────────
        if "java" in lang_lower and "javascript" not in lang_lower:
            # Extract public class name (Java requires filename == class name)
            import re as _re
            m = _re.search(r'\bpublic\s+class\s+(\w+)', code)
            class_name = m.group(1) if m else "Main"
            tmp_dir = tempfile.mkdtemp()
            tmp_path = os.path.join(tmp_dir, f"{class_name}.java")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(code)
            compile_result = subprocess.run(
                ["javac", tmp_path],
                capture_output=True, text=True, timeout=20
            )
            if compile_result.returncode != 0:
                return "", f"Compile error:\n{compile_result.stderr}"
            run_result = subprocess.run(
                ["java", "-cp", tmp_dir, class_name],
                capture_output=True, text=True, timeout=10
            )
            return run_result.stdout, run_result.stderr

        # ── Swift — compile and run ───────────────────────────────────────
        if "swift" in lang_lower:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".swift", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name
            result = subprocess.run(
                ["swift", tmp_path],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout, result.stderr

        # ── Dart / Flutter — run with dart ────────────────────────────────
        if "dart" in lang_lower or "flutter" in lang_lower:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".dart", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name
            result = subprocess.run(
                ["dart", "run", tmp_path],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout, result.stderr

        # ── SQL — run via sqlite3 (built-in, no install needed) ──────────
        if any(x in lang_lower for x in ("sql", "mysql", "nosql", "mongo")):
            # Wrap the SQL in a Python sqlite3 script and run it
            py_runner = (
                "import sqlite3, sys\n"
                "conn = sqlite3.connect(':memory:')\n"
                "cur = conn.cursor()\n"
                "sql = '''" + code.replace("'", "\\'") + "'''\n"
                "try:\n"
                "    cur.executescript(sql)\n"
                "    # Try to fetch results from last SELECT\n"
                "    stmts = [s.strip() for s in sql.split(';') if s.strip()]\n"
                "    for stmt in reversed(stmts):\n"
                "        if stmt.upper().startswith('SELECT'):\n"
                "            cur.execute(stmt)\n"
                "            rows = cur.fetchall()\n"
                "            if rows:\n"
                "                cols = [d[0] for d in cur.description]\n"
                "                print(' | '.join(cols))\n"
                "                print('-' * 40)\n"
                "                for r in rows:\n"
                "                    print(' | '.join(str(x) for x in r))\n"
                "            else:\n"
                "                print('(no rows returned)')\n"
                "            break\n"
                "    else:\n"
                "        print('OK — statement executed successfully.')\n"
                "except Exception as e:\n"
                "    print(f'Error: {e}', file=sys.stderr)\n"
                "finally:\n"
                "    conn.close()\n"
            )
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(py_runner)
                tmp_path = f.name
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout, result.stderr

        # ── All other languages ───────────────────────────────────────────
        suffix_map = {
            "python":          ".py",
            "javascript":      ".js",
            "typescript":      ".ts",
            "bash":            ".sh",
            "powershell":      ".ps1",
            "rust":            ".rs",
            "go":              ".go",
            "kotlin":          ".kts",
            "php / laravel":   ".php",
            "php":             ".php",
        }
        runner_map = {
            "python":          [sys.executable],
            "javascript":      ["node"],
            "typescript":      ["npx", "ts-node"],
            "bash":            ["bash"],
            "powershell":      ["powershell", "-File"],
            "php / laravel":   ["php"],
            "php":             ["php"],
            "kotlin":          ["kotlinc", "-script"],
            "go":              ["go", "run"],
        }

        key = lang_lower.split("/")[0].strip()
        suffix = suffix_map.get(key, ".py")
        runner = runner_map.get(key)

        # Rust needs special compile+run
        if key == "rust":
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".rs", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name
            exe_path = tmp_path + ".out"
            cr = subprocess.run(
                ["rustc", tmp_path, "-o", exe_path],
                capture_output=True, text=True, timeout=30
            )
            if cr.returncode != 0:
                return "", f"Compile error:\n{cr.stderr}"
            rr = subprocess.run([exe_path], capture_output=True, text=True, timeout=10)
            return rr.stdout, rr.stderr

        # React/Next.js/Vue/Angular — treat as plain JS (node)
        if any(x in key for x in ("react", "next", "vue", "angular")):
            runner = ["node"]
            suffix = ".js"

        if runner is None:
            return "", (
                f"⚠ No local runner configured for '{lang}'.\n"
                "This language requires an external runtime to be installed.\n"
                "Use the 'Ask' button below to get AI help instead."
            )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            runner + [tmp_path],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return "", "⏱ Execution timed out (10 s limit)."
    except FileNotFoundError as e:
        cmd = str(e).split("'")[1] if "'" in str(e) else str(e)
        return "", (
            f"⚠ Runtime not found: '{cmd}'\n\n"
            f"To run {lang} code locally, install the required tool:\n"
            + _install_hint(lang)
        )
    except Exception as e:
        return "", str(e)
    finally:
        for p in [tmp_path, exe_path]:
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass


def _install_hint(lang: str) -> str:
    """Return a helpful install hint for a missing runtime."""
    lang_lower = lang.lower()
    hints = {
        "java":        "  • Ubuntu/Debian: sudo apt install default-jdk\n  • macOS: brew install openjdk",
        "kotlin":      "  • Ubuntu/Debian: sudo apt install kotlin\n  • macOS: brew install kotlin",
        "swift":       "  • Ubuntu: https://swift.org/download\n  • macOS: included with Xcode",
        "dart":        "  • https://dart.dev/get-dart\n  • macOS: brew install dart",
        "flutter":     "  • https://flutter.dev/docs/get-started/install",
        "go":          "  • Ubuntu/Debian: sudo apt install golang\n  • macOS: brew install go",
        "rust":        "  • All platforms: curl https://sh.rustup.rs | sh",
        "node":        "  • Ubuntu/Debian: sudo apt install nodejs\n  • macOS: brew install node",
        "javascript":  "  • Ubuntu/Debian: sudo apt install nodejs\n  • macOS: brew install node",
        "typescript":  "  • Requires Node.js, then: npm install -g ts-node typescript",
        "php":         "  • Ubuntu/Debian: sudo apt install php\n  • macOS: brew install php",
        "powershell":  "  • Ubuntu: https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-linux",
    }
    for key, hint in hints.items():
        if key in lang_lower:
            return hint
    return "  • Install the appropriate runtime for your OS."


# ── Tab mixin ─────────────────────────────────────────────────────────────────

class CodeTabMixin:
    """Code tab — analysis + local IDE playground per key point."""

    def _build_code_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 18, 0, 0)
        outer.setSpacing(0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("tabPage")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 18)
        lay.setSpacing(10)

        # ── Input ─────────────────────────────────────────────────────────
        in_hdr = QHBoxLayout()
        in_hdr.setContentsMargins(0, 0, 0, 6)
        in_lbl = QLabel("Paste code")
        in_lbl.setObjectName("featureLabel")
        in_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        in_hdr.addWidget(in_lbl)
        in_hdr.addStretch()

        # Language selector
        self._code_lang = QComboBox()
        self._code_lang.setObjectName("translateCombo")
        self._code_lang.setFixedHeight(28)
        self._code_lang.setMinimumWidth(160)
        for lang in [
            # Web
            "JavaScript", "TypeScript", "HTML", "CSS",
            # Backend / frameworks
            "Python", "PHP / Laravel", "Java", "Kotlin",
            # Mobile
            "Swift", "Dart / Flutter",
            # Systems
            "C", "C++", "Rust", "Go",
            # Scripting
            "Bash", "PowerShell",
            # Data
            "SQL / MySQL", "NoSQL / MongoDB",
            # Full-stack frameworks (highlight as JS/TS)
            "React / Next.js", "Vue", "Angular",
        ]:
            self._code_lang.addItem(lang)
        in_hdr.addWidget(self._code_lang)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(70, 28)
        clear_btn.clicked.connect(self._clear_code)
        in_hdr.addWidget(clear_btn)
        lay.addLayout(in_hdr)

        self._code_input = QTextEdit()
        self._code_input.setObjectName("codeEdit")
        self._code_input.setPlaceholderText("Paste your code here…")
        self._code_input.setFixedHeight(160)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._code_input.setFont(mono)
        self._code_highlighter = _CodeHighlighter(self._code_input.document(), "Python")
        # Re-highlight when language changes
        self._code_lang.currentTextChanged.connect(
            lambda lang: self._code_highlighter.set_language(lang)
        )
        lay.addWidget(self._code_input)

        # Action row
        act_row = QHBoxLayout()
        act_row.setContentsMargins(0, 0, 0, 0)
        act_row.setSpacing(10)
        act_row.addStretch()
        analyse_btn = QPushButton("Analyse")
        analyse_btn.setObjectName("btnPrimary")
        analyse_btn.setFixedSize(100, 30)
        analyse_btn.clicked.connect(self._run_code_analyse)
        act_row.addWidget(analyse_btn)
        lay.addLayout(act_row)

        # Overview bar
        self._code_summary_lbl = QLabel("")
        self._code_summary_lbl.setObjectName("codeSummaryLbl")
        self._code_summary_lbl.setWordWrap(True)
        self._code_summary_lbl.setVisible(False)
        lay.addWidget(self._code_summary_lbl)

        # Grid label
        self._code_grid_lbl = QLabel("Key points  —  click ▶ Run to test each snippet locally")
        self._code_grid_lbl.setObjectName("featureLabel")
        self._code_grid_lbl.setVisible(False)
        lay.addWidget(self._code_grid_lbl)

        # Expandable key-point rows container
        self._code_rows_widget = QWidget()
        self._code_rows_widget.setObjectName("tabPage")
        self._code_rows_lay = QVBoxLayout(self._code_rows_widget)
        self._code_rows_lay.setContentsMargins(0, 0, 0, 0)
        self._code_rows_lay.setSpacing(6)
        self._code_rows_lay.addStretch()
        lay.addWidget(self._code_rows_widget)

        lay.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        return frame

    # ── Analysis ──────────────────────────────────────────────────────────────

    def _clear_code(self):
        self._code_input.clear()
        self._code_summary_lbl.setVisible(False)
        self._code_grid_lbl.setVisible(False)
        while self._code_rows_lay.count() > 1:
            item = self._code_rows_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _run_code_analyse(self):
        code = self._code_input.toPlainText().strip()
        if not code:
            return
        items   = self._extract_code_items(code)
        overall = self._overall_code_summary(code, items)
        self._code_summary_lbl.setText(f"<b>Overview:</b> {overall}")
        self._code_summary_lbl.setVisible(True)

        # Clear old rows
        while self._code_rows_lay.count() > 1:
            item = self._code_rows_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lang = self._code_lang.currentText()
        for i, item in enumerate(items, start=1):
            row = _CodeKeyPointRow(i, item, lang, self)
            self._code_rows_lay.insertWidget(self._code_rows_lay.count() - 1, row)

        self._code_grid_lbl.setVisible(True)

        # Fire async AI overview (enriches the summary label when ready)
        self._run_code_ai_overview(code, lang, overall)

    def _run_code_ai_overview(self, code: str, lang: str, local_summary: str):
        """Asynchronously fetch an AI-generated one-line overview of the code."""
        from gui.pages._ai_caller import call_ai, get_api_keys, best_provider

        keys = get_api_keys(self)
        if not best_provider("code", keys):
            return  # No key — keep local summary

        class _OvSignals(QObject):
            done = pyqtSignal(str)

        class _OvThread(QThread):
            def __init__(self, code, lang, mixin, signals):
                super().__init__()
                self._code = code; self._lang = lang
                self._mixin = mixin; self._signals = signals

            def run(self):
                system = (
                    "You are a senior code reviewer. "
                    "Write a single concise sentence (max 20 words) describing what this code does. "
                    "No bullet points, no markdown, just one plain sentence."
                )
                snippet = self._code[:1500] + ("…" if len(self._code) > 1500 else "")
                prompt  = f"Language: {self._lang}\n\nCode:\n{snippet}"
                result  = call_ai("code", prompt, self._mixin, system)
                self._signals.done.emit(result)

        self._ov_signals = _OvSignals()
        self._ov_signals.done.connect(
            lambda r: self._code_summary_lbl.setText(
                f"<b>Overview:</b> {local_summary} — {r}"
            )
        )
        self._ov_thread = _OvThread(code, lang, self, self._ov_signals)
        self._ov_thread.start()

    def _extract_code_items(self, code: str) -> list[dict]:
        lang = getattr(self, "_code_lang", None)
        lang_name = lang.currentText().lower() if lang else "python"
        items: list[dict] = []

        # ── C / C++ ───────────────────────────────────────────────────────
        if any(x in lang_name for x in ("c++", "c", "cpp")):
            for line in code.splitlines():
                s = line.strip()
                # #include
                m = re.match(r'^#include\s*[<"](.+?)[>"]', s)
                if m:
                    lib = m.group(1)
                    items.append({
                        "name": lib, "role": "include / header",
                        "syntax": s,
                        "how": f"Includes the '{lib}' standard library header.",
                        "purpose": f"Gives access to functions/classes in <{lib}>.",
                        "usage": s,
                        "sample": f'#include <{lib}>\n\nint main() {{\n    // use {lib} here\n    return 0;\n}}',
                    })
                    continue
                # function definition  e.g.  int main() {  or  void foo(int x) {
                m = re.match(r'^(?:[\w:*&<>]+\s+)+(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?\{?', s)
                if m and m.group(1) not in ("if", "while", "for", "switch", "catch"):
                    fname, params = m.group(1), m.group(2).strip()
                    items.append({
                        "name": fname, "role": "function",
                        "syntax": s.rstrip("{").strip(),
                        "how": f"Callable block — call as {fname}(…).",
                        "purpose": "Performs a specific task.",
                        "usage": f"{fname}({params})",
                        "sample": (
                            f'#include <iostream>\nusing namespace std;\n\n'
                            f'int {fname}() {{\n    // TODO\n    return 0;\n}}\n\n'
                            f'int main() {{\n    {fname}();\n    return 0;\n}}'
                        ),
                    })
                    continue
                # class
                m = re.match(r'^class\s+(\w+)', s)
                if m:
                    cname = m.group(1)
                    items.append({
                        "name": cname, "role": "class",
                        "syntax": f"class {cname} {{ … }};",
                        "how": "Defines a C++ class — blueprint for objects.",
                        "purpose": f"Encapsulates data and methods as '{cname}'.",
                        "usage": f"{cname} obj;",
                        "sample": (
                            f'#include <iostream>\nusing namespace std;\n\n'
                            f'class {cname} {{\npublic:\n    void hello() {{\n'
                            f'        cout << "Hello from {cname}" << endl;\n    }}\n}};\n\n'
                            f'int main() {{\n    {cname} obj;\n    obj.hello();\n    return 0;\n}}'
                        ),
                    })
                    continue
                # cout / printf statement — treat as a runnable snippet
                if re.search(r'cout\s*<<|printf\s*\(|std::cout', s):
                    items.append({
                        "name": "output statement", "role": "statement",
                        "syntax": s,
                        "how": "Prints output to the console.",
                        "purpose": "Displays a value or message.",
                        "usage": s,
                        "sample": (
                            f'#include <iostream>\nusing namespace std;\n\n'
                            f'int main() {{\n    {s}\n    return 0;\n}}'
                        ),
                    })
                    continue
            # If nothing matched, wrap the whole snippet as one runnable item
            if not items:
                items.append({
                    "name": "snippet", "role": "code block",
                    "syntax": code.splitlines()[0].strip(),
                    "how": "A block of C++ code.",
                    "purpose": "Runs the pasted code.",
                    "usage": "—",
                    "sample": (
                        f'#include <iostream>\nusing namespace std;\n\n'
                        f'int main() {{\n    {code.strip()}\n    return 0;\n}}'
                        if "main" not in code else code
                    ),
                })
            return items[:30]

        # ── Java / Kotlin ─────────────────────────────────────────────────
        if any(x in lang_name for x in ("java", "kotlin")):
            for line in code.splitlines():
                s = line.strip()
                m = re.match(r'^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?class\s+(\w+)', s)
                if m:
                    cname = m.group(1)
                    items.append({
                        "name": cname, "role": "class",
                        "syntax": s, "how": "Defines a Java/Kotlin class.",
                        "purpose": f"Blueprint for '{cname}' objects.",
                        "usage": f"{cname} obj = new {cname}();",
                        "sample": f'public class {cname} {{\n    public static void main(String[] args) {{\n        System.out.println("Hello from {cname}");\n    }}\n}}',
                    })
                    continue
                m = re.match(r'^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(([^)]*)\)', s)
                if m and m.group(1) not in ("if", "while", "for", "switch"):
                    fname = m.group(1)
                    items.append({
                        "name": fname, "role": "method",
                        "syntax": s, "how": f"Method called as {fname}(…).",
                        "purpose": "Performs a task.", "usage": f"{fname}()",
                        "sample": s,
                    })
                    continue
                m = re.match(r'^import\s+(.+);?', s)
                if m:
                    items.append({
                        "name": m.group(1).split(".")[-1], "role": "import",
                        "syntax": s, "how": "Imports a Java package/class.",
                        "purpose": f"Makes '{m.group(1)}' available.",
                        "usage": s, "sample": s,
                    })
            return items[:30]

        # ── HTML ──────────────────────────────────────────────────────────
        if "html" in lang_name:
            for line in code.splitlines():
                s = line.strip()
                # Tags
                m = re.match(r'^<(\w[\w.-]*)([^>]*)>', s)
                if m:
                    tag, attrs_str = m.group(1), m.group(2)
                    if tag.lower() in ("html", "head", "body", "div", "span",
                                       "p", "h1", "h2", "h3", "ul", "li",
                                       "a", "img", "form", "input", "button",
                                       "table", "tr", "td", "th", "script",
                                       "style", "link", "meta", "nav", "section",
                                       "article", "header", "footer", "main"):
                        id_m = re.search(r'id=["\'](\w+)["\']', attrs_str)
                        cls_m = re.search(r'class=["\']([^"\']+)["\']', attrs_str)
                        label = id_m.group(1) if id_m else (cls_m.group(1).split()[0] if cls_m else tag)
                        items.append({
                            "name": label, "role": f"<{tag}> element",
                            "syntax": s[:80],
                            "how": f"The <{tag}> tag defines a {tag} element in the page.",
                            "purpose": f"Renders a {tag} block in the HTML document.",
                            "usage": f"<{tag}>{('</' + tag + '>') if tag not in ('img','input','meta','link','br','hr') else ''}",
                            "sample": f"<!DOCTYPE html>\n<html>\n<body>\n  {s}\n</body>\n</html>",
                        })
            if not items:
                items.append({
                    "name": "HTML document", "role": "markup",
                    "syntax": code.splitlines()[0].strip(),
                    "how": "HTML defines the structure of a web page.",
                    "purpose": "Rendered by a browser to display content.",
                    "usage": "Open in a browser.",
                    "sample": code,
                })
            return items[:30]

        # ── CSS ───────────────────────────────────────────────────────────
        if "css" in lang_name:
            # Match selectors: .class, #id, element, or combinations
            for m in re.finditer(r'([.#]?[\w][\w\s,.-]*?)\s*\{([^}]*)\}', code, re.DOTALL):
                selector = m.group(1).strip()
                body = m.group(2).strip()
                props = [p.strip() for p in body.split(";") if ":" in p]
                prop_names = ", ".join(p.split(":")[0].strip() for p in props[:3])
                items.append({
                    "name": selector, "role": "CSS rule",
                    "syntax": f"{selector} {{ {prop_names}{'…' if len(props) > 3 else ''} }}",
                    "how": f"Applies styles to elements matching '{selector}'.",
                    "purpose": f"Sets: {prop_names}.",
                    "usage": f'<element class="{selector.lstrip(".")}">…</element>',
                    "sample": (
                        f"<!DOCTYPE html>\n<html><head><style>\n{selector} {{\n"
                        + "\n".join(f"  {p};" for p in props) +
                        f"\n}}\n</style></head><body>\n"
                        f'<p class="{selector.lstrip(".")}">Styled text</p>\n'
                        f"</body></html>"
                    ),
                })
            if not items:
                items.append({
                    "name": "CSS styles", "role": "stylesheet",
                    "syntax": code.splitlines()[0].strip(),
                    "how": "CSS controls the visual presentation of HTML elements.",
                    "purpose": "Styles the page layout, colours, and typography.",
                    "usage": "Link via <link rel='stylesheet'> or <style> tag.",
                    "sample": code,
                })
            return items[:30]

        # ── Swift ─────────────────────────────────────────────────────────
        if "swift" in lang_name:
            for line in code.splitlines():
                s = line.strip()
                m = re.match(r'^(?:public\s+|private\s+|internal\s+|open\s+)?(?:final\s+)?class\s+(\w+)', s)
                if m:
                    cname = m.group(1)
                    items.append({
                        "name": cname, "role": "class",
                        "syntax": s, "how": "Defines a Swift class.",
                        "purpose": f"Blueprint for '{cname}' objects.",
                        "usage": f"let obj = {cname}()",
                        "sample": f'class {cname} {{\n    init() {{\n        print("Hello from {cname}")\n    }}\n}}\n\nlet obj = {cname}()',
                    })
                    continue
                m = re.match(r'^struct\s+(\w+)', s)
                if m:
                    sname = m.group(1)
                    items.append({
                        "name": sname, "role": "struct",
                        "syntax": s, "how": "Defines a Swift value type.",
                        "purpose": f"Lightweight data container '{sname}'.",
                        "usage": f"var s = {sname}()",
                        "sample": f'struct {sname} {{\n    var value: Int = 0\n}}\n\nvar s = {sname}()\nprint(s.value)',
                    })
                    continue
                m = re.match(r'^(?:func|override func)\s+(\w+)\s*\(([^)]*)\)', s)
                if m:
                    fname, params = m.group(1), m.group(2)
                    items.append({
                        "name": fname, "role": "function",
                        "syntax": s, "how": f"Swift function called as {fname}(…).",
                        "purpose": "Performs a task.", "usage": f"{fname}()",
                        "sample": f'func {fname}({params}) {{\n    print("{fname} called")\n}}\n\n{fname}()',
                    })
                    continue
                m = re.match(r'^(?:let|var)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(.+)', s)
                if m:
                    vname, val = m.group(1), m.group(2)[:60]
                    items.append({
                        "name": vname, "role": "variable / constant",
                        "syntax": s, "how": "Declares a Swift variable or constant.",
                        "purpose": f"Stores value: {val}.", "usage": vname,
                        "sample": f'let {vname} = {val}\nprint({vname})',
                    })
            if not items:
                items.append({
                    "name": "snippet", "role": "Swift code",
                    "syntax": code.splitlines()[0].strip(),
                    "how": "A block of Swift code.", "purpose": "Runs the pasted code.",
                    "usage": "—", "sample": code,
                })
            return items[:30]

        # ── Dart / Flutter ────────────────────────────────────────────────
        if "dart" in lang_name or "flutter" in lang_name:
            for line in code.splitlines():
                s = line.strip()
                m = re.match(r'^(?:abstract\s+)?class\s+(\w+)', s)
                if m:
                    cname = m.group(1)
                    items.append({
                        "name": cname, "role": "class",
                        "syntax": s, "how": "Defines a Dart class.",
                        "purpose": f"Blueprint for '{cname}' objects.",
                        "usage": f"var obj = {cname}();",
                        "sample": f'class {cname} {{\n  {cname}() {{\n    print("Hello from {cname}");\n  }}\n}}\n\nvoid main() {{\n  var obj = {cname}();\n}}',
                    })
                    continue
                m = re.match(r'^(?:void|int|String|bool|double|List|Map|\w+)\s+(\w+)\s*\(([^)]*)\)', s)
                if m and m.group(1) not in ("if", "while", "for", "switch"):
                    fname, params = m.group(1), m.group(2)
                    items.append({
                        "name": fname, "role": "function",
                        "syntax": s, "how": f"Dart function called as {fname}(…).",
                        "purpose": "Performs a task.", "usage": f"{fname}()",
                        "sample": f'void {fname}({params}) {{\n  print("{fname} called");\n}}\n\nvoid main() {{\n  {fname}();\n}}',
                    })
                    continue
                m = re.match(r'^(?:var|final|const)\s+(\w+)\s*=\s*(.+)', s)
                if m:
                    vname, val = m.group(1), m.group(2).rstrip(";")[:60]
                    items.append({
                        "name": vname, "role": "variable",
                        "syntax": s, "how": "Declares a Dart variable.",
                        "purpose": f"Stores: {val}.", "usage": vname,
                        "sample": f'void main() {{\n  var {vname} = {val};\n  print({vname});\n}}',
                    })
                m = re.match(r'^import\s+[\'"](.+)[\'"]', s)
                if m:
                    pkg = m.group(1)
                    items.append({
                        "name": pkg.split("/")[-1].replace(".dart", ""), "role": "import",
                        "syntax": s, "how": f"Imports '{pkg}' package.",
                        "purpose": f"Makes '{pkg}' available.", "usage": s, "sample": s,
                    })
            if not items:
                items.append({
                    "name": "snippet", "role": "Dart code",
                    "syntax": code.splitlines()[0].strip(),
                    "how": "A block of Dart code.", "purpose": "Runs the pasted code.",
                    "usage": "—", "sample": code,
                })
            return items[:30]

        # ── JavaScript / TypeScript / React / Vue / Angular / Next.js ─────
        if any(x in lang_name for x in ("javascript", "typescript", "react", "vue", "angular", "next")):
            for line in code.splitlines():
                s = line.strip()
                m = re.match(r'^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', s)
                if m:
                    fname, params = m.group(1), m.group(2)
                    items.append({
                        "name": fname, "role": "function",
                        "syntax": s, "how": f"JS function called as {fname}(…).",
                        "purpose": "Performs a task.", "usage": f"{fname}()",
                        "sample": f'function {fname}({params}) {{\n    console.log("{fname} called");\n}}\n\n{fname}();',
                    })
                    continue
                m = re.match(r'^(?:export\s+)?(?:default\s+)?class\s+(\w+)', s)
                if m:
                    cname = m.group(1)
                    items.append({
                        "name": cname, "role": "class",
                        "syntax": s, "how": "ES6 class definition.",
                        "purpose": f"Blueprint for '{cname}'.",
                        "usage": f"const obj = new {cname}();",
                        "sample": f'class {cname} {{\n    constructor() {{\n        console.log("{cname} created");\n    }}\n}}\n\nconst obj = new {cname}();',
                    })
                    continue
                m = re.match(r'^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>', s)
                if m:
                    fname, params = m.group(1), m.group(2)
                    items.append({
                        "name": fname, "role": "arrow function",
                        "syntax": s, "how": "Arrow function expression.",
                        "purpose": f"Callable as {fname}(…).",
                        "usage": f"{fname}()",
                        "sample": f'const {fname} = ({params}) => {{\n    console.log("{fname} called");\n}};\n\n{fname}();',
                    })
                    continue
                m = re.match(r'^import\s+.+\s+from\s+[\'"](.+)[\'"]', s)
                if m:
                    mod = m.group(1)
                    items.append({
                        "name": mod, "role": "import",
                        "syntax": s, "how": f"Imports from '{mod}'.",
                        "purpose": f"Makes '{mod}' exports available.",
                        "usage": s, "sample": s,
                    })
            return items[:30]

        # ── SQL / MySQL / NoSQL ───────────────────────────────────────────
        if any(x in lang_name for x in ("sql", "mysql", "nosql", "mongo")):
            full_code = code.strip()
            # Split on semicolons to get individual statements
            statements = [s.strip() for s in re.split(r';', full_code) if s.strip()]
            if not statements:
                statements = [full_code]
            for stmt in statements:
                first_line = stmt.splitlines()[0].strip().upper()
                # Detect statement type
                m_create = re.match(r'CREATE\s+TABLE\s+(\w+)', stmt, re.IGNORECASE)
                m_select = re.match(r'SELECT\s+.+\s+FROM\s+(\w+)', stmt, re.IGNORECASE)
                m_insert = re.match(r'INSERT\s+INTO\s+(\w+)', stmt, re.IGNORECASE)
                m_update = re.match(r'UPDATE\s+(\w+)', stmt, re.IGNORECASE)
                m_delete = re.match(r'DELETE\s+FROM\s+(\w+)', stmt, re.IGNORECASE)
                m_alter  = re.match(r'ALTER\s+TABLE\s+(\w+)', stmt, re.IGNORECASE)
                m_drop   = re.match(r'DROP\s+TABLE\s+(\w+)', stmt, re.IGNORECASE)

                if m_create:
                    tname = m_create.group(1)
                    items.append({
                        "name": tname, "role": "CREATE TABLE",
                        "syntax": stmt.splitlines()[0],
                        "how": f"Creates a new table '{tname}' in the database.",
                        "purpose": f"Defines the schema/structure for '{tname}'.",
                        "usage": f"CREATE TABLE {tname} (...);",
                        "sample": (
                            f"import sqlite3\nconn = sqlite3.connect(':memory:')\ncur = conn.cursor()\n"
                            f"cur.executescript(\"\"\"\n{stmt};\n\"\"\")\n"
                            f"cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")\n"
                            f"print('Tables:', cur.fetchall())\nconn.close()"
                        ),
                    })
                elif m_select:
                    tname = m_select.group(1)
                    items.append({
                        "name": tname, "role": "SELECT query",
                        "syntax": stmt.splitlines()[0],
                        "how": "Retrieves rows from a table.",
                        "purpose": f"Fetches data from '{tname}'.",
                        "usage": stmt,
                        "sample": (
                            f"import sqlite3\nconn = sqlite3.connect(':memory:')\ncur = conn.cursor()\n"
                            f"cur.execute(\"CREATE TABLE IF NOT EXISTS {tname} (id INTEGER PRIMARY KEY, name TEXT)\")\n"
                            f"cur.execute(\"INSERT INTO {tname} VALUES (1, 'Alice')\")\n"
                            f"cur.execute(\"{stmt.replace(chr(10), ' ')}\")\n"
                            f"print(cur.fetchall())\nconn.close()"
                        ),
                    })
                elif m_insert:
                    tname = m_insert.group(1)
                    items.append({
                        "name": tname, "role": "INSERT INTO",
                        "syntax": stmt.splitlines()[0],
                        "how": "Inserts a new row into a table.",
                        "purpose": f"Adds data to '{tname}'.",
                        "usage": stmt,
                        "sample": (
                            f"import sqlite3\nconn = sqlite3.connect(':memory:')\ncur = conn.cursor()\n"
                            f"cur.execute(\"CREATE TABLE IF NOT EXISTS {tname} (id INTEGER, name TEXT)\")\n"
                            f"cur.execute(\"{stmt.replace(chr(10), ' ')}\")\n"
                            f"conn.commit()\ncur.execute('SELECT * FROM {tname}')\n"
                            f"print(cur.fetchall())\nconn.close()"
                        ),
                    })
                elif m_update:
                    tname = m_update.group(1)
                    items.append({
                        "name": tname, "role": "UPDATE",
                        "syntax": stmt.splitlines()[0],
                        "how": "Modifies existing rows in a table.",
                        "purpose": f"Updates data in '{tname}'.",
                        "usage": stmt, "sample": stmt,
                    })
                elif m_delete:
                    tname = m_delete.group(1)
                    items.append({
                        "name": tname, "role": "DELETE FROM",
                        "syntax": stmt.splitlines()[0],
                        "how": "Removes rows from a table.",
                        "purpose": f"Deletes data from '{tname}'.",
                        "usage": stmt, "sample": stmt,
                    })
                elif m_alter:
                    tname = m_alter.group(1)
                    items.append({
                        "name": tname, "role": "ALTER TABLE",
                        "syntax": stmt.splitlines()[0],
                        "how": "Modifies an existing table structure.",
                        "purpose": f"Changes schema of '{tname}'.",
                        "usage": stmt, "sample": stmt,
                    })
                elif m_drop:
                    tname = m_drop.group(1)
                    items.append({
                        "name": tname, "role": "DROP TABLE",
                        "syntax": stmt.splitlines()[0],
                        "how": "Permanently removes a table.",
                        "purpose": f"Deletes '{tname}' and all its data.",
                        "usage": stmt, "sample": stmt,
                    })
                else:
                    # Generic statement
                    items.append({
                        "name": first_line.split()[0] if first_line else "statement",
                        "role": "SQL statement",
                        "syntax": stmt.splitlines()[0],
                        "how": "Executes a SQL command.",
                        "purpose": "Performs a database operation.",
                        "usage": stmt, "sample": stmt,
                    })
            return items[:30]

        # ── Python (default) ──────────────────────────────────────────────
        for line in code.splitlines():
            s = line.strip()
            m = re.match(r'^(?:from\s+(\S+)\s+)?import\s+(.+)', s)
            if m:
                module = m.group(1) or ""
                names  = m.group(2).split(",")[0].strip().split(" as ")[0].strip()
                items.append({
                    "name": names, "role": f"import from {module}" if module else "import",
                    "syntax": s, "how": "Loads an external module or symbol.",
                    "purpose": f"Makes '{names}' available.", "usage": s,
                    "sample": s,
                })
                continue
            m = re.match(r'^class\s+(\w+)\s*(?:\(([^)]*)\))?:', s)
            if m:
                cname, bases = m.group(1), m.group(2) or "object"
                items.append({
                    "name": cname, "role": f"class  (inherits: {bases})",
                    "syntax": f"class {cname}({bases}):",
                    "how": "Defines a blueprint for creating objects.",
                    "purpose": f"Encapsulates data and behaviour as '{cname}'.",
                    "usage": f"obj = {cname}()",
                    "sample": f"class {cname}({bases}):\n    pass\n\nobj = {cname}()\nprint(obj)",
                })
                continue
            m = re.match(r'^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)', s)
            if m:
                fname, params = m.group(1), m.group(2).strip()
                kind = "method" if params.startswith("self") else "function"
                call_params = ", ".join(
                    "None" for p in params.split(",")
                    if p.strip() and p.strip() != "self"
                ) if params else ""
                items.append({
                    "name": fname, "role": kind,
                    "syntax": f"def {fname}({params}):",
                    "how": f"Callable block invoked as {fname}(…).",
                    "purpose": "Performs a specific task.",
                    "usage": f"{fname}({call_params})",
                    "sample": (
                        f"def {fname}({params}):\n"
                        f"    # TODO: implement\n"
                        f"    pass\n\n"
                        f"result = {fname}({call_params})\n"
                        f"print(result)"
                    ),
                })
                continue
            m = re.match(r'^([A-Z_][A-Z0-9_]{2,})\s*=\s*(.+)', s)
            if m:
                vname, val = m.group(1), m.group(2)[:60]
                items.append({
                    "name": vname, "role": "constant / config",
                    "syntax": f"{vname} = {val}",
                    "how": "Module-level name bound to a fixed value.",
                    "purpose": f"Stores '{val}' for reuse.", "usage": vname,
                    "sample": f"{vname} = {val}\nprint({vname})",
                })
        return items[:30]

    def _overall_code_summary(self, code: str, items: list[dict]) -> str:
        n_lines   = len([l for l in code.splitlines() if l.strip()])
        classes   = [i for i in items if "class"    in i["role"]]
        functions = [i for i in items if i["role"]  in ("function", "method")]
        imports   = [i for i in items if "import"   in i["role"]]
        constants = [i for i in items if "constant" in i["role"]]
        parts = [f"{n_lines} lines"]
        if classes:
            parts.append(f"{len(classes)} class{'es' if len(classes)>1 else ''} "
                         f"({', '.join(c['name'] for c in classes[:3])})")
        if functions:
            parts.append(f"{len(functions)} function/method{'s' if len(functions)>1 else ''}")
        if imports:
            parts.append(f"{len(imports)} import{'s' if len(imports)>1 else ''}")
        if constants:
            parts.append(f"{len(constants)} constant{'s' if len(constants)>1 else ''}")
        return "  ·  ".join(parts) + "."


# ══════════════════════════════════════════════════════════════════════════════
# Expandable key-point row with inline IDE playground
# ══════════════════════════════════════════════════════════════════════════════

class _CodeKeyPointRow(QWidget):
    """
    One key-point row:
      Collapsed  — shows #, name, role, ▶ Run button
      Expanded   — shows explanation + editable code editor + output panel
    Click the header to toggle expand/collapse.
    ▶ Run executes the sample code locally without expanding.
    """

    def __init__(self, index: int, item: dict, lang: str, mixin, parent=None):
        super().__init__(parent)
        self._item     = item
        self._lang     = lang
        self._mixin    = mixin
        self._expanded = False
        self._thread: QThread | None = None

        self.setObjectName("expandableRow")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("expandableRowHeader")
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(10, 7, 10, 7)
        h_lay.setSpacing(8)

        self._toggle_lbl = QLabel("▶")
        self._toggle_lbl.setFixedWidth(14)
        self._toggle_lbl.setStyleSheet("color: #888; font-size: 10px; background: transparent;")
        h_lay.addWidget(self._toggle_lbl)

        num_lbl = QLabel(str(index))
        num_lbl.setFixedWidth(22)
        num_lbl.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        h_lay.addWidget(num_lbl)

        name_lbl = QLabel(item["name"])
        name_lbl.setObjectName("cardTitle")
        name_lbl.setMinimumWidth(60)
        name_lbl.setMaximumWidth(160)
        name_lbl.setWordWrap(False)
        name_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        h_lay.addWidget(name_lbl)

        role_lbl = QLabel(item["role"])
        role_lbl.setObjectName("cardBody")
        role_lbl.setStyleSheet("font-size: 12px;")
        role_lbl.setWordWrap(False)
        h_lay.addWidget(role_lbl, 1)

        # ▶ Run button — runs without expanding
        self._run_btn = QPushButton("▶  Run")
        self._run_btn.setObjectName("btnPrimary")
        self._run_btn.setFixedSize(70, 26)
        self._run_btn.clicked.connect(self._run_sample)
        h_lay.addWidget(self._run_btn)

        root.addWidget(header)
        header.mousePressEvent = lambda _: self._toggle()

        # ── Expanded body ─────────────────────────────────────────────────
        self._body = QWidget()
        self._body.setObjectName("expandableRowBody")
        self._body.setVisible(False)
        b_lay = QVBoxLayout(self._body)
        b_lay.setContentsMargins(14, 8, 14, 12)
        b_lay.setSpacing(8)

        # Explanation with Read button
        explain_text = (
            f"Syntax: {item.get('syntax','—')}\n"
            f"How it works: {item.get('how','—')}\n"
            f"Purpose: {item.get('purpose','—')}"
        )
        explain_html = (
            f"<b>Syntax:</b> <code style='color:#ce9178'>{item.get('syntax','—')}</code><br>"
            f"<b>How it works:</b> {item.get('how','—')}<br>"
            f"<b>Purpose:</b> {item.get('purpose','—')}"
        )
        explain_lbl = QLabel(explain_html)
        explain_lbl.setObjectName("cardBody")
        explain_lbl.setWordWrap(True)
        explain_lbl.setTextFormat(Qt.TextFormat.RichText)
        explain_lbl.setStyleSheet("font-size: 12px;")
        b_lay.addWidget(explain_lbl)

        # Read button — reads explanation aloud (not code)
        read_row = QHBoxLayout()
        read_row.setContentsMargins(0, 0, 0, 0)
        read_row.addStretch()
        read_btn = QPushButton("▶  Read")
        read_btn.setObjectName("btnOutline")
        read_btn.setFixedSize(80, 26)
        read_btn.setToolTip("Let Veaja read this explanation aloud")
        read_btn.clicked.connect(lambda _=False, t=explain_text: self._read_aloud(t))
        read_row.addWidget(read_btn)
        b_lay.addLayout(read_row)

        # Syntax-highlighted code preview
        code_preview = QLabel()
        code_preview.setTextFormat(Qt.TextFormat.RichText)
        code_preview.setWordWrap(False)
        code_preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sample = item.get("sample", item.get("usage", ""))
        code_preview.setText(_highlight_python(sample))
        b_lay.addWidget(code_preview)

        # ── Nested sub-points ─────────────────────────────────────────────
        sub_points = self._build_sub_points(item)
        if sub_points:
            sub_lbl = QLabel("Sub-points:")
            sub_lbl.setObjectName("featureLabel")
            sub_lbl.setStyleSheet("font-size: 11px; margin-top: 4px;")
            b_lay.addWidget(sub_lbl)
            for sp_title, sp_body in sub_points:
                sp_row = _SubPointRow(sp_title, sp_body, mixin)
                b_lay.addWidget(sp_row)

        # Code editor label row
        editor_hdr = QHBoxLayout()
        editor_hdr.setContentsMargins(0, 4, 0, 0)
        editor_lbl = QLabel("Edit & run sample:")
        editor_lbl.setObjectName("featureLabel")
        editor_lbl.setStyleSheet("font-size: 11px;")
        editor_hdr.addWidget(editor_lbl)
        editor_hdr.addStretch()

        run_full_btn = QPushButton("▶  Run")
        run_full_btn.setObjectName("btnPrimary")
        run_full_btn.setFixedSize(70, 26)
        run_full_btn.clicked.connect(self._run_sample)
        editor_hdr.addWidget(run_full_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("btnOutline")
        reset_btn.setFixedSize(60, 26)
        reset_btn.clicked.connect(self._reset_sample)
        editor_hdr.addWidget(reset_btn)
        b_lay.addLayout(editor_hdr)

        # Code editor
        self._editor = QTextEdit()
        self._editor.setObjectName("codeEdit")
        self._editor.setFixedHeight(110)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(mono)
        self._editor.setPlainText(sample)
        _CodeHighlighter(self._editor.document(), lang)
        b_lay.addWidget(self._editor)

        # Output panel
        out_hdr = QHBoxLayout()
        out_hdr.setContentsMargins(0, 4, 0, 0)
        out_lbl = QLabel("Output:")
        out_lbl.setObjectName("featureLabel")
        out_lbl.setStyleSheet("font-size: 11px;")
        out_hdr.addWidget(out_lbl)
        out_hdr.addStretch()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size: 11px; background: transparent;")
        out_hdr.addWidget(self._status_lbl)
        b_lay.addLayout(out_hdr)

        self._output = QTextEdit()
        self._output.setObjectName("codeEdit")
        self._output.setReadOnly(True)
        self._output.setFixedHeight(80)
        self._output.setFont(mono)
        self._output.setPlaceholderText("Run the code to see output here…")
        b_lay.addWidget(self._output)

        # ── Ask Q&A ───────────────────────────────────────────────────────
        ask_sep = QLabel("Ask about this point:")
        ask_sep.setObjectName("featureLabel")
        ask_sep.setStyleSheet("font-size: 11px; margin-top: 4px;")
        b_lay.addWidget(ask_sep)

        ask_row = QHBoxLayout()
        ask_row.setSpacing(6)
        self._ask_input = QTextEdit()
        self._ask_input.setObjectName("featureEdit")
        self._ask_input.setPlaceholderText("e.g. Why use this? What does this parameter do?")
        self._ask_input.setFixedHeight(50)
        ask_row.addWidget(self._ask_input, 1)

        ask_btn = QPushButton("Ask")
        ask_btn.setObjectName("btnPrimary")
        ask_btn.setFixedSize(56, 50)
        ask_btn.clicked.connect(self._ask_about)
        ask_row.addWidget(ask_btn)
        b_lay.addLayout(ask_row)

        self._answer_lbl = QLabel("")
        self._answer_lbl.setObjectName("cardBody")
        self._answer_lbl.setWordWrap(True)
        self._answer_lbl.setStyleSheet("font-size: 12px; padding: 6px; border-radius: 6px;")
        self._answer_lbl.setVisible(False)
        b_lay.addWidget(self._answer_lbl)

        root.addWidget(self._body)

    # ── Toggle ────────────────────────────────────────────────────────────────

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._toggle_lbl.setText("▼" if self._expanded else "▶")

    # ── Run ───────────────────────────────────────────────────────────────────

    def _run_sample(self):
        code = self._editor.toPlainText().strip() if self._expanded \
               else self._item.get("sample", self._item.get("usage", ""))
        if not code:
            return

        # Show output panel if collapsed
        if not self._expanded:
            self._toggle()

        self._run_btn.setEnabled(False)
        self._run_btn.setText("…")
        self._status_lbl.setText("Running…")
        self._status_lbl.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
        self._output.setPlainText("")

        signals = _RunSignals()
        signals.finished.connect(self._on_run_finished)
        self._thread = _RunThread(code, self._lang, signals)
        self._thread.start()

    def _on_run_finished(self, stdout: str, stderr: str):
        self._run_btn.setEnabled(True)
        self._run_btn.setText("▶  Run")

        if stderr and not stdout:
            self._output.setPlainText(stderr)
            self._status_lbl.setText("✗ Error")
            self._status_lbl.setStyleSheet(
                "color: #e53935; font-size: 11px; background: transparent;"
            )
        else:
            combined = stdout
            if stderr:
                combined += f"\n--- stderr ---\n{stderr}"
            self._output.setPlainText(combined or "(no output)")
            self._status_lbl.setText("✓ Done")
            self._status_lbl.setStyleSheet(
                "color: #4caf50; font-size: 11px; background: transparent;"
            )

    def _reset_sample(self):
        self._editor.setPlainText(self._item.get("sample", self._item.get("usage", "")))
        self._output.clear()
        self._status_lbl.setText("")

    def _read_aloud(self, text: str):
        try:
            self._mixin.read_requested.emit(text)
        except Exception:
            pass

    def _ask_about(self):
        question = self._ask_input.toPlainText().strip()
        if not question:
            return
        item = self._item
        self._answer_lbl.setText("Thinking…")
        self._answer_lbl.setVisible(True)

        from gui.pages._ai_caller import call_ai
        from PyQt6.QtCore import QThread, QObject, pyqtSignal as _sig

        class _S(QObject):
            done = _sig(str)
        class _T(QThread):
            def __init__(self, q, i, m, s):
                super().__init__(); self._q=q; self._i=i; self._m=m; self._s=s
            def run(self):
                system = (
                    "You are a code expert. Answer questions about specific code elements clearly. "
                    "Be concise and practical."
                )
                prompt = (
                    f"Code element: {self._i['name']} ({self._i['role']})\n"
                    f"Syntax: {self._i.get('syntax','—')}\n\n"
                    f"Question: {self._q}"
                )
                self._s.done.emit(call_ai("code", prompt, self._m, system))

        self._ask_signals = _S()
        self._ask_signals.done.connect(lambda r: (
            self._answer_lbl.setText(r),
            self._answer_lbl.setVisible(True)
        ))
        self._ask_thread2 = _T(question, item, self._mixin, self._ask_signals)
        self._ask_thread2.start()

    def _build_sub_points(self, item: dict) -> list[tuple[str, str]]:
        """Generate nested sub-points for a code item."""
        role = item.get("role", "")
        name = item.get("name", "")
        sub = []
        if "class" in role:
            sub = [
                ("Constructor (__init__)",
                 f"The __init__ method initialises a new {name} instance. "
                 f"Called automatically when you do {name}()."),
                ("Inheritance",
                 f"Inheriting from a base class lets {name} reuse its methods and attributes. "
                 f"Use super() to call the parent's methods."),
                ("Instance vs Class attributes",
                 "Instance attributes (self.x) belong to each object. "
                 "Class attributes are shared across all instances."),
            ]
        elif role in ("function", "method"):
            sub = [
                ("Parameters",
                 f"Parameters are the inputs to {name}. "
                 "They let you pass different values each time you call the function."),
                ("Return value",
                 f"{name} can return a value using 'return'. "
                 "If no return statement, it returns None."),
                ("Scope",
                 "Variables defined inside a function are local — "
                 "they don't exist outside the function."),
            ]
        elif "import" in role:
            sub = [
                ("Why import?",
                 f"Importing {name} gives you access to code written by others "
                 "without rewriting it yourself."),
                ("Aliasing",
                 f"You can alias: 'import {name} as x' to use a shorter name."),
            ]
        elif "constant" in role:
            sub = [
                ("Convention",
                 "ALL_CAPS names signal to other developers that this value should not change."),
                ("Usage",
                 f"Reference {name} by name throughout your code instead of repeating the value."),
            ]
        return sub


# ── Nested sub-point row ──────────────────────────────────────────────────────

class _SubPointRow(QWidget):
    """A collapsible nested sub-point inside a key-point row."""

    def __init__(self, title: str, body: str, mixin, parent=None):
        super().__init__(parent)
        self._mixin    = mixin
        self._expanded = False
        self.setObjectName("expandableRow")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setObjectName("expandableRowHeader")
        hdr.setCursor(Qt.CursorShape.PointingHandCursor)
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(8, 5, 8, 5)
        h_lay.setSpacing(6)

        self._arrow = QLabel("▷")
        self._arrow.setFixedWidth(12)
        self._arrow.setStyleSheet("color: #666; font-size: 9px; background: transparent;")
        h_lay.addWidget(self._arrow)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardBody")
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        title_lbl.setWordWrap(True)
        h_lay.addWidget(title_lbl, 1)

        # Read sub-point
        read_btn = QPushButton("▶")
        read_btn.setObjectName("btnOutline")
        read_btn.setFixedSize(26, 22)
        read_btn.setToolTip("Read aloud")
        read_btn.clicked.connect(lambda _=False, t=body: self._read(t))
        h_lay.addWidget(read_btn)

        root.addWidget(hdr)
        hdr.mousePressEvent = lambda _: self._toggle()

        # Body
        self._body_lbl = QLabel(body)
        self._body_lbl.setObjectName("cardBody")
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setStyleSheet(
            "font-size: 11px; padding: 6px 8px 6px 22px;"
        )
        self._body_lbl.setVisible(False)
        root.addWidget(self._body_lbl)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body_lbl.setVisible(self._expanded)
        self._arrow.setText("▽" if self._expanded else "▷")

    def _read(self, text: str):
        try:
            self._mixin.read_requested.emit(text)
        except Exception:
            pass

# ── Syntax highlighter ────────────────────────────────────────────────────────

def _highlight_python(code: str) -> str:
    """Convert Python code to HTML with VS Code-style syntax colouring."""
    import html as _h
    import re as _re

    KEYWORDS = {
        "False","None","True","and","as","assert","async","await",
        "break","class","continue","def","del","elif","else","except",
        "finally","for","from","global","if","import","in","is",
        "lambda","nonlocal","not","or","pass","raise","return","try",
        "while","with","yield",
    }
    BUILTINS = {
        "print","len","range","type","int","str","float","list","dict",
        "set","tuple","bool","open","input","super","self","cls",
        "enumerate","zip","map","filter","sorted","reversed","any","all",
        "min","max","sum","abs","round","isinstance","hasattr","getattr",
        "setattr","staticmethod","classmethod","property",
    }

    # Colours (VS Code Dark+ palette)
    C_KW      = "#569cd6"   # blue   — keywords
    C_BUILTIN = "#dcdcaa"   # yellow — builtins
    C_STR     = "#ce9178"   # orange — strings
    C_COMMENT = "#6a9955"   # green  — comments
    C_NUM     = "#b5cea8"   # light green — numbers
    C_DECO    = "#c586c0"   # purple — decorators
    C_CLASS   = "#4ec9b0"   # teal   — class names
    C_FUNC    = "#dcdcaa"   # yellow — function names
    C_DEFAULT = "#d4d4d4"   # light grey — default text

    lines_out = []
    for line in code.splitlines():
        # Comment
        stripped = line.lstrip()
        if stripped.startswith("#"):
            lines_out.append(
                f'<span style="color:{C_COMMENT}">{_h.escape(line)}</span>'
            )
            continue

        # Decorator
        if stripped.startswith("@"):
            lines_out.append(
                f'<span style="color:{C_DECO}">{_h.escape(line)}</span>'
            )
            continue

        # Tokenise the line
        tokens = _re.split(r'(\s+|[^\w\s])', line)
        out = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if not tok:
                i += 1
                continue
            # String literals (simple single/double quote)
            if tok in ('"', "'"):
                quote = tok
                s = quote
                i += 1
                while i < len(tokens):
                    s += tokens[i]
                    if tokens[i] == quote:
                        i += 1
                        break
                    i += 1
                out.append(f'<span style="color:{C_STR}">{_h.escape(s)}</span>')
                continue
            # Number
            if _re.fullmatch(r'\d+\.?\d*', tok):
                out.append(f'<span style="color:{C_NUM}">{_h.escape(tok)}</span>')
            # Keyword
            elif tok in KEYWORDS:
                out.append(f'<span style="color:{C_KW};font-weight:600">{_h.escape(tok)}</span>')
            # Builtin / function name after def
            elif tok in BUILTINS:
                out.append(f'<span style="color:{C_BUILTIN}">{_h.escape(tok)}</span>')
            else:
                out.append(f'<span style="color:{C_DEFAULT}">{_h.escape(tok)}</span>')
            i += 1
        lines_out.append("".join(out))

    bg = "#1e1e1e"
    body = "<br>".join(lines_out)
    return (
        f'<div style="background:{bg};padding:10px 14px;border-radius:6px;'
        f'font-family:Consolas,monospace;font-size:11pt;line-height:1.6;">'
        f'{body}</div>'
    )
