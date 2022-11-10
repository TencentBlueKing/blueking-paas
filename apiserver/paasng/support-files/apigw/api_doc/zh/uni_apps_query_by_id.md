### 资源描述

根据应用 ID 查询应用基本信息，仅供内部系统使用

### 认证方式

使用 Bearer 方式认证，具体的 token 请向管理员申请。

### 输入参数说明
| 参数名称      | 参数类型     | 必须 | 参数说明                           |
|---------------|--------------|-----|--------------------------------|
| private_token | string       | 否   | PaaS 平台分配的 token,当请求方的应用身份未被 PaaS 平台认证时必须提供|
| id            | List[string] | 是   | 使用逗号分隔的应用 ID(app id) 列表 |

### 返回结果

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

### 返回结果说明

- 结果列表里的内容，与请求参数的 AppID 顺序一致
- 当某个应用 ID 查不到任何信息时，该位置内容为 null

| 参数名称 | 参数类型     | 参数说明                 |
|----------|----------|----------------------|
| source   | 应用来源平台 | 1 - 默认（v3）, 2 - 旧版本 |