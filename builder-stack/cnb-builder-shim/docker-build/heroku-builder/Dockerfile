ARG BUILDER_IMAGE=mirrors.tencent.com/bkpaas/heroku-builder
ARG BUILDER_TAG=bionic

FROM golang:1.18.10-bullseye as binary-builder

WORKDIR /src
COPY ./go.mod ./go.mod
COPY ./go.sum ./go.sum
RUN go mod download

COPY ./cmd ./cmd
COPY ./pkg ./pkg
COPY ./Makefile ./Makefile
RUN make build

FROM ${BUILDER_IMAGE}:${BUILDER_TAG}

USER root
ENV HOME /app
RUN mkdir -p /blueking-shim/bin
COPY --from=binary-builder /src/bin/* /blueking-shim/bin/
ENTRYPOINT /blueking-shim/bin/entrypoint
