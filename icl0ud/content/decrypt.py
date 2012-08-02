import os
import sys
from os.path import dirname, join, realpath

__all__ = ['read_and_decrypt_chunk', 'list_chunks']

icl0udPath = realpath(join(dirname(realpath(__file__)), '../..'))
sys.path.append(icl0udPath)

from aes import decryptor as create_decryptor
# http://stackoverflow.com/questions/8608731/pycrypto-compatibility-with-commoncrypto-in-cfb-mode

from icl0ud.utils.datastore import DataStore
from settings.development import *
DataStore.pickleFile = os.path.join(DATA_PATH, 'dataStores.pickle')
DataStore.storagePath = os.path.join(DATA_PATH, 'storage')
DataStore.readFromDisk()


def list_chunks():
    return DataStore.content['storageTokens'].keys()

def size_of_chunk(checksum):
    return DataStore.content['metadata'][checksum]['size']

def read_and_decrypt_chunk(checksum):
    metadata = DataStore.content['metadata'][checksum]
    storageToken, begin = DataStore.content['storageTokens'][checksum]
    fp = open(join(DataStore.storagePath, storageToken), 'rb')
    fp.seek(begin, os.SEEK_SET)
    content = fp.read(metadata['size'])
    fp.close()

    aes_key = metadata['bytes17'][1:]

    decryptor = create_decryptor(aes_key)
    return decryptor(content)

