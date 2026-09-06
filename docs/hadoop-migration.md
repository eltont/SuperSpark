# Hadoop / YARN migration

1. Run `deploy/yarn/inventory.sh` on an edge node; fill `configs/yarn.example.yaml`.
2. `make package-yarn CONFIG=configs/yarn.example.yaml` produces an archive with jars + wrappers.
3. Distribute via YARN localized resources / HDFS; do not replace cluster Spark defaults.
4. Pilot one job to a new output path using `submit-native.sh`; keep `submit-baseline.sh` for rollback.
5. Validate Hadoop client, HDFS connector, delegation tokens, and memory limits on the real cluster.

Live pilot status: **NOT RUN** until authorized cluster access and completed inventory.
