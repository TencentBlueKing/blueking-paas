## Context

You are in the daemon repo, helping implement features, fix bugs, and refactor existing code.

## Source code

* daemon is a lightweight HTTP service implemented in Go and Gin framework, providing remote command execution and file management capabilities for sandbox environments.
* The main entry point is in `cmd/main.go`.
* Core packages are organized in `pkg/`:
  - `config/`: Configuration loading and logging setup
  - `server/`: HTTP server and route handlers
    - `fs/`: File system operations (upload, download, create folder, delete)
    - `process/`: Command execution handlers
    - `httputil/`: HTTP utilities, middlewares, and validators
* Swagger API documentation is generated in `docs/`.
* Unit tests are placed alongside their source files with `_test.go` suffix, following Ginkgo/Gomega conventions.

## Coding style

* For Go files, follow the official Go style guide.
* For Go files, run `make fmt` to format after edits.
* For Go files, run `make lint` to check for linting issues.

### Running our tests

* Run all tests: `make test`
* Run specific package tests: `go test ./pkg/server/process/...`
* ALWAYS prefer specifying test packages for efficiency.

### Building

* Build the binary: `make build`
* This will also regenerate Swagger documentation.
