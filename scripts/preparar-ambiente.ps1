# Prepara o ambiente Python do repositório inteiro (Windows / PowerShell).
#
#   .\scripts\preparar-ambiente.ps1
#   .\scripts\preparar-ambiente.ps1 -Python C:\caminho\python.exe
#
# Cria .venv na RAIZ, instala o requirements.txt da raiz (que inclui todas as
# aulas) e registra o kernel "Python (Estudo-MDS)" usado por todos os notebooks.
# Pode rodar de novo sempre que uma aula nova entrar no requirements.txt.

param(
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
Push-Location $raiz   # volta para a pasta original no fim (finally)
try {
    Write-Host "1/4  Criando o ambiente virtual em .venv ..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        if ($Python) { Executar { & $Python -m venv .venv } }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { Executar { python -m venv .venv } }
        elseif (Get-Command py -ErrorAction SilentlyContinue) { Executar { py -3 -m venv .venv } }
        else { throw "Python nao encontrado no PATH. Informe o caminho: -Python C:\...\python.exe" }
    }
    $pythonVenv = Join-Path $raiz ".venv\Scripts\python.exe"

    Write-Host "2/4  Atualizando o pip ..." -ForegroundColor Cyan
    Executar { & $pythonVenv -m pip install --upgrade pip --quiet }

    Write-Host "3/4  Instalando as dependencias de todas as aulas (pode levar alguns minutos) ..." -ForegroundColor Cyan
    Executar { & $pythonVenv -m pip install -r requirements.txt }

    Write-Host "4/4  Registrando o kernel do Jupyter ..." -ForegroundColor Cyan
    Executar { & $pythonVenv -m ipykernel install --user --name mds --display-name "Python (Estudo-MDS)" }

    if ((Test-Path ".env.example") -and -not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Criei o .env a partir do .env.example (confira o SQL_SERVER)." -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Pronto. Nos notebooks, escolha o kernel 'Python (Estudo-MDS)'." -ForegroundColor Green
Write-Host "Apps Streamlit: rode de dentro da pasta da aula, com a .venv ativa:"
Write-Host "  .venv\Scripts\activate"
Write-Host "  cd aulas\<aula>; streamlit run app/app.py"
