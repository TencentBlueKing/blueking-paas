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
COPY ./Makefile ./Makefile

RUN make build

# -------------- runner container --------------
FROM ${BUILDER_IMAGE_NAME}:${BUILDER_IMAGE_TAG}

USER root

ENV HOME /app

ENV CNB_PLATFORM_API=0.11

RUN mkdir -p /blueking-shim/bin

COPY --from=binary-builder /src/bin/* /blueking-shim/bin/

ENTRYPOINT /blueking-shim/bin/entrypoint
