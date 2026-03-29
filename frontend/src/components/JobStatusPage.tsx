import { useEffect, useRef, useState } from 'react';

import { fetchVideoJob } from '../lib/api';
import {
  canOpenDashboard,
  getProgressPercent,
  getProgressLabel,
  getStatusBanner,
} from '../lib/workflow';
import type { VideoJobSummary } from '../lib/types';

interface JobStatusPageProps {
  job: VideoJobSummary | null;
  onJobChange: (job: VideoJobSummary) => void;
  onOpenDashboard: () => void;
  onBackToUpload: () => void;
}

export function JobStatusPage({
  job,
  onJobChange,
  onOpenDashboard,
  onBackToUpload,
}: JobStatusPageProps) {
  const [refreshError, setRefreshError] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string>('');
  const isMountedRef = useRef(true);
  const pollTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (pollTimerRef.current !== null) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  async function refreshJob() {
    if (!job?.id) {
      return;
    }

    setIsRefreshing(true);
    try {
      const updatedJob = await fetchVideoJob(job.id);
      if (!isMountedRef.current) {
        return;
      }
      onJobChange(updatedJob);
      if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
        if (pollTimerRef.current !== null) {
          window.clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      }
      setRefreshError('');
      setLastSyncedAt(new Date().toLocaleTimeString([], {
        hour: 'numeric',
        minute: '2-digit',
      }));
    } catch (error) {
      if (!isMountedRef.current) {
        return;
      }
      setRefreshError(
        error instanceof Error
          ? error.message
          : 'Unable to refresh the job status right now.',
      );
    } finally {
      if (isMountedRef.current) {
        setIsRefreshing(false);
      }
    }
  }

  useEffect(() => {
    if (!job?.id || job.status === 'completed' || job.status === 'failed') {
      if (pollTimerRef.current !== null) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      return;
    }

    let cancelled = false;
    void refreshJob();
    pollTimerRef.current = window.setInterval(() => {
      if (!cancelled) {
        void refreshJob();
      }
    }, 3000);

    return () => {
      cancelled = true;
      if (pollTimerRef.current !== null) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [job?.id, job?.status]);

  useEffect(() => {
    if (job?.status === 'completed') {
      onOpenDashboard();
    }
  }, [job?.status, onOpenDashboard]);

  if (!job) {
    return (
      <article className="panel panel--hero">
        <div className="section-heading">
          <p className="panel__eyebrow">Job status</p>
          <h2>No analysis job yet</h2>
          <p className="panel__lede">
            Upload a full-match video first. Once the backend returns a job, we
            will show progress, messages, and a dashboard unlock state here.
          </p>
        </div>

        <div className="status-banner">
          <strong>Waiting for an uploaded match.</strong>
        </div>

        <button className="secondary-button" type="button" onClick={onBackToUpload}>
          Back to upload
        </button>
      </article>
    );
  }

  const dashboardReady = canOpenDashboard(job);
  const rulesetLabel = job.ruleset_variant ?? job.rulesetVariant ?? 'unknown';

  return (
    <article className="panel panel--hero">
      <div className="section-heading">
        <p className="panel__eyebrow">Job status</p>
        <h2>Track processing progress</h2>
        <p className="panel__lede">
          The backend can keep updating this screen as the match moves through
          upload, preprocessing, Gemini analysis, and analytics generation.
        </p>
      </div>

      <div className="status-grid">
        <section className="panel panel--subtle">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Current job</p>
              <h3>{job.title || 'Untitled match'}</h3>
            </div>
            <span className="panel__badge">{job.status}</span>
          </div>

          <div className="job-progress">
            <div className="job-progress__track" aria-hidden="true">
              <span
                className="job-progress__fill"
                style={{ width: `${getProgressPercent(job)}%` }}
              />
            </div>
            <div className="job-progress__meta">
              <strong>{getProgressLabel(job)}</strong>
              <span>{rulesetLabel}</span>
            </div>
          </div>

          <div className="status-banner">
            <strong>{getStatusBanner(job)}</strong>
            <span className="status-banner__hint">
              {refreshError || `Last synced: ${lastSyncedAt || 'just now'}`}
            </span>
          </div>
        </section>

        <section className="panel panel--subtle">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Controls</p>
              <h3>Keep moving</h3>
            </div>
            <span className="panel__badge">Dashboard unlock</span>
          </div>

          <div className="status-actions">
            <button
              className="primary-button"
              type="button"
              onClick={refreshJob}
              disabled={isRefreshing}
            >
              {isRefreshing ? 'Refreshing...' : 'Refresh job status'}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={onOpenDashboard}
              disabled={!dashboardReady}
            >
              {dashboardReady ? 'Open dashboard' : 'Dashboard locked'}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={onBackToUpload}
            >
              Back to upload
            </button>
          </div>
        </section>
      </div>
    </article>
  );
}
