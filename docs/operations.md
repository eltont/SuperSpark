# Operations

## Bootstrap

`make bootstrap` is idempotent: healthy Colima/k3d resources are reused.

## Teardown

`make local-down` deletes the `k3d-superspark` cluster only. Reports and data under `artifacts/` are preserved by default.

## Rollback

- Application: submit with `MODE=baseline` (no Gluten plugin).
- Cluster: `make local-down` then `make local-up`.
- Versions: restore prior `versions.lock.yaml` from git.

## Remote deploy safety

`make deploy-k8s` refuses `REPLACE_ME` configs and requires `SUPERSPARK_ALLOW_REMOTE_DEPLOY=1`.
