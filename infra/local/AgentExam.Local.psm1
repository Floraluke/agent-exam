#requires -Version 7.4

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-AgentExamConfig {
    $root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
    $environmentFile = Join-Path $root 'infra\.env'
    if (-not (Test-Path -LiteralPath $environmentFile -PathType Leaf)) {
        throw 'Local environment is missing; copy infra/.env.example to infra/.env.'
    }
    $environment = ConvertFrom-StringData (Get-Content -Raw -LiteralPath $environmentFile)
    foreach ($name in @(
            'AGENTEXAM_DATA_ROOT', 'AGENTEXAM_POSTGRES_IMAGE',
            'AGENTEXAM_MINIO_IMAGE', 'AGENTEXAM_POSTGRES_PORT',
            'AGENTEXAM_MINIO_PORT', 'AGENTEXAM_MINIO_BUCKET',
            'AGENTEXAM_MINIO_ACCESS_KEY'
        )) {
        if (-not $environment[$name]) { throw "Missing local environment: $name" }
    }
    $data = [IO.Path]::GetFullPath($environment['AGENTEXAM_DATA_ROOT'])
    $private = Join-Path $data 'private'
    [pscustomobject]@{
        RepositoryRoot = $root
        DataRoot = $data
        PrivateRoot = $private
        PostgresRoot = Join-Path $data 'postgres'
        MinioRoot = Join-Path $data 'minio'
        ControlRoot = Join-Path $data 'control'
        StateFile = Join-Path $private 'deployment-state.json'
        PostgresPassword = Join-Path $private 'postgres-password'
        MinioPassword = Join-Path $private 'minio-password'
        MinioAppPassword = Join-Path $private 'minio-app-password'
        LicenseFile = Join-Path $private 'minio.license'
        WorkerStopFile = Join-Path $data 'control\worker.stop'
        ComposeFile = Join-Path $root 'infra\compose.yaml'
        EnvironmentFile = $environmentFile
        PolicyFile = Join-Path $root 'infra\local\minio-app-policy.json'
        Project = 'agentexam-local'
        PostgresImage = $environment['AGENTEXAM_POSTGRES_IMAGE']
        MinioImage = $environment['AGENTEXAM_MINIO_IMAGE']
        PostgresPort = [int]$environment['AGENTEXAM_POSTGRES_PORT']
        MinioPort = [int]$environment['AGENTEXAM_MINIO_PORT']
        PostgresId = 'sha256:aad6289ca337b3ce76896f2e7e61480490152886c7828120371fb28e6b779e1d'
        MinioId = 'sha256:2cacca14bad4502feddcbf99cd1a927d8002c6d1ba874a81def1c37b2986b580'
        Bucket = $environment['AGENTEXAM_MINIO_BUCKET']
        MinioRootUser = 'agentexam_admin'
        MinioAppUser = $environment['AGENTEXAM_MINIO_ACCESS_KEY']
    }
}

function Invoke-AgentExamDocker {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$InputText
    )
    if ($PSBoundParameters.ContainsKey('InputText')) {
        $output = @($InputText | & docker @Arguments 2>&1)
    }
    else {
        $output = @(& docker @Arguments 2>&1)
    }
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed: $($Arguments[0])" }
    return ($output -join [Environment]::NewLine).Trim()
}

function Invoke-AgentExamCompose {
    param([Parameter(Mandatory)][object]$Config, [string[]]$Arguments)
    $prefix = @(
        'compose', '--env-file', $Config.EnvironmentFile,
        '-f', $Config.ComposeFile
    )
    return Invoke-AgentExamDocker -Arguments ($prefix + $Arguments)
}

function Assert-AgentExamPlainPath {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { throw "Required path is missing: $Path" }
    $item = Get-Item -LiteralPath $Path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Reparse points are not accepted: $Path"
    }
}

function Get-AgentExamAcl {
    param([Parameter(Mandatory)][string]$Path)
    $item = Get-Item -LiteralPath $Path -Force
    $sections = [Security.AccessControl.AccessControlSections]'Access,Owner'
    if ($item.PSIsContainer) {
        return [IO.FileSystemAclExtensions]::GetAccessControl(
            [IO.DirectoryInfo]::new($item.FullName), $sections
        )
    }
    return [IO.FileSystemAclExtensions]::GetAccessControl(
        [IO.FileInfo]::new($item.FullName), $sections
    )
}

