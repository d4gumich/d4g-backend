import os
import sys

# Add the current directory to sys.path so the 'src' package is discoverable
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)


# This 'application' object is what PythonAnywhere looks for in your configuration
# It is now imported directly from src.main to keep the wrapper logic centralized.
