# Volleyball AI Implementation Plan

## Overview

This plan turns the MVP design in `docs/design.md` into six implementation milestones. The MVP targets full-match volleyball videos from a fixed behind-the-court camera, supports both `6-player` and `9-man` matches via explicit user input, analyzes both teams' setters when detectable, uses Gemini for semantic set understanding, and exposes analytics in a web frontend with synchronized overlays.

## Sequencing

- Milestone 1 must happen first because it establishes the repo structure, shared schemas, quality commands, and local development flow.
- Milestone 2 depends on Milestone 1.
- Milestone 3 depends on Milestone 2.
- Milestone 4 depends on Milestone 3.
- Milestone 5 depends on Milestone 4 for stable `set_event` contracts.
- Milestone 6 depends on Milestone 4, and can proceed in parallel with the backend-heavy portions of Milestone 5 once API contracts are frozen.

## Parallelization Summary

- Sequential: Milestones 1, 2, 3, and 4.
- Parallelizable: Milestones 5 and 6 after Milestone 4 stabilizes the event schema and API payloads.

## Milestone 1: Foundation and Project Scaffold

**Type:** Sequential

**Goal**

Create the initial full-stack project scaffold, shared data contracts, and repo quality gates so later milestones can land as small, reviewable diffs.

**Dependencies**

- None

**Likely Files/Modules Affected**

- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/config.py`
- `backend/app/schemas/`
- `frontend/package.json`
- `frontend/src/`
- `tests/`
- `Makefile`
- `README.md`

**Implementation Steps**

1. Scaffold a FastAPI backend with health and version endpoints.
2. Scaffold a React + TypeScript frontend with a simple shell page and API client layer.
3. Define initial shared backend schemas for `video_asset`, `processing_job`, `rally_segment`, `set_event`, and analytics payloads.
4. Establish the project layout for video processing, Gemini integration, analytics, and overlay services.
5. Add baseline lint, typecheck, and test commands through a top-level `Makefile`.
6. Add basic CI-friendly test scaffolding for backend and frontend.

**Risks / Open Questions**

- The exact frontend toolchain should stay lightweight and common; avoid over-investing in build tooling before feature work starts.
- Shared type generation between backend and frontend is helpful, but can wait if it slows the initial scaffold.

**Validation Commands**

- `make lint`
- `make typecheck`
- `make test`

**Acceptance Criteria**

- Backend and frontend both boot locally.
- `make lint`, `make typecheck`, and `make test` exist and pass.
- Core schema modules exist for the main entities used in later milestones.

## Milestone 2: Video Ingestion, Match Setup, and Job Orchestration

**Type:** Sequential

**Goal**

Accept a full-match upload or YouTube URL, require the user to choose `6-player` or `9-man`, normalize the video, and persist a processing job lifecycle.

**Dependencies**

- Milestone 1

**Likely Files/Modules Affected**

- `backend/app/api/videos.py`
- `backend/app/models/video_asset.py`
- `backend/app/models/processing_job.py`
- `backend/app/services/video_ingest.py`
- `backend/app/services/video_normalize.py`
- `backend/app/services/job_queue.py`
- `backend/app/schemas/video.py`
- `frontend/src/pages/UploadPage.tsx`
- `frontend/src/pages/JobStatusPage.tsx`
- `frontend/src/components/MatchSetupForm.tsx`
- `tests/backend/test_video_ingest.py`

**Implementation Steps**

1. Add `POST /api/videos` for upload or URL submission.
2. Require the client to submit match metadata including ruleset variant.
3. Normalize videos into a stable processing format and generate a proxy asset for playback.
4. Persist job state transitions such as `queued`, `running`, `failed`, and `completed`.
5. Build a minimal frontend flow for upload, match-type selection, and job-status polling.
6. Treat YouTube ingestion as optional/best-effort and fall back cleanly when unavailable.

**Risks / Open Questions**

- YouTube ingestion may be brittle or unavailable depending on environment and policy constraints.
- Large uploads may need chunking later, but the MVP can start with straightforward single-request uploads if bounded.

**Validation Commands**

- `make lint`
- `make typecheck`
- `pytest tests/backend/test_video_ingest.py`
- `make test`

**Acceptance Criteria**

- A user can submit a full-match video and choose `6-player` or `9-man`.
- The system stores normalized video metadata and a processing job record.
- The frontend shows upload progress and job state.

## Milestone 3: Rally Segmentation and Candidate Set Sampling

**Type:** Sequential

**Goal**

Reduce full-match video volume into rally windows and candidate setter clips so Gemini only sees a small subset of the match.

**Dependencies**

- Milestone 2

**Likely Files/Modules Affected**

- `backend/app/services/rally_segmentation.py`
- `backend/app/services/candidate_set_proposal.py`
- `backend/app/services/frame_sampling.py`
- `backend/app/services/audio_features.py`
- `backend/app/models/rally_segment.py`
- `backend/app/models/candidate_clip.py`
- `backend/app/workers/preprocess_video.py`
- `tests/backend/test_rally_segmentation.py`
- `tests/backend/test_candidate_set_proposal.py`

**Implementation Steps**

1. Add dead-time filtering using low-cost motion, cut-detection, and framing heuristics.
2. Segment active rally windows at low FPS.
3. Propose candidate set clips using second-contact heuristics, ball-motion changes, and near-net player behavior.
4. Ensure heuristics do not assume a six-player rotation shape so they remain usable for `9-man`.
5. Persist intermediate artifacts for rally windows and candidate clips to support debugging and later evaluation.
6. Add counters that estimate how much footage is filtered before Gemini is invoked.

**Risks / Open Questions**

- Candidate recall matters more than precision at this stage; being too aggressive could hide true set events.
- Some gym footage may have poor ball visibility, requiring more reliance on player-motion and timing heuristics.

**Validation Commands**

- `make lint`
- `make typecheck`
- `pytest tests/backend/test_rally_segmentation.py`
- `pytest tests/backend/test_candidate_set_proposal.py`
- `make test`

**Acceptance Criteria**

- The preprocessing pipeline produces rally windows from a full match.
- Candidate clips cover likely set moments while reducing Gemini workload materially.
- Intermediate artifacts are stored with timestamps and confidence scores.

## Milestone 4: Gemini Set Event Extraction

**Type:** Sequential

**Goal**

Use Gemini to confirm set events and extract structured setter analytics for both teams, including target zone, success, and tempo buckets.

**Dependencies**

- Milestone 3

**Likely Files/Modules Affected**

- `backend/app/integrations/gemini_client.py`
- `backend/app/services/gemini_set_analysis.py`
- `backend/app/services/event_normalization.py`
- `backend/app/models/set_event.py`
- `backend/app/schemas/set_event.py`
- `backend/app/workers/analyze_candidate_clips.py`
- `tests/backend/test_gemini_set_analysis.py`
- `tests/backend/test_event_normalization.py`

**Implementation Steps**

1. Implement Gemini clip submission for candidate windows.
2. Define a strict response schema covering team side, contact time, target zone, `set_success`, and tempo bucket.
3. Normalize Gemini outputs into stable `set_event` records.
4. Add uncertainty handling for malformed or low-confidence responses, including optional retry/refinement logic.
5. Persist per-event confidence and source-clip provenance for debugging.
6. Freeze the API shape for `GET /api/videos/{id}/events` so frontend work can begin safely.

**Risks / Open Questions**

- Gemini output consistency may vary across clips, so strong schema validation and retry logic are important.
- Tempo buckets may remain somewhat subjective until evaluated against real footage.

**Validation Commands**

- `make lint`
- `make typecheck`
- `pytest tests/backend/test_gemini_set_analysis.py`
- `pytest tests/backend/test_event_normalization.py`
- `make test`

**Acceptance Criteria**

- The system stores valid `set_event` records for both teams when detectable.
- Each event includes success, target zone, tempo bucket, timestamp, and confidence.
- The event API contract is stable enough for downstream analytics and UI work.

## Milestone 5: Analytics Aggregation and Court Registration

**Type:** Parallelizable after Milestone 4

**Goal**

Compute setter analytics and map events into court coordinates so the product can support both aggregate charts and video-aligned overlays.

**Dependencies**

- Milestone 4

**Likely Files/Modules Affected**

- `backend/app/services/analytics_aggregation.py`
- `backend/app/services/court_registration.py`
- `backend/app/services/overlay_projection.py`
- `backend/app/api/analytics.py`
- `backend/app/api/overlay.py`
- `backend/app/schemas/analytics.py`
- `backend/app/schemas/overlay.py`
- `tests/backend/test_analytics_aggregation.py`
- `tests/backend/test_court_registration.py`

**Implementation Steps**

1. Compute aggregate metrics split by team side.
2. Add tempo distribution and success-by-tempo analytics.
3. Estimate court homography from the fixed behind-the-court view.
4. Project setter contact points and target locations into canonical court coordinates.
5. Expose analytics and overlay APIs with timestamp-aligned payloads.
6. Add fallback behavior when court registration confidence is too low.

**Risks / Open Questions**

- Court-line visibility may vary across gyms, which can degrade overlay accuracy.
- Mapping destination zones may need approximation rather than exact ball landing points in the MVP.

**Validation Commands**

- `make lint`
- `make typecheck`
- `pytest tests/backend/test_analytics_aggregation.py`
- `pytest tests/backend/test_court_registration.py`
- `make test`

**Acceptance Criteria**

- Analytics APIs return team-split setter metrics including tempo buckets.
- Overlay APIs return timestamped geometry that the frontend can render.
- The system degrades gracefully when court registration is uncertain.

## Milestone 6: Frontend Dashboard and Synchronized Visualization

**Type:** Parallelizable after Milestone 4

**Goal**

Deliver the MVP web experience: original video playback, event timeline, team filter/compare mode, court overlays, and setter analytics visualizations.

**Dependencies**

- Milestone 4
- Milestone 5 APIs for final integration

**Likely Files/Modules Affected**

- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/VideoPlayer.tsx`
- `frontend/src/components/VideoOverlay.tsx`
- `frontend/src/components/EventTimeline.tsx`
- `frontend/src/components/TeamFilter.tsx`
- `frontend/src/components/SetterAnalyticsCards.tsx`
- `frontend/src/components/TempoChart.tsx`
- `frontend/src/components/SetDistributionChart.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types/`
- `tests/frontend/`

