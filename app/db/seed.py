"""Migrate first, then seed an isolated local PostgreSQL database with synthetic data."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from sqlalchemy import Engine, delete, func, insert, select, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Device, Incident, SecurityEvent, User
from app.db.session import check_db_connection, create_db_engine
from app.db.synthetic import ORGANIZATION, SYNTHETIC_NOTICE, SyntheticDataset, generate_dataset

MIGRATION_REVISION = "20260918_01"
DEFAULT_TRUTH_PATH = Path("data/runtime/ground_truth.json")


@dataclass(frozen=True)
class SeedResult:
    status: str
    seed: int
    users: int
    devices: int
    events: int
    incidents: int
    scenarios: int
    generation_seconds: float
    insertion_seconds: float
    ground_truth_path: str


def _insert_batches(session: Session, dataset: SyntheticDataset) -> None:
    session.execute(insert(User), dataset.users)
    session.execute(insert(Device), dataset.devices)
    session.execute(insert(Incident), dataset.incidents)
    for start in range(0, len(dataset.events), 1000):
        session.execute(insert(SecurityEvent), dataset.events[start : start + 1000])


def _export_ground_truth(dataset: SyntheticDataset, path: Path) -> None:
    payload = {
        "notice": SYNTHETIC_NOTICE,
        "organization": ORGANIZATION,
        "seed": dataset.seed,
        "scenarios": [scenario.as_json() for scenario in dataset.scenarios],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seed_database(
    engine: Engine,
    *,
    seed: int = 42,
    normal_event_count: int = 12_000,
    reset: bool = False,
    ground_truth_path: Path = DEFAULT_TRUTH_PATH,
) -> SeedResult:
    """Insert once; require explicit reset to replace an existing synthetic dataset."""

    check_db_connection(engine)
    try:
        with engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database schema check failed; run 'alembic upgrade head' first"
        ) from exc
    if revision != MIGRATION_REVISION:
        raise RuntimeError(f"Run 'alembic upgrade head' first; expected {MIGRATION_REVISION}")

    start = perf_counter()
    dataset = generate_dataset(seed=seed, normal_event_count=normal_event_count)
    generation_seconds = perf_counter() - start
    insertion_seconds = 0.0
    status = "seeded"
    with Session(engine) as session, session.begin():
        existing = session.scalar(select(AuditLog).where(AuditLog.action == "seed_synthetic_data"))
        counts = {
            model: session.scalar(select(func.count()).select_from(model)) or 0
            for model in (User, Device, Incident, SecurityEvent, AuditLog)
        }
        if existing is None and any(counts.values()):
            raise RuntimeError(
                "Refusing to modify a populated database without a synthetic seed marker"
            )
        if existing is not None:
            previous = json.loads(existing.details or "{}")
            expected = {
                User: 120,
                Device: 140,
                Incident: 6,
                SecurityEvent: previous.get(
                    "event_count", previous.get("normal_event_count", -1) + 65
                ),
            }
            if (
                any(counts[model] != count for model, count in expected.items())
                or counts[AuditLog] < 1
            ):
                raise RuntimeError("Seeded database has changed; refusing automatic replacement")
        if existing is not None and not reset:
            if (
                previous.get("seed") != seed
                or previous.get("normal_event_count") != normal_event_count
            ):
                raise RuntimeError("Existing seed differs; use --reset to replace local demo data")
            status = "already_seeded"
        else:
            insert_start = perf_counter()
            if reset:
                for model in (AuditLog, SecurityEvent, Incident, Device, User):
                    session.execute(delete(model))
            _insert_batches(session, dataset)
            session.add(
                AuditLog(
                    timestamp=datetime.now(UTC),
                    actor_user_id=None,
                    action="seed_synthetic_data",
                    resource_type="dataset",
                    resource_id="clockwork_badger_demo",
                    result="success",
                    details=json.dumps(
                        {
                            "seed": seed,
                            "normal_event_count": normal_event_count,
                            "event_count": len(dataset.events),
                        }
                    ),
                )
            )
            session.flush()
            insertion_seconds = perf_counter() - insert_start
    _export_ground_truth(dataset, ground_truth_path)
    return SeedResult(
        status=status,
        seed=seed,
        users=len(dataset.users),
        devices=len(dataset.devices),
        events=len(dataset.events),
        incidents=len(dataset.incidents),
        scenarios=len(dataset.scenarios),
        generation_seconds=generation_seconds,
        insertion_seconds=insertion_seconds,
        ground_truth_path=str(ground_truth_path),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=SYNTHETIC_NOTICE)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--normal-events", type=int, default=12_000)
    parser.add_argument(
        "--reset", action="store_true", help="Replace all data in the local demo database"
    )
    parser.add_argument("--ground-truth-path", type=Path, default=DEFAULT_TRUTH_PATH)
    args = parser.parse_args()
    engine = create_db_engine()
    try:
        try:
            result = seed_database(
                engine,
                seed=args.seed,
                normal_event_count=args.normal_events,
                reset=args.reset,
                ground_truth_path=args.ground_truth_path,
            )
        except OperationalError as exc:
            raise SystemExit(
                "PostgreSQL is unavailable. Start it with 'docker compose up -d postgres' "
                "and verify DATABASE_URL in the ignored .env file."
            ) from exc
    finally:
        engine.dispose()
    print(SYNTHETIC_NOTICE)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
