"""
ORGCOMMAND Kixie CSV Call Importer
Parses Kixie call history CSV export, matches users to Zoho reps,
and merges call quality metrics into zoho_report.json.

Usage:
    python3 -m integrations.kixie_csv_importer path/to/kixie_export.csv

The script will:
1. Auto-detect CSV column mapping (handles multiple Kixie export formats)
2. Parse call records: user, duration, outcome, timestamp
3. Match Kixie users to Zoho reps by fuzzy name matching
4. Calculate call quality metrics (ghost %, meaningful %, talk time)
5. Merge into zoho_report.json and regenerate dashboard
"""

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Column Detection
# ---------------------------------------------------------------------------

# Known Kixie CSV column names (from webhook payloads and dashboard exports).
# The importer tries all variations and maps to canonical names.
COLUMN_ALIASES = {
    "user": [
        "user", "agent", "agent name", "agent_name", "agentname",
        "rep", "rep name", "rep_name", "fname", "first name",
        "caller", "caller name", "calleridname", "callerid_name",
        "email", "agent email", "agent_email", "user email", "user_email",
    ],
    "user_email": [
        "email", "agent email", "agent_email", "user email", "user_email",
        "agent_email_address", "user_email_address",
    ],
    "duration": [
        "duration", "call duration", "call_duration", "callduration",
        "duration (seconds)", "duration_seconds", "talk time", "talk_time",
        "talktime", "length", "call length", "call_length",
    ],
    "outcome": [
        "outcome", "call outcome", "call_outcome", "calloutcome",
        "callstatus", "call status", "call_status", "status",
        "callresult", "call result", "call_result", "result",
        "disposition", "call disposition", "call_disposition",
    ],
    "timestamp": [
        "calldate", "call date", "call_date", "date", "datetime",
        "date/time", "timestamp", "time", "call time", "call_time",
        "created", "created_at", "start time", "start_time",
    ],
    "call_type": [
        "calltype", "call type", "call_type", "type", "direction",
        "call direction", "call_direction",
    ],
    "phone": [
        "tonumber", "to number", "to_number", "phone", "phone number",
        "phone_number", "fromnumber", "from number", "from_number",
        "target", "number", "customernumber", "customer number",
    ],
}


def _detect_columns(header_row: list[str]) -> dict[str, int | None]:
    """Map canonical field names to column indices by matching aliases."""
    normalized = [h.strip().lower().replace(" ", " ") for h in header_row]
    mapping: dict[str, int | None] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        mapping[canonical] = None
        for alias in aliases:
            for i, col in enumerate(normalized):
                if col == alias or col.replace("_", " ") == alias:
                    mapping[canonical] = i
                    break
            if mapping[canonical] is not None:
                break

    return mapping


# ---------------------------------------------------------------------------
# 2. CSV Parsing
# ---------------------------------------------------------------------------

def _parse_duration(val: str) -> int:
    """Parse duration to seconds. Handles: '267', '4:27', '00:04:27', '4m 27s'."""
    val = val.strip()
    if not val or val == "--" or val.lower() == "n/a":
        return 0

    # Pure seconds
    try:
        return int(float(val))
    except ValueError:
        pass

    # MM:SS or HH:MM:SS
    parts = val.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass

    # "4m 27s" or "4min 27sec"
    m = re.match(r"(\d+)\s*m(?:in)?\s*(\d+)\s*s", val, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))

    return 0


def _parse_timestamp(val: str) -> datetime | None:
    """Parse timestamp from various formats."""
    val = val.strip()
    if not val:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue

    # ISO format fallback
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass

    return None


def _normalize_outcome(val: str) -> str:
    """Normalize call outcome to: connected, voicemail, no_answer, missed, unknown."""
    val = val.strip().lower()
    connected = {"answered", "connected", "completed", "talked", "human", "live"}
    voicemail = {"voicemail", "vm", "left voicemail", "machine", "machinedetected"}
    no_answer = {"no answer", "no-answer", "noanswer", "unanswered", "not answered",
                 "busy", "failed", "cancelled", "canceled", "rejected", "unattended",
                 "unattended dialler", "unattended dialed"}
    missed = {"missed", "abandoned"}

    if val in connected or "answer" in val and "no" not in val:
        return "connected"
    if val in voicemail or "voicemail" in val or "vm" in val:
        return "voicemail"
    if val in no_answer or "busy" in val or "fail" in val:
        return "no_answer"
    if val in missed:
        return "missed"
    return "unknown"


