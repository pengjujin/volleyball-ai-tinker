import { useEffect, useState } from 'react';

import { fetchVideoAnalytics, fetchVideoEvents } from '../lib/api';
import type {
  MatchAnalyticsSummary,
  SetEvent,
  VideoJobSummary,
} from '../lib/types';
import { getProgressPercent } from '../lib/workflow';

interface DashboardPageProps {
  job: VideoJobSummary | null;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatTime(seconds: number): string {
  const safeSeconds = Math.max(0, seconds);
  const wholeSeconds = Math.floor(safeSeconds);
  const minutes = Math.floor(wholeSeconds / 60);
  const remainingSeconds = wholeSeconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function formatTeamSide(teamSide: string): string {
  if (teamSide === 'near_side') {
    return 'Near side';
  }

  if (teamSide === 'far_side') {
    return 'Far side';
  }

  return 'Unknown';
}

function summarizeZoneCounts(analytics: MatchAnalyticsSummary | null): Array<[string, number]> {
  if (!analytics) {
    return [];
  }

  return Object.entries(analytics.overall.target_zone_distribution).sort(
    (left, right) => right[1] - left[1],
  );
}

function getTopTempo(tempoDistribution: MatchAnalyticsSummary['overall']['tempo_distribution']): string {
  return Object.entries(tempoDistribution).sort((left, right) => right[1] - left[1])[0]?.[0] ?? 'none';
}

export function DashboardPage({ job }: DashboardPageProps) {
  const [analytics, setAnalytics] = useState<MatchAnalyticsSummary | null>(null);
  const [events, setEvents] = useState<SetEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadResults() {
      if (!job?.id) {
        setAnalytics(null);
        setEvents([]);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const [nextAnalytics, nextEvents] = await Promise.all([
          fetchVideoAnalytics(job.id),
          fetchVideoEvents(job.id),
        ]);

        if (cancelled) {
          return;
        }

        setAnalytics(nextAnalytics);
        setEvents(nextEvents);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Unable to load analysis results.',
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadResults();

    return () => {
      cancelled = true;
    };
  }, [job?.id]);

  if (!job) {
    return (
      <article className="panel panel--hero">
        <div className="section-heading">
          <p className="panel__eyebrow">Dashboard</p>
          <h2>No completed job yet</h2>
          <p className="panel__lede">
            Upload a clip and wait for processing to complete before opening the
            analytics dashboard.
          </p>
        </div>
      </article>
    );
  }

  return (
    <article className="panel panel--hero">
      <div className="section-heading">
        <p className="panel__eyebrow">Dashboard</p>
        <h2>Live setter analytics</h2>
        <p className="panel__lede">
          Results are pulled from the backend for job {job.id}. The current
          clip is {getProgressPercent(job)} percent through the UI progress bar
          state, and the analytics below reflect the latest backend response.
        </p>
      </div>

      {error ? (
        <div className="status-banner">
          <strong>Could not load results.</strong>
          <span className="status-banner__hint">{error}</span>
        </div>
      ) : null}

      <div className="metric-grid">
        <section className="metric-card">
          <p className="metric-card__label">Total sets</p>
          <strong className="metric-card__value">
            {analytics?.overall.total_set_attempts ?? 0}
          </strong>
          <span className="metric-card__detail">All detected setter actions</span>
        </section>
        <section className="metric-card">
          <p className="metric-card__label">Success rate</p>
          <strong className="metric-card__value">
            {analytics ? formatPercent(analytics.overall.success_rate) : '0%'}
          </strong>
          <span className="metric-card__detail">Attackable-ball definition</span>
        </section>
        <section className="metric-card">
          <p className="metric-card__label">Top tempo</p>
          <strong className="metric-card__value">
            {analytics ? getTopTempo(analytics.overall.tempo_distribution) : 'none'}
          </strong>
          <span className="metric-card__detail">Quick, medium, high/slow</span>
        </section>
        <section className="metric-card">
          <p className="metric-card__label">Events</p>
          <strong className="metric-card__value">{events.length}</strong>
          <span className="metric-card__detail">
            {loading ? 'Refreshing results' : 'Latest backend payload'}
          </span>
        </section>
      </div>

      {analytics?.by_team?.length ? (
        <section className="panel panel--subtle">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Breakdown</p>
              <h3>Setter analytics by team</h3>
            </div>
            <span className="panel__badge">
              {analytics.generated_at
                ? `Updated ${new Date(analytics.generated_at).toLocaleTimeString([], {
                    hour: 'numeric',
                    minute: '2-digit',
                  })}`
                : 'Backend data'}
            </span>
          </div>

          <div className="team-summary-grid">
            {analytics.by_team.map((team) => (
              <article className="team-summary-card" key={team.team_side}>
                <p className="team-summary-card__label">{formatTeamSide(team.team_side)}</p>
                <strong className="team-summary-card__value">
                  {team.successful_sets}/{team.total_set_attempts}
                </strong>
                <span className="team-summary-card__detail">
                  {formatPercent(team.success_rate)} attackable sets
                </span>
                <span className="team-summary-card__detail">
                  Top tempo: {getTopTempo(team.tempo_distribution)}
                </span>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <div className="dashboard-grid">
        <section className="panel panel--subtle">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Distribution</p>
              <h3>Target zones</h3>
            </div>
            <span className="panel__badge">Backend data</span>
          </div>

          <div className="bar-list">
            {summarizeZoneCounts(analytics).map(([zone, count]) => (
              <div className="bar-row" key={zone}>
                <div className="bar-row__meta">
                  <span>{zone}</span>
                  <strong>{count}</strong>
                </div>
                <div className="bar-track">
                  <span
                    className="bar-track__fill"
                    style={{ width: `${Math.min(100, count * 5)}%` }}
                  />
                </div>
              </div>
            ))}
            {!analytics ? <p className="panel__body">No analytics yet.</p> : null}
          </div>
        </section>

        <section className="panel panel--subtle">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Timeline</p>
              <h3>Set events</h3>
            </div>
            <span className="panel__badge">Real rows</span>
          </div>

          <div className="event-table">
            <div className="event-table__header">
              <span>Time</span>
              <span>Team</span>
              <span>Zone</span>
              <span>Tempo</span>
              <span>Result</span>
            </div>
            {events.map((event) => (
              <div className="event-table__row" key={event.set_event_id}>
                <span>{formatTime(event.timestamp_s)}</span>
                <span>{formatTeamSide(event.setter_team_side)}</span>
                <span>{event.target_zone}</span>
                <span>{event.set_tempo}</span>
                <span>{event.set_success ? 'Attackable' : 'Not attackable'}</span>
              </div>
            ))}
            {events.length === 0 && !loading ? (
              <p className="panel__body">No set events were returned for this job.</p>
            ) : null}
          </div>
        </section>
      </div>
    </article>
  );
}
