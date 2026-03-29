from .analyze_candidate_clips import (
    CandidateClipEventResult,
    analyze_candidate_clips_to_events,
)
from .audio_features import AudioBurst, burst_peak_score, detect_audio_bursts, in_audio_burst
from .candidate_set_proposal import (
    CandidateSetProposalResult,
    estimate_video_reduction,
    propose_candidate_set_clips,
)
from .frame_sampling import filter_dead_time_frames, is_active_frame, score_frame_activity
from .preprocess_video import PreprocessVideoResult, preprocess_video_signals
from .rally_segmentation import detect_active_rally_frames, detect_rally_windows
from .video_registry import (
    InMemoryVideoRegistry,
    VideoSubmissionError,
    get_video_registry,
)

__all__ = [
    "AudioBurst",
    "CandidateClipEventResult",
    "CandidateSetProposalResult",
    "InMemoryVideoRegistry",
    "PreprocessVideoResult",
    "analyze_candidate_clips_to_events",
    "VideoSubmissionError",
    "burst_peak_score",
    "detect_active_rally_frames",
    "detect_audio_bursts",
    "detect_rally_windows",
    "estimate_video_reduction",
    "filter_dead_time_frames",
    "get_video_registry",
    "in_audio_burst",
    "is_active_frame",
    "preprocess_video_signals",
    "propose_candidate_set_clips",
    "score_frame_activity",
]
