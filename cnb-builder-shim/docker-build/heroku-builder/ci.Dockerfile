ARG BUILDER_IMAGE_NAME=mirrors.tencent.com/bkpaas/builder-heroku-noble
ARG BUILDER_IMAGE_TAG=latest

# -------------- builder container --------------
FROM golang:1.24.6-bookworm as binary-builder

WORKDIR /src

COPY ./go.mod ./go.mod
COPY ./go.sum ./go.sum

RUN go mod download

COPY ./cmd ./cmd
COPY ./pkg ./pkg
COPY ./internal ./internal
COPY ./Makefile ./Makefile
COPY ./.golangci.yaml ./.golangci.yaml

RUN make ginkgo golines gofumpt golangci-lint
