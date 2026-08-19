"""
Renders a generated mobility program (output of
mobility_program_generator.generate_program) as a PDF.

Uses fpdf2 -- pure Python, no system-level dependencies (unlike WeasyPrint,
which needs Pango/Cairo installed in the container), which keeps the
Cloud Run image simple.
"""

from datetime import date
from io import BytesIO

from fpdf import FPDF

DAY_ORDER = [1, 2, 3]
SLOT_ORDER = ["Primary", "Secondary"]


class ProgramPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "HEAT Mobility Program", ln=True, align="C")
        self.set_font("Helvetica", "", 10)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def render_program_pdf(
    athlete_name: str,
    assessment_type: str,
    level_of_play: str,
    assessment_date: date,
    group_scores: dict,
    ranked_groups: list,
    program: list,
) -> bytes:
    """
    program: list of {day, slot, drill_name, sets, reps, video_link}
             (the `program` key from generate_program()'s return value)

    Returns raw PDF bytes.
    """
    pdf = ProgramPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # --- Athlete info ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, athlete_name, ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 6,
        f"{assessment_type}  |  {level_of_play}  |  {assessment_date.strftime('%B %d, %Y')}",
        ln=True,
    )
    pdf.ln(4)

    # --- Group scores summary ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Mobility Screen Results", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for rank, group in enumerate(ranked_groups, start=1):
        score = group_scores.get(group, 0)
        pdf.cell(0, 6, f"{rank}. {group} -- {score}/100", ln=True)
    pdf.ln(4)

    # --- Program by day ---
    by_day = {d: {"Primary": [], "Secondary": []} for d in DAY_ORDER}
    for row in program:
        by_day[row["day"]][row["slot"]].append(row)

    for day in DAY_ORDER:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 8, f"Day {day}", ln=True, fill=True)
        pdf.ln(1)

        for slot in SLOT_ORDER:
            drills = by_day[day][slot]
            if not drills:
                continue
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, slot, ln=True)
            pdf.set_font("Helvetica", "", 9)

            col_widths = [45, 15, 20, 40, 70]
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(col_widths[0], 6, "Drill", border=1)
            pdf.cell(col_widths[1], 6, "Sets", border=1)
            pdf.cell(col_widths[2], 6, "Reps/Time", border=1)
            pdf.cell(col_widths[3], 6, "Notes", border=1)
            pdf.cell(col_widths[4], 6, "Video", border=1, ln=True)

            pdf.set_font("Helvetica", "", 8)
            for drill in drills:
                pdf.cell(col_widths[0], 6, drill["drill_name"][:26], border=1)
                pdf.cell(col_widths[1], 6, str(drill.get("sets") or ""), border=1)
                pdf.cell(col_widths[2], 6, str(drill.get("reps") or ""), border=1)
                pdf.cell(col_widths[3], 6, (drill.get("notes") or "")[:24], border=1)
                pdf.cell(col_widths[4], 6, (drill.get("video_link") or "")[:42], border=1, ln=True)
            pdf.ln(2)
        pdf.ln(3)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
