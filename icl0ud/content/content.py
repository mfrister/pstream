import uuid
from base64 import b64encode

from twisted.python import log

import icloud_content_pb2
from icl0ud.utils.datastore import DataStore
from icl0ud.streams.helpers import AppleIdResource


# TODO refactor
class ContentResource(AppleIdResource):
    metadataKeys = ('bytes17', 'bytes21', 'size')

    def addAuthorizeHeaders(self, requestParameters, dict_):
        for name, value in dict_.iteritems():
            header = requestParameters.httpHeaders.add()
            header.name = name
            header.value = value

    def metadataProtoToDict(self, message):
        metadataDict = {}
        for key in self.metadataKeys:
            metadataDict[key] = getattr(message, key)
        return metadataDict

    def metadataDictToProto(self, dict_, message):
        for key in self.metadataKeys:
            setattr(message, key, dict_[key])

    def fillRequestParameters(self, requestParameters, method):
        requestParameters.host = 'storage.icloud.com'
        requestParameters.port = 443
        requestParameters.method = method
        requestParameters.pathAndQuery = '/%s/storage/%s' \
            % (self.appleId, method.lower())
        requestParameters.protocol = 'HTTP'
        requestParameters.protocolVersion = '1.1'
        requestParameters.scheme = 'https'

    def parseAuthorizeRequest(self, request):
        message = icloud_content_pb2.AuthorizeRequest()
        message.ParseFromString(request.content.read())
        return message


class ContentAuthorizeGet(ContentResource):
    def rangeValueForChunkWithChecksum(self, checksum):
        metadata = DataStore.content['metadata'][checksum]
        storageToken, chunkBegin = \
                DataStore.content['storageTokens'][checksum]
        return 'bytes=%i-%i' % (chunkBegin, chunkBegin + metadata['size'])

    def protoAssetsAdd(self, assets, checksum):
            asset = assets.add()

            metadata = DataStore.content['metadata'][checksum]

            requestParameters = asset.requestParameters
            self.fillRequestParameters(requestParameters, 'GET')

            storageToken, chunkNumber = \
                DataStore.content['storageTokens'][checksum]

            self.addAuthorizeHeaders(requestParameters, {
                'Storage-Token': storageToken,
                'Range': self.rangeValueForChunkWithChecksum(checksum),
            })

            self.metadataDictToProto(metadata, asset.metadata)

            # 20 bytes base64 encoded
            asset.storageToken = b64encode(uuid.uuid4().get_bytes()[:14])
            # 16 bytes base64 encoded
            random_bytes = uuid.uuid4().get_bytes()[:12]
            asset.contentReportingToken = b64encode(random_bytes)

    def render_POST(self, request):
        print "content authorizeGet"
        message = self.parseAuthorizeRequest(request)
        print message

        response = icloud_content_pb2.AuthorizeGetResponse()
        response.unknown2 = 2

        assets = response.body.assets
        checksumAndNumbers_list = response.body.checksumAndNumbers
        for i, body in enumerate(message.body):
            self.protoAssetsAdd(assets, body.checksum)

            checksumAndNumbers = checksumAndNumbers_list.add()
            checksumAndNumbers.checksum = body.checksum
            checksumAndNumbers.numbers.assetNumber = i
            checksumAndNumbers.numbers.b = 0

        # twisted otherwise makes some characters uppercase
        request.responseHeaders._caseMappings['x-apple-mmcs-proto-version'] = \
            'x-apple-mmcs-proto-version'
        request.setHeader('x-apple-mmcs-proto-version', '3.8')
        print response
        return response.SerializeToString()


class ContentAuthorizePut(ContentResource):
    def cache_checksums_for_put_complete(self, message, reporting_token):
        checksums = [body.checksum for body in message.body]
        DataStore.content_cache[reporting_token] = {
            'method': 'PUT',
            'checksums': checksums,
        }

    def render_POST(self, request):
        print "content authorizePut"
        message = self.parseAuthorizeRequest(request)
        print message

        # FIXME don't use fake token
        storageToken = message.body[0].checksum.encode('hex')

        # save metadata
        # uint32 chunk count + (21 bytes + uint32 file size) * chunk count
        chunkBegin = 4 + (21 + 4) * len(message.body)
        for body in message.body:
            DataStore.content['metadata'][body.checksum] = \
                self.metadataProtoToDict(body.metadata)
            DataStore.content['storageTokens'][body.checksum] = \
                (storageToken, chunkBegin)

            chunkBegin += body.metadata.size

        response = icloud_content_pb2.AuthorizePutResponse()
        response.c = 2  # no idea what this means
            # - disabling to see whether it produces an error

        body = response.body
        # TODO don't use fake tokens
        body.storageToken = message.body[0].contentAuthorizeToken
        body.contentReportingToken = message.body[0].contentAuthorizeToken

        self.cache_checksums_for_put_complete(message,
                                              body.contentReportingToken)

        contentLength = 4  # uint32 chunk count in upload
        # implementing this for multiple uploads
        for requestBody in message.body:
            body.bytes21.append(requestBody.metadata.bytes21)
            # 21 bytes + uint32 chunk size + chunk
            contentLength += 21 + 4 + requestBody.metadata.size

        requestParameters = body.requestParameters
        self.fillRequestParameters(body.requestParameters, 'PUT')

        # yeah, putting this in the URL would be nicer, but requires
        #  an additional class
        self.addAuthorizeHeaders(requestParameters, {
            'Storage-Token': storageToken,
            'Content-Length': str(contentLength),
            'Content-Type': 'application/octet-stream',
        })

        print response

        request.setHeader('Content-Type',
                          'application/vnd.com.apple.me.ubchunk+protobuf')

        # twisted otherwise makes some characters uppercase
        request.responseHeaders._caseMappings['x-apple-mmcs-proto-version'] = \
            'x-apple-mmcs-proto-version'
        request.setHeader('x-apple-mmcs-proto-version', '3.8')

        return response.SerializeToString()


class ContentTransferComplete(ContentResource):
    def render_POST(self, request):
        log.msg("content transferComplete")
        message = icloud_content_pb2.MethodCompletionInfoList()
        message.ParseFromString(request.content.read())
        log.msg(message)
        if len(message.method_completion_info) != 1:
            log.msg('ContentTransferComplete: Warning: Got more than'
                    ' one method_completion_info')

        auth_token = message.method_completion_info[0] \
                            .storage_container_authorization_token

        if auth_token in DataStore.content_cache:
            response = icloud_content_pb2.StorageContainerErrorList()
            checksums = DataStore.content_cache.get(auth_token) \
                                 .get('checksums')

            for checksum in checksums:
                file_success = response.file_success.add()
                file_success.file_checksum = checksum
                file_success.success_code = 1
                # whatever this receipt is good for
                # but without MMCS complains
                random_receipt = b64encode(uuid.uuid4().get_bytes()[:12])
                file_success.return_receipt = random_receipt
            log.msg(str(response))
            return response.SerializeToString()
        return ''
