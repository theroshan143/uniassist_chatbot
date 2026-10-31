"""
Generate PDF and DOCX deliverables for HCLTech platform submission.
Creates:
- docs/Project_Report.pdf & docs/Project_Report.docx
- docs/Ethical_Compliance_Declaration.pdf & docs/Ethical_Compliance_Declaration.docx
- docs/Architecture_Document.pdf & docs/Architecture_Document.docx
"""

import os
import re
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
SUBMISSION_DIR = ROOT_DIR / "submission_files"
SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

def md_to_docx(md_path: Path, docx_path: Path, title: str):
    """Convert Markdown document into professional Word docx format."""
    print(f"Creating DOCX: {docx_path.name}...")
    doc = Document()
    
    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_code_block = False
    for line in lines:
        line_str = line.rstrip()
        
        # Code blocks
        if line_str.startswith("```"):
            in_code_block = not in_code_block
            continue
            
        if in_code_block:
            p = doc.add_paragraph(line_str if line_str else " ")
            if p.runs:
                p.runs[0].font.name = 'Consolas'
                p.runs[0].font.size = Pt(9.5)
            continue

        if not line_str:
            continue

        # Headers
        if line_str.startswith("# "):
            h = doc.add_heading(line_str[2:], level=1)
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(6)
        elif line_str.startswith("## "):
            h = doc.add_heading(line_str[3:], level=2)
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(4)
        elif line_str.startswith("### "):
            h = doc.add_heading(line_str[4:], level=3)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(3)
        elif line_str.startswith("- ") or line_str.startswith("* "):
            doc.add_paragraph(line_str[2:], style='List Bullet')
        elif re.match(r"^\d+\.\s", line_str):
            clean_text = re.sub(r"^\d+\.\s", "", line_str)
            doc.add_paragraph(clean_text, style='List Number')
        elif line_str.startswith("> "):
            p = doc.add_paragraph(line_str[2:])
            p.paragraph_format.left_indent = Inches(0.4)
            p.runs[0].font.italic = True
        elif line_str.startswith("|") and line_str.endswith("|"):
            # Simple table row representation
            if "---" in line_str:
                continue
            cols = [c.strip() for c in line_str.split("|")[1:-1]]
            doc.add_paragraph(" | ".join(cols))
        else:
            # Normal paragraph
            # Strip markdown bold/italics markers for clean text
            clean_str = re.sub(r"\*\*(.*?)\*\*", r"\1", line_str)
            clean_str = re.sub(r"\*(.*?)\*", r"\1", clean_str)
            clean_str = re.sub(r"`(.*?)`", r"\1", clean_str)
            doc.add_paragraph(clean_str)

    doc.save(docx_path)
    print(f"Saved: {docx_path}")

def md_to_pdf(md_path: Path, pdf_path: Path):
    """Convert Markdown document into professional PDF using ReportLab."""
    print(f"Creating PDF: {pdf_path.name}...")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=14,
        spaceAfter=6
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2d3748'),
        spaceBefore=10,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=16,
        spaceAfter=4
    )
    
    code_style = ParagraphStyle(
        'Code',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        leftIndent=20,
        textColor=colors.HexColor('#4a5568')
    )

    story = []
    
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_code = False
    for line in lines:
        line_str = line.rstrip()
        
        if line_str.startswith("```"):
            in_code = not in_code
            continue
            
        if in_code:
            safe_str = line_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_str if safe_str else " ", code_style))
            continue
            
        if not line_str:
            story.append(Spacer(1, 4))
            continue
            
        if line_str.startswith("# "):
            story.append(Paragraph(line_str[2:], title_style))
        elif line_str.startswith("## "):
            story.append(Paragraph(line_str[3:], h1_style))
        elif line_str.startswith("### "):
            story.append(Paragraph(line_str[4:], h2_style))
        elif line_str.startswith("- ") or line_str.startswith("* "):
            safe_text = line_str[2:].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe_text)
            story.append(Paragraph(f"• {safe_text}", bullet_style))
        elif re.match(r"^\d+\.\s", line_str):
            clean_text = re.sub(r"^\d+\.\s", "", line_str)
            safe_text = clean_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe_text)
            story.append(Paragraph(safe_text, bullet_style))
        elif line_str.startswith("---"):
            story.append(Spacer(1, 8))
        elif line_str.startswith("|") and line_str.endswith("|"):
            if "---" in line_str:
                continue
            cols = [c.strip() for c in line_str.split("|")[1:-1]]
            safe_cols = [c.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for c in cols]
            story.append(Paragraph(" | ".join(safe_cols), body_style))
        else:
            safe_text = line_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe_text)
            safe_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", safe_text)
            story.append(Paragraph(safe_text, body_style))

    doc.build(story)
    print(f"Saved: {pdf_path}")

def main():
    print("=" * 60)
    print("  Building All Platform Submission Documents")
    print("=" * 60)
    
    # 1. Project Report
    md_to_docx(ROOT_DIR / "PROJECT_REPORT.md", SUBMISSION_DIR / "Project_Report.docx", "Project Report")
    md_to_pdf(ROOT_DIR / "PROJECT_REPORT.md", SUBMISSION_DIR / "Project_Report.pdf")
    
    # 2. Ethical Compliance Declaration
    md_to_docx(DOCS_DIR / "Ethical_Compliance_Declaration.md", SUBMISSION_DIR / "Ethical_Compliance_Declaration.docx", "Ethical Compliance Declaration")
    md_to_pdf(DOCS_DIR / "Ethical_Compliance_Declaration.md", SUBMISSION_DIR / "Ethical_Compliance_Declaration.pdf")
    
    # 3. Architecture Document
    md_to_docx(ROOT_DIR / "ARCHITECTURE.md", SUBMISSION_DIR / "Architecture_Document.docx", "System Architecture")
    md_to_pdf(ROOT_DIR / "ARCHITECTURE.md", SUBMISSION_DIR / "Architecture_Document.pdf")

    # 4. Software Requirements Specification (SRS)
    md_to_docx(DOCS_DIR / "SRS.md", SUBMISSION_DIR / "SRS.docx", "Software Requirements Specification")
    md_to_pdf(DOCS_DIR / "SRS.md", SUBMISSION_DIR / "SRS.pdf")

    # 4. Copy dataset.csv and data_dictionary.csv to submission folder
    import shutil
    shutil.copy2(ROOT_DIR / "data" / "dataset.csv", SUBMISSION_DIR / "dataset.csv")
    shutil.copy2(ROOT_DIR / "data" / "data_dictionary.csv", SUBMISSION_DIR / "data_dictionary.csv")
    shutil.copy2(ROOT_DIR / "eda" / "EDA_Report.pdf", SUBMISSION_DIR / "EDA_Report.pdf")

    print(f"\nAll deliverables compiled cleanly into: {SUBMISSION_DIR.resolve()}")
    for f in os.listdir(SUBMISSION_DIR):
        size_kb = os.path.getsize(SUBMISSION_DIR / f) / 1024
        print(f"  - {f} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()
