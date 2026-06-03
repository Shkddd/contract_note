"""Generate AI-annotated versions of reviewed contracts (PDF/DOCX)."""

import os
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from .db import get_db


def get_review_with_annotations(doc_id: int) -> Optional[dict]:
    """Fetch a completed review with all annotations for a document."""
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not doc:
        return None
    doc = dict(doc)

    review = db.execute(
        "SELECT * FROM reviews WHERE doc_id = ? AND status = 'completed' ORDER BY id DESC LIMIT 1",
        (doc_id,),
    ).fetchone()
    if not review:
        return None
    review = dict(review)

    annotations = [
        dict(r) for r in db.execute(
            "SELECT a.*, c.content as clause_content, c.clause_index "
            "FROM annotations a "
            "JOIN clauses c ON c.id = a.clause_id "
            "WHERE c.doc_id = ? "
            "ORDER BY c.clause_index",
            (doc_id,),
        ).fetchall()
    ]

    clauses = [
        dict(r) for r in db.execute(
            "SELECT * FROM clauses WHERE doc_id = ? ORDER BY clause_index",
            (doc_id,),
        ).fetchall()
    ]

    return {
        "doc": doc,
        "review": review,
        "annotations": annotations,
        "clauses": clauses,
    }


_RISK_COLORS = {
    "高": "#E53935",
    "中": "#FB8C00",
    "低": "#43A047",
}
_RISK_COLORS_HEX = {
    "高": "E53935",
    "中": "FB8C00",
    "低": "43A047",
}
_MATCH_LABELS = {
    "conflict": "[冲突]",
    "matched": "[匹配]",
    "missing": "[缺失]",
}

_RISK_COLORS = {"高": (200, 60, 60), "中": (200, 160, 40), "低": (60, 160, 60)}
_RISK_COLORS_HEX = {"高": "c83c3c", "中": "c8a028", "低": "3ca03c"}


