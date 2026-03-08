"""
ORGCOMMAND Dashboard Generator
Reads zoho_report.json and produces dashboard.html
Layout: Option A (Triage Board) with Executive Summary + Interactive Modals
"""

import json
import html as html_mod
from pathlib import Path
from datetime import datetime


def _esc(text: str) -> str:
    return html_mod.escape(str(text))


def _flag_label(flag: str) -> str:
    labels = {
        "GHOST_DIALER": "GHOST DIALER",
        "VOLUME_NO_OUTCOME": "VOLUME NO OUTCOME",
        "VM_RAMBLER": "VM RAMBLER",
        "FAKE_BUSY": "FAKE BUSY",
        "LOW_FOLLOW_THROUGH": "LOW FOLLOW-THROUGH",
    }
    return labels.get(flag, flag)


FLAG_EXPLANATIONS = {
    "GHOST_DIALER": (
        "This rep has an abnormally high percentage of calls lasting 5 seconds or less. "
        "This pattern indicates call-and-hang-up behavior, where the rep dials numbers and "
        "immediately disconnects to inflate their call volume metrics without having real conversations."
    ),
    "VOLUME_NO_OUTCOME": (
        "This rep is making a significant number of calls but has zero closed deals. "
        "High call volume without pipeline conversion suggests the rep is either calling "
        "unqualified leads, failing to advance conversations, or padding activity numbers."
    ),
    "VM_RAMBLER": (
        "This rep has high total talk time but a very low percentage of meaningful calls (30s+). "
        "This pattern suggests the rep is calling voicemail boxes and leaving long messages, or "
        "staying on dead lines to accumulate talk-time minutes without real engagement."
    ),
    "FAKE_BUSY": (
        "This rep has logged a high volume of activities (calls, tasks, events) but has zero deals "
        "in the pipeline. The activity is not translating into any pipeline movement, which indicates "
        "the rep may be logging fake or low-value activities to appear productive."
    ),
    "LOW_FOLLOW_THROUGH": (
        "This rep creates tasks but rarely completes them. A low task completion rate indicates "
        "poor follow-through on commitments, which directly impacts deal progression and "
        "customer experience."
    ),
}


def _score_bar_class(score: float) -> str:
    if score >= 7:
        return "high"
    if score >= 4:
        return "mid"
    return "low"


def _generate_recommendation(rep: dict) -> str:
    """Generate actionable recommendation based on rep's data."""
    color = rep["color"]
    flags = rep["flags"]
    flag_names = {f["flag"] for f in flags}
    or_score = rep["or"]
    cq = rep["call_quality"]
    dm = rep["deal_metrics"]
    act = rep["activity"]

    lines = []

    # RED tier — most severe
    if color == "RED":
        high_flags = [f for f in flags if f["severity"] == "HIGH"]
        if len(high_flags) >= 2:
            lines.append(
                "IMMEDIATE ACTION: This rep has multiple high-severity gaming flags. "
                "Schedule a direct conversation within 48 hours. Per the Red Rule, "
                "this level of performance warrants an action plan or separation discussion."
            )
        elif len(flags) >= 1:
            lines.append(
                "ACTION REQUIRED: This rep is in the bottom 20% of the team with active gaming flags. "
                "Have a direct conversation about expectations and set a 30-day improvement plan."
            )
        elif or_score <= 1.5:
            lines.append(
                "CRITICAL: This rep shows minimal activity and zero results. "
                "Determine if they are still active on the team. If so, they need an immediate "
                "performance conversation with clear deliverables for the next 2 weeks."
            )
        else:
            lines.append(
                "UNDERPERFORMING: This rep is in the bottom 20%. Review their workload and "
                "pipeline assignments. Set clear weekly targets and check in after 2 weeks."
            )

    # YELLOW tier — monitoring
    elif color == "YELLOW":
        if flag_names:
            lines.append(
                "MONITOR: This rep has gaming flags that need attention despite mid-tier ranking. "
                "Address the flagged behaviors in your next 1:1 and track for improvement."
            )
        else:
            lines.append(
                "ON TRACK: This rep is performing in the middle of the pack. "
                "Focus coaching on moving from YELLOW to GREEN by improving their weakest sub-score."
            )

    # GREEN tier — top performers
    else:
        if flag_names:
            lines.append(
                "TOP PERFORMER WITH CONCERNS: This rep ranks in the top 20% but has gaming flags. "
                "The flags may indicate process issues rather than intent. Discuss in 1:1 to understand context."
            )
        else:
            lines.append(
                "TOP PERFORMER: This rep is in the top 20% of the team. "
                "Recognize their performance and consider them for mentoring or leadership opportunities."
            )

    # Specific flag-based recommendations
    if "GHOST_DIALER" in flag_names:
        ghost_pct = cq.get("ghost_call_pct", 0)
        lines.append(
            f"GHOST CALLS: {ghost_pct}% of calls are under 5 seconds. "
            "Require this rep to log call outcomes for every dial. Review their call list "
            "for quality and consider switching to a verified contact list."
        )

    if "VM_RAMBLER" in flag_names:
        lines.append(
            "VM GAMING: High talk time with low meaningful calls suggests voicemail padding. "
            "Set a target for meaningful call percentage (aim for 40%+) and review weekly."
        )

    if "VOLUME_NO_OUTCOME" in flag_names:
        total_calls = cq.get("total_calls", 0)
        lines.append(
            f"CALL-TO-DEAL GAP: {total_calls} calls with no closed deals. "
            "Audit call recordings for quality. This rep may need sales training, "
            "better lead qualification, or a script review."
        )

    if "FAKE_BUSY" in flag_names:
        lines.append(
            "ACTIVITY THEATER: High activity count with zero pipeline. "
            "Shift from activity-based targets to outcome-based targets. "
            "Require weekly pipeline review showing stage progression."
        )

    if "LOW_FOLLOW_THROUGH" in flag_names:
        task_pct = act.get("task_completion_pct", 0)
        lines.append(
            f"FOLLOW-THROUGH: Only {task_pct}% of tasks completed. "
            "Implement daily task review and reduce task creation to only actionable items."
        )

    # Sub-score specific advice
    if rep["velocity"] < 3 and not dm.get("won"):
        lines.append(
            "VELOCITY: No deals closed means velocity score is at baseline. "
            "Focus on getting this rep's first deal through the pipeline to establish a baseline."
        )

    if rep["quality"] <= 2 and cq.get("total_calls", 0) > 0 and not flag_names:
        lines.append(
            "QUALITY: Low quality score despite call activity. Review call recordings "
            "and email engagement to identify coaching opportunities."
        )

    if rep["responsiveness"] < 3 and act.get("total_tasks", 0) == 0:
        lines.append(
            "RESPONSIVENESS: No task activity logged. Ensure this rep is using the CRM "
            "to track their work. Lack of CRM usage is itself a performance concern."
        )

    return "\n".join(lines)


