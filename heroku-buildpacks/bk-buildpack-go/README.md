# Blueking Buildpack: Go

蓝鲸 SaaS 应用（Go 语言）构建工具, 基于 [heroku-buildpack-go](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-go).

# 项目结构
```bash
.
├── buildpack      -- heroku-buildpack-go
├── hooks          -- 钩子脚本
├── patchs         -- 修改补丁
├── tests          -- 基于 bats 的脚本测试
├── Makefile       -- make 命令集
├── output         -- 构建产物目录, 使用 `make pack version=${version}` 后自动生成
└── README.md
```

# 开发指引
尽量不修改原构建工具中的内容, 而是使用 hook 的方式在原脚本中埋点修改, 或者使用 patch 的方式非侵入式地修改原脚本。
> **引入新的 hook 或 patch 后, 请维护下列的文件说明**

## 已有 hook
- post-compile: 调用 bin/post-compile, 将 GOPATH 的二进制复制到构建目录 go/bin 中, 清理代码文件以减少 slug 包体积
- pre-compile: 支持使用 GO_INSTALL_PACKAGE_SPEC 设置 go package name, 从 go.mod 解析 go version
- pre-gobuild: 调用 bin/pre-compile, 尝试读取 /tmp/environment/GO_INSTLL_ARGS, 剔除 -tags heroku
- run_hook: 用于调用其他钩子的工具脚本，可顺序尝试执行多个脚本，目前主要用于驱动 bin/pre-compile 与 bin/post-compile

## 已有 patch
- bin/compile.patch: hooks 埋点
- files.json.patch: 新增支持的 golang 二进制版本