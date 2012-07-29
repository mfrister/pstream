import os
from os.path import abspath, dirname, join

ENABLE_SSL = True
LISTEN_PORT = 443
LISTEN_HOST = '0.0.0.0'
APP_PATH = dirname(dirname(abspath(__file__)))
SERVER_KEY_PATH = join(APP_PATH, 'certs', 'icloud.com.key')
SERVER_CERT_PATH = join(APP_PATH, 'certs', 'icloud.com.crt')
DATA_PATH = join(APP_PATH, 'data')
