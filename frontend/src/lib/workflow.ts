import type {
  AppView,
  RulesetVariant,
  VideoJobSummary,
  VideoSourceType,
} from './types';

export interface SubmissionDraft {
  rulesetVariant: RulesetVariant | '';
  sourceType: VideoSourceType;
  sourceUrl: string;
  localPath: string;
  file: File | null;
}

export function getSubmissionError(draft: SubmissionDraft): string | null {
  if (!draft.rulesetVariant) {
    return 'Choose a ruleset before submitting the match.';
  }

  if (draft.sourceType === 'upload' && !draft.file) {
    return 'Choose a local video file to upload.';
  }

  if (draft.sourceType === 'local_path' && !draft.localPath.trim()) {
    return 'Paste an absolute local video path to continue.';
  }

  if (draft.sourceType === 'youtube' && !draft.sourceUrl.trim()) {
    return 'Paste a YouTube URL to continue.';
  }

  return null;
}

export function canSubmitSubmission(draft: SubmissionDraft): boolean {
  return getSubmissionError(draft) === null;
}

export function getStatusBanner(job: VideoJobSummary): string {
  if (job.status === 'queued') {
    return `${job.message} The job is waiting in line.`;
  }

  if (job.status === 'running') {
    return `${job.message} Processing is underway.`;
  }

  if (job.status === 'completed') {
    return `${job.message} Analysis finished and ready for the dashboard.`;
  }

  return `${job.message} Please review the error and try again.`;
}

export function getProgressPercent(job: VideoJobSummary): number {
  const rawValue = Number.isFinite(job.progress) ? job.progress : 0;
  const normalized = rawValue <= 1 ? rawValue * 100 : rawValue;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

export function getProgressLabel(job: VideoJobSummary): string {
  return `${getProgressPercent(job)}% complete`;
}

export function canOpenDashboard(job: VideoJobSummary | null): boolean {
  return job?.status === 'completed';
}

export function getDefaultView(job: VideoJobSummary | null): AppView {
  if (!job) {
    return 'upload';
  }

  if (job.status === 'completed') {
    return 'dashboard';
  }

  return 'job-status';
}

export function getJobSourceLabel(job: VideoJobSummary | null): string {
  if (!job) {
    return 'Unknown';
  }

  return job.source_type ?? job.sourceType ?? 'local_path';
}
