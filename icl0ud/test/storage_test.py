import os
from tempfile import mkdtemp

from twisted.internet import interfaces, reactor, protocol, address
from twisted.trial import unittest

from icl0ud import storage
from icl0ud.utils.test import DummyRequest, render
from icl0ud.utils.datastore import DataStore


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.token = 'deadbeef'
        self.tmpdir = mkdtemp()
        DataStore.storagePath = self.tmpdir
        self.request = DummyRequest([''])
        self.request.setRequestHeader('Storage-Token', self.token)

    def tearDown(self):
        try:
            os.remove(os.path.join(self.tmpdir, self.token))
        except OSError:
            pass
        os.rmdir(self.tmpdir)

    def test_storage_put(self):
        request = self.request
        request.method = 'PUT'
        request.setContent('BLOB')
        resource = storage.StoragePut('123')
        d = render(resource, request)
        def rendered(ignored):
            self.assertEquals(request.code, 200)
            self.assertEquals(len(request.written_as_string), 0)
            # FIXME ensure file exists
        d.addCallback(rendered)
        return d

    def executeRequest(self, resource, callback):
        d = render(resource, self.request)
        d.addCallback(callback)
        return d

    def setUpStorageBlob(self):
        f=open(os.path.join(self.tmpdir, self.token), 'w')
        f.write('BLOB')
        f.close()

    def tstStorageRangeGet(self, range, expected):
        self.setUpStorageBlob()
        request = self.request
        self.request.setRequestHeader('Range', range)

        def rendered(ignored):
            self.assertEquals(request.code, 200)
            self.assertEquals(request.written_as_string, expected)
        return self.executeRequest(storage.StorageGet('123'), rendered)

    def test_storage_get_range_full(self):
        self.tstStorageRangeGet('bytes=0-4', 'BLOB')

    def test_storage_get_range_1_3(self):
        self.tstStorageRangeGet('bytes=1-3', 'LO')

