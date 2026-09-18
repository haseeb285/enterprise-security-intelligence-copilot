# Synthetic security data methodology

**SYNTHETIC DEMONSTRATION DATA — NOT REAL SECURITY TELEMETRY**

The organization is **Clockwork Badger Cooperative**, an obviously fictional workplace. The generator creates 120 fictional `Demo Person` accounts across five generic departments, 140 managed demo devices, and 12,000 baseline events by default. Eight users have the privileged flag. No real email addresses or infrastructure are used. Event IPs use the documentation networks `192.0.2.0/24`, `198.51.100.0/24`, and `203.0.113.0/24`.

## Baseline behavior

`app/db/synthetic.py` uses a local `random.Random(seed)` and a fixed August 2026 UTC window. A user's home country and primary device remain stable; a minority have a second managed tablet. Most events fall during weekday working hours. The event mixture is mostly successful authentication, with occasional denied authentication, endpoint health signals, and routine firewall allows. Authentication counts/methods are null for non-authentication event types. All baseline events are low severity and unlinked to incidents.

## Injected evaluation cases

Six fixed pattern shapes are added after the baseline window. The configurable seed affects baseline sampling; scenario shape, affected account, source, and time are fixed for reproducible evaluation. These are **illustrative patterns**, not validated simulations of real attacks.

| Type | Account | Observable pattern | Events |
| --- | --- | --- | ---: |
| Brute-force pattern | U104 | 25 denied authentications from one unfamiliar source in eight minutes | 25 |
| Impossible-travel pattern | U105 | successful DE and JP sign-ins 15 minutes apart | 2 |
| Privileged-account anomaly | U003 | 02:05 login and privilege changes from unfamiliar source/device | 3 |
| Account-compromise pattern | U106 | 12 denials followed by success from new source/geography | 13 |
| Suspicious endpoint behavior | U107 | four elevated process signals on one device | 4 |
| Firewall burst | none | 18 blocked inbound connections from one source | 18 |

Each sequence has a simple open incident. Ground truth (`scenario_id`, type, affected user, start/end, related event IDs, expected investigation reason) is written separately to ignored `data/runtime/ground_truth.json`. It is for future evaluation only. Event rows contain no ground-truth flag. `incident_id` is excluded from future ML features because it would leak investigation grouping.

## Reproduce locally

Create an ignored `.env` from `.env.example`, set local PostgreSQL credentials, host port and matching `DATABASE_URL`, then run:

```bash
docker compose up -d postgres
docker compose ps
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed
```

The default seed is `42`, with 12,000 baseline events and 65 scenario events. Repeating the command with matching settings reports `already_seeded` and does not duplicate rows. To intentionally replace this dedicated demo dataset, use `python -m app.db.seed --seed 43 --reset`; the command refuses to modify a populated database without its synthetic seed marker or one whose recorded counts have changed. Do not point it at any non-demo database. `--normal-events` can reduce count for development tests; `--ground-truth-path` changes the local evaluation artifact location. The default artifact is Git-ignored.

All generated timestamps, IPs, names, and scenario outcomes are synthetic. Isolation Forest training and detection performance have not been implemented or measured in Phase 2.
