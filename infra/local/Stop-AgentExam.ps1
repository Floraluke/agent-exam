#requires -Version 7.4

[CmdletBinding()]
param([ValidateRange(1, 3600)][int]$DrainTimeoutSeconds = 300)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Lifecycle.psm1') -Force

$config = Get-AgentExamConfig
Assert-AgentExamCompleteDeployment $config
Request-AgentExamWorkerStop $config
Wait-AgentExamJobsDrained $config -TimeoutSeconds $DrainTimeoutSeconds
$null = Invoke-AgentExamCompose $config @('stop')

$status = Get-AgentExamLifecycleStatus $config
[ordered]@{
    operation = 'stopped'
    project = $status.project
    initializationState = $status.initializationState
    services = $status.services
    worker = $status.worker
} | ConvertTo-Json -Compress -Depth 4
