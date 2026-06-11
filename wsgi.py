import os
import sys

# Add the current directory to sys.path so the 'src' package is discoverable
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)


from src.main import wsgi_app as app

application = app

# This ensures compatibility with PythonAnywhere, which looks for 'app' or 'application'.
# It is imported directly from src.main to keep the wrapper logic centralized.
