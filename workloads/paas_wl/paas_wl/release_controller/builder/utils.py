# -*- coding: utf-8 -*-
import urllib.parse


def get_envs_for_pypi(index_url):
    """Produce the environment variables for python buildpack, such as:

    PIP_INDEX_URL: http://pypi.douban.com/simple/
    PIP_INDEX_HOST: pypi.douban.com
    """
    parsed = urllib.parse.urlparse(index_url)
    return {'PIP_INDEX_URL': index_url, 'PIP_INDEX_HOST': parsed.netloc}
