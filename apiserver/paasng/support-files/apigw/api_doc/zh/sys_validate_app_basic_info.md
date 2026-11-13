### 功能描述
以应用身份校验应用 ID 和名称能否用于创建应用，只校验、不创建。调用方的系统角色须具备「校验应用 ID 和名称」权限（如 AppSpark、AIDEV），否则返回 403。

应用 ID 按开发者中心的基础规则校验并要求全局唯一，不包含个别创建接口额外的要求（如 AI Agent 应用的 ai- 前缀）。应用名称在租户范围内唯一，中英文名称都参与比较，同时不能与全租户应用重名。名称中不支持的字符会被过滤掉，与创建时一致。

应用 ID 或名称不能用时依然返回 200，由 `is_valid` 和 `fields_detail` 说明原因；只有租户参数不合法时返回 400。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| name | string | 是 | 应用名称 |
| code | string | 否 | 应用 ID，不传则只校验名称 |
| app_tenant_mode | string | 否 | 应用租户模式 |
| app_tenant_id | string | 否 | 租户 ID，全租户应用则为空字符串 |

### 请求示例
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bk-app-spark", "bk_app_secret": "***"}' -d '{"code": "demo-app", "name": "demo-app"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/validations/
```

### 返回结果示例
```
{
    "is_valid": false,
    "fields_detail": {
        "name": [
            {
                "message": "应用名称(name_zh_cn) 为 demo-app 的应用已存在",
                "code": "unique"
            }
        ]
    }
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| is_valid | boolean | 应用 ID 和名称是否都能用于创建应用 |
| fields_detail | dict | 不能用的字段及原因，键为字段名（code、name），值为错误列表；都能用时为空 |

fields_detail 中的错误
| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| code | string | 错误码，unique 表示已被其他应用占用，其余表示格式不合法（如 invalid、max_length） |
| message | string | 错误说明 |
