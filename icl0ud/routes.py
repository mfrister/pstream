from twisted.web.resource import Resource

from icl0ud.content.content import ContentAuthorizeGet, \
                                   ContentAuthorizePut, \
                                   ContentTransferComplete
from icl0ud.storage import Storage
from icl0ud.streams.views import StreamRoutes
from icl0ud.utils.datastore import DataStore
from icl0ud.streams.helpers import TreeNode

storesRead = False

class ServiceUser(TreeNode):
    childMapping = {
        'streams': StreamRoutes,
        'authorizeGet': ContentAuthorizeGet,
        'authorizePut': ContentAuthorizePut,
        'getComplete': ContentTransferComplete,
        'putComplete': ContentTransferComplete,
        'storage': Storage,
    }

class ServiceRoot(Resource):
    def __init__(self, *args, **kwargs):
        if not storesRead:
            DataStore.readFromDisk()
        Resource.__init__(self, *args, **kwargs)


    def getChild(self, name, request):
        if name != '' and name.isdigit():
            # Apple ID
            return ServiceUser(name)
        else:
            return self

    def render_GET(self, request):
        return '.'
