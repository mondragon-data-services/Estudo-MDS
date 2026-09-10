#!/usr/bin/env bash
# Preparação do ambiente no Linux / macOS.
#
#   bash scripts/setup.sh
#
# Cria o ambiente virtual, instala as dependências e registra o kernel do
# Jupyter para que os notebooks encontrem os pacotes.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

echo "1/4  Criando o ambiente virtual em .venv ..."
[ -d .venv ] || python3 -m venv .venv

PYTHON="$RAIZ/.venv/bin/python"

echo "2/4  Atualizando o pip ..."
"$PYTHON" -m pip install --upgrade pip --quiet

echo "3/4  Instalando as dependencias (pode levar alguns minutos) ..."
"$PYTHON" -m pip install -r requirements.txt

echo "4/4  Registrando o kernel do Jupyter ..."
"$PYTHON" -m ipykernel install --user --name f1-pipeline --display-name "Python (f1-pipeline)"

cat <<'FIM'

Pronto. Proximos passos:
  source .venv/bin/activate
  python scripts/run_pipeline.py --seasons 2024
  streamlit run app/streamlit_app.py
  jupyter lab notebooks/
FIM
