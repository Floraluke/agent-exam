# Dedicated synthetic PG acceptance. No published ports, mounts or global settings.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$scope = 'jobs-' + [guid]::NewGuid().ToString('N')
$names = @("$scope-postgres", "$scope-tests")
$saved = @{}
$testExit = 1

function Invoke-Docker {
    param([string[]]$Arguments)
    $output = @(& docker @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "Docker operation failed: $($Arguments[0])" }
    return ($output -join [Environment]::NewLine).Trim()
}
function New-TestContainer {
    param([string]$Name, [string[]]$Arguments)
    $id = @(Invoke-Docker -Arguments (@('create', '--name', $Name, '--label',
        "agentexam.jobs-test=$scope") + $Arguments))[0]
    if ($id -notmatch '^[0-9a-f]{64}$') { throw 'Unexpected container identity' }
    return $id
}
function Check-Isolation {
    param([string]$Id, [string]$Network)
    $raw = @(Invoke-Docker -Arguments @('inspect', $Id))[0]
    $item = ($raw | ConvertFrom-Json)[0]
    if ($item.HostConfig.NetworkMode -ne $Network -or
        @($item.HostConfig.PortBindings.PSObject.Properties).Count -ne 0 -or
        @($item.Mounts | Where-Object { $_.Type -ne 'tmpfs' }).Count -ne 0 -or
        $item.HostConfig.Privileged -or -not $item.HostConfig.ReadonlyRootfs -or
        $item.HostConfig.Memory -le 0 -or $item.HostConfig.PidsLimit -le 0) {
        throw 'Test container isolation does not match the approved scope'
    }
    Write-Output "$($item.Name): network=$Network; no published ports or host mounts"
}
try {
    $base = @(Invoke-Docker -Arguments @('image', 'inspect',
        'agentexam-catalog-tests:20260912', '--format', '{{.Id}}'))[0]
    if ($base -ne 'sha256:2162edefcc51562f3a2ad3c405699f4e4b107efae8b6a92b7c38fc7e6e69cd24') {
        throw 'Unverified task-03 test runtime identity'
    }
    $postgres = 'sha256:5cce759a2777634ff1edd0d56b9241a2961deb7f72e125d4af6ae2928163a6b6'
    Invoke-Docker -Arguments @('image', 'inspect', $postgres, '--format', '{{.Id}}')
    $root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
    & docker build --network=none --tag agentexam-jobs-tests:20260912 `
        --file (Join-Path $PSScriptRoot 'Dockerfile.tests') $root
    if ($LASTEXITCODE -ne 0) { throw 'Local jobs test image build failed' }
    $driverImage = @(Invoke-Docker -Arguments @('image', 'inspect',
        'agentexam-jobs-tests:20260912', '--format', '{{.Id}}'))[0]
    Write-Output "Test driver: $driverImage; PostgreSQL: $postgres"
    $password = [Convert]::ToHexString(
        [Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    $environment = @{
        POSTGRES_USER = 'agentexam_identity_test'
        POSTGRES_DB = 'agentexam_identity_test'
        POSTGRES_PASSWORD = $password
        AGENTEXAM_TEST_DATABASE_URL = "host=127.0.0.1 port=55432 dbname=agentexam_identity_test user=agentexam_identity_test password=$password"
    }
    foreach ($key in $environment.Keys) {
        $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $environment[$key], 'Process')
    }
    $limits = @('--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
        '--memory=512m', '--cpus=1', '--pids-limit=128',
        '--env=HTTP_PROXY=', '--env=HTTPS_PROXY=', '--env=ALL_PROXY=',
        '--env=http_proxy=', '--env=https_proxy=', '--env=all_proxy=')
    $pg = New-TestContainer $names[0] ($limits + @('--network=none', '--user=70:70',
        '--tmpfs=/var/lib/postgresql/data:rw,nosuid,noexec,size=256m,uid=70,gid=70',
        '--tmpfs=/var/run/postgresql:rw,nosuid,noexec,size=16m,uid=70,gid=70',
        '--tmpfs=/tmp:rw,nosuid,noexec,size=32m,uid=70,gid=70',
        '--env=POSTGRES_USER', '--env=POSTGRES_DB', '--env=POSTGRES_PASSWORD',
        $postgres, 'postgres', '-p', '55432', '-c', 'listen_addresses=127.0.0.1',
        '-c', 'max_connections=20'))
    Check-Isolation $pg 'none'
    Invoke-Docker -Arguments @('start', $pg)
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        & docker exec $pg pg_isready -h 127.0.0.1 -p 55432 -U agentexam_identity_test *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Dedicated PostgreSQL did not become ready' }
    $network = "container:$pg"
    $driverArgs = $limits + @("--network=$network",
        '--tmpfs=/tmp:rw,nosuid,size=256m,uid=65534,gid=65534',
        '--env=AGENTEXAM_RUN_IDENTITY_POSTGRES=1',
        '--env=AGENTEXAM_TEST_DATABASE_URL', $driverImage, 'tests/jobs')
    $driver = New-TestContainer $names[1] $driverArgs
    Check-Isolation $driver $network
    & docker start --attach $driver
    $testExit = $LASTEXITCODE
    $actualExit = @(Invoke-Docker -Arguments @('inspect', $driver, '--format',
        '{{.State.ExitCode}}'))[0]
    if ($actualExit -ne '0') { $testExit = 1 }
}
finally {
    foreach ($name in @($names[1], $names[0])) {
        $raw = @(& docker inspect $name 2>$null)
        if ($LASTEXITCODE -eq 0) {
            $item = (($raw -join [Environment]::NewLine) | ConvertFrom-Json)[0]
            if ($item.Id -notmatch '^[0-9a-f]{64}$' -or
                $item.Config.Labels.'agentexam.jobs-test' -ne $scope) {
                throw 'Refusing cleanup of an unrelated container'
            }
            Invoke-Docker -Arguments @('rm', '--force', $item.Id)
        }
    }
    foreach ($key in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process')
    }
    $remaining = @(Invoke-Docker -Arguments @('ps', '-aq', '--filter',
        "label=agentexam.jobs-test=$scope"))[0]
    if ($remaining) { throw 'Dedicated containers remain after cleanup' }
    Write-Output 'Dedicated containers and tmpfs database removed; images/build caches retained.'
}
if ($testExit -ne 0) { throw 'Job acceptance did not pass; inspect test output.' }
