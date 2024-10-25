# ------------------------------- builder container -------------------------------
FROM golang:1.22.8-bullseye as binary-builder

WORKDIR /src

COPY ./go.mod ./go.mod
COPY ./go.sum ./go.sum

RUN go mod download

COPY ./cmd ./cmd
COPY ./pkg ./pkg
COPY ./Makefile ./Makefile

RUN make build

# ------------------------------- runner container -------------------------------
FROM gcr.io/kaniko-project/executor:latest

RUN --mount=from=busybox:musl,dst=/busybox/ ["/busybox/bin/sh", "-c", "/busybox/bin/mkdir -p /tmp && /busybox/bin/chmod 777 /tmp"]

COPY --from=binary-builder /src/bin/launcher /kaniko/blueking-launcher

ENTRYPOINT ["/kaniko/blueking-launcher"]
