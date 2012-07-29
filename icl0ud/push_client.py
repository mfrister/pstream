from twisted.python import log
from twisted.spread import pb

class PushService(object):
    remote = None

    @classmethod
    def create_factory(cls):
        factory = pb.PBClientFactory()
        deferred = factory.getRootObject()

        def assign_push_service(obj):
            log.msg('Connected to push service.')
            cls.remote = obj
        def push_connection_failed(error):
            log.err('Connection to push service failed: ' + str(error))

        deferred.addCallback(assign_push_service)
        deferred.addErrback(push_connection_failed)

        return factory

    @classmethod
    def send_notification(self, device, topic, payload):
        """Send a push notification via PushProxy

        Arguments:
        device -- binary device token, 32 byte long
        topic -- binary push topic, 20 byte long
        payload -- push notification payload
        """

        if not self.remote:
            log.err('uploadcomplete: Error: push service not available')
        else:
            self.remote.callRemote('sendNotification',
                                    device,
                                    topic,
                                    payload)
