# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
# This file was originally written by "revproxy" module
import logging

from django.http import HttpResponse, StreamingHttpResponse
from revproxy.utils import cookie_from_string, is_hop_by_hop, should_stream
from urllib3.response import HTTPResponse as U3HTTPResponse

#: Default number of bytes that are going to be read in a file lecture
DEFAULT_AMT = 2 ** 16
# The amount of chunk being used when no buffering is needed for reading response
NO_BUFFER_AMT = 1

logger = logging.getLogger('revproxy.response')


def set_response_headers(response, response_headers):
    # check for Django 3.2 headers interface
    # https://code.djangoproject.com/ticket/31789
    # check and set pointer before loop to improve efficiency
    if hasattr(response, 'headers'):
        headers = response.headers
    else:
        headers = response

    for header, value in response_headers.items():
        if is_hop_by_hop(header) or header.lower() == 'set-cookie':
            continue

        headers[header] = value

    if hasattr(response, 'headers'):
        logger.debug('Response headers: %s', response.headers)
    else:
        logger.debug('Response headers: %s', getattr(response, '_headers'))


def get_django_response(proxy_response, strict_cookies=False):
    """This method is used to create an appropriate response based on the
    Content-Length of the proxy_response. If the content is bigger than
    MIN_STREAMING_LENGTH, which is found on utils.py,
    than django.http.StreamingHttpResponse will be created,
    else a django.http.HTTPResponse will be created instead

    :param proxy_response: An Instance of urllib3.response.HTTPResponse that
                           will create an appropriate response
    :param strict_cookies: Whether to only accept RFC-compliant cookies
    :returns: Returns an appropriate response based on the proxy_response
              content-length
    """
    status = proxy_response.status
    headers = proxy_response.headers

    logger.debug('Proxy response headers: %s', headers)

    content_type = headers.get('Content-Type')

    logger.debug('Content-Type: %s', content_type)

    if should_stream(proxy_response):
        logger.info('Content-Length is bigger than %s', DEFAULT_AMT)
        # PATCH: get amount of bytes of streaming
        _streaming_amt = detect_streaming_amt(proxy_response)
        response = StreamingHttpResponse(
            proxy_response.stream(_streaming_amt), status=status, content_type=content_type
        )
    else:
        content = proxy_response.data or b''
        response = HttpResponse(content, status=status, content_type=content_type)

    logger.info('Normalizing response headers')
    set_response_headers(response, headers)

    cookies = proxy_response.headers.getlist('set-cookie')
    logger.info('Checking for invalid cookies')
    for cookie_string in cookies:
        cookie_dict = cookie_from_string(cookie_string, strict_cookies=strict_cookies)
        # if cookie is invalid cookie_dict will be None
        if cookie_dict:
            response.set_cookie(**cookie_dict)

    logger.debug('Response cookies: %s', response.cookies)

    return response


def detect_streaming_amt(proxy_response: U3HTTPResponse) -> int:
    """Detect the amount of bytes for streaming response"""
    content_type = proxy_response.headers.get('Content-Type', '')
    # When response was event stream, disable response buffering by setting amount to 1,
    # without this, all events will wait for a long time because how `HTTPResponse.stream()` works
    if content_type.lower() == 'text/event-stream':
        return NO_BUFFER_AMT
    return DEFAULT_AMT
