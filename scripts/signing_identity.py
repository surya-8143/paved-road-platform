"""Read the current job's Sigstore OIDC claims without logging its bearer token."""
import base64
import json
import os
import re
import urllib.request

url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=sigstore"
request = urllib.request.Request(url, headers={
    "Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]})
with urllib.request.urlopen(request, timeout=30) as response:
    token = json.load(response)["value"]
claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
workflow = claims.get("job_workflow_ref", "")
if not re.fullmatch(r"surya-8143/paved-road-platform/\.github/workflows/build-scan-sign\.yml@[0-9a-f]{40}", workflow):
    raise SystemExit("Signing requires a SHA-pinned platform reusable workflow")
if claims.get("repository") != os.environ["GITHUB_REPOSITORY"] or claims.get("ref") != "refs/heads/main":
    raise SystemExit("Unexpected signing context")
if claims.get("sha") != os.environ["GITHUB_SHA"] or claims.get("event_name") != "push":
    raise SystemExit("Signing requires the current main-branch push")
# Claims are received directly from GitHub's authenticated HTTPS endpoint, not user input.
with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as environment:
    environment.write("SIGNER_IDENTITY=https://github.com/" + workflow + "\n")
