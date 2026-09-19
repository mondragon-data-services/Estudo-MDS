#!/usr/bin/env bash
# Prepara o ambiente Python de UMA aula (Linux / macOS).
#
#   bash scripts/preparar-aula.sh 02-rag-sqlserver-2017
#
# Cria aulas/<aula>/.venv, instala o requirements.txt da aula e registra um
# kernel do Jupyter com o nome da aula — é esse kernel que você escolhe no
# notebook. Cada aula tem a sua .venv: as dependências de uma não quebram a outra.

set -euo pipefail

AULA="${1:-}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASTA="$RAIZ/aulas/$AULA"

if [ -z "$AULA" ] || [ ! -f "$PASTA/requirements.txt" ]; then
  echo "Uso: bash scripts/preparar-aula.sh <aula>. Disponíveis:"
  for d in "$RAIZ"/aulas/[!_]*/; do echo "  $(basename "$d")"; done
  exit 1
fi
cd "$PASTA"

echo "1/4  Criando o ambiente virtual em aulas/$AULA/.venv ..."
[ -d .venv ] || "${PYTHON_BASE:-python3}" -m venv .venv   # PYTHON_BASE=/caminho/python para escolher outro
PYTHON="$PASTA/.venv/bin/python"

echo "2/4  Atualizando o pip ..."
"$PYTHON" -m pip install --upgrade pip --quiet

echo "3/4  Instalando as dependencias (pode levar alguns minutos) ..."
"$PYTHON" -m pip install -r requirements.txt

echo "4/4  Registrando o kernel do Jupyter ..."
"$PYTHON" -m pip install ipykernel --quiet
"$PYTHON" -m ipykernel install --user --name "mds-$AULA" --display-name "Python (aula $AULA)"

if [ -f "$RAIZ/.env.example" ] && [ ! -f "$RAIZ/.env" ]; then
  cp "$RAIZ/.env.example" "$RAIZ/.env"
  echo "Criei o .env da raiz a partir do .env.example."
fi

cat <<FIM

Pronto. Proximos passos:
  cd aulas/$AULA
  source .venv/bin/activate
  (no notebook, escolha o kernel 'Python (aula $AULA)')
FIM
