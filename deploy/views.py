# Django libraries
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.utils.encoding import force_bytes

from auto_deploy_github.settings import *
from pathlib import Path
from hashlib import sha1
import requests
import json
import ipaddress
import git
import getpass
import hmac
import subprocess

from http import HTTPStatus

@require_POST
@csrf_exempt
def AutoDeploy(request):

    ip = get_client_ip(request)

    ips = requests.get(
        'https://api.github.com/meta',
    ).json()

    is_valid_ip = False
    for hook_ip in ips['hooks']:
        if ipaddress.ip_address(ip) in ipaddress.ip_network(hook_ip):
            is_valid_ip = True
            break

    if not is_valid_ip:
        send_deploy_email(
            'Deploy git ejemplo (invalid ip)',
            f"From ip: {ip}",
        )
        return HttpResponseForbidden('Permission denied.')

    # Verify the request signature
    header_signature = request.headers['X-Hub-Signature']
    if header_signature is None:
        return HttpResponseForbidden('Permission denied. (invalid signature)')

    sha_name, signature = header_signature.split('=')
    if sha_name != 'sha1':
        return HttpResponseServerError('Operation not supported.', status=501)

    mac = hmac.new(force_bytes(GIT_KEY), msg=force_bytes(request.body), digestmod=sha1)
    if not hmac.compare_digest(force_bytes(mac.hexdigest()), force_bytes(signature)):
        send_deploy_email(
            'Deploy git ejemplo (invalid secret)',
            f"From ip: {ip}",
        )
        return HttpResponseForbidden(f'Permission denied.')
    

    g = git.cmd.Git(BASE_DIR)
    res = g.pull()

    command = f'./sincro_require_ddbb.sh'
    process = subprocess.Popen(command.split(), cwd=BASE_DIR, stdout=subprocess.PIPE)
    output, error = process.communicate()

    result = [];
    if output is not None:
        result.append(output.decode('utf-8'))
    if error is not None:
        result.append(error.decode('utf-8'))

    mig_and_req = '\n'.join(result)

    send_deploy_email(
        'Deploy git ejemplo',
        f"From ip: {ip}\nResult git: \n{res}\nResult migrations and requirements: \n{mig_and_req}",
    )
    touch = Path(f'{BASE_DIR}/auto_deploy_github/wsgi.py').touch()

    return HttpResponse('The proccess has been done succesfully.')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def send_deploy_email(subject, body):

    from_email = 'no-reply@ejemplo.com'
    if(getpass.getuser() != 'www-data'):
        from_email = 'no-reply@ejemplo.local'

    send_mail(
        subject,
        body,
        from_email,
        ['ejemplo@gmail.com'],
        fail_silently=False,
    )