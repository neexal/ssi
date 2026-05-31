$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        $Python = $PythonCommand.Source
    } else {
        $PyCommand = Get-Command py -ErrorAction SilentlyContinue
        if ($PyCommand) {
            $Python = $PyCommand.Source
        } else {
            Write-Host "Python was not found. Create .venv and install requirements first:" -ForegroundColor Red
            Write-Host "  py -m venv .venv"
            Write-Host "  .\.venv\Scripts\Activate.ps1"
            Write-Host "  pip install -r requirements.txt"
            exit 1
        }
    }
}

$Services = @(
    @{
        Name = "Registry"
        Path = Join-Path $Root "trusted_registry"
        Address = "127.0.0.1:8004"
        Url = "http://127.0.0.1:8004/"
    },
    @{
        Name = "Issuer"
        Path = Join-Path $Root "issuer_core"
        Address = "127.0.0.1:8001"
        Url = "http://127.0.0.1:8001/admin/dashboard/"
    },
    @{
        Name = "Holder"
        Path = Join-Path $Root "holder_wallet"
        Address = "127.0.0.1:8002"
        Url = "http://127.0.0.1:8002/wallet/ui/"
    },
    @{
        Name = "Verifier"
        Path = Join-Path $Root "verifier_node"
        Address = "127.0.0.1:8003"
        Url = "http://127.0.0.1:8003/api/v1/verify/"
    }
)

$Jobs = @()

try {
    foreach ($Service in $Services) {
        $Jobs += Start-Job -Name $Service.Name -ArgumentList $Python, $Service.Path, $Service.Address, $Service.Name -ScriptBlock {
            param($Python, $ProjectPath, $Address, $ServiceName)

            Set-Location $ProjectPath
            & $Python manage.py migrate --noinput 2>&1 | ForEach-Object {
                "[$ServiceName] $_"
            }
            if ($LASTEXITCODE -ne 0) {
                throw "$ServiceName migrations failed."
            }

            & $Python manage.py runserver $Address 2>&1 | ForEach-Object {
                "[$ServiceName] $_"
            }
        }
    }

    Write-Host ""
    Write-Host "SSI services are starting. Press Ctrl+C to stop all services." -ForegroundColor Green
    foreach ($Service in $Services) {
        Write-Host ("  {0}: {1}" -f $Service.Name, $Service.Url)
    }
    Write-Host ""

    while ($true) {
        foreach ($Job in $Jobs) {
            Receive-Job -Job $Job -ErrorAction Continue
            if ($Job.State -eq "Failed") {
                throw "$($Job.Name) service failed."
            }
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    Write-Host ""
    Write-Host "Stopping SSI services..." -ForegroundColor Yellow
    foreach ($Job in $Jobs) {
        Stop-Job -Job $Job -ErrorAction SilentlyContinue
        Remove-Job -Job $Job -Force -ErrorAction SilentlyContinue
    }
}
