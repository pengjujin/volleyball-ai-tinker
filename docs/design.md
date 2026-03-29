# Volleyball AI MVP Design

## 1. Overview

This project analyzes a volleyball game video, identifies setter actions, and displays setter-focused analytics in a web application synchronized with the original game video.

The MVP must support both standard 6-player volleyball and 9-man volleyball without hardcoding assumptions that only apply to one ruleset.

The first MVP is intentionally narrow:

- Input: a local video file or a YouTube URL
- Analysis target: both teams' setters when they can be detected reliably
- Primary model: Gemini video-capable VLM for semantic understanding of rallies and set events
- Frontend: a web UI with the game video, event timeline, and court overlays
- Efficiency requirement: do not send every frame to the VLM

The design assumes mostly full-match recordings taken from behind the court, with optional support for YouTube when available.

## 2. Product Goals

- Let a user submit a volleyball match video and receive setter analytics without manual tagging.
- Show where the setter distributed the ball on a court overlay aligned with the real video.
- Quantify setter performance with interpretable metrics.
- Keep inference cost manageable through clip selection, sampling, and filtering.

## 3. Non-Goals for MVP

- Full-team player identification and tracking
- Serve receive, blocking, or libero analytics
- Frame-perfect ball trajectory reconstruction for the entire match
- Support for multiple simultaneous camera angles
- Real-time inference during live matches

## 4. MVP Questions the System Must Answer

For each detected set event:

- When did the set happen?
- Where was the setter on the court?
- Which direction / target zone was the ball set to?
- Was the set successful?
- How confident is the system in that answer?

Across the match, the system should compute:

- Set count
- Set distribution by target zone
- Success rate by target zone
- Tempo distribution
- In-system vs out-of-system set rate
- Average setter court position at contact
- Estimated movement distance before the set
- Confidence-weighted event coverage

## 5. User Experience

1. User pastes a YouTube URL or uploads a video.
2. The backend ingests the video and creates a processing job.
3. The pipeline extracts rallies, proposes candidate setter events, and sends only selected clips to Gemini.
4. The system stores normalized events, court coordinates, and analytics.
5. The frontend shows:
   - the original video player
   - a synchronized event timeline
   - a court overlay with set destinations
   - summary charts and tables for setter metrics

## 6. High-Level Architecture

### 6.1 Components

- Ingestion service
  - Accepts a YouTube URL or local upload
  - Downloads or normalizes video into a processing format
- Preprocessing pipeline
  - Detects rallies and skips dead time
  - Samples low-rate frames
  - Generates candidate clips likely to contain set events
- Gemini analysis service
  - Sends short clips plus structured prompts to Gemini
  - Receives event labels and metadata
- Analytics engine
  - Converts Gemini outputs into normalized volleyball events
  - Computes setter metrics and distributions
- Storage layer
  - Stores videos, clip metadata, event records, derived analytics, and overlay geometry
- Web frontend
  - Displays the video, overlays, charts, and event list

### 6.2 Recommended Stack

- Backend: Python + FastAPI
- Async jobs: Celery or Dramatiq with Redis
- Video processing: FFmpeg + OpenCV
- Database: PostgreSQL
- Object storage: local filesystem for MVP, S3-compatible later
- Frontend: React + TypeScript
- Visualization: custom canvas/SVG overlay + chart library

## 7. Core Technical Design

### 7.1 Video Ingestion

Supported inputs:

- Local MP4/MOV upload
- Public YouTube URL

Processing steps:

- Normalize to a standard codec/resolution for downstream processing
- Extract metadata such as FPS, duration, and resolution
- Generate a low-resolution proxy for UI playback and a processing copy for analysis
- Capture match metadata including ruleset variant such as `6-player` or `9-man`

Important note:

- YouTube ingestion should be treated as an optional connector, because download permissions and ToS constraints may affect implementation. The product should also support direct uploads so the pipeline does not depend entirely on YouTube.

### 7.2 Court Registration

To draw set distributions on top of the video and on a mini-court, the system needs a mapping between video pixels and canonical court coordinates.

Approach:

- Detect court boundary lines on selected key frames
- Estimate a homography from the behind-the-court view to a normalized court plane
- Recompute when the camera angle changes materially, although many user-recorded games may use a mostly fixed camera

Outputs:

- Court transform for each stable camera segment
- Setter and ball contact positions mapped into court coordinates
- Overlay primitives for the frontend

### 7.3 Event Proposal and Smart Sampling

The key cost-control principle is a multi-stage pipeline:

#### Stage A: Dead-Time Filtering

Skip segments that are unlikely to contain rallies by using cheap signals:

