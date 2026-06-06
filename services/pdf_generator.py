from io import BytesIO
from datetime import datetime
import uuid

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def battery_chemistry_label(chemistry: str) -> str:
    mapping = {
        "li-ion": "Lithium ion battery (rechargeable)",
        "lifepo4": "Lithium iron phosphate battery (rechargeable)",
        "li-metal": "Lithium metal battery (non-rechargeable)",
        "sodium-ion": "Sodium-ion battery (rechargeable)",
    }
    return mapping.get(chemistry, chemistry or "")


def generate_shippers_declaration(shipment: dict, classification: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "BS_Title",
        parent=styles["Heading1"],
        fontSize=13,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
    )
    style_subtitle = ParagraphStyle(
        "BS_Subtitle",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica",
        alignment=TA_CENTER,
        spaceAfter=1 * mm,
        textColor=colors.HexColor("#555555"),
    )
    style_warning_box = ParagraphStyle(
        "BS_WarningBox",
        parent=styles["Normal"],
        fontSize=7.5,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        textColor=colors.HexColor("#7B0000"),
        backColor=colors.HexColor("#FFF3F3"),
        borderPadding=(4, 6, 4, 6),
    )
    style_section_header = ParagraphStyle(
        "BS_SectionHeader",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=1 * mm,
        spaceBefore=3 * mm,
    )
    style_body = ParagraphStyle(
        "BS_Body",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica",
        spaceAfter=1 * mm,
    )
    style_small = ParagraphStyle(
        "BS_Small",
        parent=styles["Normal"],
        fontSize=7,
        fontName="Helvetica",
        textColor=colors.HexColor("#666666"),
    )
    style_footer = ParagraphStyle(
        "BS_Footer",
        parent=styles["Normal"],
        fontSize=6.5,
        fontName="Helvetica",
        textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
    )
    style_red_warning = ParagraphStyle(
        "BS_RedWarning",
        parent=styles["Normal"],
        fontSize=7,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#CC0000"),
        alignment=TA_CENTER,
    )

    page_width = A4[0] - 24 * mm
    story = []

    # BLOCK 1 — Header
    story.append(Paragraph("SHIPPER'S DECLARATION FOR DANGEROUS GOODS", style_title))
    story.append(Paragraph("Air Transport — IATA Dangerous Goods Regulations", style_subtitle))
    story.append(Spacer(1, 3 * mm))

    # BLOCK 2 — IATA Warning box
    warning_text = (
        "WARNING — Failure to comply in all respects with the applicable "
        "Dangerous Goods Regulations may be in breach of the applicable law, "
        "subject to legal penalties. This declaration must not, in any "
        "circumstances, be completed and/or signed by a consolidator, a "
        "forwarder or an IATA cargo agent."
    )
    warning_table = Table(
        [[Paragraph(warning_text, style_warning_box)]],
        colWidths=[page_width],
    )
    warning_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF3F3")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CC0000")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(warning_table)
    story.append(Spacer(1, 4 * mm))

    # BLOCK 3 — Reference and date row
    left_ref = (
        "Air Waybill No.: _______________________<br/>"
        "Page _____ of _____"
    )
    right_ref = (
        f"BatteryShip Ref: BS-{str(uuid.uuid4())[:8].upper()}<br/>"
        f"Generated: {datetime.utcnow().strftime('%d %B %Y %H:%M UTC')}"
    )
    ref_table = Table(
        [[Paragraph(left_ref, style_small), Paragraph(right_ref, style_small)]],
        colWidths=[page_width / 2, page_width / 2],
    )
    ref_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ])
    )
    story.append(ref_table)
    story.append(Spacer(1, 4 * mm))

    # BLOCK 4 — Shipper and Consignee
    shipper_text = (
        "<b>Shipper</b><br/>"
        "Name: _________________________________<br/>"
        "Address: ______________________________<br/>"
        "          ______________________________<br/>"
        "City/Country: _________________________<br/>"
        "Phone: ________________________________"
    )
    consignee_text = (
        "<b>Consignee</b><br/>"
        "Name: _________________________________<br/>"
        "Address: ______________________________<br/>"
        "          ______________________________<br/>"
        "City/Country: _________________________<br/>"
        "Phone: ________________________________"
    )
    shipper_table = Table(
        [[Paragraph(shipper_text, style_body), Paragraph(consignee_text, style_body)]],
        colWidths=[page_width / 2, page_width / 2],
    )
    shipper_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (0, 0), 0.5, colors.black),
            ("BOX", (1, 0), (1, 0), 0.5, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.append(shipper_table)
    story.append(Spacer(1, 4 * mm))

    # BLOCK 5 — Transport details
    transport_table = Table(
        [
            [
                Paragraph("Airport of Departure:<br/>_____________________", style_body),
                Paragraph("Airport of Destination:<br/>_____________________", style_body),
                Paragraph("Shipment type:<br/>[X] Non-Radioactive  [ ] Radioactive", style_body),
            ]
        ],
        colWidths=[page_width / 3, page_width / 3, page_width / 3],
    )
    transport_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.append(transport_table)
    story.append(Spacer(1, 4 * mm))

    # BLOCK 6 — Main IATA table
    un_number = classification.get("un_number", "")
    proper_name = classification.get("proper_shipping_name", "")
    chemistry_label = battery_chemistry_label(shipment.get("battery_chemistry", ""))
    if chemistry_label:
        proper_name = f"{proper_name}<br/>{chemistry_label}"

    section = classification.get("section", "")
    authorization = "Cargo Aircraft\nOnly" if section == "I" else "Passenger &\nCargo Aircraft"

    header_data = [
        [
            Paragraph("UN No.", style_section_header),
            Paragraph("Proper Shipping Name", style_section_header),
            Paragraph("Class", style_section_header),
            Paragraph("Pkg Group", style_section_header),
            Paragraph("Qty & Type", style_section_header),
            Paragraph("Pkg Instr.", style_section_header),
            Paragraph("Authorization", style_section_header),
        ]
    ]
    data_row = [
        Paragraph(un_number, style_body),
        Paragraph(proper_name, style_body),
        Paragraph(classification.get("hazard_class", ""), style_body),
        Paragraph("II", style_body),
        Paragraph(f'{shipment.get("quantity", "")} package(s)<br/>Net Qty: See attached', style_body),
        Paragraph(classification.get("packing_instruction", ""), style_body),
        Paragraph(authorization, style_body),
    ]
    empty_rows = [[Paragraph("", style_body) for _ in range(7)] for _ in range(3)]

    col_widths = [24 * mm, 58 * mm, 16 * mm, 20 * mm, 26 * mm, 20 * mm, 22 * mm]
    main_table = Table(header_data + [data_row] + empty_rows, colWidths=col_widths)
    main_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8f9fa")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(main_table)
    story.append(Spacer(1, 4 * mm))

    # BLOCK 7 — Additional handling information
    lines = []
    pi = classification.get("packing_instruction", "")
    lines.append(f"Lithium batteries — {pi} — Section {section} of IATA DGR")

    if classification.get("requires_un38_3"):
        lines.append("UN38.3 Test Summary available upon request.")

    if section == "I":
        lines.append("CARGO AIRCRAFT ONLY — CAO label required on outer packaging.")

    if classification.get("requires_shippers_declaration"):
        lines.append("This shipment requires a signed Shipper's Declaration completed by a trained person.")

    for req in classification.get("additional_requirements", []):
        lines.append(f"• {req}")

    info_text = "<br/>".join(lines)
    info_para = Paragraph(info_text, style_body)
    info_table = Table([[info_para]], colWidths=[page_width])
    info_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EBF5FB")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#2980B9")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # BLOCK 8 — Declaration text
    story.append(Paragraph("Declaration", style_section_header))
    declaration_text = (
        "I hereby declare that the contents of this consignment are fully and "
        "accurately described above by the Proper Shipping Name, and are "
        "classified, packaged, marked and labelled/placarded, and are in all "
        "respects in proper condition for transport according to applicable "
        "international and national governmental regulations. I declare that "
        "all of the applicable air transport requirements have been met."
    )
    story.append(Paragraph(declaration_text, style_body))
    story.append(Spacer(1, 4 * mm))

    sig_left = (
        "Name/Title: _________________________________<br/>"
        "<br/>"
        "Signature: __________________________________<br/>"
        "<br/>"
        "Place: ______________________________________"
    )
    sig_right = (
        "Date: ______________________________________<br/>"
        "<br/>"
        "Company: ___________________________________<br/>"
        "<br/>"
        "Phone: _____________________________________"
    )
    sig_table = Table(
        [[Paragraph(sig_left, style_body), Paragraph(sig_right, style_body)]],
        colWidths=[page_width / 2, page_width / 2],
    )
    sig_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.append(sig_table)
    story.append(Spacer(1, 6 * mm))

    # BLOCK 9 — Footer
    story.append(HRFlowable(width=page_width, thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            "Generated by BatteryShip · batteryship.onrender.com · "
            "For guidance purposes only. Always verify with a certified "
            "Dangerous Goods specialist before actual shipment. "
            "Based on IATA DGR 2026 regulations.",
            style_footer,
        )
    )

    doc.build(story)
    return buffer.getvalue()
