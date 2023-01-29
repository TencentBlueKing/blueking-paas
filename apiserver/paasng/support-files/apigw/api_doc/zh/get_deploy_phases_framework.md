### 资源描述
获取部署步骤(结构体)

### 调用示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"bk_app_code": "***", "bk_app_secret": "***", "access_token": "***"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/get_deploy_phases/
```

### 路径接口说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |
|   env | string |  是 | 环境名称，可选值 "stag" / "prod" |



### 返回结果
```json
[{
        "display_name": "准备阶段",
        "type": "preparation",
        "steps": [{
            "name": "解析应用进程信息",
            "display_name": "解析应用进程信息"
        }, {
            "name": "上传仓库代码",
            "display_name": "上传仓库代码"
        }, {
            "name": "配置资源实例",
            "display_name": "配置资源实例"
        }]
    },
    {
        "display_name": "构建阶段",
        "type": "build",
        "steps": [{
            "name": "初始化构建环境",
            "display_name": "初始化构建环境"
        }, {
            "name": "检测构建工具",
            "display_name": "检测构建工具"
        }, {
            "name": "分析构建方案",
            "display_name": "分析构建方案"
        }, {
            "name": "调用 pre-compile",
            "display_name": "调用 pre-compile"
        }, {
            "name": "构建应用",
            "display_name": "构建应用"
        }, {
            "name": "调用 post-compile",
            "display_name": "调用 post-compile"
        }, {
            "name": "生成构建结果",
            "display_name": "生成构建结果"
        }, {
            "name": "清理构建环境",
            "display_name": "清理构建环境"
        }]
    },
    {
        "display_name": "部署阶段",
        "type": "release",
        "steps": [{
            "name": "执行部署前置命令",
            "display_name": "执行部署前置命令"
        }, {
            "name": "部署应用",
            "display_name": "部署应用"
        }, {
            "name": "检测部署结果",
            "display_name": "检测部署结果"
        }]
    ]
```

### 返回结果说明

#### Phase 对象各字段说明
|   参数名称   |    参数类型  |     参数说明     |
|---|---|---|---|
| display_name | string | 当前阶段的展示用名称(会随着 i18n 改变) |
| type | string | 当前阶段类型(可用作标识符) |
| steps | List | 当前阶段包含的步骤 |


#### Step 对象各字段说明
|   参数名称   |    参数类型  |     参数说明     |
|---|---|---|---|
| display_name | string | 当前阶段的展示用名称(会随着 i18n 改变) |
| name | string | 当前阶段唯一名称 |