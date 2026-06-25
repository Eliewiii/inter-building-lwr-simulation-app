from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("your-package-name")
except PackageNotFoundError:
    # Package is not installed (e.g., during local development without pip install)
    __version__ = "0.0.0"
