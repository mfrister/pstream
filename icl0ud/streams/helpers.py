import os
import plistlib
from plistlib import writePlistToString
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from twisted.web.resource import Resource

def objects_to_plists(obj_list):
    return [writePlistToString(obj) for obj in obj_list if obj is not None]

def decode_plist(encoded):
     return plistlib.readPlist(StringIO(encoded))

def decode_chunked_plists(data):
    parts = []
    while len(data) > 0:
        # skip leading \r\n
        if data[0:2] == "\r\n":
            data = data[2:]
        # find end of length, extract and convert it to int
        length_of_length = data.index("\r\n")
        if not data[:length_of_length]:
            break
        part_length = int(data[:length_of_length], 16)
        if not part_length:
            break

        data = data[length_of_length + 2:]
        part = data[:part_length]
        data = data[part_length:]

        parts.append(plistlib.readPlist(StringIO(part)))
    return parts

def hexMultipartEncode(str_list):
    buffer = ''
    for str_ in str_list:
        if str_ != None:
            buffer += '\r\n' + ('%x' % len(str_)).upper() + '\r\n' \
                    + str_
    return buffer

class AppleIdResource(Resource):
    def __init__(self, appleId):
        allowed_ids = os.environ.get('ALLOWED_APPLEIDS', None)
        if allowed_ids and not str(appleId) in allowed_ids.split(' '):
            print 'AppleID Forbidden: ' + appleId
            raise Exception('Forbidden: ' + appleId)
        Resource.__init__(self)
        self.appleId = appleId


class TreeNode(AppleIdResource):
    childMapping = {}

    def getChild(self, name, request):
        if name in self.childMapping:
            return self.childMapping[name](self.appleId)

