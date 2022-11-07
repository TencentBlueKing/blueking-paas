#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # Disable InsecureRequestWarning
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning

    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # type: ignore

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paas_wl.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
