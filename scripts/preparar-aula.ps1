# Prepara o ambiente Python de UMA aula (Windows / PowerShell).
#
#   .\scripts\preparar-aula.ps1 02-rag-sqlserver-2017
#   .\scripts\preparar-aula.ps1 02-rag-sqlserver-2017 -Python C:\caminho\python.exe
#
# Cria aulas/<aula>/.venv, instala o requirements.txt da aula e registra um
# kernel do Jupyter com o nome da aula — é esse kernel que você escolhe no
# notebook. Cada aula tem a sua .venv: as dependências de uma não quebram a outra.

param(
    [Parameter(Mandatory = $true)][string]$Aula,
    [string]$Python   # opcional: qual Python usar para criar a .venv
)

$ErrorActionPreference = "Stop"

# O pip escreve avisos no stderr; no PowerShell 5.1 isso viraria erro fatal.
# Por isso os comandos nativos rodam com "Continue" e conferimos o código de saída.
function Executar([scriptblock]$Comando) {
    $ErrorActionPreference = "Continue"
    & $Comando 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw "Falhou (codigo $LASTEXITCODE): $Comando" }
}

$raiz = Split-Path -Parent $PSScriptRoot
$pasta = Join-Path $raiz "aulas\$Aula"
if (-not (Test-Path (Join-Path $pasta "requirements.txt"))) {
    Write-Host "Aula '$Aula' nao encontrada (ou sem requirements.txt). Disponiveis:" -ForegroundColor Red
    Get-ChildItem (Join-Path $raiz "aulas") -Directory | Where-Object { $_.Name -notlike "_*" } | ForEach-Object { "  $($_.Name)" }
    exit 1
}
Set-Location $pasta

Write-Host "1/4  Criando o ambiente virtual em aulas\$Aula\.venv ..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    if ($Python) { Executar { & $Python -m venv .venv } }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { Executar { python -m venv .venv } }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { Executar { py -3 -m venv .venv } }
    else { throw "Python nao encontrado no PATH. Informe o caminho: -Python C:\...\python.exe" }
}
$pythonVenv = Join-Path $pasta ".venv\Scripts\python.exe"

Write-Host "2/4  Atualizando o pip ..." -ForegroundColor Cyan
Executar { & $pythonVenv -m pip install --upgrade pip --quiet }

Write-Host "3/4  Instalando as dependencias (pode levar alguns minutos) ..." -ForegroundColor Cyan
Executar { & $pythonVenv -m pip install -r requirements.txt }

Write-Host "4/4  Registrando o kernel do Jupyter ..." -ForegroundColor Cyan
Executar { & $pythonVenv -m pip install ipykernel --quiet }
Executar { & $pythonVenv -m ipykernel install --user --name "mds-$Aula" --display-name "Python (aula $Aula)" }

if ((Test-Path (Join-Path $raiz ".env.example")) -and -not (Test-Path (Join-Path $raiz ".env"))) {
    Copy-Item (Join-Path $raiz ".env.example") (Join-Path $raiz ".env")
    Write-Host "Criei o .env da raiz a partir do .env.example." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Pronto. Proximos passos:" -ForegroundColor Green
Write-Host "  cd aulas\$Aula"
Write-Host "  .venv\Scripts\activate"
Write-Host "  (no notebook, escolha o kernel 'Python (aula $Aula)')"