- Large scene cuts / replay transitions
- Long periods of low motion
- Scoreboard close-ups
- Crowd shots
- Timeout or between-point pauses

#### Stage B: Coarse Rally Segmentation

Run a lightweight pass at low FPS, for example 2-4 FPS, to identify active rallies.

Useful heuristics:

- Sustained player motion on court
- Ball-like motion bursts
- Camera framing consistent with behind-the-court gameplay
- Audio energy spikes around contacts

Output:

- Rally windows such as `start_ts`, `end_ts`, and coarse confidence

#### Stage C: Candidate Set Proposal

Within rally windows, propose candidate set moments without using Gemini on every frame.

Low-cost proposal options:

- Ball motion inflection after an upward touch
- Player cluster near the net followed by ball redirection
- Team-side and formation priors learned from repeated second-contact behavior, without assuming a fixed 6-player layout
- Short tracking bursts around likely second contacts

For each proposal, extract a short clip such as 2-5 seconds around the event.

#### Stage D: Gemini Confirmation

Send only candidate clips to Gemini and ask it to:

- confirm whether the clip contains a set
- identify the setter
- identify which team the setter belongs to
- estimate contact time
- classify target zone
- classify set tempo
- classify success / failure
- return structured JSON with confidences

#### Stage E: Uncertainty-Triggered Refinement

If Gemini confidence is low:

- sample a denser clip around the same event
- add neighboring frames
- optionally run a second pass with a stronger prompt or model tier

This design keeps VLM calls focused on semantically rich moments rather than continuous video.

### 7.4 Why Gemini Should Not Be the Only Layer

Gemini is well-suited for semantic interpretation of short volleyball clips, but it is less suitable as the sole system for:

- long continuous video scanning
- frame-accurate spatial overlays
- cost-efficient whole-match processing

Therefore the MVP should use Gemini for event understanding and a traditional video pipeline for:

- clip selection
- court calibration
- timestamp alignment
- overlay geometry

### 7.5 Gemini Prompting Strategy

Each Gemini request should include:

- a short clip, not a full match
- the current task context: "analyze setter actions for both teams when detectable"
- a strict JSON schema response
- definitions of success / failure
- target zone taxonomy
- tempo taxonomy
- a request for uncertainty/confidence

Example output fields:

```json
{
  "contains_set": true,
  "setter_team": "near_side",
  "contact_time_s": 123.42,
  "setter_bbox": [x1, y1, x2, y2],
  "setter_court_xy": [4.2, 2.8],
  "target_zone": "zone_4",
  "set_type": "high_outside",
  "set_tempo": "medium",
  "set_success": true,
  "success_reason": "hitter_received_attackable_ball",
  "confidence": 0.84,
  "notes": "out_of_system set from 3-meter line"
}
```

The backend should validate Gemini outputs against a schema and reject malformed responses.

### 7.6 Setter Analytics Definitions

The MVP should explicitly define metrics so the UI is interpretable.

Suggested definitions:

- Set attempt
  - A second-contact action intended to deliver the ball to an attacker
- Successful set
  - The set produces an attackable ball for a teammate without an immediate setting error
- Failed set
  - Double contact, lift, overpass, misconnection, or a set that prevents a realistic attack
- In-system set
  - Setter delivers from a relatively stable offensive shape
- Out-of-system set
  - Setter delivers under scramble conditions or from a non-standard court position
- Set tempo
  - A coarse classification of how quickly the attack was delivered after the set, such as `quick`, `medium`, or `high/slow`, defined consistently for the chosen footage type

Recommended MVP metrics:

- Total set attempts
- Successful sets
- Success percentage
- Distribution by target zone
- Distribution by front row vs back row target
- Tempo distribution
- Success percentage by tempo
- Average setter contact location
- Average time from rally start to first set in possession
- Out-of-system frequency
- High-confidence vs low-confidence event counts

### 7.7 Data Model

Core entities:

- `video_asset`
  - source type, source URL, duration, FPS, status, ruleset variant
- `processing_job`
  - stage, progress, logs, error state
- `camera_segment`
  - start/end timestamps, homography, confidence
- `rally_segment`
  - start/end timestamps, possession metadata
- `event`
  - timestamp, type, confidence, source clip id
- `set_event`
  - event id, setter identity label, team side, target zone, success, set type, set tempo, in-system flag, court coordinates
- `analytics_snapshot`
  - aggregated metrics for frontend queries

For the first MVP, player identity can be a logical label such as:

- `near_team_setter`
- `far_team_setter`

The system does not need persistent jersey-number identification yet.

