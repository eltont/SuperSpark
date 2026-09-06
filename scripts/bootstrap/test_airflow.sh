#!/usr/bin/env bash
# Install (if needed) and run SuperSpark Airflow adaptor tests.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
AIRFLOW_DIR="$ROOT/integrations/airflow"
VENV="${SUPERSPARK_AIRFLOW_VENV:-$ROOT/artifacts/venv-airflow}"
LOG_DIR="$ROOT/artifacts/logs"
mkdir -p "$LOG_DIR" "$(dirname "$VENV")"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -U pip wheel
  # Slim Airflow for unit/DagBag tests (no celery/postgres extras).
  CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt"
  pip install "apache-airflow==2.10.5" --constraint "$CONSTRAINT_URL"
  pip install "apache-airflow-providers-apache-spark>=4.0.0"
  pip install -e "$AIRFLOW_DIR[dev]"
else
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -e "$AIRFLOW_DIR[dev]" -q
fi

export AIRFLOW_HOME="${AIRFLOW_HOME:-$ROOT/artifacts/airflow-home}"
mkdir -p "$AIRFLOW_HOME"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-sqlite:///$AIRFLOW_HOME/airflow.db}"
# Avoid interactive airflow db init prompts on first import where possible
airflow db migrate >/dev/null 2>&1 || airflow db init >/dev/null 2>&1 || true

cd "$AIRFLOW_DIR"
python -m pytest -q "$@" 2>&1 | tee "$LOG_DIR/test-airflow.log"
echo "Logs: $LOG_DIR/test-airflow.log"
