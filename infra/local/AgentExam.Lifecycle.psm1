#requires -Version 7.4

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Local.psm1') -Force

function Assert-AgentExamCompleteDeployment {
    param([Parameter(Mandatory)][object]$Config)
    $deployment = Read-AgentExamState $Config
    if ($null -eq $deployment -or $deployment.phase -ne 'complete') {
        throw 'Deployment initialization is not complete; refusing ordinary startup.'
    }
    foreach ($path in @(
            $Config.PostgresRoot, $Config.MinioRoot, $Config.ControlRoot,
            $Config.PostgresPassword, $Config.MinioPassword,
            $Config.MinioAppPassword, $Config.LicenseFile
        )) {
        Assert-AgentExamPlainPath $path
        Assert-AgentExamPrivateAcl $path
    }
}

function Get-AgentExamServiceState {
    param(
        [Parameter(Mandatory)][object]$Config,
        [Parameter(Mandatory)][ValidateSet('postgres', 'minio')][string]$Service
    )
    $id = (Invoke-AgentExamCompose $Config @('ps', '-q', $Service)).Trim()
    if (-not $id) { return 'stopped' }
    if ($id -notmatch '^[0-9a-f]{64}$') {
        throw "Unexpected $Service container identity."
    }
    $state = (Invoke-AgentExamDocker @(
            'inspect', $id, '--format', '{{.State.Status}}'
        )).Trim()
    if ($state -notin @(
            'created', 'running', 'paused', 'restarting',
            'removing', 'exited', 'dead'
        )) {
        throw "Unexpected $Service container state."
    }
    return $state
}

function Get-AgentExamActiveJobCount {
    param([Parameter(Mandatory)][object]$Config)
    $id = (Invoke-AgentExamCompose $Config @('ps', '-q', 'postgres')).Trim()
    if ($id -notmatch '^[0-9a-f]{64}$') {
        throw 'Unexpected PostgreSQL container identity.'
    }
    $query = "SELECT count(*) FROM evaluation_jobs WHERE status IN " +
        "('PREPARING','EXECUTING','CANCEL_REQUESTED','FINALIZING')"
    $count = (Invoke-AgentExamDocker @(
            'exec', $id, 'psql', '-U', 'agentexam_admin', '-d', 'agentexam',
            '-Atc', $query
        )).Trim()
    if ($count -notmatch '^\d+$') { throw 'Unexpected active Job count.' }
    return [int]$count
}

function Request-AgentExamWorkerStop {
    param([Parameter(Mandatory)][object]$Config)
    Assert-AgentExamPlainPath $Config.ControlRoot
    Assert-AgentExamPrivateAcl $Config.ControlRoot
    if (Test-Path -LiteralPath $Config.WorkerStopFile) {
        Assert-AgentExamPlainPath $Config.WorkerStopFile
        Assert-AgentExamPrivateAcl $Config.WorkerStopFile
        return
    }
    $temporary = $Config.WorkerStopFile + '.tmp-' + [guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllText($temporary, "stop`n", [Text.UTF8Encoding]::new($false))
    Set-AgentExamPrivateAcl -Path $temporary
    Move-Item -LiteralPath $temporary -Destination $Config.WorkerStopFile
}

function Clear-AgentExamWorkerStop {
    param([Parameter(Mandatory)][object]$Config)
    if (Test-Path -LiteralPath $Config.WorkerStopFile) {
        Assert-AgentExamPlainPath $Config.WorkerStopFile
        Assert-AgentExamPrivateAcl $Config.WorkerStopFile
        $postgres = Get-AgentExamServiceState $Config 'postgres'
        $minio = Get-AgentExamServiceState $Config 'minio'
        if ($postgres -eq 'running' -or $minio -eq 'running') {
            throw 'Services are still running under a stop request; inspect status first.'
        }
        Remove-Item -LiteralPath $Config.WorkerStopFile
    }
}

function Wait-AgentExamJobsDrained {
    param(
        [Parameter(Mandatory)][object]$Config,
        [ValidateRange(1, 3600)][int]$TimeoutSeconds = 300
    )
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $emptyChecks = 0
    while ([DateTime]::UtcNow -lt $deadline) {
        if ((Get-AgentExamActiveJobCount $Config) -eq 0) { $emptyChecks++ }
        else { $emptyChecks = 0 }
        if ($emptyChecks -eq 3) { return }
        Start-Sleep -Milliseconds 500
    }
    throw 'Active Jobs did not finish before the stop timeout; services remain running.'
}

function Get-AgentExamLifecycleStatus {
    param([Parameter(Mandatory)][object]$Config)
    $deployment = Read-AgentExamState $Config
    $phase = if ($null -eq $deployment) { 'uninitialized' } else { $deployment.phase }
    $postgres = Get-AgentExamServiceState $Config 'postgres'
    $activeJobs = if ($postgres -eq 'running') {
        Get-AgentExamActiveJobCount $Config
    }
    else { $null }
    return [ordered]@{
        project = $Config.Project
        initializationState = $phase
        services = [ordered]@{
            postgres = $postgres
            minio = Get-AgentExamServiceState $Config 'minio'
        }
        worker = [ordered]@{
            activeJobs = $activeJobs
            stopRequested = Test-Path -LiteralPath $Config.WorkerStopFile
        }
    }
}

Export-ModuleMember -Function *-AgentExam*