def generate(report_path: str | None = None, output_path: str | None = None) -> str:
    base = Path(__file__).resolve().parent
    if report_path is None:
        report_path = str(base / "zoho_report.json")
    if output_path is None:
        output_path = str(base / "dashboard.html")

    with open(report_path) as f:
        report = json.load(f)

    ratings = report["ratings"]
    cross_val = report["cross_validation"]
    counts = report["record_counts"]
    days_back = report["days_back"]
    generated = report.get("generated_at", datetime.utcnow().isoformat())

    # Merge cross_validation detail into ratings
    reps = []
    for oid, r in ratings.items():
        cv = cross_val.get(oid, {})
        reps.append({
            "id": oid,
            "name": r["name"],
            "or": r["output_rating"],
            "color": r["color"],
            "velocity": r["velocity_score"],
            "quality": r["quality_score"],
            "responsiveness": r["responsiveness_score"],
            "flags": r["gaming_flags"],
            "flag_count": len(r["gaming_flags"]),
            "has_high": any(f["severity"] == "HIGH" for f in r["gaming_flags"]),
            "call_quality": cv.get("call_quality", {}),
            "deal_metrics": cv.get("deal_metrics", {}),
            "activity": cv.get("activity", {}),
        })

    # Sort: flag_count desc, then OR asc
    reps.sort(key=lambda r: (-r["flag_count"], r["or"]))

    green = [r for r in reps if r["color"] == "GREEN"]
    yellow = [r for r in reps if r["color"] == "YELLOW"]
    red = [r for r in reps if r["color"] == "RED"]

    total_flags = sum(r["flag_count"] for r in reps)
    total_deals = counts.get("deals", 0)
    total_activities = counts.get("calls", 0) + counts.get("tasks", 0) + counts.get("events", 0)

    avg_or = round(sum(r["or"] for r in reps) / len(reps), 1) if reps else 0
    avg_color_class = "critical" if avg_or < 5 else "warning" if avg_or < 8 else "ok"

    # Count flag types
    flag_type_counts: dict[str, int] = {}
    for r in reps:
        for f in r["flags"]:
            flag_type_counts[f["flag"]] = flag_type_counts.get(f["flag"], 0) + 1

    # Build HTML
    parts: list[str] = []
    parts.append(_html_head())
    parts.append(_html_header(days_back, generated))
    parts.append(_html_stats_bar(len(red), len(yellow), len(green), total_flags, total_deals, avg_or, avg_color_class))
    parts.append(_html_insight_banner(len(reps), total_activities, total_deals, len(red), flag_type_counts, len(green)))
    parts.append(_html_gaming_patterns(flag_type_counts))
    parts.append('<div class="swimlanes">')
    parts.append(_html_lane("critical", "Critical - Bottom 20%", red))
    parts.append(_html_lane("watch", "Watch - Middle 60%", yellow))
    parts.append(_html_lane("performing", "Performing - Top 20%", green))
    parts.append('</div>')

    # Generate all modals
    for r in reps:
        parts.append(_html_modal(r))

    parts.append(_html_footer(generated))
    parts.append(_html_script())
    parts.append('</body></html>')

    html_out = "\n".join(parts)
    with open(output_path, "w") as f:
        f.write(html_out)
    return output_path


# ---------------------------------------------------------------------------
# HTML Fragment Generators
# ---------------------------------------------------------------------------

