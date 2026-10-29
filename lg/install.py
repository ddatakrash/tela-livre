#!/usr/bin/env python3
"""Instala o Tela Livre numa TV LG em Developer Mode, pelo Wi-Fi. Adaptado do webos/install.py do Free My TV (MIT).

    python3 lg/install.py 192.168.15.153              # instala ou atualiza, e abre
    python3 lg/install.py 192.168.15.153 --uninstall  # remove

Before the first install, on the TV: install "Developer Mode" from the LG Content Store, sign in with a free LG
developer account (webostv.developer.lge.com), turn on Dev Mode Status (the TV restarts), then turn on Key Server.
The app shows the TV's IP address and a passphrase.

The first time, this downloads the TV's key from its Key Server and asks for that passphrase (type it here; it is
not stored). The unlocked key is kept in ~/.ssh/telalivre_lg_<IP>, so updates need neither. The app is copied over
SSH (port 9922) and installed with the TV's own installer (com.webos.appInstallService), the way LG's tools do it.
Install flow based on FreeMyTvWebOS by danielthejoker18 (MIT). Needs Python 3 and OpenSSH (ssh, ssh-keygen).
"""
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPK = os.path.join(ROOT, 'TelaLivre-lg.ipk')
with open(os.path.join(ROOT, 'lg', 'appinfo.json'), encoding='utf-8') as f:
    APP_ID = json.load(f)['id']
TEMP = '/media/developer/temp/telalivre.ipk'
SSH_OPTS = ['-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=' + os.devnull, '-o', 'LogLevel=ERROR',
            '-o', 'HostKeyAlgorithms=+ssh-rsa', '-o', 'PubkeyAcceptedKeyTypes=+ssh-rsa', '-p', '9922']


def key_path(ip):
    return os.path.join(os.path.expanduser('~'), '.ssh', 'telalivre_lg_' + ip.replace('.', '_'))


def lock(path):
    """Only this user may read the key: chmod is enough on macOS and Linux, Windows' OpenSSH checks the file's ACL."""
    os.chmod(path, 0o600)
    if os.name != 'nt':
        return
    # By SID, not name: a domain PC that lost its trust with the domain can't resolve names. As bytes: whoami writes in
    # the console's code page, which a user name with accents may not decode from.
    out = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'], capture_output=True).stdout
    sid = re.search(rb'S-1-[0-9-]+', out)
    if sid:
        subprocess.run(['icacls', path, '/inheritance:r', '/grant:r', '*%s:F' % sid.group().decode()], capture_output=True)


def fetch_key(ip):
    """The TV's SSH key from its Key Server, unlocked with the passphrase the TV shows."""
    path = key_path(ip)
    if os.path.exists(path):
        return path
    url = 'http://%s:9991/webos_rsa' % ip
    print('Pegando a chave da TV em %s ...' % url)
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            data = r.read()
    except Exception as e:
        sys.exit('Nao consegui falar com o Key Server da TV (%s). No app Developer Mode da TV, ligue o Key Server.' % e)
    passphrase = getpass.getpass('Passphrase que aparece no Developer Mode da TV: ').strip()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(data)
    tmp.close()
    lock(tmp.name)
    unlock = subprocess.run(['ssh-keygen', '-p', '-P', passphrase, '-N', '', '-f', tmp.name], capture_output=True, text=True)
    if unlock.returncode != 0:
        os.unlink(tmp.name)
        # ssh-keygen's last line says why: a wrong passphrase, or a key file others can read ("bad permissions").
        reason = (unlock.stderr.strip().splitlines() or [''])[-1]
        sys.exit('Essa passphrase nao abriu a chave (%s). Confira no Developer Mode da TV e tente de novo.' % reason)
    shutil.move(tmp.name, path)
    lock(path)
    return path


def ssh(ip, key, command, stdin=None, tty=False):
    args = ['ssh'] + (['-tt'] if tty else []) + SSH_OPTS + ['-i', key, 'prisoner@' + ip, command]
    return subprocess.run(args, stdin=stdin, capture_output=True, text=stdin is None)


def luna(ip, key, uri, payload, replies=1, wait=20):
    # luna-send-pub prints nothing without a terminal (-tt), and the installer streams several replies.
    # Older webOS ships BusyBox before 1.30, whose timeout only takes -t SECS.
    # Some (webOS 6) refuse the terminal; there -i streams the replies without one, until the timeout.
    timeout = "if timeout -t 1 true 2>/dev/null; then T='timeout -t %d'; else T='timeout %d'; fi; " % (wait, wait)
    message = "%s '%s'" % (uri, json.dumps(payload, separators=(',', ':')))
    out = ssh(ip, key, timeout + '$T luna-send-pub -n %d %s' % (replies, message), tty=True).stdout or ''
    if not out.strip():
        out = ssh(ip, key, timeout + '$T luna-send-pub -i %s </dev/null' % message).stdout or ''
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args or not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', args[0]):
        sys.exit(__doc__)
    ip = args[0]
    if not shutil.which('ssh') or not shutil.which('ssh-keygen'):
        sys.exit('Precisa do OpenSSH (ssh e ssh-keygen).')
    key = fetch_key(ip)

    if '--uninstall' in sys.argv:
        out = luna(ip, key, 'luna://com.webos.appInstallService/dev/remove', {'id': APP_ID}, replies=3, wait=30)
        print('Removido.' if '"returnValue":true' in out else 'A TV respondeu: ' + out.strip())
        return

    if not os.path.exists(IPK):
        subprocess.run([sys.executable, os.path.join(ROOT, 'lg', 'build.py')], check=True)
    print('Copiando o app para a TV...')
    with open(IPK, 'rb') as f:
        copy = ssh(ip, key, 'mkdir -p /media/developer/temp && cat > ' + TEMP, stdin=f)
    if copy.returncode != 0:
        err = copy.stderr.decode('utf-8', 'replace') if isinstance(copy.stderr, bytes) else copy.stderr
        sys.exit('Nao consegui copiar: %s\nO Developer Mode ainda esta ligado? Se a chave mudou, apague %s e tente de novo.' % (err.strip(), key))
    print('Instalando...')
    out = luna(ip, key, 'luna://com.webos.appInstallService/dev/install', {'id': APP_ID, 'ipkUrl': TEMP, 'subscribe': True},
               replies=30, wait=60)
    if '"state":"installed"' not in out:
        sys.exit('A TV nao terminou de instalar. Ela respondeu:\n' + out.strip())
    ssh(ip, key, 'rm -f ' + TEMP)
    luna(ip, key, 'luna://com.webos.applicationManager/launch', {'id': APP_ID})
    print('Instalado e aberto na TV.')
    print('Dica: com o Tela Livre aberto, segure um numero no controle para abri-lo com esse numero de qualquer lugar.')
    print('O Developer Mode dura um tempo limitado: de vez em quando abra o app Developer Mode e aperte EXTEND.')


if __name__ == '__main__':
    main()
