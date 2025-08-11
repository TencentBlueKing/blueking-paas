### 功能描述
查看应用模块信息

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明              |
|----------|----------|-----|---------------------|
| app_code | string   | 是   | 应用 ID               |
| module   | string   | 是   | 模块名称，如 "default" |

#### 2、接口参数：
暂无。

### 请求示例

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{AppCode}}/modules/{{module_name}}/
```

### 返回结果示例
```json
{
    "id": "01234567-89ab-cdef-0123-456789abcdef",
    "repo": {
        "source_type": "git",
        "type": "git",
        "trunk_url": "http://example.com/foo/bar.git",
        "repo_url": "http://example.com/foo/bar.git",
        "source_dir": "",
        "repo_fullname": "foo/bar",
        "diff_feature": {
            "method": "external",
            "enabled": true
        },
        "linked_to_internal_svn": false,
        "display_name": "Git"
    },
    "repo_auth_info": {},
    "web_config": {
        "templated_source_enabled": true,
        "runtime_type": "buildpack",
        "build_method": "buildpack",
        "artifact_type": "image"
    },
    "clusters": {
        "prod": {
            "name": "default-main",
            "type": "normal",
            "is_default": true,
            "bcs_cluster_id": "BCS-K8S-00000",
            "support_bcs_metrics": false,
            "ingress_config": {
                "sub_path_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "app_root_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "frontend_ingress_ip": "",
                "default_ingress_domain_tmpl": "%s.apps.example.com",
                "port_map": {
                    "http": 80,
                    "https": 443
                }
            },
            "feature_flags": {
                "ENABLE_MOUNT_LOG_TO_HOST": true,
                "INGRESS_USE_REGEX": true,
                "ENABLE_BK_MONITOR": true,
                "ENABLE_BK_LOG_COLLECTOR": true,
                "ENABLE_AUTOSCALING": false,
                "ENABLE_BCS_EGRESS": false
            }
        },
        "stag": {
            "name": "default-main",
            "type": "normal",
            "is_default": true,
            "bcs_cluster_id": "BCS-K8S-00000",
            "support_bcs_metrics": false,
            "ingress_config": {
                "sub_path_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "app_root_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "frontend_ingress_ip": "",
                "default_ingress_domain_tmpl": "%s.apps.example.com",
                "port_map": {
                    "http": 80,
                    "https": 443
                }
            },
            "feature_flags": {
                "ENABLE_MOUNT_LOG_TO_HOST": true,
                "INGRESS_USE_REGEX": true,
                "ENABLE_BK_MONITOR": true,
                "ENABLE_BK_LOG_COLLECTOR": true,
                "ENABLE_AUTOSCALING": false,
                "ENABLE_BCS_EGRESS": false
            }
        }
    },
    "template_display_name": "Django with auth",
    "source_origin": 1,
    "region": "ieod",
    "created": "2022-01-01 12:00:00",
    "updated": "2022-01-01 12:00:00",
    "owner": "{username}",
    "name": "default",
    "is_default": true,
    "language": "Python",
    "source_init_template": "dj2_with_auth",
    "exposed_url_type": 2,
    "user_preferred_root_domain": null,
    "last_deployed_date": "2022-01-01 12:00:00",
    "creator": "{username}",
    "application": "01234567-89ab-cdef-0123-456789abcdef"
}
```

### 返回结果参数说明

| 字段                       |   类型             | 描述                                |
|----------------------------|-------------------|-------------------------------------|
| id                         | string(uuid)      | UUID                                |
| repo                       | object            | 详见之后的 .repo 对象说明              |
| repo_auth_info             | object            | 仓库鉴权相关信息                       |
| web_config                 | object            | 模块配置信息，可用于驱动客户端功能        |
| clusters                   | object            | 集群                               |
| template_display_name      | string            | 初始化时使用的模板名称                  |
| source_origin              | integer           | 模块源码来源，例如 1 表示 Git 等代码仓库  |
| region                     | string            | 部署区域                              |
| created                    | string(date-time) | 创建时间                              |
| updated                    | string(date-time) | 更新时间                              |
| name                       | string            | 模块名称                              |
| is_default                 | boolean           | 是否为默认模块                         |
| language                   | string            | 编程语言                              |
| source_init_template       | string            | 初始化模板类型                         |
| exposed_url_type           | integer           | 对外暴露访问的类型                      |
| user_preferred_root_domain | string            | 用户偏好的根域名                        |
| last_deployed_date         | string(date-time) | 最近部署时间                           |
| application                | string            | 应用信息                              |

子成员 `.repo` 对象各字段说明:

| 字段                   |   类型    | 描述                    |
|------------------------|----------|--------------------------|
| source_type            | string   | 源码类型名称                       |
| type                   | string   | 同 source_type                     |
| trunk_url              | string   | [Deprecated] 仅限 SVN 源码系统使用 |
| repo_url               | string   | 源码仓库地址                       |
| source_dir             | string   | 源码目录                           |
| repo_fullname          | string   | 仓库名                             |
| diff_feature           | object   | 与“查看源码差异”功能有关的配置字段 |
| linked_to_internal_svn | boolean  | [Deprecated] 与 SVN 有关的保留字段 |
| display_name           | string   | 源码系统用于展示的名称             |

子成员 `.web_config` 对象各字段说明:
| 字段         |   类型 | 描述 |
| ------------ | ----- | ------ |
|templated_source_enabled| boolean | #模块使用是否了源码模板 |
|runtime_type | string | 构建类型，如buildpack、dockerfile |
|build_method | string | 构建方式，如buildpack、dockerfile  |
|artifact_type | string | 制品类型 |
