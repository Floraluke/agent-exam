#requires -Version 7.4

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AgentExam.Lifecycle.psm1') -Force

$config = Get-AgentExamConfig
Get-AgentExamLifecycleStatus $config | ConvertTo-Json -Compress -Depth 4
