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
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{   "is_plugin_app": false,   "region": "default",   "code": "plugin1",   "name": "plugin1",   "source_config": {       "source_init_template": "bk-apigw-plugin-python",       "source_control_type": "bare_git",       "source_repo_url": "https://gitee.com/example/apps.git",       "source_origin": 1,       "source_dir": "plugin",       "source_repo_auth_info": {           "username": "xxxxxx ",           "password": "***"       }   },   "bkapp_spec": {       "build_config": {           "build_method": "buildpack"       }   }}' --insecure https://bkapi.example.com/api/bkpaas3/stag/bkapps/cloud-native/
```