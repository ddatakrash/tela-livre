#!/usr/bin/env python3
"""Instala o YouTube AdFree (github.com/webosbrew/youtube-webos) numa TV LG em Developer Mode, e liga o inicio automatico.

    python3 lg/youtube-adfree.py 192.168.15.153                # baixa a versao mais nova, instala e liga o autostart
    python3 lg/youtube-adfree.py 192.168.15.153 --sem-autostart
    python3 lg/youtube-adfree.py 192.168.15.153 --desligar-autostart

Antes, na TV: desinstale o app YouTube oficial (os dois usam o mesmo id). Usa a mesma chave e passphrase do
lg/install.py (Developer Mode + Key Server). Com o autostart, o YouTube vira uma "entrada" da TV e ela volta direto
nele quando ele foi o ultimo usado. Na TV, o botao VERDE do controle abre as opcoes do YouTube AdFree.
"""
import importlib.util
import json
import os
import ssl
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ID = 'youtube.leanback.v4'
RELEASE = 'https://api.github.com/repos/webosbrew/youtube-webos/releases/latest'
TEMP = '/media/developer/temp/youtube-adfree.ipk'

spec = importlib.util.spec_from_file_location('lg_install', os.path.join(HERE, 'install.py'))
tv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv)


def https():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def download():
    """Baixa o .ipk da ultima versao publicada; devolve (caminho, versao)."""
    ctx = https()
    req = urllib.request.Request(RELEASE, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'tela-livre'})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        release = json.loads(r.read().decode('utf-8'))
    assets = [a for a in release.get('assets', []) if a.get('name', '').endswith('.ipk')]
    if not assets:
        sys.exit('A ultima versao do YouTube AdFree nao tem .ipk para baixar.')
    print('Baixando %s (%s)...' % (assets[0]['name'], release.get('tag_name', '')))
    path = os.path.join(tempfile.gettempdir(), assets[0]['name'])
    with urllib.request.urlopen(assets[0]['browser_download_url'], timeout=120, context=ctx) as r, open(path, 'wb') as f:
        f.write(r.read())
    return path, release.get('tag_name', '')


def autostart(ip, key, on):
    uri = 'luna://com.webos.service.eim/' + ('addDevice' if on else 'deleteDevice')
    payload = {'appId': APP_ID, 'pigImage': '', 'mvpdIcon': ''} if on else {'appId': APP_ID}
    out = tv.luna(ip, key, uri, payload)
    if '"returnValue":true' in out:
        print('Inicio automatico %s.' % ('ligado' if on else 'desligado'))
    else:
        print('A TV nao aceitou mudar o inicio automatico. Ela respondeu: ' + (out.strip() or '(nada)'))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    ip = args[0]
    key = tv.fetch_key(ip)

    if '--desligar-autostart' in sys.argv:
        autostart(ip, key, False)
        return

    ipk, version = download()
    print('Copiando para a TV...')
    with open(ipk, 'rb') as f:
        copy = tv.ssh(ip, key, 'mkdir -p /media/developer/temp && cat > ' + TEMP, stdin=f)
    if copy.returncode != 0:
        err = copy.stderr.decode('utf-8', 'replace') if isinstance(copy.stderr, bytes) else copy.stderr
        sys.exit('Nao consegui copiar: %s\nO Developer Mode ainda esta ligado?' % err.strip())
    print('Instalando...')
    out = tv.luna(ip, key, 'luna://com.webos.appInstallService/dev/install',
                  {'id': APP_ID, 'ipkUrl': TEMP, 'subscribe': True}, replies=30, wait=90)
    tv.ssh(ip, key, 'rm -f ' + TEMP)
    if '"state":"installed"' not in out:
        sys.exit('A TV nao terminou de instalar. Se o YouTube oficial ainda esta na TV, desinstale-o e tente de novo.\n'
                 'Ela respondeu:\n' + out.strip())
    print('YouTube AdFree %s instalado.' % version)

    if '--sem-autostart' not in sys.argv:
        autostart(ip, key, True)
    tv.luna(ip, key, 'luna://com.webos.applicationManager/launch', {'id': APP_ID})
    print('Pronto: o YouTube AdFree esta aberto. Botao VERDE do controle = opcoes (SponsorBlock, Shorts, qualidade).')


if __name__ == '__main__':
    main()