function Assert-AgentExamPrivateAcl {
    param([Parameter(Mandatory)][string]$Path)
    $acl = Get-AgentExamAcl $Path
    if (-not $acl.AreAccessRulesProtected) { throw "Private ACL inheritance is enabled: $Path" }
    $owner = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $owner) {
        throw "Unexpected private path owner: $Path"
    }
    $rules = $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])
    foreach ($rule in $rules) {
        if ($rule.AccessControlType -ne 'Allow' -or
            $rule.IdentityReference.Value -notin @($owner, 'S-1-5-18')) {
            throw "Unexpected private ACL entry: $Path"
        }
    }
}

function Set-AgentExamPrivateAcl {
    param([Parameter(Mandatory)][string]$Path, [switch]$Directory)
    $owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $current = Get-AgentExamAcl $Path
    if ($current.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne
        $owner.Value) {
        throw "Refusing to change private path owner: $Path"
    }
    $sections = [Security.AccessControl.AccessControlSections]::Access
    if ($Directory) {
        $info = [IO.DirectoryInfo]::new($Path)
        $acl = [IO.FileSystemAclExtensions]::GetAccessControl($info, $sections)
        $inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
    }
    else {
        $info = [IO.FileInfo]::new($Path)
        $acl = [IO.FileSystemAclExtensions]::GetAccessControl($info, $sections)
        $inherit = [Security.AccessControl.InheritanceFlags]::None
    }
    $acl.SetAccessRuleProtection($true, $false)
    $rules = $acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])
    foreach ($rule in $rules) { $acl.RemoveAccessRuleAll($rule) }
    foreach ($sid in @($owner, [Security.Principal.SecurityIdentifier]::new('S-1-5-18'))) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $sid, [Security.AccessControl.FileSystemRights]::FullControl,
            $inherit, [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow
        )
        $null = $acl.AddAccessRule($rule)
    }
    [IO.FileSystemAclExtensions]::SetAccessControl($info, $acl)
}

function New-AgentExamPrivateDirectory {
    param([Parameter(Mandatory)][string]$Path)
    if (Test-Path -LiteralPath $Path) { throw "Refusing existing deployment path: $Path" }
    $null = New-Item -ItemType Directory -Path $Path
    Set-AgentExamPrivateAcl -Path $Path -Directory
}

function New-AgentExamSecret {
    param([Parameter(Mandatory)][string]$Path)
    if (Test-Path -LiteralPath $Path) { throw "Refusing existing secret path: $Path" }
    $secret = [Convert]::ToHexString(
        [Security.Cryptography.RandomNumberGenerator]::GetBytes(20)
    )
    [IO.File]::WriteAllText($Path, $secret, [Text.UTF8Encoding]::new($false))
    Set-AgentExamPrivateAcl -Path $Path
}

function Read-AgentExamState {
    param([Parameter(Mandatory)][object]$Config)
    if (-not (Test-Path -LiteralPath $Config.StateFile)) { return $null }
    Assert-AgentExamPlainPath $Config.StateFile
    Assert-AgentExamPrivateAcl $Config.StateFile
    $state = Get-Content -Raw -LiteralPath $Config.StateFile | ConvertFrom-Json
    if ($state.version -ne 1 -or $state.project -ne $Config.Project -or
        $state.phase -notin @('preparing', 'prepared', 'services-ready',
            'postgres-ready', 'complete')) {
        throw 'Unknown deployment state marker; refusing to continue.'
    }
    return $state
}

function Set-AgentExamState {
    param([Parameter(Mandatory)][object]$Config, [Parameter(Mandatory)][string]$Phase)
    $temporary = $Config.StateFile + '.tmp-' + [guid]::NewGuid().ToString('N')
    $json = [ordered]@{ version = 1; project = $Config.Project; phase = $Phase } |
        ConvertTo-Json -Compress
    [IO.File]::WriteAllText($temporary, $json, [Text.UTF8Encoding]::new($false))
    Set-AgentExamPrivateAcl -Path $temporary
    Move-Item -LiteralPath $temporary -Destination $Config.StateFile -Force
}

function Assert-AgentExamImage {
    param([string]$Reference, [string]$ExpectedId)
    $image = Invoke-AgentExamDocker @('image', 'inspect', $Reference, '--format', '{{json .}}') |
        ConvertFrom-Json
    if ($image.Id -ne $ExpectedId -or $image.Os -ne 'linux' -or
        $image.Architecture -ne 'amd64') {
        throw "Local image identity or platform is not approved: $Reference"
    }
}

Export-ModuleMember -Function *-AgentExam*
