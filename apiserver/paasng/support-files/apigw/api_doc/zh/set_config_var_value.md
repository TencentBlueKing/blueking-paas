### 功能描述
通过 key 创建或更新环境变量。该环境下不存在则创建，存在则更新 `value` / `description`。

修改后需重新部署才会注入到进程。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| module | string | 是 | 模块名称，如 "default" |
| config_var_key | string | 是 | 环境变量名，如 "KEY1"。须匹配 `[A-Z][A-Z0-9_]*` |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| environment_name | string | 是 | 生效环境：stag=预发布，prod=生产，_global_=所有环境 |
| value | string | 否 | 环境变量值。新建时必填；更新时为空则不改 value |
| description | string | 否 | 变量描述，不超过 200 个字符 |
| is_sensitive | boolean | 否 | 是否敏感。仅新建时生效，更新不会改这个字段 |

### 请求示例
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"environment_name":"stag","value":"0.0.1","description":"d0.0.1版本"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/KEY1/
```

### 返回结果示例

**状态码说明：**
- **201**：创建或更新成功（无响应体）
- **400**：参数不合法，例如新建时未传 value
