from index import d4g
from a2wsgi import ASGIMiddleware
application = ASGIMiddleware(d4g)