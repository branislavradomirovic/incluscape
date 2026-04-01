from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from fpdf import FPDF
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELP_SOURCE = PROJECT_ROOT / "streamlit_app" / "pages" / "7_Help.py"
OUTPUT_PDF = PROJECT_ROOT / "Playbook.pdf"
LOGO_PATH = PROJECT_ROOT / "assets" / "SIPMT_LOGO.png"

BRAND_NAVY = (15, 23, 42)
BRAND_BLUE = (30, 64, 175)
BRAND_SLATE = (51, 65, 85)
BRAND_MUTED = (100, 116, 139)
BRAND_LINE = (203, 213, 225)
BRAND_PANEL = (241, 245, 249)
BRAND_WHITE = (255, 255, 255)


@dataclass
class HelpSection:
    title: str
    screenshot_caption: Optional[str]
    screenshot_candidates: List[str]
    markdown_blocks: List[str]


def clean_text(value: str) -> str:
    value = value.replace("\u2014", "-")
    value = value.replace("\u2013", "-")
    value = value.replace("\u2022", "-")
    value = value.replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"')
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.replace("`", "")
    return value


def strip_title(raw_title: str) -> str:
    title = clean_text(raw_title)
    title = title.replace("**", "")
    return title.strip()


def extract_screenshot_details(block: str) -> tuple[Optional[str], List[str]]:
    match = re.search(
        r'render_help_screenshot\(\s*"(?P<section>[^"]+)"\s*,\s*"(?P<caption>[^"]+)"(?P<rest>.*?)\)',
        block,
        re.S,
    )
    if not match:
        return None, []

    rest = match.group("rest")
    candidates = re.findall(r'"([^"]+\.(?:png|jpg|jpeg|webp|gif))"', rest)
    return clean_text(match.group("caption")), candidates


def extract_markdown_blocks(block: str) -> List[str]:
    parts = re.findall(r'st\.markdown\("""(.*?)"""\)', block, re.S)
    return [part.strip("\n") for part in parts if part.strip()]


def parse_help_sections(source_text: str) -> List[HelpSection]:
    pattern = re.compile(
        r'with st\.expander\("(?P<title>[^"]+)"(?:,[^\n]*)?\):\n(?P<body>.*?)(?=\n(?:# [^\n]*\n)*with st\.expander\(|\nst\.markdown\("---"\)|\Z)',
        re.S,
    )
    sections: List[HelpSection] = []
    for match in pattern.finditer(source_text):
        title = strip_title(match.group("title"))
        body = match.group("body")
        screenshot_caption, screenshot_candidates = extract_screenshot_details(body)
        markdown_blocks = extract_markdown_blocks(body)
        sections.append(
            HelpSection(
                title=title,
                screenshot_caption=screenshot_caption,
                screenshot_candidates=screenshot_candidates,
                markdown_blocks=markdown_blocks,
            )
        )
    return sections


def resolve_image(candidates: List[str]) -> Optional[Path]:
    search_roots = [
        PROJECT_ROOT / "assets" / "help",
        PROJECT_ROOT / "assets",
        PROJECT_ROOT / "landing_page_assets",
    ]
    for root in search_roots:
        for candidate in candidates:
            candidate_path = root / candidate
            if candidate_path.exists():
                return candidate_path
    return None


def section_summary(section: HelpSection) -> str:
    summary_lines: List[str] = []
    for block in section.markdown_blocks:
        for raw_line in block.splitlines():
            line = clean_text(raw_line.strip())
            if not line:
                continue
            if line.startswith("####") or line.startswith("-") or re.match(r"^\d+\.\s+", line):
                continue
            line = line.replace("**", "")
            summary_lines.append(line)
            if len(summary_lines) == 3:
                break
        if len(summary_lines) == 3:
            break

    if summary_lines:
        return " ".join(summary_lines)[:420]
    return "Operational guidance and visual reference for this SIPMT application section."


