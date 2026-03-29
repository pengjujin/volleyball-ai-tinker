import { describe, expect, it } from 'vitest';

import {
  canOpenDashboard,
  canSubmitSubmission,
  getDefaultView,
  getProgressPercent,
  getProgressLabel,
  getStatusBanner,
  getSubmissionError,
} from '../../frontend/src/lib/workflow';

describe('workflow helpers', () => {
  it('requires a ruleset and the matching source input before submission', () => {
    expect(
      getSubmissionError({
        rulesetVariant: '',
        sourceType: 'upload',
        sourceUrl: '',
        localPath: '',
        file: null,
      }),
    ).toBe('Choose a ruleset before submitting the match.');

    expect(
      getSubmissionError({
        rulesetVariant: '6-player',
        sourceType: 'upload',
        sourceUrl: '',
        localPath: '',
        file: null,
      }),
    ).toBe('Choose a local video file to upload.');

    expect(
      getSubmissionError({
        rulesetVariant: '6-player',
        sourceType: 'local_path',
        sourceUrl: '',
        localPath: '',
        file: null,
      }),
    ).toBe('Paste an absolute local video path to continue.');

    expect(
      canSubmitSubmission({
        rulesetVariant: '9-man',
        sourceType: 'youtube',
        sourceUrl: 'https://youtube.com/watch?v=abc123',
        localPath: '',
        file: null,
      }),
    ).toBe(true);
  });

  it('describes job state consistently and unlocks the dashboard when done', () => {
    expect(
      getStatusBanner({
        id: 'job-1',
        title: 'Match',
        sourceType: 'upload',
        rulesetVariant: '6-player',
        status: 'running',
        progress: 66,
        message: 'Processing candidate clips',
      }),
    ).toContain('Processing is underway.');

    expect(
      getProgressLabel({
        id: 'job-1',
        title: 'Match',
        sourceType: 'upload',
        rulesetVariant: '6-player',
        status: 'running',
        progress: 66.2,
        message: 'Processing candidate clips',
      }),
    ).toBe('66% complete');

    expect(
      getProgressPercent({
        id: 'job-1',
        title: 'Match',
        sourceType: 'upload',
        rulesetVariant: '6-player',
        status: 'running',
        progress: 0.66,
        message: 'Processing candidate clips',
      }),
    ).toBe(66);

    expect(
      canOpenDashboard({
        id: 'job-1',
        title: 'Match',
        sourceType: 'upload',
        rulesetVariant: '6-player',
        status: 'completed',
        progress: 100,
        message: 'Done',
      }),
    ).toBe(true);

    expect(getDefaultView(null)).toBe('upload');
    expect(
      getDefaultView({
        id: 'job-1',
        title: 'Match',
        sourceType: 'upload',
        rulesetVariant: '6-player',
        status: 'completed',
        progress: 100,
        message: 'Done',
      }),
    ).toBe('dashboard');
  });
});
