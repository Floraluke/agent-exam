#requires -Version 7.4

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Initialize.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Lifecycle.psm1') -Force

$config = Get-AgentExamConfig
Assert-AgentExamCompleteDeployment $config
Clear-AgentExamWorkerStop $config
$null = Invoke-AgentExamCompose $config @('up', '-d')
$null = Wait-AgentExamPostgres $config
$minioId = (Invoke-AgentExamCompose $config @('ps', '-q', 'minio')).Trim()
if ($minioId -notmatch '^[0-9a-f]{64}$') {
    throw 'Unexpected AIStor container identity.'
}
$probe = '/tmp/agentexam-start-' + [guid]::NewGuid().ToString('N')
try { Open-AgentExamMinioAdmin $config $minioId $probe }
finally { $null = @(& docker exec $minioId rm -r -- $probe 2>&1) }

$status = Get-AgentExamLifecycleStatus $config
[ordered]@{
    operation = 'started'
    project = $status.project
    initializationState = $status.initializationState
    services = $status.services
    worker = $status.worker
} | ConvertTo-Json -Compress -Depth 4