def deployment_notes() -> List[str]:
    return [
        "Primary local workflow uses PostgreSQL when DATABASE_URL is configured; SQLite remains available as the local/demo fallback.",
        "Refresh the SQLite demo mirror with scripts/sync_postgres_to_sqlite.py after direct PostgreSQL-side changes.",
        "Run scripts/pre_deploy_check.sh before releases so syntax checks and mirror refresh complete consistently.",
        "Streamlit Cloud deployments rely on .streamlit/config.toml for headless startup behavior.",
    ]


def flow_multicell(pdf: FPDF, width: float, height: float, text: str) -> None:
    pdf.multi_cell(width, height, text, new_x="LMARGIN", new_y="NEXT")


def estimate_multicell_height(
    pdf: FPDF,
    width: float,
    line_height: float,
    text: str,
    *,
    font_family: Optional[str] = None,
    font_style: str = "",
    font_size: Optional[float] = None,
) -> float:
    previous_family = getattr(pdf, "font_family", "Helvetica")
    previous_style = getattr(pdf, "font_style", "")
    previous_size = getattr(pdf, "font_size_pt", 11)

    if font_family or font_size:
        pdf.set_font(font_family or previous_family, font_style, font_size or previous_size)

    text = clean_text(text)
    if not text.strip():
        if font_family or font_size:
            pdf.set_font(previous_family, previous_style, previous_size)
        return line_height

    total_lines = 0
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            total_lines += 1
            continue

        words = paragraph.split()
        if not words:
            total_lines += 1
            continue

        current_line = words[0]
        line_count = 1
        for word in words[1:]:
            candidate = f"{current_line} {word}"
            if pdf.get_string_width(candidate) <= width:
                current_line = candidate
            else:
                current_line = word
                line_count += 1
        total_lines += line_count

    height = max(total_lines, 1) * line_height

    if font_family or font_size:
        pdf.set_font(previous_family, previous_style, previous_size)

    return height


def add_text_panel(
    pdf: PlaybookPDF,
    title: str,
    body: str,
    *,
    x: float,
    y: float,
    width: float,
    title_height: float = 7,
    body_line_height: float = 5,
    inner_padding: float = 4,
) -> float:
    body_height = estimate_multicell_height(
        pdf,
        width - (inner_padding * 2),
        body_line_height,
        body,
        font_family="Helvetica",
        font_style="",
        font_size=11,
    )
    panel_height = inner_padding + title_height + 1 + body_height + inner_padding
    pdf.set_fill_color(*BRAND_PANEL)
    pdf.set_draw_color(*BRAND_LINE)
    pdf.rect(x, y, width, panel_height, style="DF")

    pdf.set_xy(x + inner_padding, y + inner_padding)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BRAND_BLUE)
    pdf.cell(width - (inner_padding * 2), title_height, title, new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x + inner_padding)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*BRAND_SLATE)
    flow_multicell(pdf, width - (inner_padding * 2), body_line_height, clean_text(body))
    pdf.set_y(y + panel_height)
    return panel_height


class PlaybookPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_section_title = ""
        self.show_running_header = False

    def header(self) -> None:
        if self.page_no() == 1 or not self.show_running_header:
            return
        if LOGO_PATH.exists():
            self.image(str(LOGO_PATH), x=self.l_margin, y=7, w=14)
        self.set_xy(self.l_margin + 18, 8)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*BRAND_NAVY)
        self.cell(self.epw * 0.45, 6, "SIPMT Playbook", new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*BRAND_MUTED)
        self.cell(self.epw * 0.55 - 20, 6, self.current_section_title, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BRAND_LINE)
        self.line(self.l_margin, 16, self.w - self.r_margin, 16)
        self.set_y(22)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*BRAND_MUTED)
        self.set_draw_color(*BRAND_LINE)
        self.line(self.l_margin, self.get_y() - 1, self.w - self.r_margin, self.get_y() - 1)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def ensure_space(self, needed_height: float) -> None:
        if self.get_y() + needed_height > self.h - 18:
            self.add_page()


