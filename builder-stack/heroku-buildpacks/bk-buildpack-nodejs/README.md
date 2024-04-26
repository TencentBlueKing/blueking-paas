# Blueking Buildpack: NodeJS

蓝鲸 SaaS 应用（NodeJS 语言）构建工具, 基于 [heroku-buildpack-nodejs](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-nodejs).

# 项目结构
```bash
.
├── buildpack      -- heroku-buildpack-nodejs
├── hooks           -- 钩子脚本
├── patchs         -- 修改补丁
├── Makefile       -- make 命令集
├── output         -- 构建产物目录, 使用 `make pack version=${version}` 后自动生成
└── README.md
```

# 开发指引
尽量不修改原构建工具中的内容, 而是使用 hook 的方式在原脚本中埋点修改, 或者使用 patch 的方式非侵入式地修改原脚本。

> **引入新的 hook 或 patch 后, 请维护下列的文件说明**

## 已有 hook
- bk-time: 打印时间
- post-app-build: 触发 post-compile
- pre-bk-compile: 下载 STDLIB
- pre-install-nodejs: 魔改探测 node 版本的逻辑; 支持 yarn
- pre-npm-install: 根据 BK_NPM_REGISTRY 设置依赖源

## 已有 patch
- bin/compile.patch: 替换 heroku 的开发文档地址
- lib/binaries.sh.patch: 设置 NPM_REGISTRY 和触发 pre-install-nodejs hook
- lib/cache.sh.patch: 删除 node_modules/.cache 目录
- lib/dependencies.sh.patch: 替换装包指令, 设置 --package-lock=false
- lib/monitor.sh.patch: 关闭 xtrace 避免打印大量无意义的日志
