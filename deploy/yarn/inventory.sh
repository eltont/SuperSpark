#!/usr/bin/env bash
set -euo pipefail
# Collect Hadoop/YARN inventory facts required for M6.
OUT="${1:-../../artifacts/reports/yarn-inventory.json}"
mkdir -p "$(dirname "$OUT")"
python3 - <<PY
import json, os, shutil, subprocess
from pathlib import Path
out = Path("$OUT")
def which(x):
    return shutil.which(x)
facts = {
  "hadoop_version": None,
  "spark_version_on_cluster": None,
  "java_version": None,
  "worker_os": None,
  "cpu": None,
  "kerberos": None,
  "metastore": None,
  "scheduler_policies": None,
  "tools": {k: which(k) for k in ["hadoop", "yarn", "hdfs", "spark-submit", "java"]},
  "required_fields_missing": ["hadoop_version","spark_version_on_cluster","java_version","worker_os","cpu","kerberos"],
  "status": "INCOMPLETE — fill before live pilot",
}
try:
    facts["java_version"] = subprocess.check_output(["java","-version"], stderr=subprocess.STDOUT, text=True).splitlines()[0]
    facts["required_fields_missing"] = [f for f in facts["required_fields_missing"] if not facts.get(f)]
except Exception:
    pass
out.write_text(json.dumps(facts, indent=2)+"\n")
print(out.read_text())
PY
