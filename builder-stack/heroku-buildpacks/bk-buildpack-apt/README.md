# Blueking Buildpack: Go

蓝鲸 SaaS 应用（Aptfile）构建工具, 基于 [heroku-buildpack-apt](https://elements.heroku.com/buildpacks/heroku/heroku-buildpack-apt).

# 项目结构
```bash
.
├── buildpack      -- heroku-buildpack-go
├── Makefile       -- make 命令集
├── output         -- 构建产物目录, 使用 `make pack version=${version}` 后自动生成
└── README.md
```

# 开发指引
尽量不修改原构建工具中的内容, 而是使用 hook 的方式在原脚本中埋点修改, 或者使用 patch 的方式非侵入式地修改原脚本。
> **引入新的 hook 或 patch 后, 请维护下列的文件说明**
