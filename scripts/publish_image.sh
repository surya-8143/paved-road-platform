#!/usr/bin/env bash
set -euo pipefail
: "${ARCH:?}" "${IMAGE_NAME:?}" "${SIGNER_IDENTITY:?}" "${GITHUB_SHA:?}"
cd "artifacts/image-$ARCH"
sha256sum --check image.tar.sha256
docker load --input image.tar
expected=$(cat image.id)
actual=$(docker image inspect --format '{{.Id}}' "paved-road-ci:$ARCH")
test "$actual" = "$expected"
test "$(docker image inspect --format '{{.Architecture}}' "paved-road-ci:$ARCH")" = "$ARCH"
tag="$IMAGE_NAME:sha-$GITHUB_SHA-$ARCH"
docker tag "$expected" "$tag"
docker push "$tag"
digest=$(docker buildx imagetools inspect "$tag" --format '{{.Manifest.Digest}}')
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]
ref="$IMAGE_NAME@$digest"
cosign sign --yes "$ref"
cosign attest --yes --type cyclonedx --predicate sbom.cdx.json "$ref"
verify=(--certificate-identity "$SIGNER_IDENTITY" --certificate-oidc-issuer https://token.actions.githubusercontent.com --certificate-github-workflow-repository "$GITHUB_REPOSITORY" --certificate-github-workflow-sha "$GITHUB_SHA")
cosign verify "${verify[@]}" "$ref" > signature-verification.json
cosign verify-attestation "${verify[@]}" --type cyclonedx "$ref" > sbom-verification.json
jq -n --arg architecture "$ARCH" --arg image "$ref" --arg config "$expected" --arg identity "$SIGNER_IDENTITY" --arg commit "$GITHUB_SHA" '{architecture:$architecture,image:$image,config:$config,identity:$identity,commit:$commit}' > release.json
rm image.tar
