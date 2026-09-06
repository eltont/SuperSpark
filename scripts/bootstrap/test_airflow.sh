#!/usr/bin/env bash
# Install (if needed) and run SuperSpark Airflow adaptor tests.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
AIRFLOW_DIR="$ROOT/integrations/airflow"
VENV="${SUPERSPARK_AIRFLOW_VENV:-$ROOT/artifacts/venv-airflow}"
LOG_DIR="$ROOT/artifacts/logs"
AIRFLOW_VERSION="${SUPERSPARK_AIRFLOW_VERSION:-2.10.5}"
CONSTRAINT_URL="${SUPERSPARK_AIRFLOW_CONSTRAINTS:-https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.12.txt}"
mkdir -p "$LOG_DIR" "$(dirname "$VENV")"

install_venv() {
  rm -rf "$VENV"
  python3 -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -U pip wheel
  pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "$CONSTRAINT_URL"
  pip install "apache-airflow-providers-apache-spark>=4.0.0,<6.0.0" --constraint "$CONSTRAINT_URL"
  pip install "pytest>=7.0" "pytest-mock>=3.10"
  # Install adaptor without resolving airflow again (already pinned above).
  pip install --no-deps -e "$AIRFLOW_DIR"
}

if [[ "${SUPERSPARK_AIRFLOW_REBUILD:-0}" == "1" || ! -x "$VENV/bin/python" ]]; then
  install_venv
else
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install --no-deps -e "$AIRFLOW_DIR" -q
fi

export AIRFLOW_HOME="${AIRFLOW_HOME:-$ROOT/artifacts/airflow-home}"
mkdir -p "$AIRFLOW_HOME"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-sqlite:///$AIRFLOW_HOME/airflow.db}"
# Avoid interactive airflow db init prompts on first import where possible
airflow db migrate >/dev/null 2>&1 || airflow db init >/dev/null 2>&1 || true

cd "$AIRFLOW_DIR"
# Prevent local directory name "airflow" from shadowing the installed package via cwd.
export PYTHONPATH="$AIRFLOW_DIR${PYTHONPATH:+:$PYTHONPATH}"
python -c "import airflow; assert getattr(airflow, '__version__', None), airflow"
python -m pytest -q "$@" 2>&1 | tee "$LOG_DIR/test-airflow.log"
echo "Logs: $LOG_DIR/test-airflow.log"
