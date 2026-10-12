import json
from datetime import date, datetime, time, timedelta, timezone
from math import isfinite
from typing import Any
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Alert, Asset, Measurement, WorkflowRun
from app.services.alerts import workflow_finding_fingerprint
from app.services.workflow_status import effective_workflow_status


router = APIRouter(prefix="/reports", tags=["Reports"])


def _utc(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _inside_period(value: object, start: datetime | None, end: datetime | None) -> bool:
    parsed = _utc(value)
    return parsed is not None and (start is None or parsed >= start) and (end is None or parsed < end)


def _display_time(value: object) -> str:
    parsed = _utc(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else "Not available"


def _fmt(value: object, decimals: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not available"
    return f"{number:.{decimals}f}" if isfinite(number) else "Not available"


def _display_metadata(value: object) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, dict):
        parts = [f"{k}: {v}" for k, v in value.items()]
        return ", ".join(parts)
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _make_pdf(lines: list[str]) -> bytes:
    buffer = BytesIO()

    navy = colors.HexColor("#142B4A")
    blue = colors.HexColor("#176B87")
    light_gray = colors.HexColor("#F3F6F9")
    dark_gray = colors.HexColor("#344054")
    border = colors.HexColor("#D6DEE8")
    white = colors.white

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Renewable Energy AI - Operational Report",
        author="Renewable Energy AI",
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=white,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=white,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=navy,
            spaceBefore=11,
            spaceAfter=5,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=dark_gray,
            spaceAfter=3,
            splitLongWords=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8.5,
            textColor=white,
            splitLongWords=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=dark_gray,
            splitLongWords=True,
        )
    )

    story = []

    def escape_text(value: object) -> str:
        text = str(value)
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

    def footer(canvas, document):
        canvas.saveState()
        page_width, _ = A4
        canvas.setStrokeColor(border)
        canvas.setLineWidth(0.5)
        canvas.line(14 * mm, 11 * mm, page_width - 14 * mm, 11 * mm)

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(dark_gray)
        canvas.drawString(14 * mm, 7 * mm, "RENEWABLE ENERGY AI | OPERATIONAL REPORT")
        canvas.drawRightString(page_width - 14 * mm, 7 * mm, f"Page {document.page}")
        canvas.restoreState()

    def make_table(rows, widths=None, header=True):
        converted_rows = []
        for row_index, row in enumerate(rows):
            converted_row = []
            for cell in row:
                if isinstance(cell, Paragraph):
                    converted_row.append(cell)
                else:
                    style = (
                        styles["TableHeader"]
                        if header and row_index == 0
                        else styles["TableCell"]
                    )
                    converted_row.append(Paragraph(escape_text(cell), style))
            converted_rows.append(converted_row)

        table = Table(
            converted_rows,
            colWidths=widths,
            repeatRows=1 if header else 0,
            hAlign="LEFT",
            splitByRow=1,
        )

        table_commands = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, border),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]

        if header:
            table_commands.append(("BACKGROUND", (0, 0), (-1, 0), navy))
            if len(converted_rows) > 1:
                table_commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, light_gray]))
        else:
            table_commands.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, light_gray]))

        table.setStyle(TableStyle(table_commands))
        return table

    title = "Renewable Energy AI"
    metadata = []

    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("Run ID:"):
            metadata.append(line)
        elif line.startswith("Generated UTC:"):
            metadata.append(line)
        elif line.startswith("Report period (UTC):"):
            metadata.append(line)
        elif line.startswith("Schedule horizon (UTC):"):
            metadata.append(line)

    header_content = [
        Paragraph(escape_text(title), styles["ReportTitle"]),
        Spacer(1, 3),
        Paragraph("<br/>".join(escape_text(item) for item in metadata), styles["ReportSubtitle"]),
    ]

    header_table = Table([[header_content]], colWidths=[182 * mm])
    header_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), navy),
            ("BOX", (0, 0), (-1, -1), 0, navy),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])
    )

    story.extend([header_table, Spacer(1, 10)])

    index = 0
    available_width = 182 * mm

    while index < len(lines):
        line = lines[index].strip()

        if not line:
            story.append(Spacer(1, 2))
            index += 1
            continue

        if (
            line.startswith("# ")
            or line.startswith("Run ID:")
            or line.startswith("Generated UTC:")
            or line.startswith("Report period (UTC):")
            or line.startswith("Schedule horizon (UTC):")
        ):
            index += 1
            continue

        if line.startswith("## "):
            heading = escape_text(line[3:].strip())
            story.append(Paragraph(heading, styles["SectionHeading"]))

            divider = Table([[""]], colWidths=[available_width], rowHeights=[1])
            divider.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), blue)]))
            story.append(divider)
            story.append(Spacer(1, 4))
            index += 1
            continue

        if "|" in line:
            group = []
            while index < len(lines):
                current = lines[index].strip()
                if not current or "|" not in current:
                    break
                cells = [cell.strip() for cell in current.split("|")]
                group.append(cells)
                index += 1

            column_count = max(len(row) for row in group)
            normalized_rows = [row + [""] * (column_count - len(row)) for row in group]

            col_w = available_width / column_count
            widths = [col_w] * column_count

            has_hdr = False
            first_row_joined = " ".join(normalized_rows[0]).lower()
            if any(term in first_row_joined for term in ("timestamp", "asset", "metric", "type", "severity", "id", "status")):
                has_hdr = True

            story.append(make_table(normalized_rows, widths=widths, header=has_hdr))
            story.append(Spacer(1, 4))
            continue

        story.append(Paragraph(escape_text(line), styles["ReportBody"]))
        index += 1

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


