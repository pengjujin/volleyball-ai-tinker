PYTHON := python3
NPM := npm --prefix frontend

.PHONY: setup lint typecheck test run-backend run-backend-reload run-frontend analyze-local

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(NPM) install

lint:
	$(PYTHON) tools/check_style.py

typecheck:
	$(PYTHON) -m compileall backend tests
	$(NPM) run typecheck

test:
	$(PYTHON) -m unittest discover -s tests/backend -t .
	$(NPM) run test

run-backend:
	$(PYTHON) -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

run-backend-reload:
	$(PYTHON) -m uvicorn backend.app.main:app --reload

run-frontend:
	$(NPM) run dev

analyze-local:
	$(PYTHON) scripts/run_local_analysis.py $(if $(VIDEO_PATH),--video-path "$(VIDEO_PATH)") $(if $(YOUTUBE_URL),--youtube-url "$(YOUTUBE_URL)") --ruleset "$(RULESET)" $(if $(TITLE),--title "$(TITLE)") $(if $(OUTPUT_DIR),--output-dir "$(OUTPUT_DIR)")
