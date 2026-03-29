from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import json
import logging
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from backend.app.config import get_settings
from backend.app.integrations.gemini_client import GeminiVideoSource
from backend.app.schemas.analytics import MatchAnalyticsSummary, TeamAnalyticsSummary
from backend.app.schemas.common import RulesetVariant, VideoSourceType
from backend.app.schemas.preprocessing import CandidateClip
from backend.app.schemas.set_event import SetEvent
from backend.app.services.analyze_candidate_clips import analyze_candidate_clips_to_events
from backend.app.services.analytics_aggregation import summarize_set_events


logger = logging.getLogger("volleyball_ai.local_analysis")


@dataclass(frozen=True, slots=True)
class LocalAnalysisResult:
    video_asset_id: str
    title: str
    video_source_type: VideoSourceType
    video_path: Path | None
    video_url: str
    report_dir: Path
    report_path: Path
    report_url: str
    analysis_json_path: Path
    analytics: MatchAnalyticsSummary
    set_events: list[SetEvent]


def run_local_analysis(
    *,
    video_path: str | Path | None = None,
    youtube_url: str | None = None,
    ruleset_variant: RulesetVariant,
    title: str | None = None,
    output_root: str | Path = "reports",
) -> LocalAnalysisResult:
    if bool(video_path) == bool(youtube_url):
        raise ValueError("Provide exactly one of video_path or youtube_url.")

    resolved_video_path: Path | None = None
    video_url: str
    video_source_type: VideoSourceType
    mime_type: str

    if video_path is not None:
        resolved_video_path = Path(video_path).expanduser().resolve()
        if not resolved_video_path.exists():
            raise ValueError(f"Video path does not exist: {resolved_video_path}")
        if not resolved_video_path.is_file():
            raise ValueError(f"Video path must be a file: {resolved_video_path}")
        video_url = resolved_video_path.as_uri()
        video_source_type = VideoSourceType.local_path
        mime_type = guess_type(str(resolved_video_path))[0] or "video/mp4"
    else:
        assert youtube_url is not None
        normalized_youtube_url = youtube_url.strip()
        if not normalized_youtube_url:
            raise ValueError("youtube_url must not be empty.")
        video_url = normalized_youtube_url
        video_source_type = VideoSourceType.youtube
        mime_type = "video/mp4"

    settings = get_settings()
    video_asset_id = f"video-{uuid4().hex[:12]}"
    fallback_title = (
        resolved_video_path.stem.replace("_", " ")
        if resolved_video_path is not None
        else "YouTube match"
    )
    resolved_title = (title or "").strip() or fallback_title or "Volleyball match"

    logger.info(
        "Starting local analysis | video_id=%s | title=%s | ruleset=%s | video_source_type=%s | video_path=%s | video_url=%s | mime_type=%s | gemini_live_enabled=%s",
        video_asset_id,
        resolved_title,
        ruleset_variant,
        video_source_type,
        resolved_video_path,
        video_url,
        mime_type,
        settings.gemini_live_enabled and bool(settings.gemini_api_key),
    )

    candidate_clips = [
        CandidateClip(
            candidate_clip_id=f"{video_asset_id}-whole-video",
            video_asset_id=video_asset_id,
            rally_segment_id=None,
            start_time_s=0.0,
            end_time_s=1.0,
            trigger_label="whole_video",
            confidence=0.95,
        )
    ]

    logger.info(
        "Prepared local candidate clips | video_id=%s | clip_ids=%s",
        video_asset_id,
        [clip.candidate_clip_id for clip in candidate_clips],
    )

    event_result = analyze_candidate_clips_to_events(
        video_asset_id=video_asset_id,
        candidate_clips=candidate_clips,
        video_source=GeminiVideoSource(
            source_type=video_source_type,
            uri=str(resolved_video_path) if resolved_video_path is not None else video_url,
            mime_type=mime_type,
        ),
    )

    analytics = summarize_set_events(
        video_asset_id=video_asset_id,
        ruleset_variant=ruleset_variant,
        set_events=event_result.set_events,
    )

    output_root_path = Path(output_root).expanduser().resolve()
    report_dir = output_root_path / video_asset_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "index.html"
    analysis_json_path = report_dir / "analysis.json"

    generated_at = datetime.now(tz=timezone.utc)
    payload = {
        "video_asset_id": video_asset_id,
        "title": resolved_title,
        "video_source_type": video_source_type.value,
        "video_path": str(resolved_video_path) if resolved_video_path is not None else None,
        "video_url": video_url,
        "ruleset_variant": ruleset_variant.value,
        "generated_at": generated_at.isoformat(),
        "mode": "live_gemini" if settings.gemini_live_enabled and settings.gemini_api_key else "stub",
        "analytics": analytics.model_dump(mode="json"),
        "set_events": [event.model_dump(mode="json") for event in event_result.set_events],
        "low_confidence_candidate_clips": event_result.low_confidence_candidate_clips,
    }

    report_path.write_text(_render_report_html(payload), encoding="utf-8")
    analysis_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    logger.info(
        "Local analysis complete | video_id=%s | set_events=%s | report_path=%s",
        video_asset_id,
        len(event_result.set_events),
        report_path,
    )

    return LocalAnalysisResult(
        video_asset_id=video_asset_id,
        title=resolved_title,
        video_source_type=video_source_type,
        video_path=resolved_video_path,
        video_url=video_url,
        report_dir=report_dir,
        report_path=report_path,
        report_url=report_path.as_uri(),
        analysis_json_path=analysis_json_path,
        analytics=analytics,
        set_events=event_result.set_events,
    )


