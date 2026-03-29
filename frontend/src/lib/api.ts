import type {
  AnalyticsSnapshot,
  MatchAnalyticsSummary,
  SetEvent,
  VideoJobSummary,
  VideoSubmissionFields,
  VideoSubmissionInput,
} from './types';

const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

export function buildApiUrl(path: string, baseUrl = ''): string {
  const resolvedBaseUrl = baseUrl || DEFAULT_API_BASE_URL;
  const trimmedBase = resolvedBaseUrl.trim().replace(/\/+$/, '');
  const trimmedPath = path.trim().replace(/^\/+/, '');

  if (!trimmedBase) {
    return `/${trimmedPath}`;
  }

  try {
    return new URL(trimmedPath, `${trimmedBase}/`).toString();
  } catch {
    return `${trimmedBase}/${trimmedPath}`;
  }
}

export function buildVideoSubmissionFields(
  input: VideoSubmissionInput,
): VideoSubmissionFields {
  return {
    title: input.title?.trim() ?? '',
    sourceType: input.sourceType,
    sourceUrl: input.sourceUrl?.trim() ?? '',
    localPath: input.localPath?.trim() ?? '',
    rulesetVariant: input.rulesetVariant,
  };
}

export function buildVideoSubmissionFormData(
  input: VideoSubmissionInput,
): FormData {
  const fields = buildVideoSubmissionFields(input);
  const formData = new FormData();

  for (const [key, value] of Object.entries(fields)) {
    if (value) {
      formData.append(key, value);
    }
  }

  if (input.file && input.sourceType === 'upload') {
    formData.append('file', input.file);
  }

  return formData;
}

export async function submitVideoJob(
  input: VideoSubmissionInput,
  fetchImpl: typeof fetch = fetch,
  baseUrl?: string,
): Promise<VideoJobSummary> {
  const response = await fetchImpl(buildApiUrl('/api/videos', baseUrl), {
    method: 'POST',
    body: buildVideoSubmissionFormData(input),
  });

  if (!response.ok) {
    throw new Error(`Video submission failed with status ${response.status}`);
  }

  return (await response.json()) as VideoJobSummary;
}

export async function fetchVideoJob(
  videoId: string,
  fetchImpl: typeof fetch = fetch,
  baseUrl?: string,
): Promise<VideoJobSummary> {
  const response = await fetchImpl(
    buildApiUrl(`/api/videos/${videoId}`, baseUrl),
  );

  if (!response.ok) {
    throw new Error(`Video lookup failed with status ${response.status}`);
  }

  return (await response.json()) as VideoJobSummary;
}

export async function fetchAnalyticsSnapshot(
  videoId: string,
  fetchImpl: typeof fetch = fetch,
  baseUrl?: string,
): Promise<AnalyticsSnapshot> {
  const response = await fetchImpl(
    buildApiUrl(`/api/videos/${videoId}/analytics`, baseUrl),
  );

  if (!response.ok) {
    throw new Error(`Analytics lookup failed with status ${response.status}`);
  }

  return (await response.json()) as AnalyticsSnapshot;
}

export async function fetchVideoEvents(
  videoId: string,
  fetchImpl: typeof fetch = fetch,
  baseUrl?: string,
): Promise<SetEvent[]> {
  const response = await fetchImpl(
    buildApiUrl(`/api/videos/${videoId}/events`, baseUrl),
  );

  if (!response.ok) {
    throw new Error(`Event lookup failed with status ${response.status}`);
  }

  return (await response.json()) as SetEvent[];
}

export async function fetchVideoAnalytics(
  videoId: string,
  fetchImpl: typeof fetch = fetch,
  baseUrl?: string,
): Promise<MatchAnalyticsSummary> {
  const response = await fetchImpl(
    buildApiUrl(`/api/videos/${videoId}/analytics`, baseUrl),
  );

  if (!response.ok) {
    throw new Error(`Analytics lookup failed with status ${response.status}`);
  }

  return (await response.json()) as MatchAnalyticsSummary;
}
