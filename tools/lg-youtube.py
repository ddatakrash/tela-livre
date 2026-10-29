#!/usr/bin/env python3
"""Abre o YouTube numa TV LG (webOS) pela rede.

    python3 tools/lg-youtube.py 192.168.15.153            # abre o YouTube
    python3 tools/lg-youtube.py 192.168.15.153 netflix    # outro app (id do webOS)

Na primeira vez a TV mostra um aviso pedindo permissao: aceite com o controle. A chave fica em ~/.lg-tv-key.
So usa o Python padrao: nada para instalar.
"""
import base64
import json
import os
import socket
import ssl
import struct
import sys


class WebSocket:
    """O minimo de WebSocket (RFC 6455) para falar com a TV: texto, sem fragmentos grandes."""

    def __init__(self, sock, host):
        self.sock = sock
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall(('GET / HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (host, key)).encode())
        head = b''
        while b'\r\n\r\n' not in head:
            chunk = sock.recv(1)
            if not chunk:
                raise IOError('a TV fechou a conexao')
            head += chunk
        if b' 101 ' not in head.split(b'\r\n')[0]:
            raise IOError('a TV recusou a conexao: %r' % head.split(b'\r\n')[0])

    def settimeout(self, t):
        self.sock.settimeout(t)

    def send(self, text):
        data = text.encode('utf-8')
        n = len(data)
        head = bytes([0x81])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack('>H', n)
        else:
            head += bytes([0x80 | 127]) + struct.pack('>Q', n)
        mask = os.urandom(4)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        out = b''
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise IOError('a TV fechou a conexao')
            out += chunk
        return out

    def recv(self):
        message = b''
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._read(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            op = b1 & 0x0F
            if op == 8:
                raise IOError('a TV fechou a conexao')
            if op == 9:   # ping: responde pong
                self.sock.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
                continue
            if op in (0, 1, 2):
                message += data
                if b1 & 0x80:
                    return message.decode('utf-8')

    def close(self):
        try:
            self.sock.sendall(bytes([0x88, 0x80]) + os.urandom(4))
        except OSError:
            pass
        self.sock.close()

KEY_FILE = os.path.expanduser('~/.lg-tv-key')
APPS = {'youtube': 'youtube.leanback.v4', 'netflix': 'netflix', 'prime': 'amazon', 'globoplay': 'globoplay'}


def connect(ip):
    """webOS 6 pede wss na 3001 (certificado proprio da TV, sem como verificar); as mais antigas, ws na 3000."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        raw = socket.create_connection((ip, 3001), timeout=10)
        return WebSocket(ctx.wrap_socket(raw, server_hostname=ip), '%s:3001' % ip)
    except (OSError, ssl.SSLError):
        return WebSocket(socket.create_connection((ip, 3000), timeout=10), '%s:3000' % ip)


def register(ws, ip):
    keys = {}
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE) as f:
            keys = json.load(f)
    payload = {'forcePairing': False, 'pairingType': 'PROMPT',
               'manifest': {'manifestVersion': 1, 'appVersion': '1.0',
                            'signed': {'appId': 'com.telalivre.remote', 'vendorId': 'telalivre'},
                            'permissions': ['LAUNCH', 'LAUNCH_WEBAPP', 'APP_TO_APP', 'READ_INSTALLED_APPS']}}
    if ip in keys:
        payload['client-key'] = keys[ip]
    ws.send(json.dumps({'type': 'register', 'id': 'reg', 'payload': payload}))
    ws.settimeout(60)   # tempo para aceitar o aviso na TV
    while True:
        msg = json.loads(ws.recv())
        if msg.get('type') == 'response' and msg.get('payload', {}).get('pairingType') == 'PROMPT':
            print('Olhe a TV e aceite o aviso com o controle...')
        elif msg.get('type') == 'registered':
            keys[ip] = msg['payload']['client-key']
            with open(KEY_FILE, 'w') as f:
                json.dump(keys, f)
            return
        elif msg.get('type') == 'error':
            sys.exit('A TV recusou: %s' % msg.get('error'))


def launch(ws, app_id):
    ws.send(json.dumps({'type': 'request', 'id': 'go', 'uri': 'ssap://system.launcher/launch',
                        'payload': {'id': app_id}}))
    ws.settimeout(15)
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == 'go':
            if msg.get('type') == 'error' or msg.get('payload', {}).get('returnValue') is False:
                sys.exit('Nao abriu: %s' % (msg.get('error') or msg.get('payload')))
            return


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ip = sys.argv[1]
    app = sys.argv[2] if len(sys.argv) > 2 else 'youtube'
    ws = connect(ip)
    register(ws, ip)
    launch(ws, APPS.get(app, app))
    ws.close()
    print('Pronto: %s aberto na TV.' % app)


if __name__ == '__main__':
    main()
