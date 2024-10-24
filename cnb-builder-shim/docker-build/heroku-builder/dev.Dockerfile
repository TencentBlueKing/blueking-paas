ARG BUILDER_IMAGE_NAME=mirrors.tencent.com/bkpaas/builder-heroku-bionic
ARG BUILDER_IMAGE_TAG=latest

# -------------- builder container --------------
FROM golang:1.22.8-bullseye as binary-builder

WORKDIR /src

COPY ./go.mod ./go.mod
COPY ./go.sum ./go.sum

RUN go mod download

COPY ./cmd ./cmd
COPY ./pkg ./pkg
COPY ./internal ./internal
COPY ./Makefile ./Makefile

RUN make build-dev

# -------------- runner container --------------
FROM ${BUILDER_IMAGE_NAME}:${BUILDER_IMAGE_TAG}

USER root

ENV HOME /app

ENV CNB_APP_DIR /app

ENV CNB_PLATFORM_API=0.11

ENV DEV_MODE=true

RUN apt-get clean && apt-get update && apt-get -y install supervisor

COPY --from=binary-builder /src/bin/* /cnb/devsandbox/bin/

ENTRYPOINT /cnb/devsandbox/bin/dev-entrypoint
