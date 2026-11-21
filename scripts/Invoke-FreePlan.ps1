[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('bootstrap-plan','bootstrap-apply','plan','apply','destroy-plan','destroy','status','smoke')]
    [string]$Action,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9]{12}$')][string]$AccountId,
    [ValidateSet('ap-southeast-2')][string]$Region = 'ap-southeast-2',
    [ValidateSet('demo','template')][string]$Service = 'demo',
    [string]$Profile = 'paved-road-personal',
    [string]$PlanSha256 = '',
    [string]$ReleaseDirectory = ''
)
$ErrorActionPreference = 'Stop'
$runner = (& wsl -d Ubuntu-24.04 --exec wslpath -a ($PSScriptRoot + '/deploy_free_plan.py')).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve runner in WSL' }
$arguments = @($runner, $Action, '--account-id', $AccountId, '--region', $Region, '--service', $Service)
if ($PlanSha256) { $arguments += @('--plan-sha256', $PlanSha256) }
if ($ReleaseDirectory) {
    $release = (& wsl -d Ubuntu-24.04 --exec wslpath -a $ReleaseDirectory).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve release directory' }
    $arguments += @('--release-directory', $release)
}
# The SDK/provider invokes a credential process and captures its output privately.
$awsCommand = (Get-Command aws -ErrorAction Stop).Source
$awsPath = (& wsl -d Ubuntu-24.04 --exec wslpath -a $awsCommand).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve Windows AWS CLI' }
$arguments += @('--credential-cli', $awsPath, '--profile', $Profile)
& wsl -d Ubuntu-24.04 --exec bash -lc 'exec "$HOME/.cache/paved-road/cloud-tools/bin/python" "$@"' paved-road @arguments
if ($LASTEXITCODE -ne 0) { throw "Free Plan command failed with exit code $LASTEXITCODE" }
