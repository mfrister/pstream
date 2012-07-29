import shutil
import tempfile
import types
from plistlib import writePlistToString
from pprint import pformat
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from mock import Mock
from twisted.internet.defer import inlineCallbacks, succeed
from twisted.trial import unittest
from twisted.spread.pb import RemoteReference
from twisted.web import http_headers, server
from twisted.web.resource import getChildForRequest
from twisted.web.test import test_web

from icl0ud import config
from icl0ud.streams.core import PushService
from icl0ud.utils.datastore import DataStore
from icl0ud.streams.helpers import decode_plist, decode_chunked_plists

# adapted from https://github.com/nkvoll/Piped/blob/528f93faf65d1512591dd6b55631dc9b3b97b89e/piped/providers/web_provider.py#L159
class DummyRequest(test_web.DummyRequest, server.Request):
    def __init__(self, *a, **kw):
        test_web.DummyRequest.__init__(self, *a, **kw)
        self.requestHeaders = http_headers.Headers()
        self.responseHeaders = http_headers.Headers()
        self.content = StringIO()

    def getHeader(self, key):
        "Get request header with name key"
        return self.requestHeaders.getRawHeaders(key)[0]

    def setRequestHeader(self, name, value):
        return self.requestHeaders.setRawHeaders(name, [value])

    def setRequestHeaders(self, headers_dict):
        for key, value in headers_dict.iteritems():
            self.setRequestHeader(key, value)

    def setHeader(self, name, value):
        self.responseHeaders.setRawHeaders(name, [value])

    def setContent(self, content):
        if not hasattr(content, 'read'):
            self.content = StringIO(content)
        else:
            self.content = content

    def setResponseCode(self, code, message=None):
        server.Request.setResponseCode(self, code, message)

    @property
    def written_as_string(self):
        return ''.join(self.written)


# from http://stackoverflow.com/questions/5210889/how-to-test-twisted-web-resource-with-trial
def render(root, request):
    resource = getChildForRequest(root, request)
    result = resource.render(request)
    if isinstance(result, str):
        request.write(result)
        request.finish()
        return succeed(None)
    elif result is server.NOT_DONE_YET:
        if request.finished:
            return succeed(None)
        else:
            return request.notifyFinish()
    else:
        raise ValueError("Unexpected return value: %r" % (result,))


class MitmTestCase(unittest.TestCase):
    disabled_methods = []
    def disable_method(self, method):
        """
            Disable bound method, will be reenabled on teardown.
        """
        def stub(*args, **kwargs):
            pass
        obj = method.im_self
        name = method.__name__
        setattr(obj, name, types.MethodType(stub, obj, type(obj)))
        self.disabled_methods.append((obj, name, method))

    def enable_methods(self):
        for obj, method_name, original in self.disabled_methods:
            setattr(obj, method_name, original)

    def setUp(self):
        self._data_path = tempfile.mkdtemp()
        config.DATA_PATH = self._data_path
        for method in (DataStore.readFromDisk, DataStore.writeToDisk):
            self.disable_method(method)
        DataStore.init()

    def tearDown(self):
        self.enable_methods()
        shutil.rmtree(self._data_path)

    def build_request(self, path, method, headers, content):
        request = DummyRequest(path.split('/'))
        request.method = method
        request.setContent(content)
        request.setRequestHeaders(headers)
        return request

    @inlineCallbacks
    def render(self, request):
        yield render(self.resource, request)

    def check_response(self, request, code, headers, content):
        self.assertEquals(request.code, code)

        response_headers = {}
        for name, value in request.responseHeaders.getAllRawHeaders():
            response_headers[name] = value[0]
        self.assertEqual(response_headers, headers)

        self.assertEquals(request.written_as_string, content)


class StreamsTestCase(MitmTestCase):
    def setUp(self):
        super(StreamsTestCase, self).setUp()
        from icl0ud.routes import ServiceRoot
        self.resource = ServiceRoot()
        PushService.remote = Mock(RemoteReference, name='push_service')

    def build_request(self, path, method, headers, content):
        content = writePlistToString(content)
        request = super(StreamsTestCase, self) \
                .build_request(path, method, headers, content)
        return request

    @inlineCallbacks
    def render(self, request):
        yield super(StreamsTestCase, self).render(request)
        self.decode_response(request)

    def decode_response(self, request):
        response = request.written_as_string

        if request.prepath[-2:] == ['streams', 'getmetadata']:
            request.written_as_string = decode_chunked_plists(response)
        else:
            request.written_as_string = decode_plist(response)

    def assert_subset(self, superset, subset):
        "Assert subset is a subset of the superset"
        result = all(item in superset.items()
                            for item in subset.items())
        if not result:
            raise AssertionError('first dict is not subset of second: \n' +
                                 pformat(subset) + '\n' + pformat(superset))

    def assert_push_notifications(self, device, count = 1):
        device = device.decode('hex')
        topic = '45d4a8f8d83fdc7ba96233018fe1aa475fbccd6e'.decode('hex')

        from icl0ud.streams.core import PushService
        remote_mock = PushService.remote.callRemote
        self.assertEquals(remote_mock.call_count, count)
        self.assertEquals(remote_mock.call_args,
            (('sendNotification', device, topic, '{"r":"123456"}'),))
