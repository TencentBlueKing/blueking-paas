# Blueking Buildpack: NodeJS

蓝鲸 SaaS 应用（NodeJS 语言）构建工具, 基于 [heroku-buildpack-nodejs](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-nodejs).

## 项目结构

```bash
.
├── buildpack      -- heroku-buildpack-nodejs
├── Makefile       -- make 命令集
├── patchs         -- 修改补丁
├── output         -- 构建产物目录, 使用 `make pack version=${version}` 后自动生成
└── README.md
```

## 开发指引

尽量不修改原构建工具中的内容, 而是使用 hook 的方式在原脚本中埋点修改, 或者使用 patch 的方式非侵入式地修改原脚本。

## 已有 patch

- bin/compile.patch: 添加对 pre-compile，post-compile hook 的支持
- lib/binaries.sh.patch: 支持从自定义对象存储仓库中下载 nodejs 二进制文件

## 自定义环境变量说明

### NODE_BINARY_MIRROR_URL

指定 Node.js 二进制文件的自定义下载源地址，用于替换 [默认配置文件](https://github.com/heroku/heroku-buildpack-nodejs/blob/v304/inventory/node.toml) 中的官方仓库地址。

**使用场景：**
- 内网环境无法访问 nodejs.org 官方源
- 使用私有制品库（如 bkrepo）加速下载

**示例：**
```bash
export NODE_BINARY_MIRROR_URL="https://bkrepo.example.com/nodejs/"
```

### NODE_BINARY_MIRROR_FLAT

配合 `NODE_BINARY_MIRROR_URL` 使用，控制镜像 URL 的目录结构模式。

**可选值：**
- `true`：平铺模式，去掉版本目录直接将文件名拼接到镜像 URL 后（与老版本 buildpack 兼容）
- 未设置或其他值：标准模式（默认），保持与官方相同的目录结构（不推荐）

**示例：**

- **平铺模式**（去掉版本目录）：
```bash
export NODE_BINARY_MIRROR_URL="https://bkrepo.example.com/nodejs/"
export NODE_BINARY_MIRROR_FLAT="true"
# 下载地址: https://bkrepo.example.com/nodejs/node-v24.6.0-linux-x64.tar.gz
```

- **标准模式**（保持目录结构，与原 buildpack 一致）：
```bash
export NODE_BINARY_MIRROR_URL="https://bkrepo.example.com/nodejs/"
# 下载地址: https://bkrepo.example.com/nodejs/v24.6.0/node-v24.6.0-linux-x64.tar.gz
```
