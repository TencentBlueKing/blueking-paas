### 功能描述

根据应用 ID 查询应用基本信息，仅供内部系统使用。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称 | 参数类型 | 是否必填 | 参数说明 |
| -------- | -------- | -------- | -------- |
| id       | List[string] | 是   | 使用逗号分隔的应用 ID(bk_app_code) 列表 |

### 请求示例

```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/uni_applications/query/by_id/?id={bk_app_code}'
```

### 返回结果示例

```javascript
[
    {
        "source": 1,
        "name": "蝙蝠侠",
        "code": "batman",
        "region": "default",
        "logo_url": "http://example.com/app-logo/blueking_app_default.png",
        "developers": [
            "username",
        ],
        "creator": "username",
        "created": "2019-08-13 19:15:38",
		"contact_info": {
		    // 最近操作者
            "latest_operator": "username",
			// 最近 1个月内部署过的人，排名不分先后
            "recent_deployment_operators": [
                "username"
            ]
        }
    }
]
```

### 返回结果参数说明

- 结果列表里的内容，与请求参数的 AppID 顺序一致。
- 当某个应用 ID 查不到任何信息时，该位置内容为 null。

| 参数名称 | 参数类型 | 参数说明 |
| -------- | -------- | -------- |
| source   | int      | 应用来源平台，1 - 默认（v3），2 - 旧版本 |
| name     | string   | 应用名称 |
| code     | string   | 应用代码 |
| region   | string   | 应用区域，默认为 "default" |
| logo_url | string   | 应用 Logo URL |
| developers | List[string] | 应用开发者列表 |
| creator  | string   | 应用创建者 |
| created  | string   | 应用创建时间 |
| contact_info | dict  | 联系信息 |
| contact_info.latest_operator | string | 最近操作者 |
| contact_info.recent_deployment_operators | List[string] | 最近 1 个月内部署过的人，排名不分先后 |