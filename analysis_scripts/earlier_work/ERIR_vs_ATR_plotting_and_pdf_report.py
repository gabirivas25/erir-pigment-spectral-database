import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

STUDENT_NAME = "Maria Gabriela Rivas Carmona"
UNIVERSITY = "University of Padova"
ADVISOR = "Professor Alfonso Zoleo"

RED = colors.HexColor("#B03A2E")
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

OUT_ROOT = Path("/mnt/user-data/outputs")


def load_dpt(path):
    data = np.loadtxt(path)
    return data[:, 0], data[:, 1]


def plot_mineral(mineral, data_dir, fig_dir, atr_filename=None, extra_exclude=None):
    fig_dir.mkdir(parents=True, exist_ok=True)
    atr_file = data_dir / (atr_filename or f"{mineral}_ATR.dpt")
    atr_wn, atr_val = load_dpt(atr_file)

    exclude_names = {atr_file.name}
    if extra_exclude:
        exclude_names |= extra_exclude

    scan_files = sorted(
        [f for f in data_dir.glob(f"{mineral}_*.dpt") if f.name not in exclude_names],
        key=lambda p: p.name
    )

    skipped = []
    for scan_path in scan_files:
        if scan_path.stat().st_size == 0:
            skipped.append(scan_path.name)
            continue
        wn, val = load_dpt(scan_path)
        scan_name = scan_path.stem

        fig, ax1 = plt.subplots(figsize=(9, 5.5))
        color1 = "#c0392b"
        ax1.set_xlabel("Wavenumber (cm$^{-1}$)")
        ax1.set_ylabel("ER-IR Reflectance (a.u.)", color=color1)
        l1, = ax1.plot(wn, val, color=color1, linewidth=1.1, label=f"{scan_name} (ER-IR)")
        ax1.tick_params(axis="y", labelcolor=color1)
        ax1.invert_xaxis()

        ax2 = ax1.twinx()
        color2 = "#2471a3"
        ax2.set_ylabel("ATR Absorbance (a.u.)", color=color2)
        l2, = ax2.plot(atr_wn, atr_val, color=color2, linewidth=1.1, alpha=0.85,
                        label=f"{mineral}_ATR (standard)")
        ax2.tick_params(axis="y", labelcolor=color2)

        ax1.set_title(f"{scan_name} — ER-IR scan vs. {mineral} ATR standard")
        ax1.grid(alpha=0.25)
        lines = [l1, l2]
        ax1.legend(lines, [l.get_label() for l in lines], loc="upper right", fontsize=9)

        fig.tight_layout()
        out_path = fig_dir / f"{scan_name}_vs_ATR.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)

    return len(scan_files) - len(skipped), skipped


def build_pdf(mineral, fig_dir, out_pdf):
    title_style = ParagraphStyle("TitleBig", fontName=FONT_BOLD, fontSize=26,
                                  textColor=RED, spaceAfter=8, leading=30)
    subtitle_style = ParagraphStyle("Subtitle", fontName=FONT, fontSize=13,
                                     textColor=colors.HexColor("#555555"), spaceAfter=26, leading=17)
    byline_label_style = ParagraphStyle("BylineLabel", fontName=FONT, fontSize=10,
                                         textColor=colors.HexColor("#888888"), spaceAfter=1)
    byline_value_style = ParagraphStyle("BylineValue", fontName=FONT_BOLD, fontSize=12.5,
                                         textColor=colors.HexColor("#222222"), spaceAfter=14)
    h2_style = ParagraphStyle("H2", fontName=FONT_BOLD, fontSize=13, textColor=RED,
                               spaceBefore=6, spaceAfter=8)
    scan_header_style = ParagraphStyle("ScanHeader", fontName=FONT_BOLD, fontSize=13,
                                        textColor=RED, spaceAfter=8)
    body_style = ParagraphStyle("Body", fontName=FONT, fontSize=10.5, leading=15,
                                 textColor=colors.HexColor("#222222"))
    caption_style = ParagraphStyle("Caption", fontName=FONT, fontSize=9,
                                    textColor=colors.grey, spaceBefore=6)

    story = []
    story.append(Spacer(1, 1.1 * inch))
    story.append(Paragraph("Pigment Spectral Standards", title_style))
    story.append(Paragraph(f"ER-IR vs. ATR Comparison Plots — {mineral}", subtitle_style))

    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("PREPARED BY", byline_label_style))
    story.append(Paragraph(STUDENT_NAME, byline_value_style))
    story.append(Paragraph("UNIVERSITY", byline_label_style))
    story.append(Paragraph(UNIVERSITY, byline_value_style))
    story.append(Paragraph("THESIS ADVISOR", byline_label_style))
    story.append(Paragraph(ADVISOR, byline_value_style))

    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph("About this report", h2_style))
    story.append(Paragraph(
        "Each page below shows a single ER-IR scan (red, left axis) plotted alongside the "
        f"{mineral} ATR standard (blue, right axis). The two techniques are shown on separate "
        "y-axes because their intensity scales are not directly comparable: ER-IR reflectance "
        "values and ATR absorbance values are measured differently. Wavenumber decreases from "
        "left to right, following standard infrared spectroscopy convention.",
        body_style
    ))
    story.append(PageBreak())

    img_files = sorted(fig_dir.glob(f"{mineral}_*_vs_ATR.png"), key=lambda p: p.name)
    for img_path in img_files:
        m = re.match(rf"({re.escape(mineral)}_\d+_\d+)_vs_ATR", img_path.name)
        scan_name = m.group(1) if m else img_path.stem
        story.append(Paragraph(f"{scan_name}", scan_header_style))
        story.append(Image(str(img_path), width=6.6 * inch, height=6.6 * inch * (5.5 / 9)))
        story.append(Paragraph(f"ER-IR scan {scan_name} plotted against the {mineral} ATR standard.",
                                caption_style))
        story.append(PageBreak())

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc = SimpleDocTemplate(str(out_pdf), pagesize=letter,
                             topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                             leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    doc.build(story)
    return len(img_files)


MINERALS = {
    "Cinnabar": Path("/home/claude/minerals/Cinnabar_DPT/Cinnabar_DPT"),
    "Orpiment": Path("/home/claude/minerals/Orpiment_DPT/Orpiment_DPT"),
}

ATR_OVERRIDE = {
    "Orpiment": "Orpiment_ATR_2.dpt",
}
EXTRA_EXCLUDE = {
    "Orpiment": {"Orpiment_ATR.dpt", "Orpiment_ATR_2.dpt"},
}

for mineral, data_dir in MINERALS.items():
    fig_dir = Path(f"/home/claude/figs_{mineral}")
    n_plots, skipped = plot_mineral(
        mineral, data_dir, fig_dir,
        atr_filename=ATR_OVERRIDE.get(mineral),
        extra_exclude=EXTRA_EXCLUDE.get(mineral),
    )
    out_pdf = OUT_ROOT / f"{mineral}_ERIR_vs_ATR_Report.pdf"
    n_pages = build_pdf(mineral, fig_dir, out_pdf)
    print(f"{mineral}: {n_plots} plots -> {out_pdf.name} ({n_pages} scan pages)")
    if skipped:
        print(f"  SKIPPED (empty files): {skipped}")
