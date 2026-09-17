#requires -Version 7.4

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Local.psm1') -Force

function Wait-AgentExamPostgres {
    param([Parameter(Mandatory)][object]$Config)
    $id = (Invoke-AgentExamCompose $Config @('ps', '-q', 'postgres')).Trim()
    if ($id -notmatch '^[0-9a-f]{64}$') { throw 'Unexpected PostgreSQL container identity.' }
    $consecutive = 0
    $arguments = @(
        'exec', $id, 'psql', '-U', 'agentexam_admin', '-d', 'agentexam',
        '-Atc', 'SELECT 1'
    )
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        $output = @(& docker @arguments 2>&1)
        if ($LASTEXITCODE -eq 0 -and ($output -join '').Trim() -eq '1') {
            $consecutive++
            if ($consecutive -eq 3) { return $id }
        }
        else { $consecutive = 0 }
        Start-Sleep -Milliseconds 500
    }
    throw 'PostgreSQL target database did not become stably ready.'
}

function Open-AgentExamMinioAdmin {
    param(
        [Parameter(Mandatory)][object]$Config,
        [Parameter(Mandatory)][string]$ContainerId,
        [Parameter(Mandatory)][string]$Directory
    )
    $password = [IO.File]::ReadAllText($Config.MinioPassword)
    $inputText = $Config.MinioRootUser + "`n" + $password + "`n"
    $arguments = @(
        'exec', '-i', $ContainerId, '/usr/bin/mc', '--config-dir', $Directory,
        '--no-color', 'alias', 'set', 'local', 'http://127.0.0.1:9000'
    )
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $output = @($inputText | & docker @arguments 2>&1)
        if ($LASTEXITCODE -eq 0) { return }
        Start-Sleep -Milliseconds 500
    }
    throw 'AIStor did not become ready or rejected its license/credentials.'
}

function Get-AgentExamDatabaseState {
    param([Parameter(Mandatory)][object]$Config)
    $id = (Invoke-AgentExamCompose $Config @('ps', '-q', 'postgres')).Trim()
    if ($id -notmatch '^[0-9a-f]{64}$') { throw 'Unexpected PostgreSQL container identity.' }
    $query = "SELECT string_agg(tablename, ',' ORDER BY tablename) " +
        "FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
    $tables = (Invoke-AgentExamDocker @(
            'exec', $id, 'psql', '-U', 'agentexam_admin', '-d', 'agentexam',
            '-Atc', $query
        )).Trim()
    if (-not $tables) { return 'empty' }
    $expected = 'accounts,agent_configurations,artifact_records,' +
        'deterministic_results,evaluation_jobs,evaluation_runs,evaluation_tasks,' +
        'invitations,job_state_events,run_state_events,sessions'
    if ($tables -ne $expected) { return 'unknown' }
    $counts = @(
        'accounts', 'agent_configurations', 'artifact_records',
        'deterministic_results', 'evaluation_jobs', 'evaluation_runs',
        'evaluation_tasks', 'invitations', 'job_state_events',
        'run_state_events', 'sessions'
    ) | ForEach-Object { "(SELECT count(*) FROM $_)" }
    $rows = Invoke-AgentExamDocker @(
        'exec', $id, 'psql', '-U', 'agentexam_admin', '-d', 'agentexam',
        '-Atc', ('SELECT ' + ($counts -join ' + '))
    )
    if ($rows.Trim() -eq '0') { return 'schema-empty' }
    return 'schema-used'
}

function Initialize-AgentExamDatabase {
    param([Parameter(Mandatory)][object]$Config)
    $python = Join-Path $Config.RepositoryRoot 'apps\backend\.venv\Scripts\python.exe'
    Assert-AgentExamPlainPath $python
    $password = [Uri]::EscapeDataString(
        [IO.File]::ReadAllText($Config.PostgresPassword)
    )
    $saved = [Environment]::GetEnvironmentVariable('AGENTEXAM_DATABASE_URL', 'Process')
    $pushed = $false
    try {
        $dsn = "postgresql://agentexam_admin:$password@127.0.0.1:55432/agentexam"
        [Environment]::SetEnvironmentVariable('AGENTEXAM_DATABASE_URL', $dsn, 'Process')
        Push-Location (Join-Path $Config.RepositoryRoot 'apps\backend')
        $pushed = $true
        $output = @(& $python -B -m eval_platform.delivery.owner init-db 2>&1)
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL schema initialization failed.' }
    }
    finally {
        if ($pushed) { Pop-Location }
        [Environment]::SetEnvironmentVariable(
            'AGENTEXAM_DATABASE_URL', $saved, 'Process'
        )
    }
}

function Initialize-AgentExamMinio {
    param([Parameter(Mandatory)][object]$Config)
    $id = (Invoke-AgentExamCompose $Config @('ps', '-q', 'minio')).Trim()
    if ($id -notmatch '^[0-9a-f]{64}$') { throw 'Unexpected AIStor container identity.' }
    $mcRoot = '/tmp/agentexam-init-' + [guid]::NewGuid().ToString('N')
    try {
        Open-AgentExamMinioAdmin $Config $id $mcRoot
        $null = Invoke-AgentExamDocker @(
            'exec', $id, '/usr/bin/mc', '--config-dir', $mcRoot,
            '--no-color', 'mb', "local/$($Config.Bucket)"
        )
        $target = "${id}:$mcRoot/policy.json"
        $null = Invoke-AgentExamDocker @('cp', $Config.PolicyFile, $target)
        $null = Invoke-AgentExamDocker @(
            'exec', $id, '/usr/bin/mc', '--config-dir', $mcRoot,
            '--no-color', 'admin', 'policy', 'create', 'local',
            'agentexam-app', "$mcRoot/policy.json"
        )
        $password = [IO.File]::ReadAllText($Config.MinioAppPassword)
        $credentials = $Config.MinioAppUser + "`n" + $password + "`n"
        $null = Invoke-AgentExamDocker -Arguments @(
            'exec', '-i', $id, '/usr/bin/mc', '--config-dir', $mcRoot,
            '--no-color', 'admin', 'user', 'add', 'local'
        ) -InputText $credentials
        $null = Invoke-AgentExamDocker @(
            'exec', $id, '/usr/bin/mc', '--config-dir', $mcRoot,
            '--no-color', 'admin', 'policy', 'attach', 'local',
            'agentexam-app', '--user', $Config.MinioAppUser
        )
    }
    finally {
        if ($id -match '^[0-9a-f]{64}$') {
            $null = @(& docker exec $id rm -r -- $mcRoot 2>&1)
        }
    }
}

Export-ModuleMember -Function *-AgentExam*
