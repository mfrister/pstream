# from http://passingcuriosity.com/2009/aes-encryption-in-python-with-m2crypto/
from base64 import b64encode, b64decode
from M2Crypto.EVP import Cipher

__all__ = ['encryptor', 'decryptor']

ENC=1
DEC=0

def build_cipher(key, iv, op=ENC):
    return Cipher(alg='aes_128_cfb', key=key, iv=iv, op=op)

def encryptor(key, iv=None):
    if iv is None:
        iv = '\0' * 16

   # Return the encryption function
    def encrypt(data):
        cipher = build_cipher(key, iv, ENC)
        v = cipher.update(data)
        v = v + cipher.final()
        del cipher
        v = b64encode(v)
        return v
    return encrypt

def decryptor(key, iv=None):
    if iv is None:
        iv = '\0' * 16

   # Return the decryption function
    def decrypt(data):
        # data = b64decode(data)
        cipher = build_cipher(key, iv, DEC)
        v = cipher.update(data)
        v = v + cipher.final()
        del cipher
        return v
    return decrypt