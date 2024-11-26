#### 操作说明

打开位于构建目录中的`app_desc.yaml`文件，定义`spec.domainResolution.hostAliases`来添加额外的域名解析规则（效果等同于向 /etc/hosts 文件中追加条目）。一份示例文件如下所示：

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

- `ip`:（string）解析目标 IP 地址
- `hostnames`:（array[string]）待解析的域名列表

**说明**：在示例配置中，当应用访问 foo.local 和 bar.local 域名时，会被解析到 127.0.0.1 目标 IP
