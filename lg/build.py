#!/usr/bin/env python3
"""Monta o Tela Livre para TVs LG (webOS): TelaLivre-lg.ipk, o pacote que o Developer Mode da TV instala.

    python3 lg/build.py              # baixa paisagens novas e monta o pacote
    python3 lg/build.py --preview    # tambem deixa os arquivos em out/lg/ para abrir index.html num navegador

As fotos de fundo: se existir a pasta fundos/ na raiz do projeto, usa as suas (jpg ou png). Senao, baixa as
paisagens mais recentes do Bing (as fotos do dia) e guarda em lg/.fundos-cache, para a proxima montagem nao
depender da internet. A cidade e os apps de baixo ficam em lg/config.json.
Empacota como o ares-package da LG (um ar com control.tar.gz e data.tar.gz), sem ferramentas da LG. So Python 3.
"""
import io
import json
import os
import shutil
import ssl
import sys
import tarfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LG = os.path.join(ROOT, 'lg')
IPK = os.path.join(ROOT, 'TelaLivre-lg.ipk')
OUT = os.path.join(ROOT, 'out', 'lg')
CACHE = os.path.join(LG, '.fundos-cache')
MINE = os.path.join(ROOT, 'fundos')
BING = 'https://www.bing.com/HPImageArchive.aspx?format=js&idx=%d&n=8&mkt=pt-BR'
SYMBOLS = ('hdmi', 'settings', 'apps', 'live_tv', 'sunny', 'clear_night', 'partly_cloudy_day', 'partly_cloudy_night',
           'cloud', 'foggy', 'rainy', 'thunderstorm', 'snowflake')
LOGOS = ('youtube.png', 'netflix.svg', 'prime.png')


