### 资源描述

部署云原生应用。

### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径接口说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |
|   env | string |  是 | 环境名称，可选值 "stag" / "prod" |

### 输入参数说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   manifest   |   object     |   是   | 云原生应用的应用模型 Json 对象 |

### 调用示例

一份示例请求体如下所示，其中 `manifest` 为示例应用模型：

```json
{
  "manifest": {
    "apiVersion": "paas.bk.tencent.com/v1alpha1",
    "kind": "BkApp",
    "spec": {
      "processes": [
        {
          "cpu": "1000m",
          "args": [],
          "name": "web",
          "image": "nginx:latest",
          "memory": "256Mi",
          "command": [],
          "replicas": 1,
          "targetPort": 80
        }
      ],
      "configuration": {
        "env": []
      }
    }
  }
}
```

有关 `manifest` 的更多信息，请参考产品中“应用编排”页面的“YAML”面板所展示的内容。

### 返回结果

调用成功后，本接口将返回应用在指定环境中的应用模型 `BkApp` 资源现状，响应结构体如下所示：

```json
{
  "apiVersion": "paas.bk.tencent.com/v1alpha1",
  "kind": "BkApp",
  "metadata": {
    // 资源元信息，内容省略
  },
  "spec": {
    // 应用模型配置，内容省略
  },
  "status": {
    // 资源当前状态，内容省略
  }
}
```