**Implementation Steps**

1. Build the dashboard page that loads video, event, analytics, and overlay data.
2. Render synchronized timeline markers for detected set events.
3. Add on-video overlays for setter position and set-direction arrows.
4. Add a mini-court or aggregate visualization for set distribution.
5. Add team filter/compare behavior when both setters are detected.
6. Display tempo buckets, success rate, and target-zone summaries in charts and cards.

**Risks / Open Questions**

- Overlay rendering must stay visually clear without obscuring the original video.
- Frontend performance may degrade if the overlay payload is overly granular; event-level overlays are preferable to frame-by-frame overlays.

**Validation Commands**

- `make lint`
- `make typecheck`
- `make test`

**Acceptance Criteria**

- A processed match can be viewed end-to-end in the browser.
- Users can inspect both teams' setter events, tempo, success, and distribution metrics.
- Video playback, overlays, and event timeline stay synchronized.

## Notes on Scope Control

- Avoid manual correction tools in the MVP.
- Avoid jersey-number identity tracking in the MVP.
- Avoid live or near-real-time processing in the MVP.
- Prefer event-level overlays and robust batch processing over fragile dense tracking.

## Recommended Next Step

Start with Milestone 1 and establish the smallest working backend/frontend scaffold plus repo-level validation commands. That will make the later milestone diffs smaller and easier to review.
