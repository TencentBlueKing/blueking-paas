# -------------- builder container --------------
# Build the daemon binary
FROM golang:1.25.4-alpine3.22 AS builder

WORKDIR /workspace

# 构建依赖: git(make build 通过 git describe 注入版本)、make、bash
RUN apk add --no-cache git make bash

# 先拉依赖, 利用层缓存
COPY go.mod go.mod
COPY go.sum go.sum
RUN go mod download

COPY . .

# make build 会同时生成 swagger 文档并产出 build/daemon
RUN make build

# -------------- runner container --------------
FROM alpine:3.22

WORKDIR /app

# 时区与根证书(archive 需 HTTPS PUT 到 bkrepo 临时 URL);
# mailcap 提供 /etc/mime.types, 让标准库 mime.TypeByExtension 能识别更多扩展名。
RUN apk add --no-cache ca-certificates tzdata mailcap

COPY --from=builder /workspace/build/daemon /app/daemon
COPY --from=builder /workspace/build/daemon /usr/local/bin/daemon

# 常驻 daemon 默认监听 8000
EXPOSE 8000

ENTRYPOINT ["/app/daemon"]
CMD ["resident"]
