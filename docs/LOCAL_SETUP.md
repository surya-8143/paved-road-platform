# Local development setup

Project source lives in D:\CLOUD. Inside Ubuntu this is /mnt/d/CLOUD.
Ubuntu's virtual disk and installer are stored separately under D:\CLOUD\.local, outside the three Git repositories.
Do not alter or restart unrelated Docker workloads.

## First launch: user-owned step

After Ubuntu-24.04 appears in `wsl --list --verbose`, open Windows Terminal or PowerShell and run:

```powershell
wsl -d Ubuntu-24.04
```

Complete Ubuntu's first-run prompts with a Linux username and a password you choose privately.
The password is for local Linux administration. Do not put it in the repository or send it in chat.
Password input may show no visible characters; this is normal.

If Windows asks for administrator approval or a reboot, report the actual message before proceeding with a restart.

## Docker integration

In Docker Desktop, open Settings > Resources > WSL Integration.
Enable integration for Ubuntu-24.04 if it is not already enabled.
Applying a Docker setting may restart the engine; preserve existing workloads and choose an appropriate time.

Inside Ubuntu, verify:

```bash
cd /mnt/d/CLOUD
python3 --version
docker version
```

Docker must report both a client and a Linux server. The application runtime target is Python 3.12.
The next automated setup step will install the development packages and project-specific tools, then record their versions.

## Filesystem considerations

The source remains on the D: drive as requested. Windows-mounted filesystems can be slower than native Linux storage for dependency installation and container builds.
Use LF line endings (enforced by .gitattributes). Do not reuse a Windows Python virtual environment from Linux.
Keep platform-specific virtual environments and build outputs ignored by Git.

## Verified so far

- Docker's official hello-world image downloaded and ran successfully on the Linux engine.
- Its temporary container was automatically removed; the small downloaded image remains cached.
- Git excludes .env, AWS credential folders, saved plans, Terraform state and local environments.
- README files are configured for LF line endings.

## Cloud access

Local setup does not require AWS credentials. The account's GitHub OIDC permission restriction remains unresolved.
Never activate Paid Plan or advanced account features as part of local setup.