def add_cover(pdf: PlaybookPDF) -> None:
    pdf.show_running_header = False
    pdf.add_page()
    pdf.set_fill_color(*BRAND_NAVY)
    pdf.rect(0, 0, pdf.w, 52, style="F")
    pdf.set_text_color(*BRAND_WHITE)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_xy(20, 18)
    flow_multicell(pdf, pdf.epw, 12, "SIPMT Playbook")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_x(20)
    flow_multicell(pdf, pdf.epw - 10, 8, "Complete application help, workflows, KPI definitions, and operational guidance.")

    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=160, y=12, w=26)

    pdf.set_text_color(*BRAND_NAVY)
    pdf.ln(14)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "What this document contains", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    items = [
        "Detailed guidance for every application function exposed in the Streamlit interface.",
        "Focused screenshots captured from the current application state.",
        "KPI and chart definitions, operational notes, configuration guidance, and troubleshooting tips.",
    ]
    for item in items:
        flow_multicell(pdf, pdf.epw, 7, f"- {item}")

    pdf.set_fill_color(*BRAND_PANEL)
    panel_y = pdf.get_y() + 6
    pdf.rect(pdf.l_margin, panel_y, pdf.epw, 28, style="F")
    pdf.set_xy(pdf.l_margin + 4, panel_y + 4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BRAND_BLUE)
    flow_multicell(pdf, pdf.epw - 8, 6, "Playbook purpose")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*BRAND_SLATE)
    flow_multicell(pdf, pdf.epw - 8, 5, "This document is intended as the printable operating guide for SIPMT users, analysts, and administrators.")

    pdf.set_y(pdf.h - 34)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*BRAND_MUTED)
    flow_multicell(pdf, pdf.epw, 4.5, "Generated from the in-application Help page and current UI screenshots. March 2026")


def add_table_of_contents(pdf: PlaybookPDF, sections: List[HelpSection], page_map: dict[str, int]) -> None:
    pdf.show_running_header = False
    pdf.add_page()
    pdf.set_text_color(*BRAND_NAVY)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    for index, section in enumerate(sections, start=1):
        pdf.ensure_space(8)
        label = f"{index}. {section.title}"
        page_no = page_map.get(section.title)
        pdf.set_text_color(*BRAND_SLATE)
        pdf.cell(pdf.epw - 18, 7, label, new_x="RIGHT", new_y="TOP")
        pdf.set_text_color(*BRAND_BLUE)
        pdf.cell(18, 7, str(page_no or "-"), align="R", new_x="LMARGIN", new_y="NEXT")


def add_section_title(pdf: PlaybookPDF, title: str) -> None:
    pdf.set_text_color(*BRAND_NAVY)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*BRAND_LINE)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)


def add_chapter_page(pdf: PlaybookPDF, section: HelpSection, chapter_number: int) -> None:
    pdf.show_running_header = False
    pdf.add_page()
    pdf.set_fill_color(*BRAND_NAVY)
    pdf.rect(0, 0, pdf.w, 64, style="F")
    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=pdf.w - 34, y=14, w=18)

    pdf.set_xy(20, 18)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(214, 224, 255)
    pdf.cell(0, 8, f"CHAPTER {chapter_number:02d}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*BRAND_WHITE)
    flow_multicell(pdf, pdf.epw - 18, 10, section.title)

    focus_panel_y = 78
    focus_panel_height = add_text_panel(
        pdf,
        "Chapter Focus",
        section_summary(section),
        x=pdf.l_margin,
        y=focus_panel_y,
        width=pdf.epw,
    )

    image_path = resolve_image(section.screenshot_candidates)
    if image_path:
        with Image.open(image_path) as img:
            width_px, height_px = img.size
        max_width = pdf.epw
        display_width = max_width
        display_height = display_width * (height_px / width_px)
        image_y = focus_panel_y + focus_panel_height + 10
        max_image_height = max(52, 244 - image_y)
        if display_height > max_image_height:
            scale = max_image_height / display_height
            display_width *= scale
            display_height = max_image_height
        pdf.set_draw_color(*BRAND_LINE)
        pdf.set_fill_color(*BRAND_WHITE)
        pdf.rect(pdf.l_margin, image_y - 4, pdf.epw, display_height + 8, style="DF")
        image_x = pdf.l_margin + (pdf.epw - display_width) / 2
        pdf.image(str(image_path), x=image_x, y=image_y, w=display_width)

    pdf.set_y(252)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*BRAND_MUTED)
    pdf.cell(0, 8, "Visual chapter opener generated from the current SIPMT interface", align="C")


