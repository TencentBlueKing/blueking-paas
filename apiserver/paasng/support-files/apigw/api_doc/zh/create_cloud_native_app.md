### 功能描述
创建云原生应用

### 请求参数

#### 1、路径参数：
|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID，如 "monitor" |
| module   | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| is_plugin_app | boolean | 否 | 是否为插件应用 |
| code | string | 是 | 应用 ID |
| name | string | 是 | 应用名称 |
| source_config | dict | 是 | 源配置 |
| bkapp_spec | dict | 是 | 应用规格 |


**source_config 字段说明：**
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| source_init_template | string | 是 | 源初始化模板 |
| source_control_type | string | 是 | 源控制类型 |
| source_repo_url | string | 是 | 源仓库 URL |
| source_origin | integer | 是 | 应用代码来源，代码仓库则值为 1 |
| source_dir | string | 是 | 构建 |
| source_repo_auth_info | dict | 是 | 源仓库认证信息 |

**source_repo_auth_info 字段说明：**
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**bkapp_spec 字段说明：**
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| build_config | dict | 是 | 构建配置 |

**build_config 字段说明：**
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| build_method | string | 是 | 构建方式，可选值为：buildpack、dockerfile |

### 请求示例
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{   "is_plugin_app": false,   "code": "testappcode",   "name": "testappcode",   "source_config": {       "source_init_template": "dj2_with_auth",       "source_control_type": "bare_git",       "source_repo_url": "https://gitee.com/example/apps.git",       "source_origin": 1,       "source_dir": "plugin",       "source_repo_auth_info": {           "username": "xxxxxx ",           "password": "***"       }   },   "bkapp_spec": {       "build_config": {           "build_method": "buildpack"       }   }}' --insecure https://bkapi.example.com/api/bkpaas3/stag/bkapps/cloud-native/
```

### 返回结果示例
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "testappcode",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "Python",
            }
        ],
        "code": "testappcode",
        "name_en": "testappcode",
        "type": "cloud_native",
        "is_plugin_app": true,
        "is_ai_agent_app": true,
        "language": "Python",
        "is_active": true,
        "is_deleted": false,
        "last_deployed_date": null
    },
}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 应用ID |
| name | string | 应用名称 |
| modules | list | 应用模块信息 |
| code | string | 应用编码 |
| name_en | string | 应用英文名称 |
| type | string | 应用类型 |
| is_plugin_app | boolean | 是否为插件应用 |
| is_ai_agent_app | boolean | 是否为 AI Agent 工具  |
| language | string | 应用语言 |
| is_active | boolean | 是否激活 |
| is_deleted | boolean | 是否已删除 |
| last_deployed_date | string | 最后部署日期 |


modules
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| name | string | 模块名称 |
| is_default | boolean | 是否为默认模块 |
| language | string | 模块语言 |