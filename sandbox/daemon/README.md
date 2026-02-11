# Daemon 服务

一个轻量级的 HTTP 服务，提供远程命令执行和文件管理功能，适用于沙箱环境或远程任务执行场景。

## 功能特性

- **命令执行**：支持远程执行系统命令，带有超时控制和进程组管理
- **文件管理**：
  - 文件上传：支持通过 HTTP 上传文件到指定路径
  - 文件下载：支持下载服务器上的文件
  - 文件夹创建：支持创建文件夹并设置权限
  - 文件删除：支持删除文件和文件夹（支持递归删除）
- **安全认证**：支持 Token 认证机制保护 API 接口
- **健康检查**：提供健康检查端点用于服务监控
- **优雅关闭**：支持 SIGINT/SIGTERM 信号的优雅关闭
- **日志管理**：基于 logrus 的结构化日志，支持日志级别配置
- **错误处理**：统一的错误处理和响应格式

## 开发指南

### 环境要求

- Go 1.25.4 或更高版本

### 执行 fmt & lint

```bash
$ make fmt
$ make lint
```

### 执行单元测试

```bash
$ make test
```

### 构建和运行

```bash
# 构建
$ make build
# 运行
$ TOKEN=your-secret-token ./build/daemon
```

## 配置说明

服务通过环境变量进行配置，完整的配置项请参考 [pkg/config/config.go](pkg/config/config.go)。

常用配置样例：

```bash
# 基础配置
export TOKEN=your-secret-token      # API 认证 Token（必须设置）
export SERVER_PORT=8000             # HTTP 服务端口
export LOG_LEVEL=info               # 日志级别：debug, info, warn, error

# 生产环境配置
export ENVIRONMENT=prod             # 设置为 prod 将关闭 Swagger 文档
export MAX_EXEC_TIMEOUT=600s        # 命令执行超时时间
```

## API 接口

### 认证方式

所有需要认证的接口（除 `/health` 和 `/swagger/*` 外）都需要在请求头中携带 TOKEN：

```http
Authorization: Bearer <TOKEN>
```

### API 文档

完整的 API 接口文档请访问 Swagger UI：

- 开发环境：`http://localhost:8000/swagger/index.html`
- 生产环境不开放 Swagger 文档

如需重新生成 Swagger 文档，请运行：

```bash
$ make build
```