def add_image_block(pdf: PlaybookPDF, image_path: Optional[Path], caption: Optional[str]) -> None:
    if not image_path:
        return

    with Image.open(image_path) as img:
        width_px, height_px = img.size

    max_width = min(120, pdf.epw)
    display_width = max_width
    display_height = display_width * (height_px / width_px)

    if display_height > 58:
        scale = 58 / display_height
        display_width *= scale
        display_height = 58

    pdf.ensure_space(display_height + 16)
    box_y = pdf.get_y()
    pdf.set_draw_color(*BRAND_LINE)
    pdf.set_fill_color(*BRAND_WHITE)
    pdf.rect(pdf.l_margin, box_y, pdf.epw, display_height + 8, style="DF")
    image_x = pdf.l_margin + (pdf.epw - display_width) / 2
    pdf.image(str(image_path), x=image_x, y=box_y + 3, w=display_width)
    pdf.ln(display_height + 5)

    if caption:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*BRAND_MUTED)
        flow_multicell(pdf, pdf.epw, 4.5, clean_text(caption))
        pdf.ln(1)


def add_visual_focus_box(pdf: PlaybookPDF, section: HelpSection) -> None:
    if not section.screenshot_caption:
        return

    panel_body = clean_text(section.screenshot_caption)
    body_height = estimate_multicell_height(
        pdf,
        pdf.epw - 8,
        3.8,
        panel_body,
        font_family="Helvetica",
        font_style="",
        font_size=9,
    )
    panel_height = 4 + 4 + 1 + body_height + 4
    pdf.ensure_space(panel_height + 3)
    y = pdf.get_y()
    pdf.set_fill_color(*BRAND_PANEL)
    pdf.set_draw_color(*BRAND_LINE)
    pdf.rect(pdf.l_margin, y, pdf.epw, panel_height, style="DF")
    pdf.set_xy(pdf.l_margin + 4, y + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*BRAND_BLUE)
    pdf.cell(0, 4, "Visual Focus", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*BRAND_SLATE)
    flow_multicell(pdf, pdf.epw - 8, 3.8, panel_body)
    pdf.set_y(y + panel_height + 2)


def write_markdown_block(pdf: PlaybookPDF, block: str) -> None:
    lines = block.splitlines()
    in_code_block = False
    for raw_line in lines:
        line = clean_text(raw_line.rstrip())
        stripped = line.strip()
        if not stripped:
            pdf.ln(2.5)
            continue

        if stripped == "```":
            in_code_block = not in_code_block
            pdf.ln(1)
            continue

        if stripped.startswith("#### "):
            pdf.ensure_space(12)
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*BRAND_SLATE)
            flow_multicell(pdf, pdf.epw, 6, stripped[5:])
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*BRAND_NAVY)
            pdf.ln(0.8)
            continue

        if stripped == "---":
            pdf.ln(1)
            pdf.set_draw_color(*BRAND_LINE)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)
            continue

        if in_code_block:
            pdf.ensure_space(7)
            pdf.set_font("Courier", "", 9)
            flow_multicell(pdf, pdf.epw, 4.5, stripped)
            pdf.set_font("Helvetica", "", 11)
            continue

        if stripped.startswith("- "):
            pdf.set_font("Helvetica", "", 11)
            flow_multicell(pdf, pdf.epw, 5, f"- {stripped[2:]}")
            pdf.ln(0.4)
            continue

        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if numbered:
            flow_multicell(pdf, pdf.epw, 5, f"{numbered.group(1)}. {numbered.group(2)}")
            pdf.ln(0.4)
            continue

        stripped = stripped.replace("**", "")
        pdf.set_font("Helvetica", "", 11)
        flow_multicell(pdf, pdf.epw, 5, stripped)
        pdf.ln(0.5)