def parse_csv(csv_path: str, days_back: int = 90) -> list[dict]:
    """Parse Kixie CSV export into normalized call records."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    records = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        # Detect delimiter
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel

        reader = csv.reader(f, dialect)
        header = next(reader)
        col_map = _detect_columns(header)

        # Report mapping
        print(f"[Kixie CSV] Detected columns from {len(header)} headers:")
        for field, idx in col_map.items():
            if idx is not None:
                print(f"  {field:15s} -> column {idx} ({header[idx]})")
            else:
                print(f"  {field:15s} -> NOT FOUND")

        user_col = col_map.get("user")
        email_col = col_map.get("user_email")
        dur_col = col_map.get("duration")
        outcome_col = col_map.get("outcome")
        ts_col = col_map.get("timestamp")
        type_col = col_map.get("call_type")

        if user_col is None and email_col is None:
            print("[Kixie CSV] WARNING: No user/agent column found. Will use 'Unknown'.")

        row_count = 0
        skipped = 0
        for row in reader:
            row_count += 1
            if not row or len(row) <= max((c for c in col_map.values() if c is not None), default=0):
                skipped += 1
                continue

            # Timestamp filter
            ts = _parse_timestamp(row[ts_col]) if ts_col is not None else None
            if ts and ts < cutoff:
                skipped += 1
                continue

            # User identification
            user = ""
            if user_col is not None:
                user = row[user_col].strip()
            user_email = ""
            if email_col is not None:
                user_email = row[email_col].strip()

            records.append({
                "user": user or user_email or "Unknown",
                "user_email": user_email,
                "duration_secs": _parse_duration(row[dur_col]) if dur_col is not None else 0,
                "outcome": _normalize_outcome(row[outcome_col]) if outcome_col is not None else "unknown",
                "timestamp": ts.isoformat() if ts else None,
                "call_type": row[type_col].strip().lower() if type_col is not None else "unknown",
            })

        print(f"[Kixie CSV] Parsed {len(records)} calls ({skipped} skipped) from {row_count} rows")

    return records


# ---------------------------------------------------------------------------
# 3. User Matching (Kixie users -> Zoho rep IDs)
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = re.sub(r"[._\-]", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _name_tokens(name: str) -> set[str]:
    return set(_normalize_name(name).split())


def match_users(kixie_calls: list[dict], zoho_report_path: str) -> dict[str, str | None]:
    """
    Match Kixie user names/emails to Zoho rep IDs.
    Returns: {kixie_user: zoho_oid or None}
    """
    with open(zoho_report_path) as f:
        report = json.load(f)

    # Build Zoho rep lookup
    zoho_reps: dict[str, str] = {}  # oid -> name
    zoho_emails: dict[str, str] = {}  # email -> oid
    for oid, r in report.get("cross_validation", {}).items():
        name = r.get("name", "")
        zoho_reps[oid] = name
        # Extract email from call_quality status_breakdown or deal data if available
        # For now, we rely on name matching

    # Get unique Kixie users
    kixie_users = set()
    for c in kixie_calls:
        kixie_users.add(c["user"])

    matches: dict[str, str | None] = {}
    unmatched = []

    for ku in sorted(kixie_users):
        ku_norm = _normalize_name(ku)
        ku_tokens = _name_tokens(ku)
        best_oid = None
        best_score = 0

        # Try email match first (if Kixie user looks like an email)
        if "@" in ku:
            local_part = ku.split("@")[0]
            ku_tokens = _name_tokens(local_part)

        for oid, zname in zoho_reps.items():
            z_norm = _normalize_name(zname)
            z_tokens = _name_tokens(zname)

            # Exact match
            if ku_norm == z_norm:
                best_oid = oid
                best_score = 100
                break

            # Token overlap (handles "James K" matching "james.k")
            if ku_tokens and z_tokens:
                overlap = len(ku_tokens & z_tokens)
                total = max(len(ku_tokens), len(z_tokens))
                score = (overlap / total) * 100 if total else 0

                # Boost if first token matches (first name)
                ku_first = sorted(ku_tokens)[0] if ku_tokens else ""
                z_first = sorted(z_tokens)[0] if z_tokens else ""
                if ku_first and z_first and ku_first[0] == z_first[0]:
                    score += 10

                # Substring match bonus
                if ku_norm in z_norm or z_norm in ku_norm:
                    score += 30

                if score > best_score:
                    best_score = score
                    best_oid = oid

        # Require minimum confidence
        if best_score >= 50:
            matches[ku] = best_oid
            z_name = zoho_reps.get(best_oid, "?")
            print(f"  MATCH: '{ku}' -> '{z_name}' (score: {best_score:.0f})")
        else:
            matches[ku] = None
            unmatched.append(ku)

    if unmatched:
        print(f"\n  UNMATCHED ({len(unmatched)}): {', '.join(unmatched)}")
        print("  You can add manual mappings in KIXIE_MANUAL_MAP below.")

    return matches


# Manual override map: add entries here if auto-matching fails.
# Format: {"Kixie Display Name": "zoho_owner_id"}
KIXIE_MANUAL_MAP: dict[str, str] = {
    # Example: "Jim K": "5062310000641109001",
}


# ---------------------------------------------------------------------------
# 4. Call Quality Metrics
# ---------------------------------------------------------------------------

GHOST_THRESHOLD = 5      # seconds
MEANINGFUL_THRESHOLD = 30 # seconds


def calc_kixie_metrics(calls: list[dict], user_match: dict[str, str | None]) -> dict[str, dict]:
    """
    Calculate per-Zoho-rep call quality metrics from Kixie data.
    Returns: {zoho_oid: {metrics...}}
    """
    # Group calls by Zoho rep
    by_rep: dict[str, list[dict]] = defaultdict(list)
    unmatched_calls = 0

    for c in calls:
        kixie_user = c["user"]
        # Check manual map first, then auto-match
        zoho_oid = KIXIE_MANUAL_MAP.get(kixie_user) or user_match.get(kixie_user)
        if zoho_oid:
            by_rep[zoho_oid].append(c)
        else:
            unmatched_calls += 1

    if unmatched_calls:
        print(f"[Kixie Metrics] {unmatched_calls} calls from unmatched users (skipped)")

    results = {}
    for oid, rep_calls in by_rep.items():
        total = len(rep_calls)
        durations = [c["duration_secs"] for c in rep_calls]

        ghost = sum(1 for d in durations if d <= GHOST_THRESHOLD)
        short = sum(1 for d in durations if GHOST_THRESHOLD < d < MEANINGFUL_THRESHOLD)
        meaningful = sum(1 for d in durations if d >= MEANINGFUL_THRESHOLD)
        total_secs = sum(durations)

        # Outcome breakdown
        outcomes = defaultdict(int)
        for c in rep_calls:
            outcomes[c["outcome"]] += 1

        results[oid] = {
            "source": "kixie",
            "total_calls": total,
            "ghost_calls": ghost,
            "short_calls": short,
            "meaningful_calls": meaningful,
            "ghost_call_pct": round(ghost / total * 100, 1) if total else 0,
            "meaningful_pct": round(meaningful / total * 100, 1) if total else 0,
            "total_talk_minutes": round(total_secs / 60, 1),
            "avg_duration_secs": round(total_secs / total, 1) if total else 0,
            "status_breakdown": dict(outcomes),
            "connected_pct": round(outcomes.get("connected", 0) / total * 100, 1) if total else 0,
        }

    return results


# ---------------------------------------------------------------------------
# 5. Merge into zoho_report.json
# ---------------------------------------------------------------------------

def merge_into_report(kixie_metrics: dict[str, dict], report_path: str) -> str:
    """
    Replace Zoho call_quality with Kixie call_quality where available.
    Recalculate output ratings and regenerate dashboard.
    """
    with open(report_path) as f:
        report = json.load(f)

    merged_count = 0
    for oid, km in kixie_metrics.items():
        if oid in report.get("cross_validation", {}):
            report["cross_validation"][oid]["call_quality"] = km
            merged_count += 1

    report["kixie_merge"] = {
        "merged_at": datetime.utcnow().isoformat(),
        "reps_updated": merged_count,
        "source": "kixie_csv",
    }

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"[Merge] Updated {merged_count} reps with Kixie call data in {report_path}")
    return report_path


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------

def run(csv_path: str, days_back: int = 90):
    """Full pipeline: parse CSV -> match users -> calc metrics -> merge -> dashboard."""
    base = Path(__file__).resolve().parent
    report_path = str(base / "zoho_report.json")

    print(f"\n{'='*60}")
    print(f"  ORGCOMMAND Kixie CSV Importer")
    print(f"{'='*60}\n")

    # 1. Parse CSV
    print("[Step 1] Parsing Kixie CSV...")
    calls = parse_csv(csv_path, days_back)
    if not calls:
        print("No calls found in CSV. Exiting.")
        return

    # Show sample
    print(f"\nSample record: {json.dumps(calls[0], indent=2)}\n")

    # 2. Match users
    print("[Step 2] Matching Kixie users to Zoho reps...")
    user_match = match_users(calls, report_path)

    # 3. Calculate metrics
    print(f"\n[Step 3] Calculating call quality metrics...")
    metrics = calc_kixie_metrics(calls, user_match)
    for oid, m in sorted(metrics.items(), key=lambda x: x[1]["total_calls"], reverse=True)[:10]:
        print(f"  {oid[:15]}... calls={m['total_calls']} ghost={m['ghost_call_pct']}% "
              f"meaningful={m['meaningful_pct']}% connected={m['connected_pct']}%")

    # 4. Merge into report
    print(f"\n[Step 4] Merging into zoho_report.json...")
    merge_into_report(metrics, report_path)

    # 5. Regenerate dashboard
    print(f"\n[Step 5] Regenerating dashboard...")
    from integrations.generate_dashboard import generate
    dashboard_path = generate(report_path)
    print(f"Dashboard updated: {dashboard_path}")

    print(f"\n{'='*60}")
    print(f"  Done. {len(metrics)} reps updated with Kixie call data.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m integrations.kixie_csv_importer <kixie_export.csv> [days_back]")
        print("\nExpected CSV columns (auto-detected):")
        for field, aliases in COLUMN_ALIASES.items():
            print(f"  {field}: {', '.join(aliases[:4])}...")
        sys.exit(1)

    csv_file = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    run(csv_file, days)
