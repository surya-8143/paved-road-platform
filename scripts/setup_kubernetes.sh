#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export KUBECONFIG="$HOME/.kube/paved-road.yaml"
export PATH="$HOME/.local/bin:$PATH"
# This configuration is separate from the user's default kubeconfig.
mkdir -p "$HOME/.kube"
k=(kubectl --context kind-paved-road)
node_image='kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0'
if ! kind get clusters | grep -qx paved-road; then
  kind create cluster --name paved-road --config kubernetes/kind.yaml --image "$node_image" --wait 180s
else
  kind export kubeconfig --name paved-road --kubeconfig "$KUBECONFIG"
fi
"${k[@]}" get node paved-road-control-plane >/dev/null
python3 scripts/fetch_kubernetes_assets.py
python3 scripts/prepare_kubernetes.py
helm upgrade --install kyverno build/kubernetes/kyverno-3.10.0.tgz \
  --kube-context kind-paved-road --namespace kyverno --create-namespace \
  --values build/kubernetes/kyverno-pinned-values.yaml --wait --timeout 15m
"${k[@]}" create namespace argocd --dry-run=client -o yaml | "${k[@]}" apply -f -
"${k[@]}" apply --server-side --field-manager paved-road-bootstrap -n argocd -f build/kubernetes/argocd-pinned.yaml
"${k[@]}" rollout status deployment/argocd-server -n argocd --timeout=600s
"${k[@]}" rollout status deployment/argocd-repo-server -n argocd --timeout=600s
"${k[@]}" rollout status statefulset/argocd-application-controller -n argocd --timeout=600s
"${k[@]}" apply -f kubernetes/admission-availability.yaml
"${k[@]}" apply -f kubernetes/namespace.yaml
"${k[@]}" apply -f kubernetes/policies/
"${k[@]}" wait --for=jsonpath='{.status.conditionStatus.ready}'=true validatingpolicy/paved-road-runtime --timeout=180s
"${k[@]}" wait --for=jsonpath='{.status.conditionStatus.ready}'=true imagevalidatingpolicy/paved-road-trusted-builds --timeout=180s
"${k[@]}" apply -f kubernetes/argocd-app.yaml
"${k[@]}" wait -n argocd --for=jsonpath='{.status.sync.status}'=Synced application/paved-road-demo --timeout=600s
"${k[@]}" wait -n argocd --for=jsonpath='{.status.health.status}'=Healthy application/paved-road-demo --timeout=600s
"${k[@]}" rollout status deployment/demo -n paved-road-demo --timeout=180s
printf 'Paved Road cluster and GitOps service are ready.\n'
