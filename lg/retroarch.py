#!/usr/bin/env python3
"""Instala o Homebrew Channel e o RetroArch (emuladores de videogame) numa TV LG em Developer Mode.

    python3 lg/retroarch.py 192.168.15.153                 # instala o Homebrew Channel e o RetroArch, e abre o RetroArch
    python3 lg/retroarch.py 192.168.15.153 --so-homebrew   # so o Homebrew Channel (o RetroArch voce instala por ele)
    python3 lg/retroarch.py 192.168.15.153 --remover       # remove o RetroArch

Usa a mesma chave e passphrase do lg/install.py (Developer Mode + Key Server).
- Homebrew Channel: a versao mais nova de github.com/webosbrew/webos-homebrew-channel
- RetroArch: o pacote publicado no repositorio do Homebrew Channel (repo.webosbrew.org), conferido pelo sha256 dele
Os jogos (ROMs) voce copia num pendrive e abre pelo RetroArch: Load Content > o pendrive (/tmp/usb).
"""
import hashlib
import importlib.util
import json
import os
import ssl
import sys
import tempfile
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HBCHANNEL_ID = 'org.webosbrew.hbchannel'
HBCHANNEL_RELEASE = 'https://api.github.com/repos/webosbrew/webos-homebrew-channel/releases/latest'
REPO = 'https://repo.webosbrew.org/api/apps.json'
TEMP = '/media/developer/temp/'

spec = importlib.util.spec_from_file_location('lg_install', os.path.join(HERE, 'install.py'))
tv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv)


def https():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'tela-livre'})
    with urllib.request.urlopen(req, timeout=timeout, context=https()) as r:
        return r.read()


def save(url, name):
    print('Baixando %s ...' % name)
    path = os.path.join(tempfile.gettempdir(), name)
    with open(path, 'wb') as f:
        f.write(get(url, timeout=300))
    return path


def homebrew_channel():
    release = json.loads(get(HBCHANNEL_RELEASE).decode('utf-8'))
    assets = [a for a in release.get('assets', []) if a.get('name', '').endswith('.ipk')]
    if not assets:
        sys.exit('A ultima versao do Homebrew Channel nao tem .ipk para baixar.')
    return save(assets[0]['browser_download_url'], assets[0]['name']), release.get('tag_name', '')


def retroarch():
    """Acha o RetroArch no repositorio do Homebrew Channel; devolve (id, caminho do .ipk, versao)."""
    packages = json.loads(get(REPO).decode('utf-8')).get('packages', [])
    found = [p for p in packages if 'retroarch' in (p.get('id', '') + ' ' + p.get('title', '')).lower()]
    if not found:
        return None
    manifest_url = urllib.parse.urljoin(REPO, found[0]['manifestUrl'])
    manifest = json.loads(get(manifest_url).decode('utf-8'))
    ipk_url = urllib.parse.urljoin(manifest_url, manifest['ipkUrl'])
    path = save(ipk_url, '%s_%s.ipk' % (manifest['id'], manifest.get('version', '')))
    expected = (manifest.get('ipkHash') or {}).get('sha256')
    if expected:
        with open(path, 'rb') as f:
            if hashlib.sha256(f.read()).hexdigest() != expected.lower():
                sys.exit('O RetroArch baixado veio diferente do publicado (sha256 nao bate). Tente de novo mais tarde.')
    return manifest['id'], path, manifest.get('version', '')


def install(ip, key, app_id, ipk):
    temp = TEMP + app_id + '.ipk'
    with open(ipk, 'rb') as f:
        copy = tv.ssh(ip, key, 'mkdir -p ' + TEMP + ' && cat > ' + temp, stdin=f)
    if copy.returncode != 0:
        err = copy.stderr.decode('utf-8', 'replace') if isinstance(copy.stderr, bytes) else copy.stderr
        sys.exit('Nao consegui copiar para a TV: %s\nO Developer Mode ainda esta ligado?' % err.strip())
    print('Instalando na TV (o RetroArch e grande, pode levar alguns minutos)...')
    out = tv.luna(ip, key, 'luna://com.webos.appInstallService/dev/install',
                  {'id': app_id, 'ipkUrl': temp, 'subscribe': True}, replies=60, wait=300)
    tv.ssh(ip, key, 'rm -f ' + temp)
    if '"state":"installed"' not in out:
        sys.exit('A TV nao terminou de instalar %s. Ela respondeu:\n%s' % (app_id, out.strip()))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    ip = args[0]
    key = tv.fetch_key(ip)

    if '--remover' in sys.argv:
        found = retroarch()
        app_id = found[0] if found else 'com.libretro.retroarch'
        out = tv.luna(ip, key, 'luna://com.webos.appInstallService/dev/remove', {'id': app_id}, replies=3, wait=30)
        print('RetroArch removido.' if '"returnValue":true' in out else 'A TV respondeu: ' + out.strip())
        return

    ipk, version = homebrew_channel()
    install(ip, key, HBCHANNEL_ID, ipk)
    print('Homebrew Channel %s instalado.' % version)
    if '--so-homebrew' in sys.argv:
        tv.luna(ip, key, 'luna://com.webos.applicationManager/launch', {'id': HBCHANNEL_ID})
        print('Pronto: o Homebrew Channel esta aberto. Procure RetroArch nele e instale.')
        return

    try:
        found = retroarch()
    except Exception as e:
        found = None
        print('Nao consegui baixar o RetroArch (%s).' % e)
    if not found:
        tv.luna(ip, key, 'luna://com.webos.applicationManager/launch', {'id': HBCHANNEL_ID})
        sys.exit('O Homebrew Channel esta aberto na TV: procure "RetroArch" nele e instale por la.')
    app_id, ipk, version = found
    install(ip, key, app_id, ipk)
    print('RetroArch %s instalado.' % version)
    tv.luna(ip, key, 'luna://com.webos.applicationManager/launch', {'id': app_id})
    print('Pronto: o RetroArch esta aberto na TV.')
    print('Jogos: copie as ROMs num pendrive, ligue na TV e no RetroArch va em Load Content > /tmp/usb.')
    print('Emuladores: no RetroArch, Online Updater > Core Downloader (ex.: Snes9x, Genesis Plus GX, PCSX ReARMed).')


if __name__ == '__main__':
    main()