def _render_report_html(payload: dict[str, object]) -> str:
    analytics = MatchAnalyticsSummary.model_validate(payload["analytics"])
    set_events = [SetEvent.model_validate(item) for item in payload["set_events"]]
    title = escape(str(payload["title"]))
    video_url = escape(str(payload["video_url"]))
    raw_video_path = payload.get("video_path")
    video_path = escape(str(raw_video_path)) if raw_video_path else "YouTube source"
    video_source_type = escape(str(payload.get("video_source_type", "local_path")))
    ruleset_variant = escape(str(payload["ruleset_variant"]))
    generated_at = escape(str(payload["generated_at"]))
    mode = escape(str(payload["mode"]))

    overall = analytics.overall
    zone_distribution = _render_distribution_bars(
        "Target zone distribution",
        overall.target_zone_distribution,
    )
    tempo_distribution = _render_distribution_bars(
        "Tempo distribution",
        {tempo.value: count for tempo, count in overall.tempo_distribution.items()},
    )
    team_cards = "".join(_render_team_card(team_summary) for team_summary in analytics.by_team)
    event_rows = "".join(_render_event_row(event) for event in set_events)
    total_events = len(set_events)
    success_rate = _format_percent(overall.success_rate)
    top_tempo = _top_key({tempo.value: count for tempo, count in overall.tempo_distribution.items()})

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} | Volleyball AI Report</title>
    <style>
      :root {{
        --bg: #f4efe4;
        --ink: #162022;
        --muted: #55666a;
        --panel: rgba(255, 251, 245, 0.9);
        --line: rgba(22, 32, 34, 0.12);
        --accent: #d95d39;
        --accent-soft: #f2b880;
        --accent-deep: #244b5a;
        --good: #2c7a52;
        --warn: #b45f06;
        --shadow: 0 24px 60px rgba(27, 33, 36, 0.12);
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        font-family: "Avenir Next", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(217, 93, 57, 0.18), transparent 30%),
          radial-gradient(circle at right center, rgba(36, 75, 90, 0.12), transparent 28%),
          linear-gradient(180deg, #f8f3e9 0%, var(--bg) 100%);
      }}

      main {{
        width: min(1200px, calc(100% - 32px));
        margin: 32px auto 48px;
      }}

      .hero {{
        display: grid;
        gap: 20px;
        padding: 28px;
        border: 1px solid var(--line);
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(255,255,255,0.86), rgba(244, 236, 221, 0.96));
        box-shadow: var(--shadow);
      }}

      .eyebrow {{
        margin: 0 0 8px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.78rem;
        color: var(--accent-deep);
      }}

      h1, h2, h3 {{
        margin: 0;
      }}

      .hero p {{
        margin: 0;
      }}

      .meta-grid,
      .metric-grid,
      .team-grid,
      .split-grid {{
        display: grid;
        gap: 16px;
      }}

      .meta-grid {{
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }}

      .metric-grid {{
        margin-top: 18px;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }}

      .team-grid {{
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }}

      .split-grid {{
        margin-top: 22px;
        grid-template-columns: 1.15fr 0.85fr;
        align-items: start;
      }}

      .panel,
      .metric,
      .meta,
      .team-card {{
        padding: 18px;
        border-radius: 22px;
        border: 1px solid var(--line);
        background: var(--panel);
        box-shadow: var(--shadow);
      }}

      .meta strong,
      .metric strong {{
        display: block;
        margin-top: 6px;
        font-size: 1.05rem;
      }}

      .metric .value {{
        font-size: 2rem;
      }}

      .muted {{
        color: var(--muted);
      }}

      video {{
        width: 100%;
        border-radius: 18px;
        border: 1px solid var(--line);
        background: #111;
      }}

      .distribution {{
        margin-top: 14px;
      }}

      .distribution h3 {{
        margin-bottom: 10px;
      }}

      .bar-row {{
        margin-bottom: 12px;
      }}

      .bar-row:last-child {{
        margin-bottom: 0;
      }}

      .bar-meta {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 6px;
        font-size: 0.95rem;
      }}

      .bar-track {{
        height: 10px;
        border-radius: 999px;
        background: rgba(22, 32, 34, 0.08);
        overflow: hidden;
      }}

      .bar-fill {{
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--accent), var(--accent-soft));
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 14px;
        font-size: 0.94rem;
      }}

      th,
      td {{
        padding: 10px 8px;
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: top;
      }}

      th {{
        color: var(--accent-deep);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}

      .badge {{
        display: inline-flex;
        align-items: center;
        padding: 5px 10px;
        border-radius: 999px;
        background: rgba(36, 75, 90, 0.08);
        color: var(--accent-deep);
        font-size: 0.84rem;
      }}

      .success {{
        color: var(--good);
        font-weight: 600;
      }}

      .failure {{
        color: var(--warn);
        font-weight: 600;
      }}

      a {{
        color: var(--accent-deep);
      }}

      @media (max-width: 860px) {{
        .split-grid {{
          grid-template-columns: 1fr;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div>
          <p class="eyebrow">Volleyball AI Local Report</p>
          <h1>{title}</h1>
          <p class="muted">Static local report generated from a direct video-path analysis run.</p>
        </div>

        <div class="meta-grid">
          <div class="meta">
            <span class="muted">Video source</span>
            <strong>{video_path}</strong>
          </div>
          <div class="meta">
            <span class="muted">Source type</span>
            <strong>{video_source_type}</strong>
          </div>
          <div class="meta">
            <span class="muted">Processing mode</span>
            <strong>{mode}</strong>
          </div>
          <div class="meta">
            <span class="muted">Ruleset</span>
            <strong>{ruleset_variant}</strong>
          </div>
          <div class="meta">
            <span class="muted">Generated at</span>
            <strong>{generated_at}</strong>
          </div>
        </div>

        <div class="metric-grid">
          <div class="metric">
            <span class="muted">Total sets</span>
            <strong class="value">{overall.total_set_attempts}</strong>
          </div>
          <div class="metric">
            <span class="muted">Success rate</span>
            <strong class="value">{success_rate}</strong>
          </div>
          <div class="metric">
            <span class="muted">Top tempo</span>
            <strong class="value">{escape(top_tempo)}</strong>
          </div>
          <div class="metric">
            <span class="muted">Returned events</span>
            <strong class="value">{total_events}</strong>
          </div>
        </div>
      </section>

      <section class="split-grid">
        <article class="panel">
          <p class="eyebrow">Video</p>
          <h2>Match clip</h2>
          <p class="muted">If the video does not load inline, open it directly from the link below.</p>
          <div style="margin-top: 14px;">
            <video controls preload="metadata" src="{video_url}"></video>
          </div>
          <p style="margin-top: 12px;">
            <a href="{video_url}">Open source video directly</a>
          </p>
        </article>

        <article class="panel">
          <p class="eyebrow">Overview</p>
          <h2>Setter output</h2>
          {zone_distribution}
          {tempo_distribution}
        </article>
      </section>

      <section class="panel" style="margin-top: 22px;">
        <p class="eyebrow">Teams</p>
        <h2>By team side</h2>
        <div class="team-grid" style="margin-top: 14px;">
          {team_cards or '<div class="team-card"><strong>No team split available</strong><p class="muted">Only overall metrics were returned for this run.</p></div>'}
        </div>
      </section>

      <section class="panel" style="margin-top: 22px;">
        <p class="eyebrow">Events</p>
        <h2>Detected set timeline</h2>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Team</th>
              <th>Zone</th>
              <th>Tempo</th>
              <th>Result</th>
              <th>Confidence</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {event_rows or '<tr><td colspan="7">No set events were returned.</td></tr>'}
          </tbody>
        </table>
      </section>
    </main>
  </body>
</html>
"""


def _render_team_card(summary: TeamAnalyticsSummary) -> str:
    team_label = summary.team_side.value.replace("_", " ")
    top_tempo = _top_key({tempo.value: count for tempo, count in summary.tempo_distribution.items()})
    return f"""
      <article class="team-card">
        <p class="muted" style="margin: 0 0 8px;">{escape(team_label)}</p>
        <strong style="font-size: 1.5rem;">{summary.successful_sets}/{summary.total_set_attempts}</strong>
        <p class="muted" style="margin: 6px 0 0;">Attackable sets: {_format_percent(summary.success_rate)}</p>
        <p class="muted" style="margin: 6px 0 0;">Top tempo: {escape(top_tempo)}</p>
      </article>
    """


def _render_distribution_bars(title: str, distribution: dict[str, int]) -> str:
    if not distribution:
        return f"""
        <div class="distribution">
          <h3>{escape(title)}</h3>
          <p class="muted">No values were returned.</p>
        </div>
        """

    max_value = max(distribution.values()) or 1
    rows = []
    for label, count in sorted(distribution.items(), key=lambda item: (-item[1], item[0])):
        width = max(8, round((count / max_value) * 100))
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-meta">
                <span>{escape(str(label))}</span>
                <strong>{count}</strong>
              </div>
              <div class="bar-track">
                <div class="bar-fill" style="width: {width}%;"></div>
              </div>
            </div>
            """
        )

    return f"""
      <div class="distribution">
        <h3>{escape(title)}</h3>
        {''.join(rows)}
      </div>
    """


def _render_event_row(event: SetEvent) -> str:
    team_label = event.setter_team_side.value.replace("_", " ")
    result_class = "success" if event.set_success else "failure"
    result_label = "Attackable" if event.set_success else "Not attackable"
    notes = escape(event.notes or "")
    return f"""
      <tr>
        <td>{_format_time(event.timestamp_s)}</td>
        <td>{escape(team_label)}</td>
        <td>{escape(event.target_zone)}</td>
        <td>{escape(event.set_tempo.value)}</td>
        <td><span class="{result_class}">{result_label}</span></td>
        <td>{round(event.confidence * 100)}%</td>
        <td>{notes or '<span class="muted">None</span>'}</td>
      </tr>
    """


def _format_percent(value: float) -> str:
    return f"{round(value * 100)}%"


def _top_key(distribution: dict[str, int]) -> str:
    if not distribution:
        return "none"
    return sorted(distribution.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _format_time(seconds: float) -> str:
    whole_seconds = max(0, int(seconds))
    minutes = whole_seconds // 60
    remaining_seconds = whole_seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"
