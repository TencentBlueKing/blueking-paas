# 包管理器支持说明（bk-buildpack-python v358）

bk-buildpack-python v358 基于上游 heroku-buildpack-python v358，支持 pip、Pipenv、Poetry、uv 四种包管理器，构建栈为 heroku-24。

## 支持情况

| 包管理器 | 版本 | 识别文件（放在应用根目录） | 安装依赖的命令 |
|---------|------|------------------------|--------------|
| pip | 26.2.2 | `requirements.txt` | `pip install -r requirements.txt` |
| Pipenv | 2026.10.2 | `Pipfile` + `Pipfile.lock` | `pipenv install --deploy` |
| Poetry | 2.5.1 | `pyproject.toml` + `poetry.lock` | `poetry sync --only main` |
| uv | 0.13.4 | `pyproject.toml` + `uv.lock` + `.python-version` | `uv sync --locked --no-default-groups` |

- 包管理器的版本由构建工具固定，应用不能指定。
- 按应用根目录中的文件识别包管理器，`pyproject.toml` 不参与识别。同时存在多种时按 Pipenv > pip > Poetry > uv 选第一个，并在日志中告警。
- 只有 `Pipfile`、没有 `Pipfile.lock` 时构建失败。
- 只有 `setup.py`、没有任何包管理器文件时构建失败。如需继续用 pip 以可编辑模式安装，新建 `requirements.txt`，内容为 `--editable .`。

## Python 版本

用应用根目录的 `.python-version` 指定，推荐只写小版本（如 `3.14`），构建时取该小版本的最新补丁：

| `.python-version` | 实际安装 |
|------------------|---------|
| `3.11` | 3.11.17 |
| `3.12` | 3.12.15 |
| `3.13` | 3.13.17 |
| `3.14` | 3.14.9 |
| `3.15` | 3.15.1 |

- 不写版本时，首次构建使用 3.14；之后的构建沿用缓存中的小版本，并升级到该小版本的最新补丁（例如缓存为 3.13.3 时安装 3.13.17），直到清理构建缓存。
- 写完整补丁版本（如 `3.14.2`）时，内部制品库必须有对应的运行时包，否则构建失败。
- Python 3.10 已被上游标记为废弃，内部制品库也未提供 3.10 的运行时包，写 3.10 会构建失败；3.9 及以下不再支持。
- 用 uv 时必须有 `.python-version`，缺少时构建失败。

## Poetry

最小示例：

```toml
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["six==1.17.0"]

[tool.poetry]
package-mode = false
```

1. 本地执行 `poetry lock`，把 `pyproject.toml` 和 `poetry.lock` 一起提交。
2. 应用不是可安装的 Python 包时，设置 `package-mode = false`，否则 Poetry 会尝试把项目本身作为包安装。
3. 构建时只安装 main 组的依赖，dev 等其他组不会安装。
4. 构建工具会关闭 Poetry 的虚拟环境，依赖直接安装到应用的 Python 环境中。

构建环境不能访问公网 PyPI 时，用 `poetry export -f requirements.txt -o requirements.txt` 导出依赖并一起提交（Poetry 2 需要安装 poetry-plugin-export 插件），构建时由 pip 安装；`poetry.lock` 可以保留。

## uv

最小示例：

```toml
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["six==1.17.0"]
```

1. 本地执行 `uv lock`，把 `pyproject.toml`、`uv.lock`、`.python-version` 一起提交。
2. 构建时用 `--locked`：`uv.lock` 与 `pyproject.toml` 不一致时构建失败，需要在本地重新 `uv lock`。
3. 构建时不安装默认依赖组（如 `dev`），只安装 `[project].dependencies`。
4. 构建工具会关闭 uv 自带的 Python 下载，始终使用构建工具安装的 Python；依赖直接安装到应用的 Python 环境中。

## 依赖从哪里下载

| 环节 | 下载来源 |
|------|---------|
| Python 运行时、uv 二进制 | `BUILDPACK_S3_BASE_URL` 指向的目录 |
| 安装 pip / Pipenv / Poetry 自身 | `PIP_INDEX_URL`（`PIP_INDEX_HOST` 作为 trusted-host） |
| pip 安装 `requirements.txt` 中的依赖 | `pip.conf`（`PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` / `PIP_INDEX_HOST`） |
| uv 安装依赖 | `uv.lock` 中来自公网 PyPI 的包改从 `PIP_INDEX_URL` 指向的镜像下载（见下文） |
| Poetry、Pipenv 安装依赖 | 不改用平台镜像，按 `pyproject.toml` / `Pipfile` 中配置的源下载 |

### uv：开发者无需关心镜像地址

开发者照常对着公网 PyPI 执行 `uv lock` 即可。构建时把 `uv.lock` 中 `source` 为 `https://pypi.org/simple` 的包改为从镜像下载，并设置 `UV_DEFAULT_INDEX`，装完后还原 `uv.lock`（安装失败时同样还原）。

- 只改来自公网 PyPI 的包；项目自身、direct URL 依赖、私有索引来的包保持不变。每个包的 sha256 保持不变，镜像内容不一致时构建会因哈希校验失败。
- 包文件地址按 `<镜像前缀>/packages/...` 推导，要求镜像与 PyPI 布局一致，且 `PIP_INDEX_URL` 以 `/simple` 结尾；不满足时跳过替换并在日志中提示。
- 开发者在 `pyproject.toml`（`[tool.uv]` 的 `index-url` 等、`[[tool.uv.index]]`）、`uv.toml` 或 `UV_DEFAULT_INDEX` 等环境变量中配置了索引时，以开发者配置为准，不做替换。
- 平台注入的 `PIP_EXTRA_INDEX_URL` 对 uv 不生效。依赖只发布在内部源的包时，需要在 `pyproject.toml` 中用 `[[tool.uv.index]]` 显式声明该源再生成锁文件。

## 构建钩子

应用根目录 `bin/` 下的 `pre-compile`、`post-compile`（或上游原生的 `pre_compile`、`post_compile`）会在安装依赖前、后执行，四种包管理器都适用。

## 内部制品库目录约定

`BUILDPACK_S3_BASE_URL` 指向的目录需要包含：

- Python 运行时：`python-<版本>-ubuntu-24.04-<arch>.tar.zst`，与上游 heroku-buildpack-python 的 S3 文件同名
- uv：`uv-<版本>-<arch>-unknown-linux-gnu.tar.gz`。上游文件名不带版本号，上传时需要改名

缺少某个文件时构建失败，日志中会打印实际请求的地址。
