"""gui/pages/_tab_generate.py — Generate tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QApplication
)
from PyQt6.QtCore import Qt

from gui.pages._flow_layout import FlowLayout as _FlowLayout


class GenerateTabMixin:
    """Generate tab builder and all generation/export logic."""

    _GEN_DESCRIPTIONS = [
        "Create a visual poster layout with headline, body and call-to-action.",
        "Write an AI prompt optimised for image or text generation models.",
        "Produce step-by-step instructions or a how-to guide.",
        "Write a short social-media caption with hashtags.",
        "Rewrite or adjust the tone, length or style of existing text.",
        "Generate a multi-slide presentation outline (title + bullet points per slide).",
        "Generate a video script with scenes, narration and on-screen text.",
        "Generate a self-contained mini web page as raw HTML + CSS.",
    ]

    def _build_generate_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(10)

        # Sub-mode bar (wraps to 2 rows)
        mode_bar = QWidget()
        mode_bar.setObjectName("subTabBar")
        mb_lay = _FlowLayout(mode_bar, h_spacing=6, v_spacing=6)
        mb_lay.setContentsMargins(0, 4, 0, 4)

        self._gen_modes = ["Poster", "Prompt", "Instruction", "Caption", "Adjust",
                           "Slide", "Video", "HTML"]
        self._gen_mode_btns: list[QPushButton] = []
        for i, label in enumerate(self._gen_modes):
            btn = QPushButton(label)
            btn.setObjectName("subTabBtn")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(label) + 28)
            btn.clicked.connect(lambda _=False, idx=i: self._switch_gen_mode(idx))
            mb_lay.addWidget(btn)
            self._gen_mode_btns.append(btn)
        lay.addWidget(mode_bar)

        # Input area
        input_card = QWidget()
        input_card.setObjectName("featureBox")
        ic_lay = QVBoxLayout(input_card)
        ic_lay.setContentsMargins(0, 0, 0, 0)
        ic_lay.setSpacing(6)

        self._gen_mode_desc = QLabel(self._gen_mode_description(0))
        self._gen_mode_desc.setObjectName("featureLabel")
        self._gen_mode_desc.setWordWrap(True)
        ic_lay.addWidget(self._gen_mode_desc)

        self._gen_text_input = QTextEdit()
        self._gen_text_input.setObjectName("featureEdit")
        self._gen_text_input.setPlaceholderText(
            "Describe what you want to generate, or paste text / URL here…"
        )
        self._gen_text_input.setFixedHeight(100)
        ic_lay.addWidget(self._gen_text_input)

        # Attachment row
        attach_row = QHBoxLayout()
        attach_row.setSpacing(8)
        attach_row.setContentsMargins(0, 0, 0, 0)
        attach_lbl = QLabel("Attach:")
        attach_lbl.setObjectName("featureLabel")
        attach_row.addWidget(attach_lbl)
        for icon, tip, slot in [
            ("🖼", "Image (jpg/png/webp)", self._gen_attach_image),
            ("📄", "PDF document",         self._gen_attach_pdf),
            ("📁", "Folder",               self._gen_attach_folder),
            ("🔗", "URL / Link",           self._gen_attach_url),
        ]:
            btn = QPushButton(f"{icon}  {tip.split()[0]}")
            btn.setObjectName("btnOutline")
            btn.setFixedHeight(28)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            attach_row.addWidget(btn)
        attach_row.addStretch()
        ic_lay.addLayout(attach_row)

        self._gen_attachments: list[str] = []
        self._gen_attach_lbl = QLabel("")
        self._gen_attach_lbl.setObjectName("settingsLabel")
        self._gen_attach_lbl.setWordWrap(True)
        self._gen_attach_lbl.setStyleSheet("font-size: 11px;")
        self._gen_attach_lbl.setVisible(False)
        ic_lay.addWidget(self._gen_attach_lbl)
        lay.addWidget(input_card)

        # Generate button row
        gen_row = QHBoxLayout()
        gen_row.setContentsMargins(0, 0, 0, 0)
        gen_row.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(80, 30)
        clear_btn.clicked.connect(self._clear_generate)
        gen_row.addWidget(clear_btn)
        gen_btn = QPushButton("Generate")
        gen_btn.setObjectName("btnPrimary")
        gen_btn.setFixedSize(110, 30)
        gen_btn.clicked.connect(self._run_generate)
        gen_row.addWidget(gen_btn)
        lay.addLayout(gen_row)

        # Output
        self._gen_out_lbl = QLabel("Output")
        self._gen_out_lbl.setObjectName("featureLabel")
        self._gen_out_lbl.setVisible(False)
        lay.addWidget(self._gen_out_lbl)

        self._gen_output = QTextEdit()
        self._gen_output.setObjectName("featureEditReadOnly")
        self._gen_output.setReadOnly(True)
        self._gen_output.setPlaceholderText("Generated content will appear here…")
        self._gen_output.setVisible(False)
        lay.addWidget(self._gen_output, 1)

        # Export row (wraps to 2 rows)
        self._gen_export_row = QWidget()
        self._gen_export_row.setVisible(False)
        er_lay = _FlowLayout(self._gen_export_row, h_spacing=6, v_spacing=6)
        er_lay.setContentsMargins(0, 4, 0, 4)

        er_lay.addWidget(QLabel("Export as:", objectName="featureLabel"))

        for label, icon, slot in [
            ("Copy",    "📋", self._gen_export_copy),
            ("PDF",     "📄", self._gen_export_pdf),
            ("DOCX",    "📝", self._gen_export_docx),
            ("JPG",     "🖼", self._gen_export_jpg),
            ("PNG",     "🖼", self._gen_export_png),
            ("PPTX",    "📊", self._gen_export_pptx),
            ("HTML",    "🌐", self._gen_export_html),
            ("QR Code", "⬛", self._gen_export_qr),
        ]:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("btnOutline")
            btn.setFixedHeight(30)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(f"{icon}  {label}") + 28)
            btn.clicked.connect(slot)
            er_lay.addWidget(btn)

        self._gen_preview_btn = QPushButton("🔍  Preview in browser")
        self._gen_preview_btn.setObjectName("btnPrimary")
        self._gen_preview_btn.setFixedHeight(30)
        self._gen_preview_btn.setVisible(False)
        self._gen_preview_btn.clicked.connect(self._gen_preview_html)
        er_lay.addWidget(self._gen_preview_btn)
        lay.addWidget(self._gen_export_row)
        return frame

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _gen_mode_description(self, idx: int) -> str:
        return self._GEN_DESCRIPTIONS[idx] if idx < len(self._GEN_DESCRIPTIONS) else ""

    def _switch_gen_mode(self, idx: int):
        for i, btn in enumerate(self._gen_mode_btns):
            btn.setChecked(i == idx)
        self._gen_mode_desc.setText(self._gen_mode_description(idx))

    def _current_gen_mode(self) -> str:
        for i, btn in enumerate(self._gen_mode_btns):
            if btn.isChecked():
                return self._gen_modes[i]
        return "Poster"

    def _update_attach_label(self):
        if self._gen_attachments:
            self._gen_attach_lbl.setText("Attached: " + "  ·  ".join(self._gen_attachments))
            self._gen_attach_lbl.setVisible(True)
        else:
            self._gen_attach_lbl.setVisible(False)

    def _gen_attach_image(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(None, "Attach image", "",
                                              "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif)")
        if path:
            self._gen_attachments.append(path)
            self._update_attach_label()

    def _gen_attach_pdf(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(None, "Attach PDF", "", "PDF (*.pdf)")
        if path:
            self._gen_attachments.append(path)
            self._update_attach_label()

    def _gen_attach_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(None, "Attach folder")
        if path:
            self._gen_attachments.append(path + "/")
            self._update_attach_label()

    def _gen_attach_url(self):
        from PyQt6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(None, "Attach URL", "Enter URL:")
        if ok and url.strip():
            self._gen_attachments.append(url.strip())
            self._update_attach_label()

    def _clear_generate(self):
        self._gen_text_input.clear()
        self._gen_attachments.clear()
        self._update_attach_label()
        self._gen_output.clear()
        self._gen_output.setVisible(False)
        self._gen_out_lbl.setVisible(False)
        self._gen_export_row.setVisible(False)

    def _run_generate(self):
        text = self._gen_text_input.toPlainText().strip()
        mode = self._current_gen_mode()
        if not text and not self._gen_attachments:
            return
        result = self._generate_content(mode, text, self._gen_attachments)
        self._gen_output.setPlainText(result)
        self._gen_output.setVisible(True)
        self._gen_out_lbl.setVisible(True)
        self._gen_export_row.setVisible(True)
        if hasattr(self, "_gen_preview_btn"):
            self._gen_preview_btn.setVisible(mode == "HTML")

    def _generate_content(self, mode: str, text: str, attachments: list) -> str:
        attach_note = (
            "\n\nAttached sources:\n" + "\n".join(f"  • {a}" for a in attachments)
            if attachments else ""
        )
        templates = {
            "Poster": (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  HEADLINE\n  {text[:60] or 'Your headline here'}\n\n"
                f"  BODY\n  {text or 'Describe your message here.'}\n\n"
                f"  CALL TO ACTION\n  Learn more → yourlink.com\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            "Prompt": (
                f"You are a helpful assistant.\n\nTask: {text or 'Describe the task.'}\n\n"
                f"Requirements:\n- Be concise and clear\n- Use structured output\n"
                f"- Tone: professional\n\nOutput format: [specify format here]"
            ),
            "Instruction": (
                f"# How to: {text[:50] or 'Your topic'}\n\n"
                f"## Prerequisites\n- Item 1\n- Item 2\n\n"
                f"## Steps\n1. First step — {text[:80] or 'describe step 1'}\n"
                f"2. Second step\n3. Third step\n\n## Notes\n- Tip or warning here."
            ),
            "Caption": f"{text[:120] or 'Your caption here.'} ✨\n\n#YourBrand #Topic #Trending",
            "Adjust": (
                f"[Adjusted version of your text]\n\n"
                f"{text or 'Paste text above to adjust its tone, length or style.'}\n\n"
                f"— Connect an AI API key in My API Key to enable live adjustment."
            ),
            "Slide": self._gen_slide_template(text),
            "Video": self._gen_video_template(text),
            "HTML":  self._gen_html_template(text),
        }
        return templates.get(mode, text) + attach_note

    # ── Export ────────────────────────────────────────────────────────────────

    def _gen_export_copy(self):
        text = self._gen_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _gen_export_pdf(self):   self._gen_save_file("PDF (*.pdf)", ".pdf", self._write_pdf)
    def _gen_export_docx(self):  self._gen_save_file("Word Document (*.docx)", ".docx", self._write_docx)
    def _gen_export_jpg(self):   self._gen_save_file("JPEG Image (*.jpg)", ".jpg", self._write_image_jpg)
    def _gen_export_png(self):   self._gen_save_file("PNG Image (*.png)", ".png", self._write_image_png)
    def _gen_export_pptx(self):  self._gen_save_file("PowerPoint (*.pptx)", ".pptx", self._write_pptx)
    def _gen_export_qr(self):    self._gen_save_file("PNG Image (*.png)", ".png", self._write_qr)
    def _gen_export_html(self):  self._gen_save_file("HTML File (*.html)", ".html", self._write_html)

    def _gen_save_file(self, filter_str: str, ext: str, writer):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(None, "Export", f"generated{ext}", filter_str)
        if path:
            try:
                writer(path)
            except Exception as e:
                QMessageBox.warning(None, "Export failed", str(e))

    def _write_pdf(self, path: str):
        from PyQt6.QtGui import QTextDocument
        from PyQt6.QtPrintSupport import QPrinter
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc = QTextDocument()
        doc.setPlainText(self._gen_output.toPlainText())
        doc.print(printer)

    def _write_docx(self, path: str):
        try:
            from docx import Document
            doc = Document()
            for line in self._gen_output.toPlainText().splitlines():
                doc.add_paragraph(line)
            doc.save(path)
        except ImportError:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._gen_output.toPlainText())

    def _write_image_jpg(self, path: str): self._render_output_image(path, "JPEG")
    def _write_image_png(self, path: str): self._render_output_image(path, "PNG")

    def _render_output_image(self, path: str, fmt: str):
        from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor
        from PyQt6.QtCore import QRect
        lines = self._gen_output.toPlainText().splitlines()
        W, line_h, pad = 800, 22, 30
        H = max(pad * 2 + len(lines) * line_h + 20, 200)
        px = QPixmap(W, H)
        px.fill(QColor("#ffffff"))
        p = QPainter(px)
        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor("#1a1a1a"))
        y = pad
        for line in lines:
            p.drawText(QRect(pad, y, W - pad * 2, line_h), Qt.AlignmentFlag.AlignLeft, line)
            y += line_h
        p.end()
        px.save(path, fmt)

    def _write_pptx(self, path: str):
        try:
            from pptx import Presentation
            prs = Presentation()
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = self._current_gen_mode()
            slide.placeholders[1].text_frame.text = self._gen_output.toPlainText()[:500]
            prs.save(path)
        except ImportError:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._gen_output.toPlainText())

    def _write_qr(self, path: str):
        try:
            import qrcode
            qrcode.make(self._gen_output.toPlainText()[:300]).save(path)
        except ImportError:
            self._render_output_image(path, "PNG")

    def _write_html(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._gen_output.toPlainText())

    def _gen_preview_html(self):
        import tempfile
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8")
        tmp.write(self._gen_output.toPlainText())
        tmp.close()
        QDesktopServices.openUrl(QUrl.fromLocalFile(tmp.name))

    # ── Templates ─────────────────────────────────────────────────────────────

    def _gen_slide_template(self, text: str) -> str:
        title = text[:60] or "Presentation Title"
        return (
            f"SLIDE 1 — Title\n  Title:    {title}\n  Subtitle: Your subtitle here\n\n"
            f"SLIDE 2 — Introduction\n  • What is this about?\n  • Why does it matter?\n\n"
            f"SLIDE 3 — Key Point 1\n  • {text[:80] or 'First key point'}\n  • Supporting detail\n\n"
            f"SLIDE 4 — Key Point 2\n  • Second key point\n  • Supporting detail\n\n"
            f"SLIDE 5 — Key Point 3\n  • Third key point\n  • Supporting detail\n\n"
            f"SLIDE 6 — Summary\n  • Recap of main points\n  • Call to action\n\n"
            f"SLIDE 7 — Thank You\n  Contact: your@email.com\n\n"
            f"— Connect an AI API key to generate real slide content."
        )

    def _gen_video_template(self, text: str) -> str:
        title = text[:50] or "Video Title"
        return (
            f"VIDEO SCRIPT — {title}\n{'─'*50}\n\n"
            f"[SCENE 1 — Hook  |  0:00–0:10]\n"
            f"  ON SCREEN:  \"{title}\"\n"
            f"  NARRATION:  \"Did you know that {text[:60] or '...'}?\"\n"
            f"  MUSIC:      Upbeat intro\n\n"
            f"[SCENE 2 — Problem  |  0:10–0:30]\n"
            f"  ON SCREEN:  Problem statement\n  NARRATION:  \"Many people struggle with...\"\n\n"
            f"[SCENE 3 — Solution  |  0:30–1:00]\n"
            f"  ON SCREEN:  Step-by-step breakdown\n  NARRATION:  \"Here's how to solve it...\"\n\n"
            f"[SCENE 4 — Demo  |  1:00–1:30]\n"
            f"  ON SCREEN:  Screen recording\n  NARRATION:  \"Let me show you exactly how...\"\n\n"
            f"[SCENE 5 — CTA  |  1:30–1:45]\n"
            f"  ON SCREEN:  Subscribe button\n  NARRATION:  \"Like and subscribe!\"\n\n"
            f"— Connect an AI API key to generate a real video script."
        )

    def _gen_html_template(self, text: str) -> str:
        title = text[:50] or "My Page"
        body  = text or "Add your content here."
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"  <title>{title}</title>\n"
            "  <style>\n"
            "    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n"
            "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;\n"
            "           background: #f8f9fa; color: #1a1a1a; line-height: 1.7; }\n"
            "    header { background: #1a1a1a; color: #fff; padding: 2rem; text-align: center; }\n"
            "    header h1 { font-size: 2rem; font-weight: 700; }\n"
            "    main { max-width: 800px; margin: 3rem auto; padding: 0 1.5rem; }\n"
            "    section { background: #fff; border-radius: 12px; padding: 2rem;\n"
            "              margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,.06); }\n"
            "    h2 { font-size: 1.3rem; margin-bottom: 1rem; }\n"
            "    .cta { display: inline-block; margin-top: 1.5rem; background: #1a1a1a;\n"
            "           color: #fff; padding: .75rem 2rem; border-radius: 8px;\n"
            "           text-decoration: none; font-weight: 600; }\n"
            "    footer { text-align: center; padding: 2rem; color: #999; font-size: .85rem; }\n"
            "  </style>\n</head>\n<body>\n"
            f"  <header><h1>{title}</h1><p>Generated by Veaja</p></header>\n"
            "  <main>\n"
            f"    <section><h2>About</h2><p>{body}</p>"
            "<a class=\"cta\" href=\"#\">Get Started</a></section>\n"
            "    <section><h2>Features</h2>"
            "<p>• Feature one<br>• Feature two<br>• Feature three</p></section>\n"
            "    <section><h2>Contact</h2><p>your@email.com</p></section>\n"
            "  </main>\n"
            f"  <footer>© 2025 {title}. All rights reserved.</footer>\n"
            "</body>\n</html>"
        )
