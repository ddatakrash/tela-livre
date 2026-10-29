#!/bin/bash
# Tela Livre: instalador para Mac. Dois cliques neste arquivo (na primeira vez: botao direito > Abrir).
cd "$(dirname "$0")" || exit 1
echo
echo " ===== Tela Livre: tela inicial sem anuncios para TVs Samsung (2016 a 2022) ====="
echo

erro() {
  echo
  echo " Deu erro. Veja o arquivo instalar-log.txt nesta pasta."
  echo
  read -r -p " Aperte Enter para fechar..." _
  exit 1
}

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import sys" >/dev/null 2>&1; then
  echo " Falta o Python 3. Instale em https://www.python.org/downloads/ e rode de novo."
  read -r -p " Aperte Enter para fechar..." _
  exit 1
fi

TVIP=""
if [ -f tv-ip.txt ]; then TVIP=$(tr -d '[:space:]' < tv-ip.txt); fi
if [ -n "$TVIP" ]; then
  echo " TV: $TVIP   [apague tv-ip.txt para trocar]"
else
  read -r -p " Digite o IP da TV, ex: 192.168.0.20: " TVIP
fi
[ -n "$TVIP" ] || erro
echo "$TVIP" > tv-ip.txt

BUILD=""
[ -f config.properties ] || BUILD="--generic"

echo
echo " [1/4] Preparando a ferramenta de assinatura..."
python3 -m pip install --user --quiet --disable-pip-version-check cryptography > instalar-log.txt 2>&1 \
  || python3 -m pip install --user --quiet --break-system-packages cryptography >> instalar-log.txt 2>&1 || erro
echo " [2/4] Montando o app..."
python3 tizen/build.py $BUILD >> instalar-log.txt 2>&1 || erro
echo " [3/4] Assinando o app."
echo "       Na primeira vez, CRIE uma senha (ela nao aparece enquanto digita) e guarde."
echo "       Nas proximas atualizacoes, use a mesma senha."
python3 tizen/sign.py 2>> instalar-log.txt || erro
echo " [4/4] Enviando pra TV. Olhe a TV: se aparecer algum aviso, aceite."
python3 tizen/install.py "$TVIP" >> instalar-log.txt 2>&1 || erro
echo
echo " PRONTO! O Tela Livre deve abrir na TV agora."
echo
read -r -p " Aperte Enter para fechar..." _
