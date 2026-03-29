export type AppView = 'upload' | 'job-status' | 'dashboard';

export type RulesetVariant = '6-player' | '9-man';

export type VideoSourceType = 'local_path' | 'upload' | 'youtube';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export type TeamSide = 'near' | 'far' | 'both';

export type TempoBucket = 'quick' | 'medium' | 'high/slow';
export type SetResult = 'success' | 'failure';

export interface TeamAnalyticsSummary {
  team_side: 'near_side' | 'far_side' | 'unknown';
  total_set_attempts: number;
  successful_sets: number;
  success_rate: number;
  tempo_distribution: Record<TempoBucket, number>;
  target_zone_distribution: Record<string, number>;
}

export interface MatchAnalyticsSummary {
  video_asset_id: string;
  ruleset_variant: RulesetVariant;
  generated_at?: string | null;
  overall: TeamAnalyticsSummary;
  by_team: TeamAnalyticsSummary[];
}

export interface SetEvent {
  set_event_id: string;
  video_asset_id: string;
  rally_segment_id?: string | null;
  source_candidate_clip_id?: string | null;
  timestamp_s: number;
  setter_team_side: 'near_side' | 'far_side' | 'unknown';
  target_zone: string;
  set_type?: string | null;
  set_success: boolean;
  success_reason?: string | null;
  set_tempo: TempoBucket;
  setter_court_x?: number | null;
  setter_court_y?: number | null;
  confidence: number;
  notes?: string | null;
  created_at?: string | null;
}

export interface VideoSubmissionInput {
  title?: string;
  sourceType: VideoSourceType;
  sourceUrl?: string;
  localPath?: string;
  file?: File | null;
  rulesetVariant: RulesetVariant;
}

export interface VideoSubmissionFields {
  title: string;
  sourceType: VideoSourceType;
  sourceUrl: string;
  localPath: string;
  rulesetVariant: RulesetVariant;
}

export interface VideoJobSummary {
  id: string;
  job_id?: string;
  title: string;
  sourceType?: VideoSourceType;
  source_type?: VideoSourceType;
  source_url?: string | null;
  local_path?: string | null;
  mime_type?: string | null;
  source_file_name?: string | null;
  rulesetVariant?: RulesetVariant;
  ruleset_variant?: RulesetVariant;
  status: JobStatus;
  progress: number;
  message: string;
  normalized_asset?: {
    kind: 'normalized' | 'proxy';
    path: string;
    status: string;
    format: string;
    codec: string;
    durationSeconds?: number | null;
    fps?: number | null;
    width?: number | null;
    height?: number | null;
  };
  proxy_asset?: {
    kind: 'normalized' | 'proxy';
    path: string;
    status: string;
    format: string;
    codec: string;
    durationSeconds?: number | null;
    fps?: number | null;
    width?: number | null;
    height?: number | null;
  };
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AnalyticsSnapshot {
  team_side: TeamSide;
  total_sets: number;
  success_rate: number;
  tempo_mix: Record<TempoBucket, number>;
  by_team?: TeamAnalyticsSummary[];
}
