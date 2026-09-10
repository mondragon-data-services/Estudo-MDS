# Preparação do ambiente no Windows (PowerShell).
#
#   .\scripts\setup.ps1
#
# Cria o ambiente virtual, instala as dependências e registra o kernel do
# Jupyter para que os notebooks encontrem os pacotes.

$ErrorActionPreference = "Stop"

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

Write-Host "1/4  Criando o ambiente virtual em .venv ..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { python -m venv .venv }

$python = Join-Path $raiz ".venv\Scripts\python.exe"

Write-Host "2/4  Atualizando o pip ..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip --quiet

Write-Host "3/4  Instalando as dependencias (pode levar alguns minutos) ..." -ForegroundColor Cyan
& $python -m pip install -r requirements.txt

Write-Host "4/4  Registrando o kernel do Jupyter ..." -ForegroundColor Cyan
& $python -m ipykernel install --user --name f1-pipeline --display-name "Python (f1-pipeline)"

Write-Host ""
Write-Host "Pronto. Proximos passos:" -ForegroundColor Green
Write-Host "  .venv\Scripts\activate"
Write-Host "  python scripts/run_pipeline.py --seasons 2024"
Write-Host "  streamlit run app/streamlit_app.py"
Write-Host "  jupyter lab notebooks/"
