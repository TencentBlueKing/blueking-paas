#### 操作说明

打开位于构建目录中的 `app_desc.yaml` 文件，定义 `spec.svcDiscovery.bkSaaS` 字段以实现服务发现，从而获取蓝鲸平台上其他应用的访问地址。以下是示例文件：

```yaml
specVersion: 3
appVersion: "1.0.0"
module:
  spec:
    processes:
      # ...已省略
    svcDiscovery:
      bkSaaS:
        - bkAppCode: bk-iam
        - bkAppCode: bk-user
          moduleName: api
```

服务发现定义字段 `spec.svcDiscovery.bkSaaS`，类型为数组结构：
- `bkAppCode`: (必填，string) 蓝鲸应用的 Code
- `moduleName`: (可选，string) 应用的模块名称。如果不设置，表示“主模块”（即 `isDefault` 为 True 的模块）。

**说明**：如果只需获取应用的主访问地址，而不关注具体模块，建议不要指定 `moduleName` 字段。