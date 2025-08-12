### 功能描述
查看应用信息

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
|----------|----------|-----|--------|
| app_code | string   | 是   | 应用 ID  |

#### 2、接口参数：
暂无。

### 请求示例

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{AppCode}}/
```

### 返回结果示例

```json
// 内容过长，暂时省略。请直接通过下方表格查看字段详情。
```

### 返回结果参数说明

`.application` 成员对象各字段说明:

| 参数名称           | 参数类型          | 参数说明                               |
|--------------------|-------------------|----------------------------------------|
| id                 | string(uuid)      | 应用UUID                                   |
| name               | string            | 应用名称                                       |
| region_name        | string            | 应用版本名称                           |
| logo_url           | string            | 应用的 Logo 地址                       |
| config_info        | dict                  | 应用的额外状态信息                     |
| modules            | dict                  | 应用各模块信息列表                     |
| region             | string            | 部署区域                               |
| created            | string(date-time) | 创建时间                                      |
| updated            | string(date-time) | 更新时间                                      |
| owner              | string            | 应用所有者                                       |
| code               | string            | 应用代号                               |
| name_en            | string            | 应用名称(英文); 目前仅用于 S-Mart 应用 |
| type               | string            | 应用类型                               |
| is_smart_app       | boolean           | 是否为 S-Mart 应用                     |
| language           | string            | 编程语言                               |
| creator            | string            | 应用创建者                                     |
| is_active          | boolean           | 是否活跃                               |
| is_deleted         | boolean           | 是否删除                               |
| last_deployed_date | string(date-time) | 最近部署时间                           |

`.web_config` 成员对象各字段说明:

| 参数名称                      | 参数类型 | 参数说明                         |
|-------------------------------|----------|------------------------------|
| engine_enabled                | bool     | 是否启用应用引擎                 |
| can_create_extra_modules      | bool     | 是否允许创建额外模块             |
| confirm_required_when_publish | bool     | 发布到市场时是否需要二次确认     |
| market_published              | bool     | 是否已经发布到应用市场           |