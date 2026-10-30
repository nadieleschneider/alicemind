import re
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas


SECTION_HEADINGS = {
    "CONTATO",
    "OBJETIVO",
    "RESUMO",
    "RESUMO PROFISSIONAL",
    "PERFIL",
    "PERFIL PROFISSIONAL",
    "EXPERIÊNCIA",
    "EXPERIÊNCIA PROFISSIONAL",
    "FORMAÇÃO",
    "FORMAÇÃO ACADÊMICA",
    "EDUCAÇÃO",
    "PROJETOS",
    "HABILIDADES",
    "COMPETÊNCIAS",
    "IDIOMAS",
    "CERTIFICAÇÕES",
    "CURSOS",
}


def _plain_text(line):
    line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", line)
    line = re.sub(r"`([^`]*)`", r"\1", line)
    return line.replace("**", "").replace("__", "").replace("*", "").strip()


def _is_section_heading(line):
    plain = _plain_text(line.lstrip("# ").strip())
    normalized = plain.upper().rstrip(":")
    return (
        line.startswith("#")
        or normalized in SECTION_HEADINGS
        or (
            2 <= len(plain) <= 64
            and plain == plain.upper()
            and any(character.isalpha() for character in plain)
        )
    )


def _pdf_safe_text(text):
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _wrap_line(text, font_name, font_size, max_width):
    words = _pdf_safe_text(text).split()
    lines = []
    current = ""
    for word in words:
        if stringWidth(word, font_name, font_size) > max_width:
            if current:
                lines.append(current)
                current = ""
            chunk = ""
            for character in word:
                if (
                    chunk
                    and stringWidth(chunk + character, font_name, font_size)
                    > max_width
                ):
                    lines.append(chunk)
                    chunk = character
                else:
                    chunk += character
            current = chunk
            continue
        candidate = f"{current} {word}".strip()
        if current and stringWidth(candidate, font_name, font_size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def create_resume_pdf(resume_text):
    if not isinstance(resume_text, str) or not resume_text.strip():
        raise ValueError("O currículo está vazio.")
    if len(resume_text) > 50_000:
        raise ValueError("O currículo excede o limite de 50.000 caracteres.")

    lines = [line.strip() for line in resume_text.replace("\r", "").split("\n")]
    first_content_index = next(
        (index for index, line in enumerate(lines) if line), None
    )
    candidate_name = "Currículo profissional"
    if first_content_index is not None:
        first_line = lines[first_content_index]
        potential_name = _plain_text(first_line.lstrip("# ").strip())
        normalized_first_line = potential_name.upper().rstrip(":")
        known_section = normalized_first_line in SECTION_HEADINGS or (
            normalized_first_line.startswith("CURRÍCULO")
        )
        if not known_section and len(potential_name) <= 100:
            candidate_name = potential_name
            lines[first_content_index] = ""

    page_width, page_height = A4
    margin = 19 * mm
    content_width = page_width - 2 * margin
    footer_y = 13 * mm
    body_bottom = 22 * mm
    body_size = 9.5
    line_height = 14
    navy = (24 / 255, 50 / 255, 75 / 255)
    teal = (22 / 255, 140 / 255, 140 / 255)
    ink = (37 / 255, 52 / 255, 67 / 255)
    muted = (100 / 255, 116 / 255, 139 / 255)
    pale = (215 / 255, 225 / 255, 231 / 255)

    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=A4, pageCompression=1)
    pdf.setTitle(f"Currículo - {_pdf_safe_text(candidate_name)}")
    pdf.setSubject("Currículo profissional")
    page_number = 1

    def draw_footer():
        pdf.setStrokeColorRGB(*pale)
        pdf.setLineWidth(0.5)
        pdf.line(margin, footer_y, page_width - margin, footer_y)
        pdf.setFillColorRGB(*muted)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(margin, 8 * mm, "Currículo profissional")
        pdf.drawRightString(page_width - margin, 8 * mm, str(page_number))

    pdf.setFillColorRGB(*navy)
    header_top = page_height - margin
    header_height = 30 * mm
    header_bottom = header_top - header_height
    pdf.roundRect(
        margin,
        header_bottom,
        content_width,
        header_height,
        5,
        fill=1,
        stroke=0,
    )
    pdf.setFillColorRGB(169 / 255, 217 / 255, 213 / 255)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(margin + 14, header_top - 18, "CURRÍCULO PROFISSIONAL")
    name_lines = _wrap_line(
        candidate_name,
        "Helvetica-Bold",
        19,
        content_width - 28,
    )
    name_font_size = 19
    if any(
        stringWidth(name_line, "Helvetica-Bold", name_font_size)
        > content_width - 28
        for name_line in name_lines
    ):
        name_font_size = 15
        name_lines = _wrap_line(
            candidate_name,
            "Helvetica-Bold",
            name_font_size,
            content_width - 28,
        )
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", name_font_size)
    for index, name_line in enumerate(name_lines[:2]):
        pdf.drawString(
            margin + 14,
            header_top - 42 - index * (name_font_size + 3),
            name_line,
        )
    pdf.setFillColorRGB(190 / 255, 204 / 255, 216 / 255)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin + 14, header_bottom + 10, "Perfil profissional")
    pdf.setStrokeColorRGB(*teal)
    pdf.setLineWidth(1.2)
    pdf.line(margin, header_bottom - 9, page_width - margin, header_bottom - 9)

    y = header_bottom - 25

    def start_next_page():
        nonlocal page_number, y
        draw_footer()
        pdf.showPage()
        page_number += 1
        pdf.setStrokeColorRGB(*pale)
        pdf.setLineWidth(0.7)
        pdf.line(margin, page_height - margin, page_width - margin, page_height - margin)
        pdf.setFillColorRGB(*muted)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(
            margin,
            page_height - margin - 14,
            _pdf_safe_text(candidate_name),
        )
        y = page_height - margin - 34

    def ensure_space(height):
        nonlocal y
        if y - height < body_bottom:
            start_next_page()

    for line in lines:
        if not line:
            continue
        if _is_section_heading(line):
            ensure_space(31)
            heading = _pdf_safe_text(
                _plain_text(line.lstrip("# ").strip()).rstrip(":")
            )
            y -= 3
            pdf.setFillColorRGB(*navy)
            pdf.setFont("Helvetica-Bold", 10.5)
            pdf.drawString(margin, y, heading)
            y -= 5
            pdf.setStrokeColorRGB(*pale)
            pdf.setLineWidth(0.6)
            pdf.line(margin, y, page_width - margin, y)
            y -= 13
            continue

        plain = _plain_text(line)
        is_bullet = plain.startswith(("- ", "• ", "* "))
        if is_bullet:
            plain = plain[2:].strip()
        text_x = margin + (14 if is_bullet else 0)
        wrapped = _wrap_line(
            plain,
            "Helvetica",
            body_size,
            page_width - margin - text_x,
        )
        for index, wrapped_line in enumerate(wrapped):
            ensure_space(line_height)
            pdf.setFillColorRGB(*ink)
            pdf.setFont("Helvetica", body_size)
            if is_bullet and index == 0:
                pdf.setFillColorRGB(*teal)
                pdf.circle(margin + 4, y + 3, 1.5, fill=1, stroke=0)
                pdf.setFillColorRGB(*ink)
            pdf.drawString(text_x, y, wrapped_line)
            y -= line_height
        y -= 4

    draw_footer()
    pdf.save()
    return buffer.getvalue()