@router.get("/runs")
def list_report_runs(db: Session = Depends(get_db)):
    rows = db.scalars(select(WorkflowRun).order_by(WorkflowRun.created_at.desc())).all()
    return [
        {
            "workflow_id": row.id,
            "status": effective_workflow_status(row.status, row.approval_status, row.state_json),
            "approval_status": row.approval_status,
            "plan_version": row.plan_version,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.get("/{workflow_id}.pdf")
def download_workflow_report(
    workflow_id: str,
    period_start: date | None = None,
    period_end: date | None = None,
    db: Session = Depends(get_db),
):
    if period_start and period_end and period_start > period_end:
        raise HTTPException(status_code=422, detail="Reporting period start must not be after its end.")
    run = db.get(WorkflowRun, workflow_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Stored workflow run not found.")

    start_utc = datetime.combine(period_start, time.min, tzinfo=timezone.utc) if period_start else None
    end_utc = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc) if period_end else None

    state = run.state_json or {}
    inner = state.get("state", {}) if isinstance(state.get("state", {}), dict) else {}
    provenance = state.get("forecast_provenance", {}) or inner.get("forecast_provenance", {}) or {}
    agent_results = inner.get("agent_results", {}) or state.get("agent_results", {}) or {}

    gen_prov = provenance.get("generation_forecasting", {}) or {}
    gen_agent = agent_results.get("generation_forecasting", {}) or {}
    demand_prov = provenance.get("demand_forecasting", {}) or {}
    demand_agent = agent_results.get("demand_forecasting", {}) or {}

    optimization = inner.get("grid_optimization", {}) or state.get("grid_optimization", {}) or {}
    battery_limits = inner.get("battery_limits", {}) or state.get("battery_limits", {}) or {}
    workflow_inputs = inner.get("workflow_inputs", {}) or state.get("workflow_inputs", {}) or {}
    performance = inner.get("performance_analysis", {}) or state.get("performance_analysis", {}) or {}
    comparison = performance.get("measurement_comparison", {}) or {}
    anomalies = inner.get("anomalies", []) or state.get("anomalies", []) or []
    timestamps = (
        inner.get("generation_forecast_timestamps", [])
        or state.get("generation_forecast_timestamps", [])
        or []
    )

    measurement_query = select(Measurement)
    finding_fingerprints = {
        workflow_finding_fingerprint(finding, timestamps)
        for finding in anomalies
        if isinstance(finding, dict)
    }
    alert_query = select(Alert)
    if finding_fingerprints:
        alert_query = alert_query.where(or_(Alert.workflow_id == workflow_id, Alert.fingerprint.in_(finding_fingerprints)))
    else:
        alert_query = alert_query.where(Alert.workflow_id == workflow_id)

    if start_utc:
        measurement_query = measurement_query.where(Measurement.timestamp >= start_utc)
        alert_query = alert_query.where(Alert.created_at >= start_utc)
    if end_utc:
        measurement_query = measurement_query.where(Measurement.timestamp < end_utc)
        alert_query = alert_query.where(Alert.created_at < end_utc)

    measurements = list(db.scalars(measurement_query.order_by(Measurement.timestamp.desc()).limit(100)).all())
    measurements.reverse()
    measurement_count_query = select(func.count()).select_from(Measurement)
    if start_utc:
        measurement_count_query = measurement_count_query.where(Measurement.timestamp >= start_utc)
    if end_utc:
        measurement_count_query = measurement_count_query.where(Measurement.timestamp < end_utc)
    measurement_count = db.scalar(measurement_count_query) or 0
    alerts = db.scalars(alert_query.order_by(Alert.created_at, Alert.id)).all()
    assets = db.scalars(select(Asset).order_by(Asset.id)).all()

    generation_all = (
        inner.get("generation_forecast")
        or state.get("generation_forecast")
        or gen_agent.get("forecasts")
        or []
    )
    demand_all = (
        inner.get("demand_forecast")
        or state.get("demand_forecast")
        or demand_agent.get("forecasts")
        or []
    )
    schedule_all = optimization.get("schedule", []) or []

    has_period_filter = start_utc is not None or end_utc is not None
    generation_forecasts = (
        [row for row in generation_all if _inside_period(row.get("timestamp_utc"), start_utc, end_utc)]
        if has_period_filter
        else list(generation_all)
    )
    demand_forecasts = (
        [row for row in demand_all if _inside_period(row.get("timestamp_utc"), start_utc, end_utc)]
        if has_period_filter
        else list(demand_all)
    )
    schedule = (
        [row for row in schedule_all if _inside_period(row.get("timestamp_utc"), start_utc, end_utc)]
        if has_period_filter
        else list(schedule_all)
    )

    solar_by_time: dict[str, float] = {}
    wind_by_time: dict[str, float] = {}
    for g in generation_all:
        ts = g.get("timestamp_utc")
        if not ts:
            continue
        g_type = str(g.get("source_type") or g.get("asset_type") or g.get("type") or "").lower()
        val = g.get("predicted_generation_mw") or g.get("generation_mw") or g.get("predicted_mw") or 0.0
        try:
            f_val = float(val)
            if "solar" in g_type:
                solar_by_time[ts] = f_val
            elif "wind" in g_type:
                wind_by_time[ts] = f_val
        except (ValueError, TypeError):
            pass

    actual_demand_by_time: dict[str, float] = {}
    for m in measurements:
        ts_str = _display_time(getattr(m, "timestamp", None))
        d_val = getattr(m, "demand_mw", None)
        if ts_str != "Not available" and d_val is not None:
            try:
                actual_demand_by_time[ts_str] = float(d_val)
            except (ValueError, TypeError):
                pass

    approval_rows = run.approval_history or []
    if start_utc or end_utc:
        approval_rows = [
            row
            for row in approval_rows
            if _inside_period(row.get("recorded_at") if isinstance(row, dict) else None, start_utc, end_utc)
        ]

    selected_anomalies: list[tuple[dict[str, Any], object]] = []
    for finding in anomalies:
        finding_time = finding.get("timestamp_utc")
        timestep = finding.get("timestep")
        if finding_time is None and isinstance(timestep, int) and not isinstance(timestep, bool) and 0 <= timestep < len(timestamps):
            finding_time = timestamps[timestep]
        if start_utc is None and end_utc is None:
            selected_anomalies.append((finding, finding_time))
        elif finding_time and _inside_period(finding_time, start_utc, end_utc):
            selected_anomalies.append((finding, finding_time))

    effective_status = effective_workflow_status(run.status, run.approval_status, state)
    weather = inner.get("weather_data", {}) or {}
    weather_result = agent_results.get("weather_intelligence", {}) or {}
    weather_records = weather.get("hourly_forecast", []) or []
    weather_filtered = (
        [row for row in weather_records if _inside_period(row.get("timestamp_utc"), start_utc, end_utc)]
        if has_period_filter
        else weather_records
    )

    solar_capacity = sum(float(a.capacity_mw or 0) for a in assets if str(a.asset_type).lower() == "solar")
    wind_capacity = sum(float(a.capacity_mw or 0) for a in assets if str(a.asset_type).lower() == "wind")
    total_capacity = solar_capacity + wind_capacity

    latest = measurements[-1] if measurements else None
    latest_generation = getattr(latest, "generation_mw", None) if latest else None
    latest_demand = getattr(latest, "demand_mw", None) if latest else None

    battery_capacity = (
        optimization.get("battery_capacity_mwh")
        or battery_limits.get("capacity_mwh")
        or workflow_inputs.get("battery_capacity_mwh")
        or next((float(a.capacity_mw or 0) for a in assets if str(a.asset_type).lower() == "battery"), 8.0)
    )
    battery_soc = (
        optimization.get("initial_soc_pct")
        or battery_limits.get("configured_soc_pct")
        or workflow_inputs.get("initial_soc_pct")
        or 45.0
    )
    max_charge = (
        optimization.get("max_charge_mw")
        or battery_limits.get("max_charge_mw")
        or workflow_inputs.get("max_charge_mw")
        or 2.0
    )
    max_discharge = (
        optimization.get("max_discharge_mw")
        or battery_limits.get("max_discharge_mw")
        or workflow_inputs.get("max_discharge_mw")
        or 2.0
    )
    battery_avail = (
        optimization.get("battery_is_available")
        if optimization.get("battery_is_available") is not None
        else battery_limits.get("is_available", True)
    )

    report_period = (
        f"{period_start.isoformat() if period_start else 'Beginning'} to "
        f"{period_end.isoformat() if period_end else 'Latest available'} (UTC)"
    )

    lines = [
        "# RENEWABLE ENERGY & GRID COORDINATION REPORT",
        f"Run ID: {workflow_id}",
        f"Generated UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Report period (UTC): {report_period}",
        f"Schedule horizon (UTC): {_display_time(schedule[0].get('timestamp_utc')) if schedule else 'Not available'} through {_display_time(schedule[-1].get('timestamp_utc')) if schedule else 'Not available'}",
        "",
        "## 1. Executive Summary",
        "Metric | Value",
        f"Workflow Status | {effective_status.replace('_', ' ').title()}",
        f"Plan Version | {getattr(run, 'plan_version', 'Not available')}",
        f"Human Approval Status | {getattr(run, 'approval_status', 'Not available')}",
        f"Installed Solar Capacity | {_fmt(solar_capacity)} MW",
        f"Installed Wind Capacity | {_fmt(wind_capacity)} MW",
        f"Total Solar + Wind Capacity | {_fmt(total_capacity)} MW",
        f"Latest Recorded Generation | {_fmt(latest_generation)} MW",
        f"Latest Recorded Demand | {_fmt(latest_demand)} MW",
        f"Stored Measurement Records in Period | {measurement_count}",
        f"Generation Forecast Intervals | {len(generation_forecasts)}",
        f"Demand Forecast Intervals | {len(demand_forecasts)}",
        f"Optimization Schedule Intervals | {len(schedule)}",
        "",
        "## 2. Renewable Assets & Configuration",
        "Asset | Type | Capacity (MW) | Location | Status",
    ]

    if assets:
        for asset in assets:
            lines.append(
                f"{getattr(asset, 'name', 'Unnamed asset')} | "
                f"{getattr(asset, 'asset_type', 'Not available')} | "
                f"{_fmt(getattr(asset, 'capacity_mw', None))} | "
                f"{getattr(asset, 'location', None) or 'Not available'} | "
                f"{'Active' if getattr(asset, 'is_active', False) else 'Inactive'}"
            )
    else:
        lines.append("No registered assets were found.")

    lines.extend([
        "",
        "## 3. Recorded Measurements",
        "Timestamp (UTC) | Asset ID | Generation (MW) | Demand (MW) | Source | Quality",
    ])
    if measurements:
        for item in measurements[-30:]:
            lines.append(
                f"{_display_time(getattr(item, 'timestamp', None))} | "
                f"{getattr(item, 'asset_id', None) or 'System'} | "
                f"{_fmt(getattr(item, 'generation_mw', None))} | "
                f"{_fmt(getattr(item, 'demand_mw', None))} | "
                f"{getattr(item, 'source', None) or getattr(item, 'data_source', None) or 'Not recorded'} | "
                f"{getattr(item, 'quality_flag', None) or getattr(item, 'quality', None) or 'Not recorded'}"
            )
    else:
        lines.append("No measurement records were found for the selected period.")

    lines.extend([
        "",
        "## 4. Weather Context",
        f"Weather Provider | {weather_result.get('provider', weather_result.get('source', weather.get('source', 'Open-Meteo API')))}",
        f"Weather Retrieved At (UTC) | {_display_time(weather.get('retrieved_at_utc') or weather.get('retrieved_at'))}",
        f"Weather Data Source | {_display_metadata(weather.get('source') or weather_result.get('source', 'Open-Meteo'))}",
        "Timestamp (UTC) | Temperature (C) | Cloud Cover (%) | Wind Speed (m/s) | Wind Direction (deg) | Solar Radiation (W/m2)",
    ])
    if weather_filtered:
        for row in weather_filtered[:12]:
            lines.append(
                f"{_display_time(row.get('timestamp_utc'))} | "
                f"{_fmt(row.get('temperature_c'))} | {_fmt(row.get('cloud_cover_pct'))} | "
                f"{_fmt(row.get('wind_speed_ms'))} | {_fmt(row.get('wind_direction_deg'))} | "
                f"{_fmt(row.get('solar_radiation_wm2', row.get('shortwave_radiation_wm2')))}"
            )
    else:
        lines.append("No timestamped weather records were stored for this period.")

    lines.extend([
        "",
        "## 5. Generation Forecasts",
        f"Model Data Source | {_display_metadata(gen_prov.get('model_data_source') or gen_agent.get('model_data_source') or 'Synthetic training dataset')}",
        f"Model Version | {_display_metadata(gen_prov.get('model_version') or gen_agent.get('model_version'))}",
        f"Model Warning | {_display_metadata(gen_agent.get('warning') or gen_agent.get('validation_note') or 'Trained on synthetic data. Output is experimental.')}",
        "Timestamp (UTC) | Forecast Type | Predicted Generation (MW) | Model Version | Data Source",
    ])
    if generation_forecasts:
        for row in generation_forecasts[:24]:
            val = (
                row.get("predicted_generation_mw")
                or row.get("generation_mw")
                or row.get("predicted_mw")
                or row.get("total_generation_mw")
            )
            v_ver = _display_metadata(row.get("model_version") or gen_agent.get("model_version"))
            d_src = _display_metadata(row.get("data_source") or gen_prov.get("model_data_source") or "Synthetic")
            lines.append(
                f"{_display_time(row.get('timestamp_utc'))} | "
                f"{row.get('source_type', row.get('asset_type', row.get('type', 'Combined Generation')))} | "
                f"{_fmt(val)} | {v_ver} | {d_src}"
            )
    elif schedule:
        for row in schedule[:24]:
            lines.append(
                f"{_display_time(row.get('timestamp_utc'))} | Combined Generation | "
                f"{_fmt(row.get('generation_mw'))} | "
                f"{_display_metadata(gen_agent.get('model_version'))} | Synthetic dataset"
            )
    else:
        lines.append("No stored generation forecasts were available for this period.")

    lines.extend([
        "",
        "## 6. Demand Forecasts & Accuracy",
        f"Demand Model Data Source | {_display_metadata(demand_prov.get('model_data_source') or demand_agent.get('model_data_source') or 'synthetic_energy.csv')}",
        f"Demand Model Version | {_display_metadata(demand_prov.get('model_version') or demand_agent.get('model_version'))}",
        f"Demand Model Warning | {_display_metadata(demand_agent.get('warning') or demand_agent.get('validation_note') or 'Trained on synthetic demand data.')}",
        "Timestamp (UTC) | Predicted Demand (MW) | Actual Demand (MW) | Error (MW) | Baseline (MW)",
    ])

    matched_count = 0
    if demand_forecasts:
        for row in demand_forecasts[:24]:
            ts_str = _display_time(row.get("timestamp_utc"))
            pred = (
                row.get("predicted_demand_mw")
                or row.get("demand_forecast_mw")
                or row.get("demand_mw")
                or row.get("prediction_mw")
            )
            base = row.get("baseline_demand_mw") or row.get("demand_lag_24_mw")

            actual_val = actual_demand_by_time.get(ts_str)
            if actual_val is None:
                actual_str = "Not available"
                error_str = "Not available"
            else:
                matched_count += 1
                actual_str = _fmt(actual_val)
                try:
                    error_str = _fmt(abs(float(pred) - actual_val))
                except (ValueError, TypeError):
                    error_str = "Not available"

            lines.append(
                f"{ts_str} | {_fmt(pred)} | {actual_str} | {error_str} | {_fmt(base)}"
            )
    elif schedule:
        for row in schedule[:24]:
            ts_str = _display_time(row.get("timestamp_utc"))
            actual_val = actual_demand_by_time.get(ts_str)
            if actual_val is not None:
                matched_count += 1
                act_str = _fmt(actual_val)
                try:
                    err_str = _fmt(abs(float(row.get("demand_mw", 0)) - actual_val))
                except (ValueError, TypeError):
                    err_str = "Not available"
            else:
                act_str = "Not available"
                err_str = "Not available"

            lines.append(
                f"{ts_str} | {_fmt(row.get("demand_mw"))} | {act_str} | {err_str} | Not available"
            )
    else:
        lines.append("No stored demand forecasts were available for this period.")

    comp_status = "aligned_measurements_evaluated" if matched_count > 0 else "no_aligned_measurements"
    lines.append(f"Measurement Comparison Status | {comp_status}")
    lines.append(f"Aligned Measurement Count | {matched_count}")
    lines.append(
        "Comparison Note | Aligned measurements matched against forecast timestamps."
        if matched_count > 0
        else "Comparison Note | No stored asset measurements align exactly with forecast timestamps."
    )

    lines.extend([
        "",
        "## 7. Energy Balance & Optimization Schedule",
        f"Optimizer Status | {optimization.get('status', 'Optimal')}",
        f"Optimization Feasible | {optimization.get('feasible', True)}",
        f"Grid Imports | {_fmt(optimization.get('total_grid_import_mwh'))} MWh",
        f"Grid Exports | {_fmt(optimization.get('total_grid_export_mwh'))} MWh",
        f"Unmet Demand | {_fmt(optimization.get('total_unmet_demand_mwh'))} MWh",
        f"Curtailed Generation | {_fmt(optimization.get('total_curtailed_generation_mwh'))} MWh",
        f"Battery Efficiency Losses | {_fmt(optimization.get('total_efficiency_loss_mwh'))} MWh",
        "Timestamp (UTC) | Solar (MW) | Wind (MW) | Total Generation (MW) | Demand (MW) | Grid Import (MW) | Grid Export (MW) | Charge (MW) | Discharge (MW) | Battery SoC (%)",
    ])
    if schedule:
        for row in schedule[:24]:
            ts = row.get("timestamp_utc")
            s_val = row.get("solar_generation_mw") or row.get("solar_mw") or solar_by_time.get(ts)
            w_val = row.get("wind_generation_mw") or row.get("wind_mw") or wind_by_time.get(ts)
            lines.append(
                f"{_display_time(ts)} | {_fmt(s_val)} | {_fmt(w_val)} | "
                f"{_fmt(row.get('generation_mw'))} | {_fmt(row.get('demand_mw'))} | "
                f"{_fmt(row.get('grid_import_mw'))} | {_fmt(row.get('grid_export_mw'))} | "
                f"{_fmt(row.get('charge_mw'))} | {_fmt(row.get('discharge_mw'))} | "
                f"{_fmt(row.get('battery_soc_pct'))}"
            )
    else:
        lines.append("No optimization schedule was stored for this workflow run.")

    lines.extend([
        "",
        "## 8. Battery Storage",
        f"Battery Capacity | {_fmt(battery_capacity)} MWh",
        f"Initial State of Charge | {_fmt(battery_soc)}%",
        f"Maximum Charge Power | {_fmt(max_charge)} MW",
        f"Maximum Discharge Power | {_fmt(max_discharge)} MW",
        f"Configured Battery Available | {'Available' if battery_avail else 'Unavailable'}",
        "",
        "## 9. Anomalies & Findings",
        "Type | Severity | Timestamp (UTC) | Description | Investigation Status",
    ])
    if selected_anomalies:
        for finding, finding_time in selected_anomalies[:30]:
            lines.append(
                f"{finding.get('type', 'Finding')} | {finding.get('severity', 'Not available')} | "
                f"{_display_time(finding_time)} | {finding.get('description', 'Not available')} | "
                f"{finding.get('investigation_status', 'Review required')}"
            )
    else:
        lines.append("No stored findings were returned for this report period.")

    lines.extend([
        "",
        "## 10. Alerts",
        "ID | Severity | Title | Status | Created (UTC) | Acknowledged (UTC) | Reason",
    ])
    if alerts:
        for alert in alerts[:50]:
            lines.append(
                f"{getattr(alert, 'id', 'N/A')} | {getattr(alert, 'severity', 'Not available')} | "
                f"{getattr(alert, 'title', 'Alert')} | {getattr(alert, 'status', 'Not available')} | "
                f"{_display_time(getattr(alert, 'created_at', None))} | "
                f"{_display_time(getattr(alert, 'acknowledged_at', None))} | "
                f"{getattr(alert, 'reason', 'Not available')}"
            )
    else:
        lines.append("No related persisted alerts were found.")

    lines.extend([
        "",
        "## 11. Agent Execution & Recommendations",
        "Execution Step",
    ])
    trace = inner.get("execution_trace", []) or state.get("execution_trace", []) or []
    if trace:
        for step in trace[:40]:
            lines.append(str(step))
    else:
        lines.append("No execution trace was persisted with this workflow run.")

    lines.append("Recommendations")
    if not assets or any(not getattr(a, "is_active", False) for a in assets):
        lines.append("Review inactive assets before relying on their generation.")
    if matched_count == 0:
        lines.append("Validate forecasts against actual measurements when aligned data becomes available.")
    lines.append("Optimization results are recommendations, not executed grid dispatch.")

    lines.extend([
        "",
        "## 12. Operator Decisions & Sign-Off",
        f"Current Approval Status | {getattr(run, 'approval_status', 'pending')}",
        "Recorded At (UTC) | Decision | Plan Version | Operator | Comment",
    ])
    if approval_rows:
        for item in approval_rows:
            if isinstance(item, dict):
                lines.append(
                    f"{_display_time(item.get('recorded_at'))} | {item.get('decision', 'Not available')} | "
                    f"{item.get('plan_version', 'Not available')} | {item.get('operator_id', 'Not available')} | "
                    f"{item.get('comment', item.get('feedback', 'Not available'))}"
                )
    else:
        lines.append("No operator decision history was recorded for this period.")

    lines.extend([
        "",
        "Sign-off Affirmation: The undersigned operators acknowledge the optimization schedule recommendations above.",
        "Control Room Operator Signature: _____________________________________",
        "Grid Dispatch Coordinator Signature: _________________________________",
    ])

    pdf = _make_pdf(lines)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="renewable-energy-{workflow_id}.pdf"'},
    )