import { describe, expect, it, vi } from 'vitest';

import {
  buildApiUrl,
  buildVideoSubmissionFormData,
  buildVideoSubmissionFields,
  fetchVideoAnalytics,
  fetchVideoEvents,
  fetchVideoJob,
  submitVideoJob,
} from '../../frontend/src/lib/api';

describe('buildApiUrl', () => {
  it('uses the app-relative path when no base URL is configured', () => {
    expect(buildApiUrl('/api/videos')).toBe('/api/videos');
  });

  it('joins an absolute base URL cleanly', () => {
    expect(buildApiUrl('/api/videos', 'https://api.example.com/')).toBe(
      'https://api.example.com/api/videos',
    );
  });
});

describe('buildVideoSubmissionFields', () => {
  it('trims optional fields and preserves the selected ruleset', () => {
    expect(
      buildVideoSubmissionFields({
        title: '  Varsity final  ',
        sourceType: 'local_path',
        localPath: '  /tmp/varsity-final.mp4  ',
        sourceUrl: '  https://youtube.com/watch?v=abc123  ',
        rulesetVariant: '9-man',
      }),
    ).toEqual({
      title: 'Varsity final',
      sourceType: 'local_path',
      localPath: '/tmp/varsity-final.mp4',
      sourceUrl: 'https://youtube.com/watch?v=abc123',
      rulesetVariant: '9-man',
    });
  });
});

describe('buildVideoSubmissionFormData', () => {
  it('does not append file bytes when the source type is local_path', () => {
    const formData = buildVideoSubmissionFormData({
      title: 'Varsity final',
      sourceType: 'local_path',
      localPath: '/tmp/varsity-final.mp4',
      file: new File(['video-bytes'], 'varsity-final.mp4', { type: 'video/mp4' }),
      rulesetVariant: '9-man',
    });

    expect(formData.get('sourceType')).toBe('local_path');
    expect(formData.get('localPath')).toBe('/tmp/varsity-final.mp4');
    expect(formData.get('file')).toBeNull();
  });
});

describe('submitVideoJob', () => {
  it('posts the submission fields and returns the created job summary', async () => {
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      const body = init?.body as FormData;

      expect(body.get('title')).toBe('Varsity final');
      expect(body.get('sourceType')).toBe('local_path');
      expect(body.get('localPath')).toBe('/tmp/varsity-final.mp4');
      expect(body.get('rulesetVariant')).toBe('9-man');

      return new Response(
        JSON.stringify({
          id: 'job-123',
          title: 'Varsity final',
          sourceType: 'local_path',
          local_path: '/tmp/varsity-final.mp4',
          rulesetVariant: '9-man',
          status: 'queued',
          progress: 12,
          message: 'Queued for preprocessing',
        }),
        {
          status: 201,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    }) as typeof fetch;

    const job = await submitVideoJob(
      {
        title: 'Varsity final',
        sourceType: 'local_path',
        localPath: '/tmp/varsity-final.mp4',
        rulesetVariant: '9-man',
      },
      fetchImpl,
      'https://api.example.com',
    );

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(job).toEqual({
      id: 'job-123',
      title: 'Varsity final',
      sourceType: 'local_path',
      local_path: '/tmp/varsity-final.mp4',
      rulesetVariant: '9-man',
      status: 'queued',
      progress: 12,
      message: 'Queued for preprocessing',
    });
  });
});

describe('fetchVideoJob', () => {
  it('fetches and parses the live job state', async () => {
    const fetchImpl = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          id: 'job-456',
          title: 'Night session',
          sourceType: 'upload',
          rulesetVariant: '6-player',
          status: 'running',
          progress: 74,
          message: 'Analyzing candidate set clips',
        }),
        {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    }) as typeof fetch;

    const job = await fetchVideoJob(
      'job-456',
      fetchImpl,
      'https://api.example.com',
    );

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(job.status).toBe('running');
    expect(job.progress).toBe(74);
    expect(job.message).toContain('Analyzing');
  });
});

describe('fetchVideoEvents', () => {
  it('fetches set events with snake_case backend fields', async () => {
    const fetchImpl = vi.fn(async () => {
      return new Response(
        JSON.stringify([
          {
            set_event_id: 'set-1',
            video_asset_id: 'video-1',
            timestamp_s: 12.345,
            setter_team_side: 'near_side',
            target_zone: 'zone_4',
            set_success: true,
            set_tempo: 'quick',
            confidence: 0.93,
          },
        ]),
        {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    }) as typeof fetch;

    const events = await fetchVideoEvents('video-1', fetchImpl, 'https://api.example.com');

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(events).toHaveLength(1);
    expect(events[0].set_event_id).toBe('set-1');
    expect(events[0].setter_team_side).toBe('near_side');
  });
});

describe('fetchVideoAnalytics', () => {
  it('fetches aggregated analytics with snake_case backend fields', async () => {
    const fetchImpl = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          video_asset_id: 'video-1',
          ruleset_variant: '6-player',
          overall: {
            team_side: 'unknown',
            total_set_attempts: 4,
            successful_sets: 3,
            success_rate: 0.75,
            tempo_distribution: {
              quick: 2,
              medium: 1,
              'high/slow': 1,
            },
            target_zone_distribution: {
              zone_4: 2,
              zone_2: 1,
              zone_3: 1,
            },
          },
          by_team: [],
        }),
        {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    }) as typeof fetch;

    const analytics = await fetchVideoAnalytics(
      'video-1',
      fetchImpl,
      'https://api.example.com',
    );

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(analytics.video_asset_id).toBe('video-1');
    expect(analytics.overall.total_set_attempts).toBe(4);
    expect(analytics.overall.tempo_distribution.quick).toBe(2);
  });
});
