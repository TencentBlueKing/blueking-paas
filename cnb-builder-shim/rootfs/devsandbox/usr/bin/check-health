#!/bin/sh

# check dev-server health
curl -fs http://localhost:8000/healthz || exit 1

# check code-server health
curl -fs http://localhost:8080/healthz || exit 1

exit 0
