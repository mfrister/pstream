from os import path

from twisted.python import log
from twisted.protocols.basic import FileSender
from twisted.web.server import NOT_DONE_YET

from utils.datastore import DataStore
from utils.helpers import http403, http404
from utils.storage_helpers import FileRangeSender
from icl0ud.streams.helpers import AppleIdResource, TreeNode


class StorageResource(AppleIdResource):
    def isValidStorageToken(self, token):
        # TODO check length
        try:
            token.decode('hex')
        except TypeError:
            log.err('Storage: Got non-hex Storage-Token: "%s"' % token)
            return False
        return True

    def storageTokenForRequest(self, request):
        storageToken = request.requestHeaders.getRawHeaders('Storage-Token')[0]
        if not self.isValidStorageToken(storageToken):
            return None
        return storageToken

class StorageGet(StorageResource):
    def render_GET(self, request):
        storageToken = self.storageTokenForRequest(request)
        if not storageToken:
            return http403(request)
        log.msg("Storage GET: " + storageToken)

        # get Range header, remove leading bytes=
        range = request.requestHeaders.getRawHeaders('Range')[0][6:]
        rangeBegin, rangeEnd = range.split('-')

        try:
            fp = open(path.join(DataStore.storagePath, storageToken), 'rb')
        except IOError, e:
            if e.errno == 2:
                log.err('Storage GET: Not found: ' + storageToken)
                return http404(request)
            raise e
        d = FileRangeSender().beginFileTransfer(fp,
                                                request,
                                                int(rangeBegin),
                                                int(rangeEnd))
        def cbFinished(ignored):
            fp.close()
            request.finish()
        d.addErrback(log.err).addCallback(cbFinished)

        return NOT_DONE_YET


class StoragePut(StorageResource):
    copyBufSize = 2**14 # 16k
    # TODO don't unnecessarily copy tempfile
    #  - replace Site.requestFactory, see http://twistedmatrix.com/trac/browser/trunk/twisted/web/server.py#L465
    #  - overwrite Request.gotLength, see http://twistedmatrix.com/trac/browser/trunk/twisted/web/http.py#L664
    def render_PUT(self, request):
        storageToken = self.storageTokenForRequest(request)
        if not storageToken:
            return http403(request)
        log.msg("Storage PUT: " + storageToken)

        target = open(path.join(DataStore.storagePath, storageToken), 'wb')
        while True:
            buf = request.content.read(self.copyBufSize)
            if not buf:
                break
            target.write(buf)

        target.close()
        return ''


class Storage(TreeNode):
    childMapping = {
        'get': StorageGet,
        'put': StoragePut,
    }
