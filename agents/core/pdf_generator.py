"""ReportLab PDF builder for analyst reports and retrospectives."""
import os
from pathlib import Path

from agents.core import github_storage

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle
)

ARTIFACTS_BASE = Path(__file__).parents[2] / "artifacts"

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY        = colors.HexColor("#1E3A5F")
GREEN       = colors.HexColor("#27AE60")
GREEN_BG    = colors.HexColor("#EAFAF1")
RED         = colors.HexColor("#E74C3C")
RED_BG      = colors.HexColor("#FDEDEC")
GOLD        = colors.HexColor("#F39C12")
GOLD_BG     = colors.HexColor("#FEF9E7")
BLUE_BG     = colors.HexColor("#EBF5FB")
LIGHT_GREY  = colors.HexColor("#F5F7FA")
MID_GREY    = colors.HexColor("#BDC3C7")
DARK_GREY   = colors.HexColor("#7F8C8D")
WHITE       = colors.white

_ss = getSampleStyleSheet()

def _s(name, **kw):
    return ParagraphStyle(name, parent=_ss["Normal"], **kw)

# Shared styles
S_TITLE     = _s("Title",    fontSize=20, textColor=WHITE,    fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=0)
S_SUBTITLE  = _s("Sub",      fontSize=10, textColor=WHITE,    alignment=TA_CENTER, spaceAfter=0)
S_PICK_HDR  = _s("PH",       fontSize=15, textColor=NAVY,     fontName="Helvetica-Bold", spaceAfter=4, spaceBefore=10)
S_SECTOR    = _s("Sec",      fontSize=9,  textColor=DARK_GREY, spaceAfter=2)
S_LABEL     = _s("Lbl",      fontSize=7,  textColor=DARK_GREY, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=0)
S_VALUE     = _s("Val",      fontSize=13, textColor=NAVY,     fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=0)
S_VALUE_GRN = _s("ValG",     fontSize=13, textColor=GREEN,    fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=0)
S_VALUE_RED = _s("ValR",     fontSize=13, textColor=RED,      fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=0)
S_SECTION   = _s("SH",       fontSize=10, textColor=NAVY,     fontName="Helvetica-Bold", spaceAfter=3, spaceBefore=8)
S_BODY      = _s("Body",     fontSize=9,  leading=14,         spaceAfter=4, alignment=TA_JUSTIFY)
S_SMALL     = _s("Sm",       fontSize=7.5, textColor=DARK_GREY, spaceAfter=2)
S_BODY_CENT = _s("BC",       fontSize=9,  leading=13,         alignment=TA_CENTER)
S_MKT_HDR  = _s("MH",       fontSize=11, textColor=NAVY,     fontName="Helvetica-Bold", spaceAfter=4)


def _confidence_color(pct: int):
    if pct >= 80: return GREEN
    if pct >= 70: return GOLD
    return RED


def _gain_pct(entry, exit_p) -> float:
    try: return (exit_p - entry) / entry * 100
    except: return 0.0


def _cell(label: str, value: str, value_style=None, bg=None):
    """Returns a 2-row, 1-col inner table for a metric box."""
    vs = value_style or S_VALUE
    inner = Table(
        [[Paragraph(label, S_LABEL)],
         [Paragraph(value, vs)]],
        colWidths=[1.4 * inch],
    )
    bg_color = bg or LIGHT_GREY
    inner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg_color),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ("LINEBELOW",     (0,0), (-1,0),  0.5, MID_GREY),
    ]))
    return inner


