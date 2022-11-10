from typing import Dict

from django.conf import settings
from django.middleware.csrf import get_token


def context_processors(request) -> Dict:
    return {
        'csrf_token': get_token(request),
        'settings': settings,
    }
