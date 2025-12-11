# -------------- builder container --------------
# Build the manager binary
FROM golang:1.23.8-alpine3.20 as builder

LABEL maintainer="Tencent BlueKing"

WORKDIR /workspace

# Copy the Go Modules manifests
COPY go.mod go.mod
COPY go.sum go.sum

# cache deps before building and copying source so that we don't need to re-download as much
# and so that source changes don't invalidate our downloaded layer
RUN go mod download

# Copy the go source
COPY main.go main.go
COPY api/ api/
COPY controllers/ controllers/
COPY pkg/ pkg/

# Build
ARG LDFLAGS
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags "$LDFLAGS" -o manager ./main.go

# -------------- runner container --------------
FROM tencentos/tencentos4-minimal AS runner

LABEL maintainer="Tencent BlueKing"

RUN yum -y install ca-certificates procps bind-utils && yum clean all && rm -rf /var/cache/yum

WORKDIR /

COPY config/samples/paas_v1alpha1_projectconfig.yaml config.yaml
COPY --from=builder /workspace/manager .

USER 65532:65532

ENTRYPOINT ["/manager"]
CMD ["--config", "config.yaml"]
