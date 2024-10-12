### 功能描述
创建模块

### 请求参数

#### 1. 路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |

#### 2. 接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| name | string | 是 | 模块名称 |
| source_config | dict | 是 | 源配置 |
| bkapp_spec | dict | 是 | 应用规格 |

source_config
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| source_init_template | string | 是 | 源初始化模板 |

bkapp_spec
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| build_config | dict | 是 | 构建配置 |

build_config
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| build_method | string | 是 | 构建方法，例如 "buildpack" |

### 请求示例
```
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{ "name": "dd1", "source_config": { "source_init_template": "dj2_with_auth", "source_origin": 2 }, "bkapp_spec": { "build_config": { "build_method": "buildpack" } } }' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/
```

### 返回结果示例
```json
{
    "module": {
        "id": "d3a06af5-3d70-4e56-8380-44ec3d41dded",
        "repo": {
            "source_type": "",
            "type": "",
            "trunk_url": null,
            "repo_url": null,
            "source_dir": "",
            "repo_fullname": null,
            "diff_feature": {},
            "linked_to_internal_svn": false,
            "display_name": ""
        },
        "repo_auth_info": {},
        "web_config": {
            "templated_source_enabled": false,
            "runtime_type": "buildpack",
            "build_method": "buildpack",
            "artifact_type": "slug"
        },
        "template_display_name": "蓝鲸应用开发框架（Django3.x）",
        "source_origin": 2,
        "region": "ieod",
        "created": "2024-05-09 19:32:50",
        "updated": "2024-05-09 19:32:50",
        "owner": "023ec1eb8c894a90",
        "name": "dd1",
        "is_default": false,
        "language": "Python",
        "source_init_template": "dj2_with_auth",
        "exposed_url_type": 2,
        "user_preferred_root_domain": null,
        "last_deployed_date": null,
        "creator": "023ec1eb8c894a90",
        "application": "a9f88dd9-0779-496a-b2c0-9200f06dbec7"
    },
    "source_init_result": {}
}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| module | dict | 模块信息 |
| source_init_result | dict | 源初始化结果 |

module
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 模块 ID |
| repo | dict | 仓库信息 |
| repo_auth_info | dict | 仓库认证信息 |
| web_config | dict | Web 配置 |
| template_display_name | string | 模板显示名称 |
| source_origin | int | 源起源 |
| region | string | 区域 |
| created | string | 创建时间 |
| updated | string | 更新时间 |
| owner | string | 所有者 |
| name | string | 模