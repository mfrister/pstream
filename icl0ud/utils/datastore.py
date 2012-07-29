import cPickle as pickle
import time
from os import path

from icl0ud import config


class DataStore(object):
    storagePath = path.join(config.DATA_PATH, 'storage')
    pickleFile = path.join(config.DATA_PATH, 'dataStores.pickle')

    @classmethod
    def init(cls):
        "Initialize DataStore, clear streams and content objects."

        cls.streams = {
            'users': {},
        }
        cls.content = {
            'metadata': {},
            'storageTokens': {},
        }
        cls.content_cache = CacheDict(size=100, timeout=300)

    @classmethod
    def writeToDisk(cls):
        # ugly hack to force syncTokens being stored as strings
        # restored in Stream class
        for user in cls.streams['users'].itervalues():
            user['syncToken'] = str(user['syncToken'])
        print "Writing stores to disk..."
        try:
            stores = (cls.streams, cls.content, None)
            pickle.dump(stores, open(cls.pickleFile, 'wb'))
        except Exception, e:
            print "Warning: Failed to write stores to disk: %s" % repr(e)

    @classmethod
    def readFromDisk(cls):
        print "Reading stores from disk..."

        try:
            cls.streams, cls.content, ignored = \
                pickle.load(open(cls.pickleFile, 'r'))
        except Exception, e:
            print "Warning: Failed to read stores from disk: %s" % repr(e)


# From http://code.activestate.com/recipes/496842-sized-dictionary/
# by James Kassemi
class CacheDict(dict):
    ''' A sized dictionary with a timeout (seconds) '''

    def __init__(self, size=1000, timeout=None):
        dict.__init__(self)
        self._maxsize = size
        self._stack = []
        self._timeout = timeout

    def __setitem__(self, name, value, timeout=None):
        if len(self._stack) >= self._maxsize:
            self.__delitem__(self._stack[0])
            del self._stack[0]
        if timeout is None:
            timeout = self._timeout
        if timeout is not None:
            timeout = time.time() + timeout
        self._stack.append(name)
        dict.__setitem__(self, name, (value, timeout))

    def get(self, name, default=None):
        try:
            focus = self.__getitem__(name)
            if focus[1] is not None:
                if focus[1] < time.time():
                    self.__delitem__(name)
                    self._stack.remove(name)
                    raise KeyError
            return focus[0]
        except KeyError:
            return default


DataStore.init()
