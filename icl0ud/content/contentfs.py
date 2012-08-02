#!/usr/bin/env python

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from decrypt import list_chunks, read_and_decrypt_chunk, size_of_chunk

class ICl0udContent(LoggingMixIn, Operations):
    """iCloud content filesystem. Decrypts files on open."""

    def __init__(self):
        self.files = {}
        self.data = defaultdict(str)
        self.fd = 0
        now = time()
        self.files['/'] = dict(st_mode=(S_IFDIR | 0555),
                               st_ctime=now,
                               st_mtime=now,
                               st_atime=now, st_nlink=2)

    def getattr(self, path, fh=None):
        if path == '/':
            return self.files[path]
        path = path[1:]
        if len(path) == 42:
            # not sure whether the decrypted size equals the encrypted
            # at least doesn't hurt for JPEG images
            size = size_of_chunk(path.decode('hex'))
            return dict(st_mode=(S_IFREG | 0444),
                        st_nlink=1,
                        st_size=size,
                        st_ctime=time(),
                        st_mtime=time(),
                        st_atime=time())
        else:
            print len(path)
            raise FuseOSError(ENOENT)

    def open(self, path, flags):
        if(len(path) == 43):
            self.data[path] = read_and_decrypt_chunk(path[1:].decode('hex'))
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        return self.data[path][offset:offset + size]

    def readdir(self, path, fh):
        checksums = list_chunks()
        chunk_names = [sum.encode('hex') for sum in checksums]
        return ['.', '..'] + chunk_names

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime


if __name__ == "__main__":
    if len(argv) != 2:
        print 'usage: %s <mountpoint>' % argv[0]
        exit(1)
    fuse = FUSE(ICl0udContent(), argv[1], foreground=True)
