"""TrainWatch package."""

from . import monitor as monitor
from .cloud import add_email as add_email
from .cloud import delete_email as delete_email
from .cloud import verify_email as verify_email
from .help import help as help

__all__ = [
    "monitor",
    "add_email",
    "delete_email",
    "verify_email",
    "help",
]
__version__ = "0.1.0"
