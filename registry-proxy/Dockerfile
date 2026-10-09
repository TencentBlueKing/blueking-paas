# -------------- builder container --------------
FROM golang:1.25.4-alpine3.22 AS builder

WORKDIR /workspace

# 构建依赖: git(make build 通过 git describe 注入版本)、make、bash
RUN apk add --no-cache git make bash

# 先拉依赖, 利用层缓存
COPY go.mod go.mod
COPY go.sum go.sum
RUN go mod download

COPY . .

RUN make build

# -------------- runner container --------------
FROM alpine:3.22

WORKDIR /app

# 根证书用于校验 HTTPS 上游
RUN apk add --no-cache ca-certificates tzdata

COPY --from=builder /workspace/build/registry-proxy /app/registry-proxy

USER 65532:65532

# 8443: 构建容器访问的 HTTPS 入口；9090: healthz / readyz / metrics
EXPOSE 8443 9090

ENTRYPOINT ["/app/registry-proxy"]
CMD ["-config", "/etc/registry-proxy/config.yaml"]
