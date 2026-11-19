### 功能描述

以应用身份申请网关接口权限。

#### 路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须归调用方管理 |
| gateway_name | string | 是 | 网关名称 |

#### 请求体

```json
{
    "resource_ids": [1, 2],
    "reason": "需要调用该接口",
    "expire_days": 180,
    "grant_dimension": "resource",
    "operator": "admin"
}
```

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| resource_ids | list[int] | 否 | 资源 ID 列表，为空则按网关整体申请 |
| reason | string | 否 | 申请原因，最长 512 字符 |
| expire_days | integer | 是 | 权限有效期（天） |
| grant_dimension | string | 是 | 授权维度：api / resource |
| operator | string | 是 | 操作人用户名，记入 PaaS 操作记录，允许使用虚拟账号 |

### 请求示例

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"resource_ids": [1, 2], "reason": "需要调用该接口", "expire_days": 180, "grant_dimension": "resource", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/paasv3/permissions/apply/
```

### 返回结果示例

```json
{
    "record_id": 12
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| record_id | integer | 申请记录 ID，可用于查询申请状态 |
