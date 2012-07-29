# default settings
from settings.development import *

production = False
if os.path.exists(
        os.path.join(
            os.path.dirname(
                os.path.dirname(
                os.path.abspath(__file__))),
            'production')):
    from settings.production import *
    production = True
