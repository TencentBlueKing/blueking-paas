# -*- coding: utf-8 -*-
import random
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager, Iterator

from django.conf import settings
from django.utils.crypto import get_random_string


def random_resource_name():
    """A random name used as kubernetes resource name to avoid conflict
    can also be used for application name
    """
    return 'bkapp-' + get_random_string(length=12).lower() + "-" + random.choice(["stag", "prod"])


def get_default_region():
    return settings.FOR_TESTS_DEFAULT_REGION


def __generate_temp_dir__(suffix=None) -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mkdtemp(suffix=suffix))
        yield path
    finally:
        if path and path and path.exists():
            shutil.rmtree(path)


generate_temp_dir: Callable[..., ContextManager[Path]] = contextmanager(__generate_temp_dir__)


def __generate_temp_file__(suffix="") -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mktemp(suffix=suffix))
        yield path
    finally:
        if path and path.exists():
            path.unlink()


generate_temp_file: Callable[..., ContextManager[Path]] = contextmanager(__generate_temp_file__)
