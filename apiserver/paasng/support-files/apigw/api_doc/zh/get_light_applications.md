### 资源描述

获取轻应用信息，仅供管理侧 APP 使用。

### 认证方式

使用 Bearer 方式认证，具体的 token 请向管理员申请。

### 输入参数说明

| 参数名称 | 参数类型 | 必须 | 参数说明          |
| -------- | -------- | ---- | ----------------- |
| app_code | string   | 是   | 轻应用的 APP Code |

### 返回结果

```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
    "app_code": "demo-0727-001_ps",
    "app_name": "demo-0727-001_ps",
    "app_url": "http://app.demo.com",
    "introduction": "测试应用",
    "creator": "admin",
    "logo": "http://demo.com/app-logo/o_demo-0727-001_ps.png",
    "developers": [
      "admin"
    ]
  },
  "result": true
}
```

### 返回结果说明

| 名称         | 类型   | 说明              |
| ------------ | ------ | ----------------- |
| app_code     | string | 轻应用的 APP Code |
| app_name     | string | 轻应用的名称      |
| app_url      | string | 应用链接          |
| introduction | string | 应用介绍          |
| creator      | string | 创建者            |
| logo         | string | 图标地址          |
| developers   | array  | 开发者列表        |
| state        | int    | 应用状态          |