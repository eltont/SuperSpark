#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
export KUBECONFIG="${ROOT}/artifacts/kubeconfig-superspark.yaml"
CLUSTER=superspark
NS=superspark

mkdir -p "$ROOT/artifacts"

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon not ready; start Colima first" >&2
  exit 1
fi

if k3d cluster list 2>/dev/null | grep -q "^${CLUSTER}"; then
  echo "[local-up] cluster $CLUSTER already exists; reusing"
else
  k3d cluster create "$CLUSTER" \
    --agents 0 \
    --servers 1 \
    --api-port 6550 \
    --port "18080:80@loadbalancer" \
    --k3s-arg "--disable=traefik@server:0" \
    --kubeconfig-update-default=false \
    --kubeconfig-switch-context=false
fi

k3d kubeconfig get "$CLUSTER" >"$KUBECONFIG"
kubectl --kubeconfig "$KUBECONFIG" config use-context "k3d-${CLUSTER}" >/dev/null

# Import images
k3d image import superspark/spark-baseline:3.5.5 -c "$CLUSTER" || true
k3d image import superspark/spark-native:3.5.5-gluten1.6.0 -c "$CLUSTER" || true

kubectl --kubeconfig "$KUBECONFIG" create namespace "$NS" --dry-run=client -o yaml | kubectl --kubeconfig "$KUBECONFIG" apply -f -
kubectl --kubeconfig "$KUBECONFIG" -n "$NS" apply -f "$ROOT/deploy/k3d/rbac.yaml"
kubectl --kubeconfig "$KUBECONFIG" -n "$NS" apply -f "$ROOT/deploy/k3d/minio.yaml" || true
kubectl --kubeconfig "$KUBECONFIG" -n "$NS" apply -f "$ROOT/deploy/k3d/pvc.yaml"

# Wait for nodes
kubectl --kubeconfig "$KUBECONFIG" wait --for=condition=Ready nodes --all --timeout=180s
echo "[local-up] ready; KUBECONFIG=$KUBECONFIG"
