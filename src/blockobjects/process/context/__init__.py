""" __init__.py

"""
# Package Header #
from ...header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


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
