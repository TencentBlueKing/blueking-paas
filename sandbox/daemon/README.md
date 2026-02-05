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
$ ./build/daemon
```


## 配置说明

服务通过环境变量进行配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `SERVER_PORT` | HTTP 服务监听端口 | `8000` |
| `TOKEN` | API 调用认证 Token | `jwram1lpbnuugmcv` |
| `MAX_EXEC_TIMEOUT` | 命令执行最大超时时间 | `360s` |
| `LOG_LEVEL` | 日志级别 | `warn` |
| `DAYTONA_DAEMON_LOG_FILE_PATH` | Daemon 日志文件路径 | `/tmp/sandbox-daemon.log` |
| `ENTRYPOINT_LOG_FILE_PATH` | Entrypoint 日志文件路径 | `/tmp/sandbox-entrypoint.log` |
| `ENTRYPOINT_SHUTDOWN_TIMEOUT` | 关闭 Entrypoint 的超时时间 | `60s` |
| `SIGTERM_SHUTDOWN_TIMEOUT` | 收到 SIGTERM 后关闭的超时时间 | `5s` |
| `USER_HOME_AS_WORKDIR` | 是否使用用户 home 目录作为工作目录 | `false` |

## API 接口

所有需要认证的接口（除 `/health` 外）都需要在请求头中携带 Token：

```http
Authorization: Bearer <TOKEN>
```

### 1. 健康检查

检查服务是否正常运行（无需认证）。

**请求**

```http
GET /health
```

**响应**

```json
{
  "status": "ok"
}
```

### 2. 执行命令

远程执行系统命令。

**请求**

```http
POST /process/execute
Content-Type: application/json

{
  "command": "ls -la /tmp",
  "timeout": 30,
  "cwd": "/home/user"
}
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | string | 是 | 要执行的命令（支持引号解析） |
| `timeout` | uint32 | 否 | 超时时间（秒），不设置则使用全局配置 |
| `cwd` | string | 否 | 工作目录，不设置则使用当前目录 |

**响应**

```json
{
    "exitCode": 0,
    "output": "total 8\ndrwxrwxrwt  10 root  wheel  320 Feb  5 10:00 .\n..."
}
```

**响应字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| `exitCode` | int | 命令退出码，0 表示成功，-1 表示执行失败 |
| `output` | string | 命令的标准输出和标准错误输出（合并） |

**特性说明**

- 支持命令字符串中的引号解析（单引号和双引号）
- 自动管理进程组，确保子进程也能被正确终止
- 超时后会强制终止整个进程组
- 返回合并的 stdout 和 stderr 输出

### 3. 上传文件

上传文件到服务器指定路径。

**请求**

```http
POST /files/upload
Content-Type: multipart/form-data

destPath: /tmp/uploaded_file.txt
file: <binary file data>
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `destPath` | string | 是 | 目标文件路径（完整路径） |
| `file` | file | 是 | 要上传的文件 |

**响应**

```
HTTP/1.1 200 OK
```

### 4. 下载文件

从服务器下载文件。

**请求**

```http
GET /files/download?path=/tmp/myfile.txt
Authorization: Bearer <TOKEN>
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 要下载的文件路径（完整路径） |

**响应**

返回文件的二进制内容，响应头包含：
- `Content-Type: application/octet-stream`
- `Content-Disposition: attachment; filename=<文件名>`


### 5. 创建文件夹

创建文件夹，支持递归创建多级目录。

**请求**

```http
POST /files/folder
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "path": "/tmp/new/folder",
  "mode": "0755"
}
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 要创建的文件夹路径 |
| `mode` | string | 否 | 文件夹权限（八进制字符串），默认 `0755` |

**响应**

```
HTTP/1.1 201 Created
```

### 6. 删除文件

删除文件或文件夹。

**请求**

```http
DELETE /files/?path=/tmp/myfile.txt&recursive=true
Authorization: Bearer <TOKEN>
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 要删除的文件或文件夹路径 |
| `recursive` | boolean | 否 | 是否递归删除（删除文件夹时必须设置为 `true`） |

**响应**

```
HTTP/1.1 204 No Content
```

