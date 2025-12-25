### 功能描述  
删除 AI 插件的插件使用方

### 请求参数

#### 1、路径参数：
| 参数名称         | 参数类型 | 必须 | 参数说明                |
| ---------------- | -------- | ---- | ----------------------- |
| code             | string   | 是   | 应用 ID                 |
| distributor_code | string   | 是   | 插件使用方对应的应用 ID |

#### 2、接口参数：
暂无。


### 请求示例

```bash
curl -X DELETE \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' \
  -d '{}' \
  --insecure \
  https://bkapi.example.com/prod/system/bk_plugins/ai/ai-sundytest111/granted_distributors/bkchat-wxbot/
```

### 返回结果示例

```json
[
    {
        "code_name": "bkchat",
        "name": "bkchat",
        "introduction": null
    }
]
```

### 返回结果参数说明

无返回字段，返回为空数组 []。

| 字段         | 类型           | 是否必填 | 描述             |
| ------------ | -------------- | -------- | ---------------- |
| code_name    | string         | 是       | 插件使用方英文名 |
| name         | string         | 是       | 插件使用方名称   |
| introduction | null 或 string | 否       | 使用方简介       |
