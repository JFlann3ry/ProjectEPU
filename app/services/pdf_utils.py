from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReceiptPDF:
    """
    Tiny helper to generate a minimal, professional-looking receipt PDF.
    Output: bytes of a single-page A4 PDF in most cases.
    """

    def __init__(self, title: str = "EPU – Receipt") -> None:
        self.title = title

    def _fmt_amount(self, amount: Decimal | float | int, currency: str) -> str:
        try:
            q = Decimal(str(amount)).quantize(Decimal("0.01"))
        except Exception:
            q = Decimal("0.00")
        return f"{q} {currency.upper()}"

    def build(
        self,
        *,
        receipt_no: int | str,
        date: datetime,
        status: str,
        billed_to: str,
        plan_name: str,
        plan_code: str = "",
        description: str = "",
        amount: Decimal | float | int = 0,
        currency: str = "GBP",
        note_lines: Optional[list[str]] = None,
    ) -> bytes:
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=22 * mm,
            bottomMargin=20 * mm,
            title=self.title,
        )
        styles = getSampleStyleSheet()
        story: list = []

        # Header
        story.append(Paragraph(self.title, styles["Title"]))
        story.append(Spacer(1, 6))

        # Meta details
        meta_tbl = Table(
            [
                ["Receipt #", str(receipt_no)],
                ["Date", date.strftime("%d %B %Y")],
                ["Status", status.capitalize()],
            ],
            colWidths=[35 * mm, 120 * mm],
            hAlign="LEFT",
        )
        meta_tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(meta_tbl)
        story.append(Spacer(1, 10))

        # Billed To
        story.append(Paragraph("<b>Billed To</b>", styles["Heading4"]))
        story.append(Paragraph(billed_to or "User", styles["Normal"]))
        story.append(Spacer(1, 8))

        # Items
        items = [["Item", "Details"], ["Plan", plan_name or "Plan"]]
        if plan_code:
            items.append(["Code", plan_code])
        if description:
            items.append(["Description", description])
        tbl = Table(items, colWidths=[30 * mm, 125 * mm])
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, 0), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 8))

        # Totals
        story.append(Paragraph("<b>Totals</b>", styles["Heading4"]))
        story.append(
            Paragraph(
                self._fmt_amount(amount, currency),
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 10))

        # Notes
        notes = note_lines or [
            "This is a receipt for your records. It is not a VAT invoice.",
            "For questions, please contact support via /contact.",
        ]
        for line in notes:
            story.append(Paragraph(line, styles["Italic"]))
        story.append(Spacer(1, 6))

        doc.build(story)
        return buf.getvalue()
