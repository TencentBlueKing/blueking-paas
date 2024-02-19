ARG BUILDER_IMAGE_NAME=mirrors.tencent.com/bkpaas/builder-heroku-bionic
ARG BUILDER_IMAGE_TAG=latest

FROM golang:1.20.14-bullseye as binary-builder

WORKDIR /src
COPY ./go.mod ./go.mod
COPY ./go.sum ./go.sum
RUN go mod download

COPY ./cmd ./cmd
COPY ./pkg ./pkg
COPY ./Makefile ./Makefile
RUN make build

FROM ${BUILDER_IMAGE_NAME}:${BUILDER_IMAGE_TAG}

USER root
ENV HOME /app
ENV CNB_PLATFORM_API=0.11
RUN mkdir -p /blueking-shim/bin
COPY --from=binary-builder /src/bin/* /blueking-shim/bin/
ENTRYPOINT /blueking-shim/bin/entrypoint
