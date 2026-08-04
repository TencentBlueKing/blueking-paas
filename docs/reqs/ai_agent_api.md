# AI Agent 应用接口文档（SandboxInstance 部署）

## 1. 创建 AI Agent 应用

**POST** `/api/bkapps/ai_agent/`

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 应用 ID |
| name | string | 是 | 应用名称 |
| region | string | 否 | 部署区域（使用默认区域时可不传） |
| is_isolated | bool | 否 | 是否部署到隔离环境（SandboxInstance），默认 false |
| is_engineless | bool | 否 | 是否创建为无引擎外链应用，与 is_isolated 互斥 |
| source_config | object | 否 | Git 源码配置，不传则使用固定模板包（bk-ai-plugin-python） |
| bkapp_spec | object | 条件必填 | 构建配置，传了 source_config 时必填 |

### source_config 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source_origin | int | 是 | 源码来源，使用 git 仓库时填 `1` |
| source_control_type | string | 是 | 仓库类型，见下方枚举 |
| source_repo_url | string | 是 | 仓库地址 |
| source_repo_auth_info | object | 否 | 仓库认证 `{"username": "xx", "password": "token"}` |
| source_dir | string | 否 | 源码子目录，默认 `""` |
| source_init_template | string | 否 | 初始化模板名，可为空 |
| auto_create_repo | bool | 否 | 是否由平台自动创建仓库，默认 false |

### bkapp_spec 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| build_config | object | 是 | 构建配置 |
| build_config.build_method | string | 是 | `"buildpack"` 或 `"dockerfile"`（AI Agent 不支持 `"custom_image"`） |
| build_config.dockerfile_path | string | 否 | Dockerfile 路径，默认 `"Dockerfile"` |
| build_config.docker_build_args | dict | 否 | Dockerfile 构建参数 |

### 枚举值：source_origin

| 值 | 名称 | 支持的 build_method |
|---|---|---|
| 1 | AUTHORIZED_VCS（git 仓库） | buildpack, dockerfile |
| 2 | BK_LESS_CODE | 仅 buildpack |
| 7 | AI_AGENT（模板包） | 仅 buildpack |

### 枚举值：source_control_type

| 值 | 说明 |
|---|---|
| bare_git | 原生 Git |
| bare_svn | 原生 SVN |
| bk_svn | 蓝鲸 SVN |
| bk_gitlab | 蓝鲸 Gitlab |
| tc_git | 工蜂 Git（git.woa.com） |
| github | GitHub |

### 请求示例（使用工蜂 Git + Dockerfile 构建 + 隔离部署）

```json
{
    "code": "ai-porter-bkapp",
    "name": "ai-porter-bkapp",
    "is_isolated": true,
    "source_config": {
        "source_origin": 1,
        "source_control_type": "tc_git",
        "source_repo_url": "https://git.woa.com/porterlin/just-work.git",
        "source_repo_auth_info": {},
        "source_dir": "",
        "source_init_template": ""
    },
    "bkapp_spec": {
        "build_config": {
            "build_method": "dockerfile"
        }
    }
}
```

### ���应示例

```json
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "code": "ai-porter-bkapp",
        "name": "ai-porter-bkapp",
        "modules": [...]
    },
    "source_init_result": {
        "code": "OK",
        "extra_info": {},
        "dest_type": null,
        "error": ""
    }
}
```

---

## 2. 部署应用

**POST** `/api/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/deployments/`

- `code`: 应用 ID，如 `ai-porter-bkapp`
- `module_name`: 模块名，默认 `default`
- `environment`: 部署环境，`stag` 或 `prod`

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version_type | string | 是 | 版本类型：`branch` / `tag` / `trunk` |
| version_name | string | 是 | 分支名或 Tag 名，如 `master`、`main` |
| revision | string | 否 | commit hash，不传则自动获取最新 |
| advanced_options | object | 否 | 高级选项 |

### advanced_options 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| build_id | string | 否 | 复用历史构建的镜像 ID |

### 请求示例

```json
{
    "version_type": "branch",
    "version_name": "master"
}
```

### 响应示例

```json
{
    "deployment_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "stream_url": "/streams/a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

---

## 3. 查询部署结果

**GET** `/api/bkapps/applications/{code}/deployments/{deployment_id}/result/`

- `code`: 应用 ID
- `deployment_id`: 部署接口返回的 deployment_id

### 请求参数

无（路径参数即可）

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 部署状态：`successful` / `failed` / `pending` |
| reason | string | 失败原因（成功时为空） |
| logs | string | 部署日志摘要 |

---

## 4. 部署历史列表

**GET** `/api/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/deployments/lists/`

### 请求参数

无（路径参数即可）

### 响应示例

```json
[
    {
        "id": "a1b2c3d4-...",
        "status": "successful",
        "operator": "admin",
        "created": "2026-07-31T10:00:00Z",
        "version_info": {
            "version_type": "branch",
            "version_name": "master",
            "revision": "abc123def456"
        }
    }
]
```

---

## 5. 导出部署日志

**GET** `/api/bkapps/applications/{code}/deployments/{deployment_id}/logs/export/`

### 请求参数

无（路径参数即可）

---

## 部署内部流程

```
创建应用 (is_isolated=true)
  → Application.deploy_policy = "isolated", is_ai_agent_app = True

触发部署
  → 构建镜像（Dockerfile / Buildpack）
  → 生成 BkApp CR，注入 spec.workloadType = "sandboxInstance"
  → 下发 BkApp CR 到集群

Operator 侧
  → BkApp Reconciler 检测 workloadType == "sandboxInstance"
  → 跳过 Deployment 创建
  → SandboxInstanceReconciler 创建/更新 SandboxInstance CR
  → sandbox-controller 渲染 cube MicroVM Pod
```