def https():
    """O Python do python.org no Mac vem sem certificados: usa os do certifi quando existem."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def photos():
    """As fotos de fundo: {nome no app: bytes}."""
    if os.path.isdir(MINE):
        names = sorted(n for n in os.listdir(MINE) if n.lower().endswith(('.jpg', '.jpeg', '.png')))
        if names:
            print('Fundos: %d foto(s) da sua pasta fundos/' % len(names))
            return {'fundos/%02d%s' % (i, os.path.splitext(n)[1].lower()): open(os.path.join(MINE, n), 'rb').read()
                    for i, n in enumerate(names)}
    got = {}
    try:
        ctx = https()
        urls = []
        for idx in (0, 8):
            with urllib.request.urlopen(BING % idx, timeout=20, context=ctx) as r:
                for img in json.loads(r.read().decode('utf-8')).get('images', []):
                    if img.get('urlbase'):
                        urls.append('https://www.bing.com%s_1920x1080.jpg' % img['urlbase'])
        for i, url in enumerate(dict.fromkeys(urls)):
            with urllib.request.urlopen(url, timeout=30, context=ctx) as r:
                got['fundos/%02d.jpg' % i] = r.read()
    except Exception as e:
        print('Nao consegui baixar paisagens novas (%s).' % e)
    if got:
        shutil.rmtree(CACHE, ignore_errors=True)
        os.makedirs(CACHE)
        for name, data in got.items():
            with open(os.path.join(CACHE, os.path.basename(name)), 'wb') as f:
                f.write(data)
        print('Fundos: %d paisagens baixadas' % len(got))
        return got
    if os.path.isdir(CACHE):
        old = {'fundos/' + n: open(os.path.join(CACHE, n), 'rb').read() for n in sorted(os.listdir(CACHE))}
        if old:
            print('Fundos: %d paisagens da ultima vez' % len(old))
            return old
    print('Fundos: nenhum (fica um degrade azul)')
    return {}


def app_files():
    """{caminho dentro do app: bytes}."""
    out = {}
    web = os.path.join(LG, 'web')
    for name in sorted(os.listdir(web)):
        with open(os.path.join(web, name), 'rb') as f:
            out[name] = f.read()
    for name in ('appinfo.json', 'icon.png', 'largeIcon.png'):
        with open(os.path.join(LG, name), 'rb') as f:
            out[name] = f.read()
    for s in SYMBOLS:
        with open(os.path.join(ROOT, 'assets', 'symbols', s + '.png'), 'rb') as f:
            out['symbols/%s.png' % s] = f.read()
    for name in LOGOS:
        with open(os.path.join(ROOT, 'web', 'icons', name), 'rb') as f:
            out['icons/' + name] = f.read()
    for name in ('InterVariable.ttf', 'OFL.txt'):
        with open(os.path.join(ROOT, 'assets', 'fonts', name), 'rb') as f:
            out['fonts/' + name] = f.read()
    with open(os.path.join(LG, 'config.json'), encoding='utf-8') as f:
        config = json.load(f)
    fundos = photos()
    out.update(fundos)
    config['photos'] = sorted(fundos)
    out['config.js'] = ('/* Gerado por lg/build.py a partir de lg/config.json. */\nwindow.CONFIG = %s;\n'
                        % json.dumps(config, ensure_ascii=False)).encode('utf-8')
    return out


def tar_gz(entries):
    """Um .tar.gz de [(nome, bytes ou None para pasta)], do root, como o ares-package faz."""
    buf = io.BytesIO()
    now = int(time.time())
    with tarfile.open(fileobj=buf, mode='w:gz', format=tarfile.PAX_FORMAT) as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.mtime = now
            info.uid = info.gid = 0
            if data is None:
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            else:
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def ar(members):
    out = io.BytesIO()
    out.write(b'!<arch>\n')
    now = int(time.time())
    for name, data in members:
        out.write(('%-16s%-12d%-6d%-6d%-8s%-10d`\n' % (name, now, 0, 0, '100644', len(data))).encode('ascii'))
        out.write(data)
        if len(data) % 2:
            out.write(b'\n')
    return out.getvalue()


def build(preview):
    with open(os.path.join(LG, 'appinfo.json'), encoding='utf-8') as f:
        info = json.load(f)
    app_id, version = info['id'], info['version']
    app = app_files()

    base = 'usr/palm/applications/' + app_id
    entries = [('usr', None), ('usr/palm', None), ('usr/palm/applications', None), (base, None)]
    dirs = set()
    for path in sorted(app):
        parent = os.path.dirname(path)
        if parent and parent not in dirs:
            dirs.add(parent)
            entries.append((base + '/' + parent, None))
        entries.append((base + '/' + path, app[path]))
    # O servico JS que alcanca a API de controle remoto da TV quando a origem da pagina e recusada (webOS 6+).
    service_id = app_id + '.service'
    with open(os.path.join(LG, 'service', 'service.js'), 'rb') as f:
        service = {'service.js': f.read(),
                   'package.json': json.dumps({'name': service_id, 'version': version, 'main': 'service.js'},
                                              indent=2).encode('utf-8'),
                   'services.json': json.dumps({'id': service_id, 'description': 'Tela Livre',
                                                'services': [{'name': service_id, 'description': 'Tela Livre'}]},
                                               indent=2).encode('utf-8')}
    service_base = 'usr/palm/services/' + service_id
    entries += [('usr/palm/services', None), (service_base, None)]
    entries += [(service_base + '/' + name, service[name]) for name in sorted(service)]

    package = json.dumps({'id': app_id, 'version': version, 'app': app_id, 'services': [service_id]},
                         indent=2).encode('utf-8')
    entries += [('usr/palm/packages', None), ('usr/palm/packages/' + app_id, None),
                ('usr/palm/packages/' + app_id + '/packageinfo.json', package)]

    size = sum(len(d) for d in app.values()) + sum(len(d) for d in service.values()) + len(package)
    control = ('Package: %s\nVersion: %s\nSection: misc\nPriority: optional\nArchitecture: all\nInstalled-Size: %d\n'
               'Maintainer: Tela Livre\nDescription: Tela inicial sem anuncios.\n'
               'webOS-Package-Format-Version: 2\nwebOS-Packager-Version: 1.0.0\n' % (app_id, version, size))
    data = ar([('debian-binary', b'2.0\n'), ('control.tar.gz', tar_gz([('control', control.encode('utf-8'))])),
               ('data.tar.gz', tar_gz(entries))])
    with open(IPK, 'wb') as f:
        f.write(data)

    if preview:
        shutil.rmtree(OUT, ignore_errors=True)
        for path, content in app.items():
            target = os.path.join(OUT, path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(content)
        print('Previa: abra out/lg/index.html num navegador.')
    print('Montado %s (%s %s, %d KB)' % (os.path.basename(IPK), app_id, version, len(data) // 1024))


if __name__ == '__main__':
    build('--preview' in sys.argv)
