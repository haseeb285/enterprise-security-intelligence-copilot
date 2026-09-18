# Phase 1 checkpoint

Completed 2026-09-18 on macOS arm64, Python 3.11.7. Phase 1 was approved after the Phase 0 architecture review.

## Added

- Initialized the `main` Git repository and an ignored `.venv` using the installed arm64 Python 3.11.
- Added a package foundation and immutable, validated Pydantic Settings for local URLs, model selection, request bounds, and future credentials. Database URLs and demo tokens are redacted in object representations.
- Added `.env.example`, `.gitignore`, direct dependency pins in `pyproject.toml`, and the installed development dependency set in `requirements-dev.lock`.
- Added pytest and Ruff configuration, configuration contract tests, and a README with exact setup commands.

## Verification performed

| Check | Result |
| --- | --- |
| Editable install from `requirements-dev.lock` | Passed |
| `python -m pytest` | 5 passed |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed, 9 files formatted |
| `python -m pip check` | No broken requirements |
| `python -m compileall -q app tests` | Passed |
| Import and settings load | Passed, `development` environment |
| Git ignore review | `.env`, `.venv`, `work`, and `outputs` ignored |
| Credential pattern scan | No matching token/private-key pattern in project files outside ignored paths |

The installed wheel for Pydantic Core and Ruff was macOS arm64. Runtime services, API startup, Docker, and Ollama are intentionally outside Phase 1 and were not tested here.

## Next phase boundary

Phase 2 will create PostgreSQL models and migrations, deterministic synthetic events, and tested event/incident queries. It requires separate user direction before work begins.
