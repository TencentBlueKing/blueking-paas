FROM golang:1.23-alpine AS builder

WORKDIR /builder

ADD go.mod go.mod
ADD go.sum go.sum

RUN go mod download
ADD ./cmd ./cmd
ADD ./pkg ./pkg

RUN go build -ldflags '-extldflags "-static" -w -s' -o smart-app-builder ./cmd/builder

FROM docker:28.0.1-dind

WORKDIR /tmp

COPY --from=builder /builder/smart-app-builder /usr/local/bin/smart-app-builder

COPY ./docker-build/runner-scratch.tar /tmp/runner-scratch.tar

ENV RUNTIME="dind" RUNTIME_WORKSPACE=/tmp/smart-app DAEMON_SOCK=/var/run/docker.sock \
    CNB_RUN_IMAGE_TAR=/tmp/runner-scratch.tar CNB_RUN_IMAGE=docker.io/library/cnb-runner:scratch

ENTRYPOINT ["/usr/local/bin/smart-app-builder"]
