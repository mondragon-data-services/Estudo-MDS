#!/usr/bin/env bash
# Prepara o ambiente Python do repositório inteiro (Linux / macOS).
#
#   bash scripts/preparar-ambiente.sh
#   PYTHON_BASE=/caminho/python3.12 bash scripts/preparar-ambiente.sh
#
# Cria .venv na RAIZ, instala o requirements.txt da raiz (que inclui todas as
# aulas) e registra o kernel "Python (Estudo-MDS)" usado por todos os notebooks.
# Pode rodar de novo sempre que uma aula nova entrar no requirements.txt.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

echo "1/4  Criando o ambiente virtual em .venv ..."
[ -d .venv ] || "${PYTHON_BASE:-python3}" -m venv .venv
PYTHON="$RAIZ/.venv/bin/python"

echo "2/4  Atualizando o pip ..."
"$PYTHON" -m pip install --upgrade pip --quiet

echo "3/4  Instalando as dependencias de todas as aulas (pode levar alguns minutos) ..."
"$PYTHON" -m pip install -r requirements.txt

echo "4/4  Registrando o kernel do Jupyter ..."
"$PYTHON" -m ipykernel install --user --name mds --display-name "Python (Estudo-MDS)"

if [ -f .env.example ] && [ ! -f .env ]; then
  cp .env.example .env
  echo "Criei o .env a partir do .env.example (confira o SQL_SERVER)."
fi

cat <<'FIM'

Pronto. Nos notebooks, escolha o kernel "Python (Estudo-MDS)".
Apps Streamlit: rode de dentro da pasta da aula, com a .venv ativa:
  source .venv/bin/activate
  cd aulas/<aula> && streamlit run app/app.py
FIM
