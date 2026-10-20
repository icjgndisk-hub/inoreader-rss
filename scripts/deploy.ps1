# Optional: Git and GitHub CLI must already be installed from their official sources.
# Run in PowerShell: .\scripts\deploy.ps1
param([string]$RepositoryName = 'inoreader-rss')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required: https://git-scm.com/downloads' }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI is required: https://cli.github.com/' }
if ($RepositoryName -notmatch '^[a-zA-Z0-9_.-]+$') { throw 'Invalid repository name.' }
Write-Host 'This creates a PUBLIC repository containing code, headline/date/article URL/image URL history and reports.'
if ((Read-Host 'Type PUBLIC to continue') -cne 'PUBLIC') { throw 'Cancelled.' }
gh auth status
if ($LASTEXITCODE -ne 0) {
    gh auth login --web --git-protocol https
    if ($LASTEXITCODE -ne 0) { throw 'Authentication was not completed.' }
}
$Owner = gh api user --jq .login
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine GitHub account.' }
if (Test-Path .git) { throw 'Existing git checkout detected. Deploy manually to avoid changing its remote.' }
git init -b main
if ($LASTEXITCODE -ne 0) { throw 'git init failed.' }
git config user.name $Owner
git config user.email "$Owner@users.noreply.github.com"
git add .
git commit -m 'Initial tested image RSS kit'
if ($LASTEXITCODE -ne 0) { throw 'Commit failed.' }
gh repo create "$Owner/$RepositoryName" --public --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw 'Repository creation/push failed; do not overwrite an existing repository.' }
gh api --method POST "repos/$Owner/$RepositoryName/pages" -f build_type=workflow
if ($LASTEXITCODE -ne 0) { throw 'Set Settings > Pages > Source to GitHub Actions, then run the workflow.' }
gh workflow run update.yml --repo "$Owner/$RepositoryName"
if ($LASTEXITCODE -ne 0) { throw 'Run Update image RSS from the Actions tab.' }
Write-Host 'Deployment requested. Check the Actions result; a requested run is not yet proof of publication.'
gh repo view "$Owner/$RepositoryName" --web