def export_annotated_pdf(data: dict, output_path: str) -> str:
    """Generate an annotated PDF with clause-by-clause review results."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_font("Songti", "", "/System/Library/Fonts/Supplemental/Songti.ttc")
    pdf.add_font("SongtiBold", "", "/System/Library/Fonts/Supplemental/Songti.ttc")
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Title Page ──
    pdf.add_page()
    pdf.set_font("Songti", "", 22)
    pdf.ln(50)
    pdf.cell(0, 14, "合同智能审核批注版", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)
    pdf.set_font("Songti", "", 12)
    pdf.cell(0, 8, data["doc"]["original_name"], new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    pdf.set_font("Songti", "", 10)
    info_lines = [
        f"审核时间: {data['review']['created_at']}",
        f"条款总数: {data['review']['total_clauses']} 条",
        f"高风险: {data['review']['high_risk']} · 中风险: {data['review']['medium_risk']} · 低风险: {data['review']['low_risk']}",
        f"匹配: {data['review']['matched']} · 冲突: {data['review']['conflicted']} · 缺失: {data['review']['missing_info']}",
    ]
    for line in info_lines:
        pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT", align="C")

    # ── Legend ──
    pdf.ln(10)
    pdf.set_font("Songti", "", 10)
    pdf.cell(0, 7, "图例:", new_x="LMARGIN", new_y="NEXT")
    for level, color, label in [
        ("高", "E53935", "高风险"),
        ("中", "FB8C00", "中风险"),
        ("低", "43A047", "低风险"),
    ]:
        pdf.set_fill_color(int(color[:2], 16), int(color[2:4], 16), int(color[4:], 16))
        pdf.cell(8, 6, "", border=0, fill=True)
        pdf.cell(4)
        pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")

    # ── Annotations Index ──
    pdf.add_page()
    pdf.set_font("Songti", "", 14)
    pdf.cell(0, 10, "批注意见总览", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for ann in data["annotations"]:
        risk = ann["risk_level"]
        r, g_, b = int(_RISK_COLORS_HEX[risk][:2], 16), int(_RISK_COLORS_HEX[risk][2:4], 16), int(
            _RISK_COLORS_HEX[risk][4:], 16
        )
        pdf.set_fill_color(r, g_, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Songti", "", 9)
        tag = f"[{risk}] {_MATCH_LABELS.get(ann['match_type'], ann['match_type'])}"
        tw = pdf.get_string_width(tag) + 4
        pdf.cell(tw, 6, tag, fill=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.cell(2)
        pdf.set_font("Songti", "", 9)
        pdf.cell(0, 6, f"条款{ann['clause_index']} — {ann['kb_title']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Songti", "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 5, ann["comment"][:120] + ("..." if len(ann["comment"]) > 120 else ""))
        pdf.ln(1)

    # ── Clause-by-Clause Review ──
    pdf.add_page()
    pdf.set_font("Songti", "", 14)
    pdf.cell(0, 10, "逐条审核详情", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    clause_annotations = {}
    for ann in data["annotations"]:
        ci = ann["clause_index"]
        clause_annotations.setdefault(ci, []).append(ann)

    for clause in data["clauses"]:
        ci = clause["clause_index"]
        anns = clause_annotations.get(ci, [])

        # Check if we need a new page (rough estimate)
        if pdf.get_y() > 220:
            pdf.add_page()

        pdf.set_fill_color(240, 240, 248)
        pdf.set_draw_color(200, 200, 220)
        pdf.set_line_width(0.5)
        y_start = pdf.get_y()
        pdf.rect(10, y_start, 190, 10)

        pdf.set_text_color(50, 50, 80)
        pdf.set_font("Songti", "", 11)
        pdf.set_xy(14, y_start + 1)
        pdf.cell(0, 8, f"条款 {ci}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Songti", "", 9)
        clause_text = clause["content"].strip()
        for line in clause_text.split("\n"):
            if pdf.get_y() > 265:
                pdf.add_page()
            pdf.multi_cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Annotations for this clause
        if anns:
            for ann in anns:
                risk = ann["risk_level"]
                r, g_, b = int(_RISK_COLORS_HEX[risk][:2], 16), int(
                    _RISK_COLORS_HEX[risk][2:4], 16
                ), int(_RISK_COLORS_HEX[risk][4:], 16)

                if pdf.get_y() > 250:
                    pdf.add_page()

                # Annotation callout
                pdf.set_fill_color(r, g_, b)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Songti", "", 9)
                tag = f"  {_MATCH_LABELS.get(ann['match_type'], ann['match_type'])}  |  {risk}风险  "
                tw = pdf.get_string_width(tag) + 4
                pdf.cell(tw, 6, tag, fill=True)

                pdf.set_text_color(80, 80, 80)
                pdf.set_font("Songti", "", 8)
                pdf.cell(0, 6, f"  参考: {ann['kb_title']}", new_x="LMARGIN", new_y="NEXT")

                # Comment
                pdf.set_text_color(60, 60, 60)
                pdf.set_font("Songti", "", 8)
                pdf.multi_cell(0, 4.5, ann["comment"], new_x="LMARGIN", new_y="NEXT")

                # Suggestion
                pdf.set_text_color(40, 80, 140)
                pdf.set_font("Songti", "", 8)
                if ann.get("suggestion"):
                    pdf.multi_cell(0, 4.5, f"建议: {ann['suggestion']}", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
        else:
            pdf.set_text_color(100, 180, 100)
            pdf.set_font("Songti", "", 9)
            pdf.cell(0, 6, "  ✅ 此条款无异常", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

    pdf.output(str(output_path))
    return output_path


def export_annotated_docx(data: dict, output_path: str) -> str:
    """Generate an annotated DOCX with colored highlights and comments."""
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import copy

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Songti SC"
    style.font.size = Pt(10.5)
    style.paragraph_format.line_spacing = 1.2

    # ── Title ──
    p = doc.add_heading("合同智能审核批注版", level=1)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(data["doc"]["original_name"])
    run.font.size = Pt(12)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run(
        f"审核时间: {data['review']['created_at']}  "
        f"高: {data['review']['high_risk']}  "
        f"中: {data['review']['medium_risk']}  "
        f"低: {data['review']['low_risk']}"
    )
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph("─" * 60)

    # ── Summary ──
    doc.add_heading("审核概览", level=2)
    summary = doc.add_paragraph()
    run = summary.add_run(
        f"共 {data['review']['total_clauses']} 条条款 · "
        f"匹配 {data['review']['matched']} · "
        f"冲突 {data['review']['conflicted']} · "
        f"缺失: {data['review']['missing_info']}"
    )

    doc.add_heading("批注意见", level=2)

    clause_annotations = {}
    for ann in data["annotations"]:
        clause_annotations.setdefault(ann["clause_index"], []).append(ann)

    for clause in data["clauses"]:
        ci = clause["clause_index"]
        anns = clause_annotations.get(ci, [])

        # Clause heading
        p = doc.add_paragraph()
        run = p.add_run(f"条款 {ci}")
        run.bold = True
        run.font.size = Pt(11)

        # Clause content
        clause_text = clause["content"].strip()
        for line in clause_text.split("\n"):
            p = doc.add_paragraph(line, style="Normal")
            p.paragraph_format.left_indent = Cm(0.5)

        # Annotation section
        if anns:
            for ann in anns:
                risk = ann["risk_level"]
                if risk == "高":
                    r, g, b_val = 229, 57, 53
                elif risk == "中":
                    r, g, b_val = 251, 140, 0
                else:
                    r, g, b_val = 67, 160, 71

                # Risk tag
                p = doc.add_paragraph()
                run = p.add_run(f"[{risk}] {_MATCH_LABELS.get(ann['match_type'], ann['match_type'])}")
                run.bold = True
                run.font.color.rgb = RGBColor(r, g, b_val)
                run.font.size = Pt(9)

                # KB reference
                run2 = p.add_run(f"  参考: {ann['kb_title']}")
                run2.font.size = Pt(9)
                run2.font.color.rgb = RGBColor(100, 100, 100)

                # Comment
                p = doc.add_paragraph(ann["comment"])
                p.paragraph_format.left_indent = Cm(0.5)
                for run in p.runs:
                    run.font.size = Pt(9)
                    run.font.color.rgb = RGBColor(60, 60, 60)

                # Suggestion
                if ann.get("suggestion"):
                    p = doc.add_paragraph(ann["suggestion"])
                    p.paragraph_format.left_indent = Cm(0.5)
                    for run in p.runs:
                        run.font.size = Pt(9)
                        run.font.color.rgb = RGBColor(40, 80, 140)
        else:
            p = doc.add_paragraph()
            run = p.add_run("✅ 此条款无异常")
            run.font.color.rgb = RGBColor(67, 160, 71)
            run.font.size = Pt(9)

        doc.add_paragraph("─" * 40)  # separator

    doc.save(str(output_path))
    return output_path


def export_annotated(doc_id: int, output_dir: str) -> dict:
    """Generate annotated document. Returns {filepath, filename, mime}."""
    data = get_review_with_annotations(doc_id)
    if not data:
        return {"error": "未找到审核结果"}

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = data["doc"]["file_type"]
    orig_name = Path(data["doc"]["original_name"]).stem
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if ext == "pdf":
        out_path = str(out_dir / f"{orig_name}_批注版_{ts}.pdf")
        export_annotated_pdf(data, out_path)
        return {
            "filepath": out_path,
            "filename": f"{orig_name}_批注版.pdf",
            "mime": "application/pdf",
        }
    elif ext == "docx":
        out_path = str(out_dir / f"{orig_name}_批注版_{ts}.docx")
        export_annotated_docx(data, out_path)
        return {
            "filepath": out_path,
            "filename": f"{orig_name}_批注版.docx",
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
    else:
        return {"error": f"不支持的文件类型: {ext}"}
