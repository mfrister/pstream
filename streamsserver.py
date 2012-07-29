import sys

from OpenSSL import SSL
from twisted.application import internet, service
from twisted.web.server import Site

sys.path.append('.')

from icl0ud import config
from icl0ud.routes import ServiceRoot
from icl0ud.push_client import PushService


def create_service():
    class ServerContextFactory:
        def getContext(self):
            ctx = SSL.Context(SSL.SSLv23_METHOD)
            ctx.use_certificate_file(config.SERVER_CERT_PATH)
            ctx.use_privatekey_file(config.SERVER_KEY_PATH)
            return ctx

    root = ServiceRoot()
    siteFactory = Site(root, logPath='data/access_log')

    if config.production:
        siteFactory.displayTracebacks = False

    if config.ENABLE_SSL:
        server = internet.SSLServer(config.LISTEN_PORT,
                                    siteFactory,
                                    ServerContextFactory(),
                                    interface=config.LISTEN_HOST)
    else:
        server = internet.TCPServer(config.LISTEN_PORT,
                                    siteFactory,
                                    interface=config.LISTEN_HOST)
    return server


def connect_to_push_service(application):
    factory = PushService.create_factory()
    internet.TCPClient('127.0.0.1', 1234, factory) \
            .setServiceParent(application)


application = service.Application('i4d')
server = create_service()
server.setServiceParent(service.IServiceCollection(application))
connect_to_push_service(application)
