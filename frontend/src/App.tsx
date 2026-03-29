import { useEffect, useState } from 'react';

import { DashboardPage } from './components/DashboardPage';
import { JobStatusPage } from './components/JobStatusPage';
import { UploadPage } from './components/UploadPage';
import { canOpenDashboard, getDefaultView } from './lib/workflow';
import type { AppView, VideoJobSummary } from './lib/types';

const navigation: Array<{ id: AppView; label: string; description: string }> = [
  {
    id: 'upload',
    label: 'Upload',
    description: 'Choose a full-match recording and set the ruleset.',
  },
  {
    id: 'job-status',
    label: 'Job status',
    description: 'Watch upload progress and analysis updates.',
  },
  {
    id: 'dashboard',
    label: 'Dashboard',
    description: 'Review setter analytics, tempo, and event summaries.',
  },
];

export default function App() {
  const [currentJob, setCurrentJob] = useState<VideoJobSummary | null>(null);
  const [activeView, setActiveView] = useState<AppView>(
    getDefaultView(currentJob),
  );
  const resolvedView: AppView =
    currentJob?.status === 'completed' ? 'dashboard' : activeView;

  useEffect(() => {
    if (currentJob?.status === 'completed') {
      setActiveView('dashboard');
    }
  }, [currentJob?.status]);

  function handleJobCreated(job: VideoJobSummary) {
    setCurrentJob(job);
    setActiveView(job.status === 'completed' ? 'dashboard' : 'job-status');
  }

  function handleJobUpdate(job: VideoJobSummary) {
    setCurrentJob(job);
  }

  function openDashboard() {
    if (canOpenDashboard(currentJob)) {
      setActiveView('dashboard');
    }
  }

  return (
    <div className="app-shell">
      <div className="app-shell__glow app-shell__glow--one" />
      <div className="app-shell__glow app-shell__glow--two" />

      <header className="hero">
        <div className="hero__copy">
          <p className="eyebrow">Volleyball AI</p>
          <h1>Setter analytics for full-match volleyball videos.</h1>
          <p className="hero__lede">
            A clean MVP scaffold for fixed-camera recordings, user-selected
            match rulesets, and Gemini-assisted set analysis.
          </p>
        </div>

        <div className="hero__stats" aria-label="scaffold highlights">
          <div className="stat-chip">
            <span className="stat-chip__label">Input</span>
            <span className="stat-chip__value">Local path, upload, or YouTube</span>
          </div>
          <div className="stat-chip">
            <span className="stat-chip__label">Rulesets</span>
            <span className="stat-chip__value">6-player and 9-man</span>
          </div>
          <div className="stat-chip">
            <span className="stat-chip__label">Metrics</span>
            <span className="stat-chip__value">Zone, success, tempo</span>
          </div>
        </div>
      </header>

      <nav className="nav-tabs" aria-label="main sections">
        {navigation.map((item) => {
          const isActive = item.id === resolvedView;
          const isLocked =
            item.id === 'job-status' ? !currentJob : item.id === 'dashboard' && !canOpenDashboard(currentJob);

          return (
            <button
              key={item.id}
              type="button"
              className={`nav-tabs__item${isActive ? ' nav-tabs__item--active' : ''}`}
              disabled={isLocked}
              onClick={() => setActiveView(item.id)}
            >
              <span className="nav-tabs__title">{item.label}</span>
              <span className="nav-tabs__description">{item.description}</span>
            </button>
          );
        })}
      </nav>

      <main className="workspace">
        <aside className="workspace__rail">
          <section className="panel panel--compact">
            <p className="panel__eyebrow">Pipeline</p>
            <h2>What this scaffold prepares</h2>
            <ul className="checklist">
              <li>Full-match upload and job setup</li>
              <li>Ruleset selection before processing</li>
              <li>Status polling after upload</li>
              <li>Setter-only analytics for both teams</li>
              <li>Event overlays and tempo summaries</li>
            </ul>
          </section>

          <section className="panel panel--compact">
            <p className="panel__eyebrow">API surface</p>
            <h2>Frontend client entry points</h2>
            <p className="panel__body">
              The API client lives in <code>src/lib/api.ts</code> and keeps URL
              composition and multipart payload creation isolated from the UI.
            </p>
          </section>
        </aside>

        <section className="workspace__content">
          {activeView === 'upload' ? (
            <UploadPage onJobCreated={handleJobCreated} />
          ) : null}
          {resolvedView === 'job-status' ? (
            <JobStatusPage
              job={currentJob}
              onJobChange={handleJobUpdate}
              onOpenDashboard={openDashboard}
              onBackToUpload={() => setActiveView('upload')}
            />
          ) : null}
          {resolvedView === 'dashboard' ? (
            <DashboardPage job={currentJob} />
          ) : null}
        </section>
      </main>
    </div>
  );
}