def build_analyst_report(report_date: str, picks: list[dict],
                          market_summary: str, vix_level) -> str:
    out_dir = ARTIFACTS_BASE / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = str(out_dir / f"{report_date}-analyst.pdf")

    doc = SimpleDocTemplate(
        path, pagesize=letter,
        leftMargin=0.65*inch, rightMargin=0.65*inch,
        topMargin=0.65*inch,  bottomMargin=0.65*inch,
    )
    story = []

    # ── Document header banner ─────────────────────────────────────────────────
    banner = Table(
        [[Paragraph("StockAdvisor — Daily Analyst Report", S_TITLE)],
         [Paragraph(f"Report Date: {report_date}   |   VIX: {vix_level or 'N/A'}", S_SUBTITLE)]],
        colWidths=[7.2 * inch],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    story.append(banner)
    story.append(Spacer(1, 10))

    # ── Market summary ─────────────────────────────────────────────────────────
    if market_summary:
        story.append(Paragraph("Market Overview", S_MKT_HDR))
        story.append(Paragraph(market_summary, S_BODY))
        story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=10))

    # ── Picks ──────────────────────────────────────────────────────────────────
    for i, pick in enumerate(picks, 1):
        sym      = pick.get("symbol", "")
        company  = pick.get("company", sym)
        sector   = pick.get("sector", "")
        cur_p    = pick.get("current_price") or pick.get("entry_price", 0)
        entry_p  = pick.get("entry_price", 0)
        stop_p   = pick.get("stop_loss", 0)
        target_p = pick.get("exit_price", 0)
        conf     = pick.get("confidence_pct", 0)
        conf_lbl = pick.get("confidence_label", "")
        earnings = pick.get("earnings_date") or "N/A"
        gain_pct = _gain_pct(entry_p, target_p)
        conf_clr = _confidence_color(conf)

        thesis     = pick.get("thesis") or pick.get("reason", "")
        fund_text  = pick.get("fundamental_analysis", "")
        tech_text  = pick.get("technical_analysis", "")
        risk_text  = pick.get("risks") or pick.get("risk_warning", "")

        # ── Pick header ────────────────────────────────────────────────────────
        pick_block = []

        pick_block.append(Paragraph(
            f"#{i}  {sym} — {company}", S_PICK_HDR))
        pick_block.append(Paragraph(
            f"Sector: {sector}", S_SECTOR))

        # ── 6-cell metric bar ──────────────────────────────────────────────────
        gain_str = f"${target_p:,.2f}  (+{gain_pct:.0f}%)"
        conf_str = f"+{gain_pct:.0f}%  (Confidence: {conf_lbl} {conf}%)"

        metric_row = Table(
            [[
                _cell("Current Price",  f"${cur_p:,.2f}",   S_VALUE,     LIGHT_GREY),
                _cell("Entry Price",    f"${entry_p:,.2f}",  S_VALUE,     LIGHT_GREY),
                _cell("Stop Loss",      f"${stop_p:,.2f}",   S_VALUE_RED, RED_BG),
                _cell("Earnings Date",  earnings,            S_VALUE,     LIGHT_GREY),
                _cell("Target Price",   f"${target_p:,.2f}", S_VALUE_GRN, GREEN_BG),
                _cell("Expected Gain",  gain_str,            S_VALUE_GRN, GREEN_BG),
            ]],
            colWidths=[1.2*inch]*6,
        )
        metric_row.setStyle(TableStyle([
            ("GRID",          (0,0), (-1,-1), 0.5, MID_GREY),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))
        pick_block.append(metric_row)
        pick_block.append(Spacer(1, 4))

        # Confidence chip
        conf_chip = Table(
            [[Paragraph(conf_str, _s("CC", fontSize=9, textColor=conf_clr,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER))]],
            colWidths=[7.2 * inch],
        )
        conf_chip.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), GOLD_BG if conf < 80 else GREEN_BG),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LINEBELOW",     (0,0), (-1,-1), 1, conf_clr),
            ("LINEABOVE",     (0,0), (-1,-1), 1, conf_clr),
        ]))
        pick_block.append(conf_chip)
        pick_block.append(Spacer(1, 6))

        # ── Analysis sections ──────────────────────────────────────────────────
        if thesis:
            pick_block.append(Paragraph("Thesis:", S_SECTION))
            pick_block.append(Paragraph(thesis, S_BODY))

        if fund_text:
            pick_block.append(Paragraph("Fundamental Analysis:", S_SECTION))
            pick_block.append(Paragraph(fund_text, S_BODY))

        if tech_text:
            pick_block.append(Paragraph("Technical Analysis:", S_SECTION))
            pick_block.append(Paragraph(tech_text, S_BODY))

        if risk_text:
            pick_block.append(Paragraph("Risks:", S_SECTION))
            pick_block.append(Paragraph(risk_text, S_BODY))

        pick_block.append(Spacer(1, 8))
        pick_block.append(HRFlowable(width="100%", thickness=1, color=MID_GREY, spaceAfter=10))

        story.append(KeepTogether(pick_block[:6]))   # keep header+metrics together
        story.extend(pick_block[6:])                  # let analysis flow freely

        if i < len(picks):
            story.append(Spacer(1, 4))

    # ── Disclaimer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "DISCLAIMER: This report is generated by an AI paper trading simulation and does not "
        "constitute financial advice. All prices are simulated. Past performance does not "
        "guarantee future results. Do not make real investment decisions based on this report.",
        S_SMALL,
    ))

    doc.build(story)

    if github_storage.is_configured():
        return github_storage.upload(path, f"reports/{report_date}-analyst.pdf")
    return path


# ── Retrospective (unchanged structure, minor style refresh) ───────────────────

