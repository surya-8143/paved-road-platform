#!/usr/bin/env bash
set -euo pipefail
: "${IMAGE_NAME:?}" "${GITHUB_SHA:?}" "${SIGNER_IDENTITY:?}"
amd64=$(jq -er '.image' artifacts/released-amd64/release.json)
arm64=$(jq -er '.image' artifacts/released-arm64/release.json)
[[ "$amd64" == "$IMAGE_NAME@sha256:"* && "$arm64" == "$IMAGE_NAME@sha256:"* ]]
verify=(--certificate-identity "$SIGNER_IDENTITY" --certificate-oidc-issuer https://token.actions.githubusercontent.com --certificate-github-workflow-repository "$GITHUB_REPOSITORY" --certificate-github-workflow-sha "$GITHUB_SHA")
for ref in "$amd64" "$arm64"; do cosign verify "${verify[@]}" "$ref" >/dev/null; done
tag="$IMAGE_NAME:sha-$GITHUB_SHA"
docker buildx imagetools create --tag "$tag" "$amd64" "$arm64"
digest=$(docker buildx imagetools inspect "$tag" --format '{{.Manifest.Digest}}')
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]
ref="$IMAGE_NAME@$digest"
cosign sign --yes "$ref"
cosign verify "${verify[@]}" "$ref" > artifacts/index-verification.json
cd artifacts/lambda
sha256sum --check lambda.sha256
cosign sign-blob --yes --bundle lambda.sigstore.json lambda.zip
cosign verify-blob "${verify[@]}" --bundle lambda.sigstore.json lambda.zip
cd ../..
jq -n --arg image "$ref" --arg sha "$GITHUB_SHA" --arg identity "$SIGNER_IDENTITY" --arg run "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" --arg lambda_sha "$(cut -d ' ' -f 1 artifacts/lambda/lambda.sha256)" --arg lambda_sbom_sha "$(sha256sum artifacts/lambda/sbom.cdx.json | cut -d ' ' -f 1)" --slurpfile amd64 artifacts/released-amd64/release.json --slurpfile arm64 artifacts/released-arm64/release.json '{schema:1,commit:$sha,image:$image,signer:$identity,run:$run,lambda_sha256:$lambda_sha,lambda_sbom_sha256:$lambda_sbom_sha,architectures:[$amd64[0],$arm64[0]]}' > artifacts/release.json
cosign sign-blob --yes --bundle artifacts/release.sigstore.json artifacts/release.json
cosign verify-blob "${verify[@]}" --bundle artifacts/release.sigstore.json artifacts/release.json
cat artifacts/release.json >> "$GITHUB_STEP_SUMMARY"
