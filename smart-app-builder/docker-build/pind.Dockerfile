FROM golang:1.23-alpine AS builder

WORKDIR /builder

ADD go.mod go.mod
ADD go.sum go.sum

RUN go mod download
ADD ./cmd ./cmd
ADD ./pkg ./pkg

RUN go build -ldflags '-extldflags "-static" -w -s' -o smart-app-builder ./cmd/builder

FROM mgoltzsche/podman:5.4.0

WORKDIR /podman

COPY --from=builder /builder/smart-app-builder /usr/local/bin/smart-app-builder

COPY ./docker-build/runner-scratch.tar /podman/runner-scratch.tar

ENV RUNTIME="pind" RUNTIME_WORKSPACE=/podman/smart-app DAEMON_SOCK=/tmp/storage-run-1000/podman/podman.sock \
    CNB_RUN_IMAGE_TAR=/podman/runner-scratch.tar CNB_RUN_IMAGE=docker.io/library/cnb-runner:scratch

# 切换至 podman 用户, 使用 rootless 模式
USER podman

ENTRYPOINT ["/usr/local/bin/smart-app-builder"]
