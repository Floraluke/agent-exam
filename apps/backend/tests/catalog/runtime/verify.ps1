# Dedicated synthetic PG + MinIO acceptance. No host ports, mounts or global settings.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$scope = 'catalog-' + [guid]::NewGuid().ToString('N')
$names = @("$scope-minio", "$scope-postgres", "$scope-tests")
$owned = [System.Collections.Generic.List[string]]::new()
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
        "agentexam.catalog-test=$scope") + $Arguments))[0]
    if ($id -notmatch '^[0-9a-f]{64}$') { throw 'Unexpected container identity' }
    $owned.Add($id)
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
    $minioImage = @(Invoke-Docker -Arguments @('image', 'inspect',
        'agentexam-minio-test:7aac2a2c-go1.26.8', '--format', '{{.Id}}'))[0]
    if ($minioImage -ne 'sha256:922042a62be66dc71bd1b23de25c7c232a6084033f3bcc2337ab49611cc3aba8') {
        throw 'Unverified MinIO build identity'
    }
    $driverImage = @(Invoke-Docker -Arguments @('image', 'inspect',
        'agentexam-catalog-tests:20260912', '--format', '{{.Id}}'))[0]
    $postgresImage = 'sha256:5cce759a2777634ff1edd0d56b9241a2961deb7f72e125d4af6ae2928163a6b6'
    Invoke-Docker -Arguments @('image', 'inspect', $postgresImage, '--format', '{{.Id}}')
    Write-Output "MinIO image: $minioImage; test driver: $driverImage"
    $password = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    $access = 'ae_test_' + [guid]::NewGuid().ToString('N')
    $environment = @{
        MINIO_ROOT_USER = $access
        MINIO_ROOT_PASSWORD = $password
        POSTGRES_USER = 'agentexam_identity_test'
        POSTGRES_DB = 'agentexam_identity_test'
        POSTGRES_PASSWORD = $password
        AGENTEXAM_TEST_DATABASE_URL = "host=127.0.0.1 port=55432 dbname=agentexam_identity_test user=agentexam_identity_test password=$password"
        AGENTEXAM_MINIO_ENDPOINT = 'http://127.0.0.1:9000'
        AGENTEXAM_MINIO_BUCKET = 'agentexam-synthetic-test'
        AGENTEXAM_MINIO_ACCESS_KEY = $access
        AGENTEXAM_MINIO_SECRET_KEY = $password
    }
    foreach ($key in $environment.Keys) {
        $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $environment[$key], 'Process')
    }
    $limits = @('--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
        '--memory=512m', '--cpus=1', '--pids-limit=128',
        '--env=HTTP_PROXY=', '--env=HTTPS_PROXY=', '--env=ALL_PROXY=',
        '--env=http_proxy=', '--env=https_proxy=', '--env=all_proxy=')
    $minio = New-TestContainer $names[0] ($limits + @('--network=none',
        '--tmpfs=/data:rw,nosuid,noexec,size=256m,uid=65534,gid=65534',
        '--tmpfs=/tmp:rw,nosuid,noexec,size=64m,uid=65534,gid=65534',
        '--env=MINIO_ROOT_USER', '--env=MINIO_ROOT_PASSWORD', '--env=MINIO_BROWSER=off',
        $minioImage, 'server', '/data', '--address', '127.0.0.1:9000',
        '--console-address', '127.0.0.1:9001'))
    Check-Isolation $minio 'none'
    Invoke-Docker -Arguments @('start', $minio)
    $network = "container:$minio"
    $pg = New-TestContainer $names[1] ($limits + @("--network=$network", '--user=70:70',
        '--tmpfs=/var/lib/postgresql/data:rw,nosuid,noexec,size=256m,uid=70,gid=70',
        '--tmpfs=/var/run/postgresql:rw,nosuid,noexec,size=16m,uid=70,gid=70',
        '--tmpfs=/tmp:rw,nosuid,noexec,size=32m,uid=70,gid=70',
        '--env=POSTGRES_USER', '--env=POSTGRES_DB', '--env=POSTGRES_PASSWORD',
        $postgresImage, 'postgres', '-p', '55432', '-c', 'listen_addresses=127.0.0.1',
        '-c', 'max_connections=20'))
    Check-Isolation $pg $network
    Invoke-Docker -Arguments @('start', $pg)
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        & docker exec $pg pg_isready -h 127.0.0.1 -p 55432 -U agentexam_identity_test *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Dedicated PostgreSQL did not become ready' }
    $driverArgs = $limits + @("--network=$network",
        '--tmpfs=/tmp:rw,nosuid,size=256m,uid=65534,gid=65534',
        '--env=AGENTEXAM_RUN_IDENTITY_POSTGRES=1', '--env=AGENTEXAM_RUN_CATALOG_MINIO=1')
    foreach ($key in $environment.Keys | Where-Object { $_ -like 'AGENTEXAM_*' }) {
        $driverArgs += "--env=$key"
    }
    $driverArgs += @($driverImage, 'tests/catalog', 'tests/identity/test_postgres_identity.py',
        'tests/membership/test_postgres.py', 'tests/membership/test_postgres_rollback.py')
    $driver = New-TestContainer $names[2] $driverArgs
    Check-Isolation $driver $network
    & docker start --attach $driver
    $testExit = $LASTEXITCODE
    $actualExit = @(Invoke-Docker -Arguments @('inspect', $driver, '--format',
        '{{.State.ExitCode}}'))[0]
    if ($actualExit -ne '0') { $testExit = 1 }
}
finally {
    # Only exact, freshly generated names with our matching label can be removed.
    foreach ($name in @($names[2], $names[1], $names[0])) {
        $raw = @(& docker inspect $name 2>$null)
        if ($LASTEXITCODE -eq 0) {
            $item = (($raw -join [Environment]::NewLine) | ConvertFrom-Json)[0]
            if ($item.Id -notmatch '^[0-9a-f]{64}$' -or
                $item.Config.Labels.'agentexam.catalog-test' -ne $scope) {
                throw 'Refusing cleanup of an unrelated container'
            }
            Invoke-Docker -Arguments @('rm', '--force', $item.Id)
        }
    }
    foreach ($key in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process')
    }
    $remaining = @(Invoke-Docker -Arguments @('ps', '-aq', '--filter',
        "label=agentexam.catalog-test=$scope"))[0]
    if ($remaining) { throw 'Dedicated containers remain after cleanup' }
    Write-Output 'Dedicated containers and tmpfs test data removed; images/build caches retained.'
}
if ($testExit -ne 0) { throw 'Catalog acceptance did not pass; inspect the test output.' }
