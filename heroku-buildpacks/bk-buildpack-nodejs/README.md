# Blueking Buildpack: NodeJS

蓝鲸 SaaS 应用（NodeJS 语言）构建工具, 基于 [heroku-buildpack-nodejs](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-nodejs).

# 项目结构
```bash
.
├── buildpack      -- heroku-buildpack-nodejs
├── Makefile       -- make 命令集
├── output         -- 构建产物目录, 使用 `make pack version=${version}` 后自动生成
└── README.md
```

# 开发指引

尽量不修改原构建工具中的内容, 而是使用 hook 的方式在原脚本中埋点修改, 或者使用 patch 的方式非侵入式地修改原脚本。
