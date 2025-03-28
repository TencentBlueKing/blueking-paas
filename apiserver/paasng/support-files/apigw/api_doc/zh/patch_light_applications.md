### 功能描述
修改轻应用信息。

说明：轻应用相关 API 默认只允许标准运维（应用ID：bk_sops）调用，如需调用请联系平台管理员添加权限。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称     | 参数类型 | 是否必填 | 参数说明                                                     |
| ------------ | -------- | -------- | ------------------------------------------------------------ |
| light_app_code     | string   | 是       | 轻应用的 APP Code                                            |
| app_name     | string   | 是       | 轻应用名称                                                   |
| app_url      | string   | 是       | 应用链接                                                     |
| developers   | array    | 是       | 应用开发者用户名列表                                         |
| app_tag      | string   | 是       | 应用分类，可选分类： "OpsTools"（运维工具），"MonitorAlarm"（监控告警），"ConfManage"（配置管理），"DevTools"（开发工具），"EnterpriseIT"（企业IT），"OfficeApp"（办公应用），"Other"（其它）。如果传入空参数或不是上诉分类，则使用 "Other" |
| logo         | string   | 否       | 图标 png 文件 base64 编码形式                                |
| introduction | string   | 否       | 应用的简介                                                   |
| width        | int      | 否       | 应用在桌面打开窗口宽度，默认为父应用宽度                     |
| height       | int      | 否       | 应用在桌面打开窗口高度，默认为父应用高度                     |

### 请求示例
```bash
curl -X PATCH -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "appid", "bk_app_secret": "***"}' -d '{
    "light_app_code":"code",
    "app_name":"name",
    "app_url":"http://example.com",
    "developers":["admin"],
    "app_tag": "tag"
}' --insecure http://bkapi.example.com/api/bkpaas3/prod/system/light-applications
```

### 返回结果示例
```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
        "light_app_code": "demo_code",
        "app_name": "name",
        "app_url": "http://example.com",
        "introduction": "-",
        "creator": "admin",
        "logo": "",
        "developers": [
            "admin"
        ],
        "state": 4
  },
  "result": true
}
```

### 返回结果参数说明

| 名称         | 类型   | 说明              |
| ------------ | ------ | ----------------- |
| light_app_code | string | 轻应用的 APP Code |
| app_name     | string | 轻应用的名称      |
| app_url      | string | 应用链接          |
| introduction | string | 应用介绍          |
| creator      | string | 创建者            |
| logo         | string | 图标地址          |
| developers   | array  | 开发者列表        |
| state        | int    | 应用状态          |