def add_section(pdf: PlaybookPDF, section: HelpSection) -> None:
    pdf.current_section_title = section.title
    pdf.show_running_header = True
    pdf.add_page()
    add_section_title(pdf, section.title)
    image_path = resolve_image(section.screenshot_candidates)
    add_image_block(pdf, image_path, section.screenshot_caption)
    add_visual_focus_box(pdf, section)
    for block in section.markdown_blocks:
        write_markdown_block(pdf, block)
        pdf.ln(2)


def add_back_cover(pdf: PlaybookPDF) -> None:
    pdf.show_running_header = False
    pdf.add_page()
    pdf.set_fill_color(*BRAND_NAVY)
    pdf.rect(0, 0, pdf.w, 60, style="F")
    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=pdf.w - 38, y=14, w=24)

    pdf.set_xy(18, 18)
    pdf.set_text_color(*BRAND_WHITE)
    pdf.set_font("Helvetica", "B", 24)
    flow_multicell(pdf, pdf.epw - 18, 11, "Support, Versioning, and Deployment Notes")

    pdf.set_text_color(*BRAND_NAVY)
    pdf.set_y(76)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Developer Contact", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    contact_lines = [
        "Opus Labs d.o.o. Novi Sad",
        "Nikolajevska 2",
        "21000 Novi Sad, Serbia",
        "www.opus.rs",
        "office@opus.rs",
    ]
    for line in contact_lines:
        flow_multicell(pdf, pdf.epw, 6, line)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Versioning", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    version_lines = [
        "Document: SIPMT Playbook",
        "Edition: March 2026",
        "Source: Generated from the current in-application Help page and captured screenshots",
    ]
    for line in version_lines:
        flow_multicell(pdf, pdf.epw, 6, line)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Deployment Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for item in deployment_notes():
        flow_multicell(pdf, pdf.epw, 6, f"- {item}")

    pdf.set_y(-26)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*BRAND_MUTED)
    flow_multicell(pdf, pdf.epw, 5, "For deployment, configuration, or support questions, contact the developer using the details above.")


def populate_pdf(pdf: PlaybookPDF, sections: List[HelpSection], page_map: Optional[dict[str, int]] = None) -> dict[str, int]:
    recorded_pages: dict[str, int] = {}
    add_cover(pdf)
    add_table_of_contents(pdf, sections, page_map or {})
    for index, section in enumerate(sections, start=1):
        recorded_pages[section.title] = pdf.page_no() + 1
        add_chapter_page(pdf, section, index)
        add_section(pdf, section)
    add_back_cover(pdf)
    return recorded_pages


def build_playbook() -> None:
    source_text = HELP_SOURCE.read_text(encoding="utf-8")
    sections = parse_help_sections(source_text)

    probe_pdf = PlaybookPDF("P", "mm", "A4")
    probe_pdf.set_auto_page_break(auto=True, margin=22)
    probe_pdf.set_margins(25, 22, 25)
    section_pages = populate_pdf(probe_pdf, sections)

    pdf = PlaybookPDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.set_margins(25, 22, 25)
    populate_pdf(pdf, sections, page_map=section_pages)

    pdf.output(str(OUTPUT_PDF))
    print(f"Created {OUTPUT_PDF}")


if __name__ == "__main__":
    build_playbook()