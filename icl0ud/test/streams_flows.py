from twisted.internet.defer import inlineCallbacks

from icl0ud.utils.test import StreamsTestCase

CLIENT_TOKEN = ('c352aaadd63c418cb838322ea55c7fc509'
                    'ab2fc8f6c64596aafb9e0219aef562')
CLIENT_UDID = 'eaa3e70d70164423907915115e212dcc4005f6a3'


class TestStreamsBasic(StreamsTestCase):
    @inlineCallbacks
    def test_new_stream(self):
        request = self.build_request(**{   'content': {   },
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
            'method': 'POST',
            'path': '/123456/streams/getmetadata'})
        yield self.render(request)

        response = request.written_as_string
        self.assertEquals(request.code, 200)
        self.assert_subset(response[0],
            {   'devices': [],
                'parttype': 'stream-metadata-begin',
                'streamid': '123456'})
        self.assert_subset(response[1],
            {   'assetcount': '0',
                'parttype': 'stream-metadata-end',
                'streamid': '123456'})

        # ctag looks like 'FT=-@RU=bb51cf8c-c988-4aa3-adc2-64dc27143395@S=0'
        ctag = response[0]['ctag'].split('@')
        self.assertEquals(ctag[0], 'FT=-')
        self.assertEquals(ctag[1][:3], 'RU=')
        self.assertEquals(len(ctag[1][3:]), 36)
        self.assertEquals(ctag[2], 'S=0')

    @inlineCallbacks
    def test_configuration(self):
        request = self.build_request(**{   'content': '',
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
            'method': 'GET',
            'path': '/123456/streams/configuration'})
        yield self.render(request)
        self.check_response(request, **{   'code': 200,
    'content': {   'mme.streams.application.apiVersion': '1.2',
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
                                        'maxFileSizeMB': '50'}]},
    'headers': {   'x-apple-mme-streams-config-version': '3'}})

class TestStreamsUpload(StreamsTestCase):
    client_token = ('c352aaadd63c418cb838322ea55c7fc509'
                    'ab2fc8f6c64596aafb9e0219aef562')
    client_udid = 'eaa3e70d70164423907915115e212dcc4005f6a3'

    @inlineCallbacks
    def test_upload(self):
        # run all in one test to keep dataStore and force order
        yield self.create_stream()
        yield self.putmetadata()
        yield self.uploadcomplete()
        yield self.getmetadata()
        self.assert_push_notifications(CLIENT_TOKEN)

    @inlineCallbacks
    def create_stream(self):
        request = self.build_request(**{   'content': {   },
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
            'method': 'POST',
            'path': '/123456/streams/getmetadata'})
        yield self.render(request)
        self.assertEquals(request.code, 200)

        response = request.written_as_string
        self.assertTrue('reset' in response[0], 'stream must be reset')

        self.ctag = response[0]['ctag']


    @inlineCallbacks
    def putmetadata(self):
        request = self.build_request(**{
            'content': {'assets': [
                {'assetcollid': 'c753251c-9e73-4162-a592-ec992e15cefa',
                 'bytecount': '2955117',
                 'checksum': '01feedfacefeedfacefeedfacefeedfacefeedface',
                 'dateContentCreated': '320848404.000000',
                 'dateContentModified': '329683249.000000',
                 'derivatives': [
                    {   'bytecount': '515359',
                        'checksum': '01deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
                        'height': '1536',
                        'sha1': 'ddef802fd2dacd10db5ecfc0703cb99ef4c6caac',
                        'size': '515359',
                        'type': 'public.jpeg',
                        'width': '2457'}],
                 'filename': 'Mt. Fuji.jpg',
                 'height': '2000',
                 'sha1': '1b9e7f7fd287b4810681e7d9392149b56ffa8e45',
                 'size': '2955117',
                 'type': 'public.jpeg',
                 'width': '3200'}]},
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
            'method': 'POST',
            'path': '/123456/streams/putmetadata'})
        yield self.render(request)

        response = request.written_as_string
        self.assertEquals(request.code, 200)
        self.assert_subset(response, {
            'mmcsurl': 'https://content.icloud.com:443/123456'
            })
        for checksum in ('01feedfacefeedfacefeedfacefeedfacefeedface',
                         '01deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'):
            self.assertTrue(len(response['assets'][checksum]) > 0)

    @inlineCallbacks
    def uploadcomplete(self):
        request = self.build_request(**{   'content': [
          {'assetcollid': 'c753251c-9e73-4162-a592-ec992e15cefa',
           'assets': [{'checksum': '01feedfacefeedfacefeedfacefeedfacefeedface'},
                      {'checksum': '01deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'}]}],
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
    'method': 'POST',
    'path': '/123456/streams/uploadcomplete'})
        yield self.render(request)
        self.check_response(request, **{   'code': 200,
    'content': {   'c753251c-9e73-4162-a592-ec992e15cefa': {   'success': '1'}},
    'headers': {   'x-apple-mme-streams-config-version': '3'}})

    @inlineCallbacks
    def getmetadata(self):
        request = self.build_request(**{
            'content': {
                '123456': self.ctag},
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
            'method': 'POST',
            'path': '/123456/streams/getmetadata'})
        yield self.render(request)
        self.assertEquals(request.code, 200)

        response = request.written_as_string
        # ctag with revision incremented by 1
        self.assertEquals(response[0]['ctag'], self.ctag[:-1] + '1')
        self.ctag = response[0]['ctag']
        self.assert_subset(response[0], {
            # not implemented yet
            # 'devices': [   {   'client-info': '<...>',
            #                    'client-token': 'c352aaadd63c418cb838322ea55c7fc509ab2fc8f6c64596aafb9e0219aef562',
            #                    'deviceid': 'eaa3e70d70164423907915115e212dcc4005f6a3'}],
            'parttype': 'stream-metadata-begin',
            'streamid': '123456'})
        self.assertTrue('reset' not in response[0], 'stream must not be reset')

        self.assert_subset(response[1], {
            'assets': [{
                'assetcollid': 'c753251c-9e73-4162-a592-ec992e15cefa',
                'bytecount': '2955117',
                'checksum': '01feedfacefeedfacefeedfacefeedfacefeedface',
                'dateContentCreated': '320848404.000000',
                'dateContentModified': '329683249.000000',
                'derivatives': [{'bytecount': '515359',
                              'checksum': '01deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
                              'height': '1536',
                              'sha1': 'ddef802fd2dacd10db5ecfc0703cb99ef4c6caac',
                              'size': '515359',
                              'type': 'public.jpeg',
                              'width': '2457'}],
                # 'deviceid': 'eaa3e70d70164423907915115e212dcc4005f6a3',
                'filename': 'Mt. Fuji.jpg',
                'height': '2000',
                # 'server-uploadeddate': 1335117478390,
                'sha1': '1b9e7f7fd287b4810681e7d9392149b56ffa8e45',
                'size': '2955117',
                'type': 'public.jpeg',
                'width': '3200'}],
            'mmcsurl': 'https://content.icloud.com:443/123456',
            'parttype': 'asset-metadata',
            'streamid': '123456'})
        for checksum in ('01feedfacefeedfacefeedfacefeedfacefeedface',
                         '01deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'):
            self.assertTrue(len(response[1]['mmcsheaders'][checksum]) > 0)

        self.assert_subset(response[2],
           {   'assetcount': '1',
               'parttype': 'stream-metadata-end',
               'streamid': '123456'})


