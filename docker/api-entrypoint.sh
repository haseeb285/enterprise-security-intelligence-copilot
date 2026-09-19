#!/bin/sh
set -eu
python -m app.db.wait
exec "$@"
