#!/bin/bash
# RetroArch (emuladores) para TVs LG (webOS): instalador para Mac. Dois cliques (na primeira vez: botao direito > Abrir).
cd "$(dirname "$0")" || exit 1
echo
echo " ===== RetroArch para LG ====="
echo

fim() { echo; read -r -p " Aperte Enter para fechar..." _; exit "$1"; }

if ! command -v python3 >/dev/null 2>&1; then
  echo " Falta o Python 3. Instale em https://www.python.org/downloads/ e rode de novo."
  fim 1
fi

TVIP=""
if [ -f tv-ip-lg.txt ]; then TVIP=$(tr -d '[:space:]' < tv-ip-lg.txt); fi
if [ -n "$TVIP" ]; then
  echo " TV: $TVIP   [apague tv-ip-lg.txt para trocar]"
else
  echo " Na TV, abra o app Developer Mode: ele mostra o IP da TV e uma passphrase. Ligue o Key Server."
  read -r -p " Digite o IP da TV, ex: 192.168.15.153: " TVIP
fi
[ -n "$TVIP" ] || fim 1
echo "$TVIP" > tv-ip-lg.txt

python3 -m pip install --user --quiet --disable-pip-version-check --no-warn-script-location certifi >/dev/null 2>&1
echo " Na primeira vez, digite a passphrase que aparece no Developer Mode."
python3 lg/retroarch.py "$TVIP" || fim 1
fim 0
