本配置项可通过两种方式定义：在线表单或代码仓库中的应用描述文件`app_desc.yaml`，推荐使用应用描述文件定义。

#### 在线表单

对于通过镜像仓库部署的应用，您可以直接在页面上添加域名解析规则，保存后重新部署即可生效。

#### 应用描述文件

对于通过源码部署的应用，请在构建目录中的 app_desc.yaml 文件中定义`spec.domainResolution.hostAliases`来添加额外的域名解析规则，效果等同于向 /etc/hosts 文件中追加条目。

以下是示例文件：
```yaml
specVersion: 3
appVersion: "1.0.0"
module:
  spec:
    processes:
	  # ...已省略
    domainResolution:
        hostAliases:
        - ip: "127.0.0.1"
            hostnames:
            - "foo.local"
            - "bar.local"
```

字段说明：
- `ip`:（string）解析目标 IP 地址。
- `hostnames`:（array[string]）待解析的域名列表。

在示例配置中，当应用访问 foo.local 和 bar.local 域名时，会被解析到 127.0.0.1 目标 IP。

> 注意：示例中的配置遵循云原生应用描述文件的最新规范（specVersion: 3）。如果您的描述文件版本为 spec_version: 2，请先将其转换为最新版本。

#### 注意事项

1. 生效范围：定义后，应用下所有模块都会生效。
2. 优先级：应用描述文件 `app_desc.yaml` 文件中如果定义了该项，则每次部署时均会刷新该配置项。