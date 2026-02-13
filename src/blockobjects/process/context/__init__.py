"""__init__.py
Summary.

"""

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Local Packages #
from .bases import *
from .contextualobjects import *
from .managercontext import *
from .asynccontext import *
from .multiprocessingcontext import *

# Defaults #
DEFAULT_PROCESS_CONTEXT = ManagerContext()
DEFAULT_PROCESS_CONTEXT.select_context("async")
BaseContextualObject._context = DEFAULT_PROCESS_CONTEXT

# Optional Modules #
try:
    import ray
except ModuleNotFoundError:
    pass
else:
    from .raycontext import *
    ManagerContext.contexts["ray"] = ray_context = RayContext()
    DEFAULT_PROCESS_CONTEXT.contexts["ray"] = ray_context