class TestStreamsDelete(StreamsTestCase):
    # @inlineCallbacks
    def setUp(self):
        super(TestStreamsDelete, self).setUp()
        self.upload = TestStreamsUpload()
        self.upload.setUp()

    @inlineCallbacks
    def test_delete(self):
        yield self.upload.test_upload()
        yield self.deletemetadata()
        yield self.getmetadata()
        # two notifications, one for upload, one for delete
        self.assert_push_notifications(CLIENT_TOKEN, count=2)

    @inlineCallbacks
    def deletemetadata(self):
        request = self.build_request(**{
            'content': [
                {'assetcollid': 'C3133796-BA88-482B-9A11-F8EA90E2A5F8',
                 'checksum': '01feedfacefeedfacefeedfacefeedfacefeedface'}],
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
            'method': 'POST',
            'path': '/123456/streams/deletemetadata'})
        yield self.render(request)
        self.check_response(request, **{
            'code': 200,
            'content': [
                {'checksum': '01feedfacefeedfacefeedfacefeedfacefeedface',
                 'success': '1'},],
            'headers': {'x-apple-mme-streams-config-version': '3'}})

    @inlineCallbacks
    def getmetadata(self):
        request = self.build_request(**{
            'content': {'123456': self.upload.ctag},
            'headers': {'Host': 'p01-streams.icloud.com:443',
                        'x-apple-mme-streams-client-token': CLIENT_TOKEN,
                        'x-apple-mme-streams-client-udid': CLIENT_UDID},
            'method': 'POST',
            'path': '/123456/streams/getmetadata'})
        yield self.render(request)
        response = request.written_as_string

        self.ctag = response[0]['ctag']
        self.assertTrue('reset' not in response[0], 'stream must not be reset')

        self.assert_subset(response[1],
            {'assets': [
                {'checksum': '01feedfacefeedfacefeedfacefeedfacefeedface',
                             'delete': '1',
                             # 'server-uploadeddate': 1338038473478
            }],
             'parttype': 'asset-metadata',
             'streamid': '123456'},
        )
        # make sure mmcs headers are not returned for deleted files
        self.assertEquals(len(response[1]['mmcsheaders']), 0)