The system should also avoid hardcoding six-player rotational assumptions so the same pipeline can operate on both 6-player and 9-man videos.

## 8. Backend APIs

Suggested API surface:

- `POST /api/videos`
  - create video from upload or URL
- `POST /api/videos/{id}/process`
  - enqueue analysis
- `GET /api/videos/{id}`
  - get processing status
- `GET /api/videos/{id}/events`
  - list set events with timestamps and metadata
- `GET /api/videos/{id}/analytics`
  - aggregated setter metrics, split by team side when available
- `GET /api/videos/{id}/overlay`
  - court overlay primitives by timestamp

## 9. Frontend Design

### 9.1 Core Screens

- Video upload / URL submission page
- Processing status page
- Analytics dashboard page

### 9.2 Dashboard Layout

Main elements:

- Video player with synchronized overlay
- Team filter or compare mode for near-side and far-side setters when both are detected
- Toggleable overlay layers:
  - setter position
  - set target arrow
  - destination zone heatmap
- Timeline markers for detected set events
- Summary cards:
  - total sets
  - success rate
  - tempo mix
  - out-of-system rate
- Charts:
  - set distribution by zone
  - success by zone
  - tempo distribution
  - setter contact heatmap
- Event table:
  - timestamp
  - target zone
  - success/failure
  - confidence

### 9.3 Overlay Behavior

Two synchronized views are useful:

- On-video overlay for spatial context in the original behind-the-court recording
- Mini-court overlay for clean aggregate visualization

For each event, show:

- setter contact point
- arrow from setter to target zone
- optional confidence label

## 10. Validation Strategy

### 10.1 Ground Truth for MVP

Start with a small labeled evaluation set:

- 3-5 matches or rally collections
- manually labeled set events
- success/failure labels
- target zone labels

### 10.2 Metrics

Measure:

- set event precision / recall
- target zone classification accuracy
- success classification accuracy
- timestamp error tolerance, for example within 0.5-1.0 seconds
- overlay alignment sanity checks on sampled clips

### 10.3 Human-in-the-Loop Option

Because video understanding will not be perfect, the MVP should leave room for optional review tools later:

- accept/reject detected events
- correct target zones
- mark missed sets

This is intentionally deferred for the first build, but the data model should not block it.

## 11. Risks and Open Technical Challenges

- Behind-the-court recordings may still hide the ball or contact point during fast plays, especially if the camera is low-resolution or handheld.
- Court-line detection may fail under severe perspective shifts or occlusion.
- A pure VLM approach may be too expensive or inconsistent for full-match analysis.
- 9-man footage may differ enough in formations and offensive patterns that simple 6-player heuristics will underperform if not made configurable.
- YouTube ingestion may introduce legal or operational constraints.
- Without robust player identification, team-side inference may occasionally flip after side changes.

## 12. Recommended MVP Build Order

### Milestone 1: Ingestion and Playback

- Accept local video and optional YouTube URL
- Normalize video and show it in a simple web player
- Store metadata including ruleset variant and job status

### Milestone 2: Rally Segmentation and Clip Proposal

- Detect active rally windows
- Build candidate set clip extraction
- Verify that the pipeline reduces video volume substantially before VLM calls

### Milestone 3: Gemini Set Detection

- Send candidate clips to Gemini
- Parse structured responses
- Persist set events for both detectable teams with confidence

### Milestone 4: Court Registration and Overlay

- Map event positions to court coordinates
- Render event overlays on top of the video and on a mini-court

### Milestone 5: Setter Analytics Dashboard

- Compute metrics
- Display team-split distribution charts, success rate, tempo metrics, and event table

### Milestone 6: Evaluation and Refinement

- Compare against labeled data
- Tune prompts, thresholds, and sampling rules

## 13. Locked-In MVP Decisions

The first version should assume:

- one full-match video per analysis job
- mostly behind-the-court recordings captured by the user
- a fixed camera for the duration of the match
- both teams' setters should be analyzed when detectable
- a successful set means the ball is attackable for a teammate
- offline batch processing, not real-time
- local upload support from day one, with YouTube URL support as a best-effort option
- no manual correction workflow in the MVP
- the user explicitly selects `6-player` or `9-man` before processing
- support for both 6-player and 9-man matches through configurable match metadata and analytics logic
- tempo should use simple discrete buckets such as `quick`, `medium`, and `high/slow`
- event-level overlays and aggregated charts before any advanced player tracking

## 14. Resolved Product Decisions

- The user should specify `6-player` versus `9-man` before processing.
- The camera should be treated as fixed for the full match in the MVP.
- Tempo should be shown using simple discrete buckets: `quick`, `medium`, and `high/slow`.
