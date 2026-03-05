"""TrainWatcher package."""

from . import monitor as monitor
from .cloud import add_email as add_email
from .cloud import delete_email as delete_email
from .cloud import verify_email as verify_email
from .cloud import get_base_url as get_base_url
from .help import help as help

__all__ = [
    "monitor",
    "add_email",
    "delete_email",
    "verify_email",
    "get_base_url",
    "help",
]
__version__ = "0.2.1"
