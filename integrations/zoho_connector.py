"""
ORGCOMMAND Zoho CRM Connector
Fetches deals, calls, activities and calculates anti-gaming quality metrics.
Stdlib only (urllib, json, os).
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Environment / Credentials
# ---------------------------------------------------------------------------

def load_env(env_path: str | None = None) -> dict[str, str]:
    """Load .env file into os.environ and return the values."""
    if env_path is None:
        env_path = str(Path(__file__).resolve().parent.parent / ".env")
    env_vars = {}
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                os.environ.setdefault(key, value)
                env_vars[key] = value
    except FileNotFoundError:
        raise FileNotFoundError(f".env file not found at {env_path}")
    return env_vars


def _required_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Missing required env var: {key}")
    return val


# ---------------------------------------------------------------------------
# 2. OAuth Token Management
# ---------------------------------------------------------------------------

class ZohoAuth:
    """Handles Zoho OAuth2 token refresh using refresh_token grant."""

    def __init__(self):
        self.client_id = _required_env("ZOHO_CLIENT_ID")
        self.client_secret = _required_env("ZOHO_CLIENT_SECRET")
        self.refresh_token = _required_env("ZOHO_REFRESH_TOKEN")
        self.region = os.environ.get("ZOHO_REGION", "com")
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

    @property
    def token_url(self) -> str:
        return f"https://accounts.zoho.{self.region}/oauth/v2/token"

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._access_token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._access_token

        params = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }).encode()

        req = urllib.request.Request(self.token_url, data=params, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            raise RuntimeError(f"Token refresh failed ({e.code}): {body}")

        if "access_token" not in data:
            raise RuntimeError(f"Token refresh error: {data.get('error', data)}")

        self._access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
        return self._access_token


# ---------------------------------------------------------------------------
# 3. Zoho CRM API Client
# ---------------------------------------------------------------------------

class ZohoCRM:
    """Minimal Zoho CRM v7 API client using only stdlib."""

    BASE = "https://www.zohoapis.{region}/crm/v7"

    def __init__(self, auth: ZohoAuth):
        self.auth = auth
        self.base_url = self.BASE.format(region=auth.region)

    def _request(self, path: str, params: dict | None = None) -> dict:
        token = self.auth.get_access_token()
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            raise RuntimeError(f"API error {e.code} on {path}: {body}")

    def _fetch_all(self, path: str, params: dict | None = None, max_pages: int = 10) -> list[dict]:
        """Paginate through a Zoho list endpoint."""
        params = dict(params or {})
        params.setdefault("per_page", "200")
        all_records = []
        page = 1
        while page <= max_pages:
            params["page"] = str(page)
            data = self._request(path, params)
            records = data.get("data", [])
            if not records:
                break
            all_records.extend(records)
            info = data.get("info", {})
            if not info.get("more_records", False):
                break
            page += 1
        return all_records

    # -- Deals ---------------------------------------------------------------

    def get_deals(self, days_back: int = 90) -> list[dict]:
        """Fetch deals modified in the last N days."""
        since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        return self._fetch_all("/Deals", params={
            "sort_by": "Modified_Time",
            "sort_order": "desc",
            "fields": "Deal_Name,Owner,Stage,Amount,Closing_Date,Probability,"
                      "Created_Time,Modified_Time,Stage_Modified_Time,Type,Lead_Source",
        })

    def get_deal_stage_history(self, deal_id: str) -> list[dict]:
        """Fetch stage transition history for a deal via the timeline API."""
        try:
            data = self._request(f"/Deals/{deal_id}/actions/timeline", {"per_page": "50"})
            timeline = data.get("timeline", data.get("data", []))
            stage_changes = []
            for entry in timeline:
                field_history = entry.get("field_history", [])
                for fh in field_history:
                    if fh.get("api_name") == "Stage":
                        stage_changes.append({
                            "from": fh.get("_previous_value"),
                            "to": fh.get("_value"),
                            "time": entry.get("done_time") or entry.get("audit_time"),
                        })
            return stage_changes
        except RuntimeError:
            # Timeline API may not be available on all editions
            return []

    # -- Calls ---------------------------------------------------------------

    def get_calls(self, days_back: int = 90) -> list[dict]:
        """Fetch call logs."""
        return self._fetch_all("/Calls", params={
            "sort_by": "Modified_Time",
            "sort_order": "desc",
            "fields": "Owner,Call_Duration,Call_Start_Time,Call_Status,"
                      "Call_Type,Caller_ID,Subject,Description",
        })

    # -- Activities (Tasks + Events) ----------------------------------------

    def get_tasks(self, days_back: int = 90) -> list[dict]:
        return self._fetch_all("/Tasks", params={
            "sort_by": "Modified_Time",
            "sort_order": "desc",
            "fields": "Owner,Subject,Status,Priority,Due_Date,Created_Time,Modified_Time",
        })

    def get_events(self, days_back: int = 90) -> list[dict]:
        return self._fetch_all("/Events", params={
            "sort_by": "Modified_Time",
            "sort_order": "desc",
            "fields": "Owner,Event_Title,Start_DateTime,End_DateTime,Created_Time",
        })


# ---------------------------------------------------------------------------
# 4. Anti-Gaming Quality Metrics Engine
# ---------------------------------------------------------------------------

def _owner_id(record: dict) -> str | None:
    owner = record.get("Owner")
    if isinstance(owner, dict):
        return owner.get("id")
    return None


def _owner_name(record: dict) -> str:
    owner = record.get("Owner")
    if isinstance(owner, dict):
        return owner.get("name", "Unknown")
    return "Unknown"


def _parse_duration_seconds(duration_str: str | None) -> int:
    """Parse Zoho call duration like '00:05' or '00:05:30' to seconds."""
    if not duration_str:
        return 0
    parts = duration_str.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return 0


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S+00:00",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
    return None


class MetricsEngine:
    """
    Calculates per-rep quality metrics with anti-gaming cross-validation.

    Tier 1 (Hard to game): Win rate, deal velocity, avg deal size, revenue
    Tier 2 (Cross-validated): Call→meeting conversion, activity→pipeline
    Tier 3 (Volume, grain of salt): Call count, email count

    Anti-gaming signals:
    - High calls + zero meetings = dialing for dollars
    - High talk time + low meetings = VM rambling
    - High activity + stale pipeline = fake busy work
    - Zero-second calls inflating volume
    """

    # Minimum thresholds to flag gaming
    MIN_MEANINGFUL_CALL_SECS = 30  # Calls under 30s are likely not real conversations
    GHOST_CALL_THRESHOLD = 5       # Seconds — basically a hang-up

    def __init__(self, deals: list[dict], calls: list[dict],
                 tasks: list[dict], events: list[dict]):
        self.deals = deals
        self.calls = calls
        self.tasks = tasks
        self.events = events

    def _group_by_owner(self, records: list[dict]) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in records:
            oid = _owner_id(r)
            if oid:
                groups[oid].append(r)
        return dict(groups)

    def _owner_names(self) -> dict[str, str]:
        names: dict[str, str] = {}
        for records in (self.deals, self.calls, self.tasks, self.events):
            for r in records:
                oid = _owner_id(r)
                if oid and oid not in names:
                    names[oid] = _owner_name(r)
        return names

    # -- Tier 1: Outcome Metrics (hard to game) -----------------------------

    def calc_deal_metrics(self) -> dict[str, dict]:
        """Per-rep: win_rate, avg_deal_size, total_revenue, deal_count, deal_velocity_days."""
        by_owner = self._group_by_owner(self.deals)
        results = {}
        for oid, deals in by_owner.items():
            won = [d for d in deals if d.get("Stage") == "Closed Won"]
            lost = [d for d in deals if d.get("Stage") == "Closed Lost"]
            closed = won + lost
            total_deals = len(deals)
            won_count = len(won)
            win_rate = (won_count / len(closed) * 100) if closed else 0.0

            amounts = [d.get("Amount", 0) or 0 for d in won]
            total_revenue = sum(amounts)
            avg_deal_size = (total_revenue / won_count) if won_count else 0.0

            # Deal velocity: average days from creation to close (won deals)
            velocities = []
            for d in won:
                created = _parse_datetime(d.get("Created_Time"))
                closed_at = _parse_datetime(d.get("Modified_Time"))
                if created and closed_at:
                    delta = (closed_at - created).days
                    if delta >= 0:
                        velocities.append(delta)
            avg_velocity = (sum(velocities) / len(velocities)) if velocities else None

            results[oid] = {
                "total_deals": total_deals,
                "won": won_count,
                "lost": len(lost),
                "open": total_deals - len(closed),
                "win_rate_pct": round(win_rate, 1),
                "total_revenue": round(total_revenue, 2),
                "avg_deal_size": round(avg_deal_size, 2),
                "avg_velocity_days": round(avg_velocity, 1) if avg_velocity else None,
            }
        return results

    # -- Tier 2: Activity Quality (cross-validated) -------------------------

    def calc_call_quality(self) -> dict[str, dict]:
        """Per-rep call analysis with ghost-call detection."""
        by_owner = self._group_by_owner(self.calls)
        results = {}
        for oid, calls in by_owner.items():
            total = len(calls)
            durations = [_parse_duration_seconds(c.get("Call_Duration")) for c in calls]

            ghost_calls = sum(1 for d in durations if d <= self.GHOST_CALL_THRESHOLD)
            short_calls = sum(1 for d in durations if self.GHOST_CALL_THRESHOLD < d < self.MIN_MEANINGFUL_CALL_SECS)
            meaningful_calls = sum(1 for d in durations if d >= self.MIN_MEANINGFUL_CALL_SECS)
            total_talk_secs = sum(durations)
            avg_duration = (total_talk_secs / total) if total else 0

            # Status breakdown
            statuses = defaultdict(int)
            for c in calls:
                statuses[c.get("Call_Status", "Unknown")] += 1

            results[oid] = {
                "total_calls": total,
                "ghost_calls": ghost_calls,
                "short_calls": short_calls,
                "meaningful_calls": meaningful_calls,
                "ghost_call_pct": round(ghost_calls / total * 100, 1) if total else 0,
                "meaningful_pct": round(meaningful_calls / total * 100, 1) if total else 0,
                "total_talk_minutes": round(total_talk_secs / 60, 1),
                "avg_duration_secs": round(avg_duration, 1),
                "status_breakdown": dict(statuses),
            }
        return results

    def calc_activity_metrics(self) -> dict[str, dict]:
        """Per-rep task and event counts."""
        tasks_by = self._group_by_owner(self.tasks)
        events_by = self._group_by_owner(self.events)
        all_ids = set(tasks_by) | set(events_by)
        results = {}
        for oid in all_ids:
            t = tasks_by.get(oid, [])
            e = events_by.get(oid, [])
            completed_tasks = sum(1 for tk in t if tk.get("Status") in ("Completed", "Done"))
            results[oid] = {
                "total_tasks": len(t),
                "completed_tasks": completed_tasks,
                "task_completion_pct": round(completed_tasks / len(t) * 100, 1) if t else 0,
                "total_events": len(e),
            }
        return results

    # -- Anti-Gaming Cross-Validation ---------------------------------------

    def cross_validate(self) -> dict[str, dict]:
        """
        Cross-validate activity vs outcomes to detect gaming patterns.

        Flags:
        - GHOST_DIALER: >40% ghost calls (call-and-hang-up)
        - VOLUME_NO_OUTCOME: High call volume but 0 wins
        - VM_RAMBLER: High total talk time but low meaningful call %
        - FAKE_BUSY: High tasks/events but pipeline not moving
        """
        deal_metrics = self.calc_deal_metrics()
        call_metrics = self.calc_call_quality()
        activity_metrics = self.calc_activity_metrics()
        names = self._owner_names()

        all_ids = set(deal_metrics) | set(call_metrics) | set(activity_metrics)
        results = {}

        for oid in all_ids:
            dm = deal_metrics.get(oid, {})
            cm = call_metrics.get(oid, {})
            am = activity_metrics.get(oid, {})
            flags = []

            # Ghost dialer: >40% ghost calls
            if cm.get("total_calls", 0) >= 10 and cm.get("ghost_call_pct", 0) > 40:
                flags.append({
                    "flag": "GHOST_DIALER",
                    "detail": f"{cm['ghost_call_pct']}% of {cm['total_calls']} calls are <=5s (call-and-hang-up)",
                    "severity": "HIGH",
                })

            # Volume without outcomes
            if cm.get("total_calls", 0) >= 20 and dm.get("won", 0) == 0:
                flags.append({
                    "flag": "VOLUME_NO_OUTCOME",
                    "detail": f"{cm['total_calls']} calls but 0 deals won",
                    "severity": "MEDIUM",
                })

            # VM rambler: lots of talk time but low meaningful %
            if (cm.get("total_talk_minutes", 0) > 60
                    and cm.get("meaningful_pct", 100) < 30):
                flags.append({
                    "flag": "VM_RAMBLER",
                    "detail": f"{cm['total_talk_minutes']}min talk time but only {cm['meaningful_pct']}% meaningful calls",
                    "severity": "MEDIUM",
                })

            # Fake busy: lots of activity but pipeline stagnant
            total_activity = am.get("total_tasks", 0) + am.get("total_events", 0) + cm.get("total_calls", 0)
            if total_activity >= 30 and dm.get("total_deals", 0) == 0:
                flags.append({
                    "flag": "FAKE_BUSY",
                    "detail": f"{total_activity} activities logged but 0 deals in pipeline",
                    "severity": "HIGH",
                })

            # Low task completion: logs tasks but never completes them
            if am.get("total_tasks", 0) >= 10 and am.get("task_completion_pct", 100) < 20:
                flags.append({
                    "flag": "LOW_FOLLOW_THROUGH",
                    "detail": f"Only {am['task_completion_pct']}% of {am['total_tasks']} tasks completed",
                    "severity": "LOW",
                })

            results[oid] = {
                "name": names.get(oid, "Unknown"),
                "deal_metrics": dm,
                "call_quality": cm,
                "activity": am,
                "gaming_flags": flags,
                "flag_count": len(flags),
                "has_red_flags": any(f["severity"] == "HIGH" for f in flags),
            }

        return results

    # -- Composite Output Rating --------------------------------------------

    def calc_output_ratings(self) -> dict[str, dict]:
        """
        Calculate Output Rating per rep.
        OR = (Velocity x 0.4) + (Quality x 0.35) + (Responsiveness x 0.25)
        Each component scored 1-10.

        Velocity: Based on win rate + deal velocity
        Quality: Based on meaningful call %, deal size, gaming flags
        Responsiveness: Based on task completion + activity volume (validated)
        """
        cross = self.cross_validate()
        results = {}

        for oid, data in cross.items():
            dm = data["deal_metrics"]
            cm = data["call_quality"]
            am = data["activity"]
            flags = data["gaming_flags"]

            # -- Velocity (0.4 weight) --
            # Win rate contributes 60%, deal velocity contributes 40%
            win_rate = dm.get("win_rate_pct", 0)
            velocity_from_wins = min(win_rate / 10, 10)  # 100% win rate = 10

            vel_days = dm.get("avg_velocity_days")
            if vel_days is not None and vel_days > 0:
                # Faster is better: 7 days = 10, 90 days = 3
                velocity_from_speed = max(1, min(10, 10 - (vel_days - 7) * 7 / 83))
            else:
                velocity_from_speed = 5  # neutral if no data

            velocity_score = velocity_from_wins * 0.6 + velocity_from_speed * 0.4

            # -- Quality (0.35 weight) --
            meaningful_pct = cm.get("meaningful_pct", 50)
            quality_from_calls = min(meaningful_pct / 10, 10)

            # Penalize gaming flags
            flag_penalty = sum(
                3 if f["severity"] == "HIGH" else 1.5 if f["severity"] == "MEDIUM" else 0.5
                for f in flags
            )
            quality_score = max(1, min(10, quality_from_calls - flag_penalty))

            # -- Responsiveness (0.25 weight) --
            task_comp = am.get("task_completion_pct", 50)
            responsiveness_score = min(task_comp / 10, 10)

            # Final OR
            output_rating = round(
                velocity_score * 0.4 + quality_score * 0.35 + responsiveness_score * 0.25, 1
            )

            results[oid] = {
                "name": data["name"],
                "output_rating": output_rating,
                "color": "",  # assigned below via percentile ranking
                "velocity_score": round(velocity_score, 1),
                "quality_score": round(quality_score, 1),
                "responsiveness_score": round(responsiveness_score, 1),
                "gaming_flags": flags,
            }

        # Percentile-based color assignment:
        # Sort all reps by output_rating ascending
        # Bottom 20% = RED, Middle 60% = YELLOW, Top 20% = GREEN
        sorted_ids = sorted(results, key=lambda oid: results[oid]["output_rating"])
        n = len(sorted_ids)
        red_cutoff = max(1, round(n * 0.20))      # bottom 20%
        green_cutoff = n - max(1, round(n * 0.20)) # top 20%

        for i, oid in enumerate(sorted_ids):
            if i < red_cutoff:
                results[oid]["color"] = "RED"
            elif i >= green_cutoff:
                results[oid]["color"] = "GREEN"
            else:
                results[oid]["color"] = "YELLOW"

        return results


# ---------------------------------------------------------------------------
# 5. Main: Fetch + Analyze + Report
# ---------------------------------------------------------------------------

def run_report(days_back: int = 90) -> dict:
    """Full pipeline: load env, authenticate, fetch data, compute metrics."""
    load_env()
    auth = ZohoAuth()
    crm = ZohoCRM(auth)

    print(f"[ORGCOMMAND] Fetching Zoho CRM data (last {days_back} days)...")

    deals = crm.get_deals(days_back)
    print(f"  Deals: {len(deals)}")

    calls = crm.get_calls(days_back)
    print(f"  Calls: {len(calls)}")

    tasks = crm.get_tasks(days_back)
    print(f"  Tasks: {len(tasks)}")

    events = crm.get_events(days_back)
    print(f"  Events: {len(events)}")

    engine = MetricsEngine(deals, calls, tasks, events)
    ratings = engine.calc_output_ratings()

    print(f"\n{'='*60}")
    print(f"  ORGCOMMAND Sales Output Ratings")
    print(f"{'='*60}\n")

    for oid, r in sorted(ratings.items(), key=lambda x: x[1]["output_rating"], reverse=True):
        color_indicator = {"GREEN": "+", "YELLOW": "~", "RED": "!"}[r["color"]]
        print(f"  [{color_indicator}] {r['name']:20s}  OR: {r['output_rating']:4.1f}  ({r['color']})")
        print(f"      Velocity: {r['velocity_score']:.1f}  Quality: {r['quality_score']:.1f}  Responsiveness: {r['responsiveness_score']:.1f}")
        if r["gaming_flags"]:
            for f in r["gaming_flags"]:
                print(f"      *** {f['flag']}: {f['detail']}")
        print()

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "days_back": days_back,
        "record_counts": {
            "deals": len(deals),
            "calls": len(calls),
            "tasks": len(tasks),
            "events": len(events),
        },
        "ratings": ratings,
        "cross_validation": engine.cross_validate(),
    }


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    report = run_report(days)
    # Dump full report to JSON
    out_path = Path(__file__).parent / "zoho_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report saved to {out_path}")
