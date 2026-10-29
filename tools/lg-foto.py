#!/usr/bin/env python3
"""Mostra uma foto (ou varias, em sequencia) em tela cheia numa TV LG (webOS), pela sua rede.

    python3 lg-foto.py 192.168.15.153 ~/Desktop/familia.jpg
    python3 lg-foto.py 192.168.15.153 ~/Pictures/familia/          # todas as fotos da pasta, trocando a cada 20 s

O Mac serve a foto so na sua rede e abre o navegador da TV nela. Deixe esta janela aberta enquanto quiser as fotos
na TV (com varias fotos, a TV busca a proxima no Mac); Ctrl+C encerra. Usa o lg-youtube.py da mesma pasta para
falar com a TV (a mesma permissao que voce ja aceitou).
"""
import http.server
import importlib.util
import json
import mimetypes
import os
import socket
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
FOTOS = ('.jpg', '.jpeg', '.png', '.heic', '.webp', '.gif')
TROCA = 20   # segundos por foto, quando sao varias

PAGE = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=1920, height=1080"><title>Fotos</title>
<style>
html,body{margin:0;height:100%;background:#000;overflow:hidden;cursor:none}
img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;opacity:0;transition:opacity 1.5s}
img.on{opacity:1}
</style></head><body>
<img id="a"><img id="b">
<script>
var fotos = __FOTOS__, i = 0, cur = 'a';
function show() {
  var next = cur === 'a' ? 'b' : 'a', el = document.getElementById(next);
  el.onload = function () {
    el.className = 'on';
    document.getElementById(cur).className = '';
    cur = next;
  };
  el.src = '/foto/' + i + '?t=' + Date.now();
  i = (i + 1) % fotos.length;
}
show();
if (fotos.length > 1) setInterval(show, __TROCA__ * 1000);
</script></body></html>'''


def load_tv():
    path = os.path.join(HERE, 'lg-youtube.py')
    if not os.path.exists(path):
        sys.exit('Falta o lg-youtube.py nesta pasta (%s).' % HERE)
    spec = importlib.util.spec_from_file_location('lg_youtube', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def photos(target):
    target = os.path.expanduser(target)
    if os.path.isdir(target):
        out = sorted(os.path.join(target, n) for n in os.listdir(target) if n.lower().endswith(FOTOS))
    elif os.path.isfile(target):
        out = [target]
    else:
        sys.exit('Nao achei: %s' % target)
    if not out:
        sys.exit('Nenhuma foto (jpg, png, heic, webp) em %s' % target)
    heic = [p for p in out if p.lower().endswith('.heic')]
    if heic:
        out = convert_heic(out)
    return out


def convert_heic(paths):
    """A TV nao abre HEIC (o formato do iPhone): converte para JPG com o sips do proprio Mac."""
    tmp = os.path.join(os.path.expanduser('~'), '.lg-foto-cache')
    os.makedirs(tmp, exist_ok=True)
    out = []
    for p in paths:
        if p.lower().endswith('.heic'):
            jpg = os.path.join(tmp, os.path.splitext(os.path.basename(p))[0] + '.jpg')
            if not os.path.exists(jpg):
                os.system('sips -s format jpeg "%s" --out "%s" >/dev/null 2>&1' % (p, jpg))
            if os.path.exists(jpg):
                out.append(jpg)
        else:
            out.append(p)
    return out


def my_ip(tv_ip):
    """O IP deste Mac na rede da TV."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((tv_ip, 9))
        return s.getsockname()[0]
    finally:
        s.close()


def serve(files):
    page = PAGE.replace('__FOTOS__', json.dumps([os.path.basename(f) for f in files])).replace('__TROCA__', str(TROCA))

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?')[0]
            if path == '/':
                body, kind = page.encode('utf-8'), 'text/html; charset=utf-8'
            elif path.startswith('/foto/'):
                try:
                    f = files[int(path[6:]) % len(files)]
                except ValueError:
                    return self.send_error(404)
                with open(f, 'rb') as fh:
                    body = fh.read()
                kind = mimetypes.guess_type(f)[0] or 'image/jpeg'
            else:
                return self.send_error(404)
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('0.0.0.0', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    tv_ip, files = sys.argv[1], photos(sys.argv[2])
    tv = load_tv()
    server = serve(files)
    url = 'http://%s:%d/' % (my_ip(tv_ip), server.server_address[1])
    ws = tv.connect(tv_ip)
    tv.register(ws, tv_ip)
    ws.send(json.dumps({'type': 'request', 'id': 'go', 'uri': 'ssap://system.launcher/open', 'payload': {'target': url}}))
    ws.settimeout(15)
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == 'go':
            if msg.get('type') == 'error' or msg.get('payload', {}).get('returnValue') is False:
                sys.exit('A TV nao abriu a pagina: %s' % (msg.get('error') or msg.get('payload')))
            break
    ws.close()
    print('Na TV: %d foto(s). Deixe esta janela aberta; Ctrl+C encerra.' % len(files))
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print()


if __name__ == '__main__':
    main()
