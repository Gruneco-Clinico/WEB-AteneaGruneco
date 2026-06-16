# -*- encoding: utf-8 -*-
"""
Views package for apps.home
Split from monolithic views.py for maintainability.
All views are re-exported here for backward compatibility with urls.py.
"""

from .scheduling import *  # noqa: F401,F403
from .auth import *  # noqa: F401,F403
from .patients import *  # noqa: F401,F403
from .exams_public import *  # noqa: F401,F403
from .visits import *  # noqa: F401,F403
from .projects import *  # noqa: F401,F403
from .exams_dispatch import *  # noqa: F401,F403
from .exam_builder import *  # noqa: F401,F403
from .exams_sleep import *  # noqa: F401,F403
from .exams_anosognosia import *  # noqa: F401,F403
from .analytics import *  # noqa: F401,F403
from .exams_general import *  # noqa: F401,F403
from .pdf import *  # noqa: F401,F403
