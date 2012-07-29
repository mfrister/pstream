import re
from base64 import b64encode
from itertools import chain, islice
from uuid import uuid4

from twisted.python import log

from icl0ud.push_client import PushService
from icl0ud.utils.datastore import DataStore

class SyncToken(object):
    def __init__(self, token = None):
        if token:
            self.parse(token)
        else:
            self.ft = '-'
            self.ru = str(uuid4())
            self.s = 0    # revision number

    def parse(self, str_):
        if str_[0]=='@':
            str_=str_[1:]

        matches = re.match(r"FT=(?P<FT>[-+]+)"
                            r"@RU=(?P<RU>[0-9a-f-]+)@S=(?P<S>\d+)", str_) \
                    .groups()

        self.ft, self.ru, self.s = matches
        self.s = int(self.s)

    def __str__(self):
        return 'FT=%s@RU=%s@S=%i' % (self.ft, self.ru, self.s)

    def __repr__(self):
        return str(self)


class Stream(object):
    def __init__(self, apple_id):
        self.user = self._get_or_create_user(apple_id)
        self.apple_id = apple_id

    def _get_or_create_user(self, apple_id):
        streams_users = DataStore.streams['users']
        if not apple_id in streams_users:
            streams_users[apple_id] = {
                'devices': {},
                'metadataPending': {},
                'metadata': {},
                'metadataRevisions': [],
                'syncToken': SyncToken(),
            }
        else:
            # ugly hack to force syncTokens being restored as SyncTokens
            user = streams_users[apple_id]
            if not isinstance(user['syncToken'], SyncToken):
                user['syncToken'] = SyncToken(user['syncToken'])
        return streams_users[apple_id]

    def _metadata_for_checksums(self, checksums):
        for checksum in checksums:
            metadata = self.user['metadata'][checksum]
            if 'deleted' in metadata and metadata['deleted'] == True:
                yield {
                    'checksum': checksum,
                    'delete': '1',
                }
            else:
                yield metadata

    def changes_since(self, client_revision):
        stream_revisions = self.user['metadataRevisions']

        revisions = islice(stream_revisions, client_revision, None)
        checksums = chain(*revisions)

        metadata = self.user['metadata']
        return self._metadata_for_checksums(checksums)

    def collection_id_for_checksum(self, checksum):
        """
        Return collection id for an asset identified by its master checksum
        """
        return self.user['metadata'][checksum]['assetcollid']

    def add_pending_assets(self, changes):
        for asset in changes:
            self.add_pending_asset(asset)

    def add_pending_asset(self, asset):
        # FIXME reject if collection was already uploaded
        metadataPending = self.user['metadataPending']
        collection_id = asset['assetcollid']
        metadataPending[collection_id] = asset

    def add_revision(self, checksums):
        if checksums:
            revisions = self.user['metadataRevisions']
            revisions.append(checksums)
            self.user['syncToken'].s = len(revisions)
        DataStore.writeToDisk()

    def _confirm_collection_upload(self, collection):
        collection_id = collection['assetcollid']
        pending = self.user['metadataPending']

        if collection_id in pending:
            # FIXME check count and checksums of asset + derivatives
            metadata = pending.pop(collection_id)
            checksum = metadata['checksum']
            self.user['metadata'][checksum] = metadata
            return checksum
        log.err('Stream confirm_collection_upload: asset collection was not'
                ' pending: ' + collection_id)

    def confirm_uploads(self, collections):
        confirmed_checksums=[]
        response={}
        for assetcoll in collections:
            checksum = self._confirm_collection_upload(assetcoll)
            if checksum is not None:
                confirmed_checksums.append(checksum)

        self.add_revision(confirmed_checksums)
        if confirmed_checksums:
            self.send_push_notification()
        log.msg('uploads confirmed')
        return confirmed_checksums

    def _delete_asset(self, checksum):
        self.user['metadata'][checksum]['deleted'] = True
        # TODO gracefully handle errors, remove content

    def delete_assets(self, checksums):
        for checksum in checksums:
            self._delete_asset(checksum)
        self.add_revision(checksums)
        self.send_push_notification()

    def examine_sync_token(self, client_token):
        """Find out revision known by client and whether stream should be reset

        Return (client_revision, reset)

        reset is true if the stream should be reset since client and
        server token differ.
        """
        server_token = self.user['syncToken']

        log.msg("client/server syncTokens:")
        log.msg(client_token)
        log.msg(server_token)
        if client_token and server_token.ru == client_token.ru and \
                client_token.s <= server_token.s:
            reset = False
            return (client_token.s, False)

        return (0, True)

    def update_push_token(self, udid, token):
        self.user['devices'][udid] = token

    def send_push_notification(self):
        devices = self.user['devices'].values()
        topic = '45d4a8f8d83fdc7ba96233018fe1aa475fbccd6e'.decode('hex')
        payload = '{"r":"%s"}' % str(self.apple_id)
        log.msg('send_push_notification: Sending push notifications to '
                'tokens: %s' % repr(devices))

        for device in devices:
            device = device.decode('hex')
            PushService.send_notification(device, topic, payload)


class ContentTokenGenerator(object):
    @classmethod
    def content_auth_for_checksum(self, checksum):
        """
            fake 12 byte contentAuthorizeToken, 16 byte base64 encoded
            FIXME secure this
        """
        return b64encode(checksum[:12])

    @classmethod
    def get_tokens(cls, assets):
        checksums = []
        for asset in assets:
            if asset.get('delete', False) == '1':
                continue
            checksums.append(asset['checksum'])
            for derivative in asset.get('derivatives', ()):
                checksums.append(derivative['checksum'])

        return dict([(checksum, cls.content_auth_for_checksum(checksum))
                    for checksum in checksums])

    @classmethod
    def put_tokens(cls, assets):
        return cls.get_tokens(assets)
