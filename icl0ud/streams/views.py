from plistlib import readPlist, writePlistToString
from pprint import pformat

from twisted.python import log

from .core import ContentTokenGenerator, Stream, SyncToken
from .helpers import AppleIdResource, hexMultipartEncode, objects_to_plists


UDID_HEADER = 'x-apple-mme-streams-client-udid'
PUSH_TOKEN_HEADER = 'x-apple-mme-streams-client-token'

class StreamHandler(AppleIdResource):
    config_version = '3'
    def render_POST(self, request):
        stream = Stream(self.appleId)
        self.update_push_token(stream, request.requestHeaders)

        request_plist = readPlist(request.content)
        self.log_obj(request_plist, 'request')

        self.set_response_headers(request)

        return self.handle_request(request, request_plist, stream)

    def update_push_token(self, stream, headers):
        try:
            udid = headers.getRawHeaders(UDID_HEADER)[0]
            token = headers.getRawHeaders(PUSH_TOKEN_HEADER)[0]
            # TODO remove token from list if push notification service
            # has no device with this token
            stream.update_push_token(udid, token)
            log.msg('Device Push Token updated: %s for device %s'
                    % (token, udid))
        except TypeError:
            log.err('update_push_token: Header missing: %s or %s' %
                    (UDID_HEADER, PUSH_TOKEN_HEADER))

    def set_response_headers(self, request):
        """Set the config version header, otherwise clients do not request
        the configuration at all."""

        # force lower-case
        request.responseHeaders._caseMappings \
            ['x-apple-mme-streams-config-version'] = \
                'x-apple-mme-streams-config-version'
        request.setHeader('x-apple-mme-streams-config-version',
                          self.config_version)

    def log_obj(self, obj, comment):
        log.msg('%s %s' % (self.__class__.__name__, comment))
        log.msg(pformat(obj))

    def log_response(self, obj):
        self.log_obj(obj, 'response')


class StreamConfiguration(StreamHandler):
    configuration = {'mme.streams.application.apiVersion': '1.2',
                     'mme.streams.application.configVersion': '3',
                     'mme.streams.client.maxAssetsToDisplay': '2000',
                     'mme.streams.client.pubMaxUploadBatchCount': '1',
                     'supportedAssets': [{'assetType': 'public.tiff',
                                          'maxFileSizeMB': '100'},
                                         {'assetType': 'public.jpeg',
                                          'maxFileSizeMB': '50'},
                                         {'assetType': 'public.camera-raw-image',
                                          'maxFileSizeMB': '100'},
                                         {'assetType': 'public.png',
                                          'maxFileSizeMB': '50'}]}

    def render_GET(self, request):
        self.set_response_headers(request)
        log.msg(self.__class__.__name__)

        return self.handle_request(request, None, None)

    def handle_request(self, request, request_plist, stream):
        self.log_response(self.configuration)
        return writePlistToString(self.configuration)


class StreamDeleteMetadata(StreamHandler):
    def build_response(self, checksums):
        return [{'checksum': checksum, 'success': '1'}
                for checksum in checksums]

    def handle_request(self, request, request_plist, stream):
        """Handle deletion request

        Expects a list of assets as request plist. One asset is represented
        by a randomly generated UUID(not the asset collection ID of the
        asset to be deleted) and a "master" file hash identifying the
        asset to be deleted.
        """
        checksums = [asset['checksum'] for asset in request_plist]
        stream.delete_assets(checksums)

        response = self.build_response(checksums)
        self.log_response(response)
        return writePlistToString(response)

class StreamGetMetadata(StreamHandler):
    def get_client_token(self, request_plist):
        if self.appleId in request_plist:
            return SyncToken(request_plist[self.appleId])

    def build_response(self, user, assets, reset):
        begin = {
            'parttype': 'stream-metadata-begin',
            'ctag': str(user['syncToken']),
            'streamid': self.appleId,
            'devices': [],
        }
        if reset:
            begin['reset'] = '1'

        end = {
            'parttype': 'stream-metadata-end',
            'streamid': self.appleId,
            'assetcount': str(len(assets)),
        }
        metadata = None
        if assets:
            metadata = {
                'assets': assets,
                'mmcsheaders': ContentTokenGenerator.get_tokens(assets),
                'mmcsurl': 'https://content.icloud.com:443/%s' % self.appleId,
                'parttype': 'asset-metadata',
                'streamid': self.appleId,
            }

        self.log_response((begin, metadata, end))
        return (begin, metadata, end)

    def handle_request(self, request, request_plist, stream):
        client_token = self.get_client_token(request_plist)
        client_revision, reset = stream.examine_sync_token(client_token)
        assets = list(stream.changes_since(client_revision))

        response = hexMultipartEncode(
                    objects_to_plists(
                       self.build_response(stream.user, assets, reset)))
        return response


class StreamPutMetadata(StreamHandler):
    def build_response(self, assets):
        return {
            'assets': assets,
            # TODO make this URL configurable
            'mmcsurl': 'https://content.icloud.com:443/%s' % self.appleId,
        }

    def handle_request(self, request, request_plist, stream):
        stream.add_pending_assets(request_plist['assets'])

        tokens = ContentTokenGenerator.put_tokens(request_plist['assets'])
        response = self.build_response(tokens)

        self.log_response(response)
        return writePlistToString(response)


class StreamUploadComplete(StreamHandler):
    def build_response(self, checksums, stream):
        response = {}
        for checksum in checksums:
            collection_id = stream.collection_id_for_checksum(checksum)
            response[collection_id] = {'success': '1'}
        return response

    def handle_request(self, request, request_plist, stream):
        confirmed = stream.confirm_uploads(request_plist)
        response = self.build_response(confirmed, stream)
        self.log_response(response)
        return writePlistToString(response)

# TODO use routes
class StreamRoutes(AppleIdResource):
    childHandlers = {
        'configuration': StreamConfiguration,
        'deletemetadata': StreamDeleteMetadata,
        'getmetadata': StreamGetMetadata,
        'putmetadata': StreamPutMetadata,
        'uploadcomplete': StreamUploadComplete,
    }

    def getChild(self, action, request):
        if action in self.childHandlers:
            return self.childHandlers[action](self.appleId)