def _html_head() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ORGCOMMAND - Sales Performance Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #fff; color: #1a1a1a; padding: 32px 40px;
    max-width: 1400px; margin: 0 auto;
  }

  /* Header */
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 28px; padding-bottom: 18px; border-bottom: 2px solid #e5e5e5; }
  .header h1 { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
  .header h1 span { color: #888; font-weight: 400; font-size: 20px; }
  .header .meta { font-size: 13px; color: #888; text-align: right; line-height: 1.6; }

  /* Stats bar */
  .stats-bar { display: flex; gap: 16px; margin-bottom: 24px; }
  .stat-box { flex: 1; background: #fafafa; border: 1px solid #e5e5e5; border-radius: 8px; padding: 18px 16px; text-align: center; }
  .stat-box .number { font-size: 34px; font-weight: 700; line-height: 1.1; }
  .stat-box .label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
  .stat-box .context { font-size: 11px; color: #aaa; margin-top: 5px; }
  .stat-box.critical { border-color: #fecaca; background: #fffafa; }
  .stat-box.critical .number { color: #dc2626; }
  .stat-box.warning { border-color: #fde68a; background: #fffdf5; }
  .stat-box.warning .number { color: #d97706; }
  .stat-box.ok { border-color: #bbf7d0; background: #f8fff8; }
  .stat-box.ok .number { color: #16a34a; }

  /* Insight banner */
  .insight-banner { background: #111; color: #e5e5e5; border-radius: 8px; padding: 18px 24px; margin-bottom: 24px; line-height: 1.6; font-size: 14px; }
  .insight-banner strong { color: #f87171; }
  .insight-banner em { color: #fbbf24; font-style: normal; font-weight: 600; }

  /* Gaming patterns */
  .patterns { display: flex; gap: 12px; margin-bottom: 28px; }
  .pattern-box { flex: 1; border: 1px solid #e5e5e5; border-radius: 6px; padding: 14px; }
  .pattern-box .p-count { font-size: 26px; font-weight: 700; color: #dc2626; line-height: 1.1; }
  .pattern-box .p-name { font-size: 11px; font-weight: 700; margin-top: 3px; letter-spacing: 0.3px; }
  .pattern-box .p-desc { font-size: 11px; color: #888; margin-top: 4px; line-height: 1.4; }

  /* Swim lanes */
  .swimlanes { display: flex; flex-direction: column; gap: 24px; }
  .lane { border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden; }
  .lane-header { padding: 12px 20px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center; }
  .lane-header .count { font-size: 12px; font-weight: 400; opacity: 0.7; }
  .lane.critical .lane-header { background: #fef2f2; color: #991b1b; border-bottom: 2px solid #fecaca; }
  .lane.watch .lane-header { background: #fffbeb; color: #92400e; border-bottom: 2px solid #fde68a; }
  .lane.performing .lane-header { background: #f0fdf4; color: #166534; border-bottom: 2px solid #bbf7d0; }
  .lane-body { padding: 14px; display: flex; flex-wrap: wrap; gap: 10px; min-height: 60px; }

  /* Rep cards */
  .rep-card {
    width: 240px; border: 1px solid #e5e5e5; border-radius: 6px;
    padding: 14px 14px 12px; background: #fff;
    transition: box-shadow 0.15s; cursor: pointer;
  }
  .rep-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.1); border-color: #ccc; }
  .rep-card.has-high-flags { border-left: 3px solid #dc2626; }
  .rep-card .card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
  .rep-card .name { font-size: 13px; font-weight: 600; line-height: 1.3; max-width: 160px; }
  .rep-card .or-badge { font-size: 18px; font-weight: 700; padding: 2px 8px; border-radius: 4px; line-height: 1.2; }
  .rep-card .or-badge.red { background: #fee2e2; color: #991b1b; }
  .rep-card .or-badge.yellow { background: #fef9c3; color: #854d0e; }
  .rep-card .or-badge.green { background: #dcfce7; color: #166534; }
  .rep-card .click-hint { font-size: 9px; color: #bbb; text-align: right; margin-top: 4px; }

  /* Sub-score bars */
  .sub-scores { margin-bottom: 8px; }
  .score-row { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
  .score-label { font-size: 10px; color: #999; width: 38px; text-align: right; }
  .score-track { flex: 1; height: 5px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
  .score-fill { height: 100%; border-radius: 3px; }
  .score-fill.high { background: #86efac; }
  .score-fill.mid { background: #fcd34d; }
  .score-fill.low { background: #fca5a5; }
  .score-val { font-size: 10px; color: #666; width: 22px; font-weight: 500; }

  /* Call stats */
  .call-stats { font-size: 10px; color: #888; margin-bottom: 6px; line-height: 1.5; border-top: 1px solid #f0f0f0; padding-top: 6px; }
  .call-stats .stat-line { display: flex; justify-content: space-between; }
  .call-stats .ghost { color: #dc2626; font-weight: 600; }
  .call-stats .meaningful { color: #16a34a; font-weight: 600; }
  .call-stats .num-val { font-weight: 600; color: #555; }

  /* Deal stats */
  .deal-stats { font-size: 10px; color: #888; line-height: 1.5; border-top: 1px solid #f0f0f0; padding-top: 6px; margin-bottom: 6px; }
  .deal-stats .stat-line { display: flex; justify-content: space-between; }

  /* Flags */
  .flags { margin-top: 6px; }
  .flag-badge { display: inline-block; font-size: 9px; font-weight: 600; padding: 2px 5px; border-radius: 3px; margin: 1px 1px 1px 0; line-height: 1.3; }
  .flag-badge.high { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
  .flag-badge.medium { background: #fff7ed; color: #9a3412; border: 1px solid #fed7aa; }
  .flag-badge.low { background: #f4f4f5; color: #71717a; border: 1px solid #e4e4e7; }

  .empty-note { color: #aaa; font-size: 13px; font-style: italic; padding: 16px 8px; }

  /* Footer */
  .footer { margin-top: 36px; padding-top: 16px; border-top: 1px solid #e5e5e5; font-size: 11px; color: #bbb; display: flex; justify-content: space-between; }

  /* ============ MODAL ============ */
  .modal-overlay {
    display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.45); z-index: 1000; justify-content: center; align-items: flex-start;
    padding: 40px 20px; overflow-y: auto;
  }
  .modal-overlay.active { display: flex; }

  .modal {
    background: #fff; border-radius: 10px; width: 100%; max-width: 720px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.2); position: relative;
    margin: auto;
  }

  .modal-top {
    display: flex; justify-content: space-between; align-items: center;
    padding: 24px 28px 18px; border-bottom: 1px solid #eee;
  }
  .modal-top .m-name { font-size: 20px; font-weight: 700; }
  .modal-top .m-or {
    font-size: 28px; font-weight: 700; padding: 4px 14px; border-radius: 6px;
  }
  .modal-top .m-or.red { background: #fee2e2; color: #991b1b; }
  .modal-top .m-or.yellow { background: #fef9c3; color: #854d0e; }
  .modal-top .m-or.green { background: #dcfce7; color: #166534; }

  .modal-close {
    position: absolute; top: 16px; right: 20px; background: none; border: none;
    font-size: 24px; color: #aaa; cursor: pointer; width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center; border-radius: 4px;
  }
  .modal-close:hover { background: #f0f0f0; color: #333; }

  .modal-body { padding: 24px 28px 28px; }

  .modal-section { margin-bottom: 24px; }
  .modal-section:last-child { margin-bottom: 0; }
  .modal-section h3 {
    font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;
    color: #888; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #f0f0f0;
  }

  /* Score breakdown */
  .m-scores { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
  .m-score-card { border: 1px solid #e5e5e5; border-radius: 6px; padding: 14px; text-align: center; }
  .m-score-card .m-sc-val { font-size: 28px; font-weight: 700; line-height: 1.1; }
  .m-score-card .m-sc-label { font-size: 11px; color: #888; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.3px; }
  .m-score-card .m-sc-weight { font-size: 10px; color: #bbb; margin-top: 2px; }
  .m-score-card .m-sc-bar { height: 4px; border-radius: 2px; margin-top: 8px; background: #f0f0f0; overflow: hidden; }
  .m-score-card .m-sc-fill { height: 100%; border-radius: 2px; }
  .m-sc-fill.high { background: #86efac; }
  .m-sc-fill.mid { background: #fcd34d; }
  .m-sc-fill.low { background: #fca5a5; }

  /* Metric rows */
  .m-metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .m-metric { display: flex; justify-content: space-between; padding: 8px 12px; background: #fafafa; border-radius: 4px; font-size: 13px; }
  .m-metric .m-label { color: #666; }
  .m-metric .m-value { font-weight: 600; color: #333; }
  .m-metric .m-value.danger { color: #dc2626; }
  .m-metric .m-value.success { color: #16a34a; }
  .m-metric.full-width { grid-column: 1 / -1; }

  /* Call breakdown bar */
  .m-call-bar { display: flex; height: 24px; border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
  .m-call-bar .segment { display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; color: #fff; min-width: 1px; }
  .m-call-bar .seg-ghost { background: #ef4444; }
  .m-call-bar .seg-short { background: #f59e0b; }
  .m-call-bar .seg-meaningful { background: #22c55e; }
  .m-call-legend { display: flex; gap: 16px; font-size: 11px; color: #888; margin-bottom: 4px; }
  .m-call-legend span { display: flex; align-items: center; gap: 4px; }
  .m-call-legend .dot { width: 8px; height: 8px; border-radius: 50%; }

  /* Flag cards */
  .m-flag-card {
    border: 1px solid #e5e5e5; border-radius: 6px; padding: 14px 16px; margin-bottom: 10px;
  }
  .m-flag-card:last-child { margin-bottom: 0; }
  .m-flag-card .m-flag-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .m-flag-card .m-flag-sev {
    font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .m-flag-sev.high { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
  .m-flag-sev.medium { background: #fff7ed; color: #9a3412; border: 1px solid #fed7aa; }
  .m-flag-sev.low { background: #f4f4f5; color: #71717a; border: 1px solid #e4e4e7; }
  .m-flag-card .m-flag-name { font-size: 13px; font-weight: 700; }
  .m-flag-card .m-flag-detail { font-size: 12px; color: #dc2626; margin-bottom: 6px; }
  .m-flag-card .m-flag-explain { font-size: 12px; color: #666; line-height: 1.5; }

  .m-no-data { color: #bbb; font-size: 13px; font-style: italic; }

  /* Recommendation box */
  .m-rec-box {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
    padding: 16px 18px;
  }
  .m-rec-box p {
    font-size: 13px; line-height: 1.6; color: #334155; margin-bottom: 10px;
  }
  .m-rec-box p:last-child { margin-bottom: 0; }
  .m-rec-box p strong { color: #111; }
  .m-rec-box.action-red { border-left: 4px solid #dc2626; }
  .m-rec-box.action-yellow { border-left: 4px solid #d97706; }
  .m-rec-box.action-green { border-left: 4px solid #16a34a; }

  /* Status pill in modal */
  .m-status-pill {
    display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 10px;
    border-radius: 12px; margin-left: 8px; vertical-align: middle;
  }
  .m-status-pill.red { background: #fee2e2; color: #991b1b; }
  .m-status-pill.yellow { background: #fef9c3; color: #854d0e; }
  .m-status-pill.green { background: #dcfce7; color: #166534; }

  @media print {
    body { padding: 16px; }
    .rep-card { break-inside: avoid; }
    .lane { break-inside: avoid; }
    .modal-overlay { display: none !important; }
  }
</style>
</head>
<body>"""


def _html_header(days_back: int, generated: str) -> str:
    try:
        dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        gen_str = dt.strftime("%b %d, %Y %H:%M UTC")
    except (ValueError, AttributeError):
        gen_str = generated
    return f"""
<div class="header">
  <h1>ORGCOMMAND <span>Sales Performance Dashboard</span></h1>
  <div class="meta">
    Period: Last {days_back} Days<br>
    Generated: {_esc(gen_str)}<br>
    Source: Zoho CRM
  </div>
</div>"""


def _html_stats_bar(red: int, yellow: int, green: int,
                    flags: int, deals: int, avg_or: float, avg_class: str) -> str:
    return f"""
<div class="stats-bar">
  <div class="stat-box {avg_class}">
    <div class="number">{avg_or}</div>
    <div class="label">Team Avg OR</div>
    <div class="context">Target: 8.0+</div>
  </div>
  <div class="stat-box critical">
    <div class="number">{red}</div>
    <div class="label">RED</div>
    <div class="context">Bottom 20%</div>
  </div>
  <div class="stat-box warning">
    <div class="number">{yellow}</div>
    <div class="label">YELLOW</div>
    <div class="context">Middle 60%</div>
  </div>
  <div class="stat-box ok">
    <div class="number">{green}</div>
    <div class="label">GREEN</div>
    <div class="context">Top 20%</div>
  </div>
  <div class="stat-box{"  critical" if flags > 20 else ""}">
    <div class="number">{flags}</div>
    <div class="label">Gaming Flags</div>
    <div class="context">Across team</div>
  </div>
  <div class="stat-box{"  critical" if deals <= 1 else ""}">
    <div class="number">{deals}</div>
    <div class="label">Deals</div>
    <div class="context">In pipeline</div>
  </div>
</div>"""


def _html_insight_banner(total_reps: int, total_activities: int,
                         total_deals: int, red_count: int,
                         flag_types: dict[str, int], green_count: int) -> str:
    fake_busy = flag_types.get("FAKE_BUSY", 0)
    ghost = flag_types.get("GHOST_DIALER", 0)
    vol_no_out = flag_types.get("VOLUME_NO_OUTCOME", 0)

    lines = []
    lines.append(f"Your team of <em>{total_reps} reps</em> logged "
                 f"<strong>{total_activities:,}+ activities</strong> in the last 90 days "
                 f"and produced <strong>{total_deals} deal{'s' if total_deals != 1 else ''}</strong>.")
    if fake_busy:
        lines.append(f"<em>{fake_busy} reps</em> flagged <strong>FAKE BUSY</strong> "
                     f"&mdash; high activity volume with zero pipeline movement.")
    if ghost:
        lines.append(f"<em>{ghost} rep{'s' if ghost > 1 else ''}</em> confirmed "
                     f"<strong>GHOST DIALER{'S' if ghost > 1 else ''}</strong> "
                     f"(&gt;50% of calls under 5 seconds).")
    if vol_no_out:
        lines.append(f"<em>{vol_no_out} reps</em> making 20+ calls with "
                     f"<strong>zero deals closed</strong>.")
    lines.append(f"Click any rep card for full assessment and recommendations.")

    return f"""
<div class="insight-banner">
  {" ".join(lines)}
</div>"""


def _html_gaming_patterns(flag_types: dict[str, int]) -> str:
    patterns = [
        ("FAKE_BUSY", "FAKE BUSY", "High activity volume, zero pipeline movement"),
        ("VOLUME_NO_OUTCOME", "VOLUME NO OUTCOME", "Many calls made, no deals closed"),
        ("VM_RAMBLER", "VM RAMBLER", "High talk time, low meaningful call %"),
        ("GHOST_DIALER", "GHOST DIALER", "Majority of calls under 5 seconds"),
        ("LOW_FOLLOW_THROUGH", "LOW FOLLOW-THROUGH", "Tasks created but never completed"),
    ]
    active = [(key, label, desc) for key, label, desc in patterns if flag_types.get(key, 0) > 0]
    if not active:
        return ""

    boxes = []
    for key, label, desc in active:
        count = flag_types.get(key, 0)
        boxes.append(f"""  <div class="pattern-box">
    <div class="p-count">{count}</div>
    <div class="p-name">{_esc(label)}</div>
    <div class="p-desc">{_esc(desc)}</div>
  </div>""")

    return f"""
<div class="patterns">
{chr(10).join(boxes)}
</div>"""


def _html_rep_card(rep: dict) -> str:
    color = rep["color"].lower()
    has_high = "has-high-flags" if rep["has_high"] else ""
    vel_class = _score_bar_class(rep["velocity"])
    qual_class = _score_bar_class(rep["quality"])
    resp_class = _score_bar_class(rep["responsiveness"])
    safe_id = rep["id"].replace("'", "")

    cq = rep["call_quality"]
    dm = rep["deal_metrics"]
    act = rep["activity"]

    parts = []
    parts.append(f'<div class="rep-card {has_high}" onclick="openModal(\'{safe_id}\')">')
    parts.append(f'  <div class="card-top">')
    parts.append(f'    <div class="name">{_esc(rep["name"])}</div>')
    parts.append(f'    <div class="or-badge {color}">{rep["or"]}</div>')
    parts.append(f'  </div>')

    # Sub-score bars
    parts.append(f'  <div class="sub-scores">')
    for label, val, cls in [("Vel", rep["velocity"], vel_class),
                             ("Qual", rep["quality"], qual_class),
                             ("Resp", rep["responsiveness"], resp_class)]:
        width = max(2, min(100, val * 10))
        parts.append(f'    <div class="score-row">'
                     f'<div class="score-label">{label}</div>'
                     f'<div class="score-track"><div class="score-fill {cls}" style="width:{width}%;"></div></div>'
                     f'<div class="score-val">{val}</div></div>')
    parts.append(f'  </div>')

    # Call stats (if any)
    if cq.get("total_calls", 0) > 0:
        ghost_pct = cq.get("ghost_call_pct", 0)
        meaningful_pct = cq.get("meaningful_pct", 0)
        total_calls = cq.get("total_calls", 0)
        avg_dur = cq.get("avg_duration_secs", 0)
        ghost_cls = ' class="ghost"' if ghost_pct > 40 else ""
        mean_cls = ' class="meaningful"' if meaningful_pct >= 50 else ""
        parts.append(f'  <div class="call-stats">')
        parts.append(f'    <div class="stat-line"><span>Calls</span><span class="num-val">{total_calls}</span></div>')
        parts.append(f'    <div class="stat-line"><span>Ghost (&#8804;5s)</span><span{ghost_cls}>{ghost_pct}%</span></div>')
        parts.append(f'    <div class="stat-line"><span>Meaningful (30s+)</span><span{mean_cls}>{meaningful_pct}%</span></div>')
        parts.append(f'    <div class="stat-line"><span>Avg Duration</span><span>{avg_dur}s</span></div>')
        parts.append(f'  </div>')

    # Activity/Deal stats
    has_activity = act.get("total_tasks", 0) > 0 or act.get("total_events", 0) > 0
    has_deals = dm.get("total_deals", 0) > 0
    if has_activity or has_deals:
        parts.append(f'  <div class="deal-stats">')
        if has_activity:
            parts.append(f'    <div class="stat-line"><span>Tasks</span><span class="num-val">{act.get("total_tasks", 0)} ({act.get("task_completion_pct", 0)}% done)</span></div>')
            parts.append(f'    <div class="stat-line"><span>Events</span><span class="num-val">{act.get("total_events", 0)}</span></div>')
        if has_deals:
            parts.append(f'    <div class="stat-line"><span>Deals</span><span class="num-val">{dm.get("won", 0)}W / {dm.get("lost", 0)}L / {dm.get("open", 0)}O</span></div>')
            if dm.get("win_rate_pct") is not None:
                parts.append(f'    <div class="stat-line"><span>Win Rate</span><span class="num-val">{dm["win_rate_pct"]}%</span></div>')
        parts.append(f'  </div>')

    # Flags
    if rep["flags"]:
        parts.append(f'  <div class="flags">')
        for f in rep["flags"]:
            sev = f["severity"].lower()
            parts.append(f'    <span class="flag-badge {sev}">{_esc(_flag_label(f["flag"]))}</span>')
        parts.append(f'  </div>')

    parts.append(f'  <div class="click-hint">Click for full assessment</div>')
    parts.append(f'</div>')
    return "\n".join(parts)


def _html_modal(rep: dict) -> str:
    """Generate a detailed modal popup for a rep."""
    safe_id = rep["id"].replace("'", "")
    color = rep["color"].lower()
    color_label = rep["color"]
    cq = rep["call_quality"]
    dm = rep["deal_metrics"]
    act = rep["activity"]

    vel_class = _score_bar_class(rep["velocity"])
    qual_class = _score_bar_class(rep["quality"])
    resp_class = _score_bar_class(rep["responsiveness"])

    recommendation = _generate_recommendation(rep)

    parts = []
    parts.append(f'<div class="modal-overlay" id="modal-{safe_id}">')
    parts.append(f'<div class="modal">')

    # Top bar
    parts.append(f'  <div class="modal-top">')
    parts.append(f'    <div>')
    parts.append(f'      <span class="m-name">{_esc(rep["name"])}</span>')
    parts.append(f'      <span class="m-status-pill {color}">{color_label} &mdash; '
                 f'{"Bottom 20%" if color_label == "RED" else "Middle 60%" if color_label == "YELLOW" else "Top 20%"}</span>')
    parts.append(f'    </div>')
    parts.append(f'    <div class="m-or {color}">{rep["or"]}</div>')
    parts.append(f'  </div>')
    parts.append(f'  <button class="modal-close" onclick="closeModal(\'{safe_id}\')">&times;</button>')

    parts.append(f'  <div class="modal-body">')

    # Section 1: Score Breakdown
    parts.append(f'    <div class="modal-section">')
    parts.append(f'      <h3>Output Rating Breakdown</h3>')
    parts.append(f'      <div class="m-scores">')
    for label, val, weight, cls in [
        ("Velocity", rep["velocity"], "40%", vel_class),
        ("Quality", rep["quality"], "35%", qual_class),
        ("Responsiveness", rep["responsiveness"], "25%", resp_class),
    ]:
        width = max(2, min(100, val * 10))
        parts.append(f'        <div class="m-score-card">')
        parts.append(f'          <div class="m-sc-val">{val}</div>')
        parts.append(f'          <div class="m-sc-label">{label}</div>')
        parts.append(f'          <div class="m-sc-weight">Weight: {weight}</div>')
        parts.append(f'          <div class="m-sc-bar"><div class="m-sc-fill {cls}" style="width:{width}%;"></div></div>')
        parts.append(f'        </div>')
    parts.append(f'      </div>')
    parts.append(f'    </div>')

    # Section 2: Call Quality
    parts.append(f'    <div class="modal-section">')
    parts.append(f'      <h3>Call Quality Breakdown</h3>')
    if cq.get("total_calls", 0) > 0:
        total = cq["total_calls"]
        ghost = cq.get("ghost_calls", 0)
        short = cq.get("short_calls", 0)
        meaningful = cq.get("meaningful_calls", 0)
        ghost_pct = round(ghost / total * 100, 1) if total else 0
        short_pct = round(short / total * 100, 1) if total else 0
        mean_pct = round(meaningful / total * 100, 1) if total else 0

        parts.append(f'      <div class="m-call-bar">')
        if ghost_pct > 0:
            parts.append(f'        <div class="segment seg-ghost" style="width:{max(ghost_pct, 3)}%;">{ghost}</div>')
        if short_pct > 0:
            parts.append(f'        <div class="segment seg-short" style="width:{max(short_pct, 3)}%;">{short}</div>')
        if mean_pct > 0:
            parts.append(f'        <div class="segment seg-meaningful" style="width:{max(mean_pct, 3)}%;">{meaningful}</div>')
        parts.append(f'      </div>')
        parts.append(f'      <div class="m-call-legend">')
        parts.append(f'        <span><span class="dot" style="background:#ef4444;"></span> Ghost (&#8804;5s): {ghost} ({ghost_pct}%)</span>')
        parts.append(f'        <span><span class="dot" style="background:#f59e0b;"></span> Short (6-29s): {short} ({short_pct}%)</span>')
        parts.append(f'        <span><span class="dot" style="background:#22c55e;"></span> Meaningful (30s+): {meaningful} ({mean_pct}%)</span>')
        parts.append(f'      </div>')

        ghost_cls = ' danger' if cq.get("ghost_call_pct", 0) > 40 else ""
        mean_cls = ' success' if cq.get("meaningful_pct", 0) >= 50 else ""
        parts.append(f'      <div class="m-metric-grid">')
        parts.append(f'        <div class="m-metric"><span class="m-label">Total Calls</span><span class="m-value">{total}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Ghost Call %</span><span class="m-value{ghost_cls}">{cq.get("ghost_call_pct", 0)}%</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Meaningful %</span><span class="m-value{mean_cls}">{cq.get("meaningful_pct", 0)}%</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Avg Duration</span><span class="m-value">{cq.get("avg_duration_secs", 0)}s</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Total Talk Time</span><span class="m-value">{cq.get("total_talk_minutes", 0)} min</span></div>')
        # Status breakdown
        statuses = cq.get("status_breakdown", {})
        if statuses:
            status_str = ", ".join(f"{k}: {v}" for k, v in sorted(statuses.items(), key=lambda x: -x[1]))
            parts.append(f'        <div class="m-metric full-width"><span class="m-label">Call Outcomes</span><span class="m-value">{_esc(status_str)}</span></div>')
        parts.append(f'      </div>')
    else:
        parts.append(f'      <div class="m-no-data">No call data recorded for this rep.</div>')
    parts.append(f'    </div>')

    # Section 3: Activity Details
    parts.append(f'    <div class="modal-section">')
    parts.append(f'      <h3>Activity Details</h3>')
    has_act = act.get("total_tasks", 0) > 0 or act.get("total_events", 0) > 0
    if has_act:
        comp_cls = ' success' if act.get("task_completion_pct", 0) >= 70 else ' danger' if act.get("task_completion_pct", 0) < 30 else ""
        parts.append(f'      <div class="m-metric-grid">')
        parts.append(f'        <div class="m-metric"><span class="m-label">Total Tasks</span><span class="m-value">{act.get("total_tasks", 0)}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Completed Tasks</span><span class="m-value">{act.get("completed_tasks", 0)}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Completion Rate</span><span class="m-value{comp_cls}">{act.get("task_completion_pct", 0)}%</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Events Logged</span><span class="m-value">{act.get("total_events", 0)}</span></div>')
        parts.append(f'      </div>')
    else:
        parts.append(f'      <div class="m-no-data">No task or event data recorded for this rep.</div>')
    parts.append(f'    </div>')

    # Section 4: Deal Metrics
    parts.append(f'    <div class="modal-section">')
    parts.append(f'      <h3>Deal Pipeline</h3>')
    if dm.get("total_deals", 0) > 0:
        wr_cls = ' success' if dm.get("win_rate_pct", 0) >= 50 else ' danger' if dm.get("win_rate_pct", 0) < 20 else ""
        parts.append(f'      <div class="m-metric-grid">')
        parts.append(f'        <div class="m-metric"><span class="m-label">Total Deals</span><span class="m-value">{dm.get("total_deals", 0)}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Won</span><span class="m-value success">{dm.get("won", 0)}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Lost</span><span class="m-value danger">{dm.get("lost", 0)}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Open</span><span class="m-value">{dm.get("open", 0)}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Win Rate</span><span class="m-value{wr_cls}">{dm.get("win_rate_pct", 0)}%</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Total Revenue</span><span class="m-value">${dm.get("total_revenue", 0):,.2f}</span></div>')
        parts.append(f'        <div class="m-metric"><span class="m-label">Avg Deal Size</span><span class="m-value">${dm.get("avg_deal_size", 0):,.2f}</span></div>')
        vel = dm.get("avg_velocity_days")
        parts.append(f'        <div class="m-metric"><span class="m-label">Avg Velocity</span><span class="m-value">{f"{vel} days" if vel else "N/A"}</span></div>')
        parts.append(f'      </div>')
    else:
        parts.append(f'      <div class="m-no-data">No deals in pipeline for this rep (last 90 days).</div>')
    parts.append(f'    </div>')

    # Section 5: Gaming Flags
    parts.append(f'    <div class="modal-section">')
    parts.append(f'      <h3>Gaming Flag Analysis</h3>')
    if rep["flags"]:
        for f in rep["flags"]:
            sev = f["severity"].lower()
            flag_key = f["flag"]
            explanation = FLAG_EXPLANATIONS.get(flag_key, "")
            parts.append(f'      <div class="m-flag-card">')
            parts.append(f'        <div class="m-flag-top">')
            parts.append(f'          <span class="m-flag-sev {sev}">{f["severity"]}</span>')
            parts.append(f'          <span class="m-flag-name">{_esc(_flag_label(flag_key))}</span>')
            parts.append(f'        </div>')
            parts.append(f'        <div class="m-flag-detail">{_esc(f["detail"])}</div>')
            if explanation:
                parts.append(f'        <div class="m-flag-explain">{_esc(explanation)}</div>')
            parts.append(f'      </div>')
    else:
        parts.append(f'      <div class="m-no-data">No gaming flags detected for this rep.</div>')
    parts.append(f'    </div>')

    # Section 6: Recommendations
    parts.append(f'    <div class="modal-section">')
    parts.append(f'      <h3>Assessment &amp; Recommendations</h3>')
    parts.append(f'      <div class="m-rec-box action-{color}">')
    for paragraph in recommendation.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        # Bold the label before the colon
        if ":" in paragraph:
            label_part, _, rest = paragraph.partition(":")
            parts.append(f'        <p><strong>{_esc(label_part)}:</strong> {_esc(rest.strip())}</p>')
        else:
            parts.append(f'        <p>{_esc(paragraph)}</p>')
    parts.append(f'      </div>')
    parts.append(f'    </div>')

    parts.append(f'  </div>')  # modal-body
    parts.append(f'</div>')    # modal
    parts.append(f'</div>')    # modal-overlay
    return "\n".join(parts)


def _html_lane(lane_class: str, title: str, reps: list[dict]) -> str:
    lane_names = {"critical": "RED", "watch": "YELLOW", "performing": "GREEN"}
    parts = []
    parts.append(f'<div class="lane {lane_class}">')
    parts.append(f'  <div class="lane-header">{_esc(title)}<span class="count">{len(reps)} rep{"s" if len(reps) != 1 else ""}</span></div>')
    parts.append(f'  <div class="lane-body">')
    if reps:
        for r in reps:
            parts.append(_html_rep_card(r))
    else:
        threshold = {"critical": "Bottom 20%", "watch": "Middle 60%", "performing": "Top 20%"}
        parts.append(f'    <div class="empty-note">No reps currently in {lane_names[lane_class]} status ({threshold[lane_class]})</div>')
    parts.append(f'  </div>')
    parts.append(f'</div>')
    return "\n".join(parts)


def _html_footer(generated: str) -> str:
    return f"""
<div class="footer">
  <span>ORGCOMMAND Sales Performance Dashboard</span>
  <span>Data: Zoho CRM &bull; Anti-gaming cross-validation enabled &bull; Generated {_esc(generated[:19])}</span>
</div>"""


def _html_script() -> str:
    return """
<script>
function openModal(id) {
  var el = document.getElementById('modal-' + id);
  if (el) {
    el.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}
function closeModal(id) {
  var el = document.getElementById('modal-' + id);
  if (el) {
    el.classList.remove('active');
    document.body.style.overflow = '';
  }
}
// Close on overlay click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    document.body.style.overflow = '';
  }
});
// Close on Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var modals = document.querySelectorAll('.modal-overlay.active');
    modals.forEach(function(m) { m.classList.remove('active'); });
    document.body.style.overflow = '';
  }
});
</script>"""


if __name__ == "__main__":
    out = generate()
    print(f"Dashboard generated: {out}")
