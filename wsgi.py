import os

from pytwitterwall import app as application
from pytwitterwall import credentials

key, secret = credentials(os.path.join(os.environ['OPENSHIFT_DATA_DIR'],
                                       'auth.cfg'))

application.config['API_KEY'], application.config['API_SECRET'] = key, secret