def build_retrospective_report(year: int, month: int,
                                performance: dict, pattern_analysis: str,
                                old_strategy: dict | None,
                                new_strategy: dict | None,
                                transactions: list[dict]) -> str:
    month_str = f"{year}-{month:02d}"
    out_dir = ARTIFACTS_BASE / "retrospectives"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = str(out_dir / f"{month_str}-retrospective.pdf")

    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=0.65*inch, rightMargin=0.65*inch,
                            topMargin=0.65*inch,  bottomMargin=0.65*inch)
    story = []

    banner = Table(
        [[Paragraph("StockAdvisor — Monthly Retrospective", S_TITLE)],
         [Paragraph(f"Period: {month_str}", S_SUBTITLE)]],
        colWidths=[7.2 * inch],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(banner)
    story.append(Spacer(1, 12))

    # Performance summary table
    story.append(Paragraph("Performance Summary", S_MKT_HDR))
    pnl   = performance.get("total_pnl", 0)
    spy   = performance.get("spy_return_pct")
    init  = performance.get("initial_value", 5000)
    pct   = pnl / init * 100 if init else 0
    vs    = "OUTPERFORMED SPY" if spy is not None and pct >= spy else "UNDERPERFORMED SPY"
    vs_c  = GREEN if vs.startswith("OUT") else RED

    perf_data = [
        ["Metric", "Value"],
        ["Total Realized P&L",  f"${pnl:+.2f}"],
        ["Portfolio Return",     f"{pct:+.2f}%"],
        ["Win Rate",             f"{performance.get('win_rate_pct', 0):.1f}%"],
        ["Total Trades",         str(performance.get("total_trades", 0))],
        ["Winning Trades",       str(performance.get("wins", 0))],
        ["Losing Trades",        str(performance.get("losses", 0))],
        ["SPY Monthly Return",   f"{spy:.2f}%" if spy is not None else "N/A"],
        ["vs Benchmark",         vs],
    ]
    tbl = Table(perf_data, colWidths=[3.6*inch, 3.6*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",      (0,0), (-1,0),  WHITE),
        ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT_GREY, WHITE]),
        ("GRID",           (0,0), (-1,-1), 0.5, MID_GREY),
        ("ALIGN",          (1,0), (1,-1),  "CENTER"),
        ("TEXTCOLOR",      (1,-1),(1,-1),  vs_c),
        ("FONTNAME",       (1,-1),(1,-1),  "Helvetica-Bold"),
        ("TOPPADDING",     (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 12))

    story.append(Paragraph("AI Pattern Analysis", S_MKT_HDR))
    story.append(Paragraph(pattern_analysis or "No analysis available.", S_BODY))
    story.append(Spacer(1, 10))

    if new_strategy:
        story.append(Paragraph("Strategy Update", S_MKT_HDR))
        story.append(Paragraph(
            f"<b>Previous:</b> {old_strategy.get('name','N/A') if old_strategy else 'N/A'}", S_BODY))
        story.append(Paragraph(
            f"<b>New ({new_strategy.get('name','')}):</b> {new_strategy.get('description','')}", S_BODY))
        params = new_strategy.get("parameters", {})
        if isinstance(params, str):
            import json; params = json.loads(params)
        for k, v in params.items():
            story.append(Paragraph(f"  • {k}: {v}", S_SMALL))
    else:
        story.append(Paragraph("Strategy Update", S_MKT_HDR))
        story.append(Paragraph(
            "Strategy performing at or above SPY benchmark. No changes made.", S_BODY))

    story.append(Spacer(1, 12))

    if transactions:
        story.append(Paragraph("Transaction Log", S_MKT_HDR))
        headers = ["Symbol", "Action", "Price", "Qty", "Amount", "P&L", "Date"]
        rows = [headers]
        for tx in transactions[:50]:
            pv = tx.get("realized_pnl")
            rows.append([
                tx.get("symbol",""), tx.get("action",""),
                f"${tx.get('price',0):.2f}", str(tx.get("quantity",0)),
                f"${tx.get('amount',0):.2f}",
                f"${pv:.2f}" if pv is not None else "—",
                str(tx.get("executed_at",""))[:10],
            ])
        cw = [0.8*inch, 0.7*inch, 0.9*inch, 0.5*inch, 0.9*inch, 0.9*inch, 1.1*inch]
        tbl2 = Table(rows, colWidths=cw)
        tbl2.setStyle(TableStyle([
            ("BACKGROUND",     (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",      (0,0), (-1,0),  WHITE),
            ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0), (-1,-1), 7.5),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT_GREY, WHITE]),
            ("GRID",           (0,0), (-1,-1), 0.3, MID_GREY),
            ("ALIGN",          (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING",     (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",  (0,0), (-1,-1), 3),
        ]))
        story.append(tbl2)

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "DISCLAIMER: Paper trading simulation only. Not financial advice.", S_SMALL))

    doc.build(story)

    if github_storage.is_configured():
        return github_storage.upload(path, f"retrospectives/{month_str}-retrospective.pdf")
    return path
