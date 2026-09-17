#requires -Version 7.4

[CmdletBinding()]
param([switch]$ValidateOnly, [switch]$Resume)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Local.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Initialize.psm1') -Force

function Get-Preflight {
    param([Parameter(Mandatory)][object]$Config)
    Assert-AgentExamPlainPath $Config.RepositoryRoot
    Assert-AgentExamPlainPath $Config.DataRoot
    Assert-AgentExamPlainPath $Config.PrivateRoot
    Assert-AgentExamPlainPath $Config.LicenseFile
    Assert-AgentExamPrivateAcl $Config.PrivateRoot
    Assert-AgentExamPrivateAcl $Config.LicenseFile
    $state = Read-AgentExamState $Config
    if ($null -eq $state) {
        foreach ($path in @(
                $Config.PostgresRoot, $Config.MinioRoot, $Config.ControlRoot,
                $Config.PostgresPassword, $Config.MinioPassword,
                $Config.MinioAppPassword
            )) {
            if (Test-Path -LiteralPath $path) {
                throw 'Unmarked deployment data already exists; refusing initialization.'
            }
        }
        $status = 'fresh'
    }
    elseif ($state.phase -eq 'complete') { $status = 'complete' }
    else { $status = 'partial' }
    $server = Invoke-AgentExamDocker @('version', '--format', '{{.Server.Version}}')
    Assert-AgentExamImage $Config.PostgresImage $Config.PostgresId
    Assert-AgentExamImage $Config.MinioImage $Config.MinioId
    $compose = Invoke-AgentExamCompose $Config @('config', '--format', 'json') |
        ConvertFrom-Json
    if ($compose.name -ne $Config.Project) { throw 'Unexpected Compose project identity.' }
    [ordered]@{
        ready = $true
        dataRoot = $Config.DataRoot
        project = $Config.Project
        dockerServer = $server
        postgresImage = $Config.PostgresImage
        minioImage = $Config.MinioImage
        licensePresent = $true
        initializationState = $status
    }
}

function Assert-PreparedLayout {
    param([Parameter(Mandatory)][object]$Config)
    foreach ($path in @(
            $Config.PostgresRoot, $Config.MinioRoot, $Config.ControlRoot,
            $Config.PostgresPassword, $Config.MinioPassword,
            $Config.MinioAppPassword
        )) {
        Assert-AgentExamPlainPath $path
    }
    foreach ($path in @(
            $Config.PostgresRoot, $Config.MinioRoot, $Config.ControlRoot,
            $Config.PostgresPassword, $Config.MinioPassword,
            $Config.MinioAppPassword
        )) {
        Assert-AgentExamPrivateAcl $path
    }
}

$config = Get-AgentExamConfig
$preflight = Get-Preflight $config
if ($ValidateOnly -or $preflight.initializationState -eq 'complete') {
    if ($preflight.initializationState -eq 'complete') {
        Assert-PreparedLayout $config
    }
    $preflight | ConvertTo-Json -Compress
    return
}

$state = Read-AgentExamState $config
$recovering = $preflight.initializationState -eq 'partial'
if ($recovering -and -not $Resume) {
    throw 'A previous initialization is incomplete; inspect it before using -Resume.'
}
$phase = if ($null -eq $state) { 'fresh' } else { $state.phase }
if ($phase -eq 'fresh') {
    Set-AgentExamState $config 'preparing'
    $phase = 'preparing'
}
if ($phase -eq 'preparing') {
    foreach ($path in @(
            $config.PostgresRoot, $config.MinioRoot, $config.ControlRoot,
            $config.PostgresPassword, $config.MinioPassword,
            $config.MinioAppPassword
        )) {
        if (Test-Path -LiteralPath $path) {
            throw 'Preparing can continue only before deployment paths exist.'
        }
    }
    foreach ($path in @($config.PostgresRoot, $config.MinioRoot, $config.ControlRoot)) {
        New-AgentExamPrivateDirectory $path
    }
    foreach ($path in @(
            $config.PostgresPassword, $config.MinioPassword,
            $config.MinioAppPassword
        )) {
        New-AgentExamSecret $path
    }
    Set-AgentExamState $config 'prepared'
    $phase = 'prepared'
}
if ($phase -eq 'prepared') {
    Assert-PreparedLayout $config
    $null = Invoke-AgentExamCompose $config @('up', '-d')
    $null = Wait-AgentExamPostgres $config
    $minioId = (Invoke-AgentExamCompose $config @('ps', '-q', 'minio')).Trim()
    $probe = '/tmp/agentexam-probe-' + [guid]::NewGuid().ToString('N')
    try { Open-AgentExamMinioAdmin $config $minioId $probe }
    finally { $null = @(& docker exec $minioId rm -r -- $probe 2>&1) }
    Set-AgentExamState $config 'services-ready'
    $phase = 'services-ready'
}
if ($phase -eq 'services-ready') {
    $null = Wait-AgentExamPostgres $config
    $database = Get-AgentExamDatabaseState $config
    if ($database -eq 'empty') { Initialize-AgentExamDatabase $config }
    elseif ($database -ne 'schema-empty') {
        throw 'Database contents do not match a safe initialization recovery state.'
    }
    Set-AgentExamState $config 'postgres-ready'
    $phase = 'postgres-ready'
}
if ($phase -ne 'postgres-ready') {
    throw 'Initialization phase is not safe to continue automatically.'
}
Initialize-AgentExamMinio $config
Set-AgentExamState $config 'complete'
(Get-Preflight $config) | ConvertTo-Json -Compress
