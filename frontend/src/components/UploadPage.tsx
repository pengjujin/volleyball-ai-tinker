import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

import { submitVideoJob } from '../lib/api';
import { canSubmitSubmission, getSubmissionError } from '../lib/workflow';
import type {
  RulesetVariant,
  VideoJobSummary,
  VideoSourceType,
} from '../lib/types';

const sourceOptions: Array<{ value: VideoSourceType; label: string }> = [
  { value: 'local_path', label: 'Local path' },
  { value: 'upload', label: 'Local file' },
  { value: 'youtube', label: 'YouTube URL' },
];

interface UploadPageProps {
  onJobCreated: (job: VideoJobSummary) => void;
}

export function UploadPage({ onJobCreated }: UploadPageProps) {
  const [title, setTitle] = useState('');
  const [rulesetVariant, setRulesetVariant] = useState<RulesetVariant | ''>('');
  const [sourceType, setSourceType] = useState<VideoSourceType>('local_path');
  const [sourceUrl, setSourceUrl] = useState('');
  const [localPath, setLocalPath] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState('No file selected yet');
  const [status, setStatus] = useState(
    'Choose a ruleset and a video source to begin.',
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submissionDraft = {
    rulesetVariant,
    sourceType,
    sourceUrl,
    localPath,
    file,
  };
  const submissionError = getSubmissionError(submissionDraft);
  const canSubmit = canSubmitSubmission(submissionDraft) && !isSubmitting;

  const activeSourceLabel =
    sourceOptions.find((option) => option.value === sourceType)?.label ??
    'Unknown';

  function handleSourceTypeChange(nextSourceType: VideoSourceType) {
    setSourceType(nextSourceType);

    if (nextSourceType !== 'upload') {
      setFile(null);
      setFileName('No file selected yet');
    }

    if (nextSourceType !== 'local_path') {
      setLocalPath('');
    }

    if (nextSourceType !== 'youtube') {
      setSourceUrl('');
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (file) {
      setFile(file);
      setFileName(file.name);
      setStatus(`Ready to submit ${file.name}.`);
    } else {
      setFile(null);
      setFileName('No file selected yet');
      setStatus('Choose a local file to continue.');
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationError = getSubmissionError(submissionDraft);
    if (validationError) {
      setStatus(validationError);
      return;
    }

    setIsSubmitting(true);
    setStatus('Submitting match for analysis...');

    try {
      const job = await submitVideoJob({
        title: title.trim() || undefined,
        sourceType,
        sourceUrl: sourceUrl.trim() || undefined,
        localPath: localPath.trim() || undefined,
        file,
        rulesetVariant: rulesetVariant as RulesetVariant,
      });
      setStatus(`Job ${job.id} queued. ${job.message}`);
      onJobCreated(job);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Submission failed. Please try again.';
      setStatus(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <article className="panel panel--hero">
      <div className="section-heading">
        <p className="panel__eyebrow">Upload flow</p>
        <h2>Prepare a match for analysis</h2>
        <p className="panel__lede">
          This is the first screen a coach or analyst will see. It keeps the
          upload path simple, requires a match ruleset, and leaves room for a
          backend job queue later.
        </p>
      </div>

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Match title</span>
          <input
            className="field__control"
            type="text"
            placeholder="Example: Varsity semifinal, set 4"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Ruleset</span>
          <select
            className="field__control"
            value={rulesetVariant}
            onChange={(event) =>
              setRulesetVariant(event.target.value as RulesetVariant | '')
            }
          >
            <option value="">Select ruleset</option>
            <option value="6-player">6-player</option>
            <option value="9-man">9-man</option>
          </select>
          <span className="field__hint">
            This choice is required before the job can be submitted.
          </span>
        </label>

        <label className="field">
          <span className="field__label">Video source</span>
          <div className="segmented-control" role="radiogroup">
            {sourceOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`segmented-control__item${
                  sourceType === option.value
                    ? ' segmented-control__item--active'
                    : ''
                }`}
                onClick={() => handleSourceTypeChange(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </label>

        {sourceType === 'local_path' ? (
          <label className="field field--wide">
            <span className="field__label">Local path</span>
            <input
              className="field__control"
              type="text"
              placeholder="/absolute/path/to/match.mp4"
              value={localPath}
              onChange={(event) => setLocalPath(event.target.value)}
            />
            <span className="field__hint">
              The backend will analyze this file in place without copying it.
            </span>
          </label>
        ) : null}

        {sourceType === 'upload' ? (
          <label className="field field--wide">
            <span className="field__label">Local file</span>
            <input
              className="field__control field__control--file"
              type="file"
              accept="video/*"
              onChange={handleFileChange}
            />
            <span className="field__hint">{fileName}</span>
          </label>
        ) : null}

        {sourceType === 'youtube' ? (
          <label className="field field--wide">
            <span className="field__label">YouTube URL</span>
            <input
              className="field__control"
              type="url"
              placeholder="https://www.youtube.com/watch?v=..."
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
            />
            <span className="field__hint">
              Optional best-effort input when direct upload is not convenient.
            </span>
          </label>
        ) : null}

        <button className="primary-button" type="submit" disabled={!canSubmit}>
          {isSubmitting ? 'Submitting...' : 'Prepare analysis job'}
        </button>
      </form>

      <div className="status-banner" aria-live="polite">
        <strong>{status}</strong>
        {submissionError && !isSubmitting ? (
          <span className="status-banner__hint">{submissionError}</span>
        ) : null}
      </div>

      <section className="preview-grid" aria-label="submission preview">
        <div className="preview-card">
          <p className="preview-card__label">Target endpoint</p>
          <p className="preview-card__value">/api/videos</p>
        </div>
        <div className="preview-card">
          <p className="preview-card__label">Selected source</p>
          <p className="preview-card__value">{activeSourceLabel}</p>
        </div>
        <div className="preview-card">
          <p className="preview-card__label">Submission fields</p>
          <ul className="preview-list">
            {[
              ['title', title.trim() || 'unset'],
              ['rulesetVariant', rulesetVariant || 'unset'],
              ['sourceUrl', sourceUrl.trim() || 'unset'],
              ['localPath', localPath.trim() || 'unset'],
              ['selectedFile', fileName],
            ].map(([key, value]) => (
              <li key={key}>
                <span>{key}</span>
                <strong>{value}</strong>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </article>
  );
}
