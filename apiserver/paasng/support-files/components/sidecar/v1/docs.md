## sidecar

在进程主容器旁运行一个附属（sidecar）容器，用于日志采集、代理转发、辅助计算等场景。

当前仅在 `workloadType=sandboxInstance` 的工作负载（AI Agent 隔离沙箱）上生效。

需要多个附属容器时，为同一进程声明多个 `sidecar` 组件条目，每个条目描述一个容器。

### 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 容器名称，需符合 DNS-1123 规范，不能与进程名重复 |
| `image` | string | 是 | 容器镜像，必须为平台构建产出的镜像 |
| `command` | string[] | 否 | 启动命令（entrypoint），不经 shell 解释 |
| `args` | string[] | 否 | 启动命令参数 |
| `env` | object[] | 否 | 环境变量，元素为 `{name, value}` |
| `ports` | object[] | 否 | 暴露端口，元素为 `{name?, containerPort, protocol?}` |
| `resources` | object | 否 | 资源配额，含 `limits` / `requests`，各自可设 `cpu` / `memory` |
| `sharedVolumes` | object[] | 否 | 声明共享的 emptyDir 卷，元素为 `{name, medium?, sizeLimit?}` |
| `volumeMounts` | object[] | 否 | 挂载到**附属容器**的卷，元素为 `{name, mountPath, readOnly?}` |
| `mainContainerVolumeMounts` | object[] | 否 | 挂载到**进程主容器**的卷，字段同上 |

### 卷共享方式

卷的声明与挂载是分开的：先在 `sharedVolumes` 中声明卷，再由每个容器通过自己的挂载列表选择性接入。

- 附属容器通过 `volumeMounts` 接入
- 进程主容器通过 `mainContainerVolumeMounts` 接入

只有两侧都挂载了同一个卷，数据才真正共享；仅声明不挂载的卷不会出现在任何容器内。

`medium` 留空表示使用节点磁盘，填 `Memory` 表示使用 tmpfs（占用容器内存配额）。

### 示例

主容器把日志写到 `/app/logs`，附属容器以只读方式采集同一目录：

```yaml
processes:
  - name: web
    components:
      - name: sidecar
        version: v1
        properties:
          name: log-collector
          image: mirrors.example.com/bkpaas/fluentd:v1.16
          args: ["-c", "/etc/fluentd/fluent.conf"]
          env:
            - name: LOG_LEVEL
              value: info
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
          sharedVolumes:
            - name: app-logs
              sizeLimit: 1Gi
          volumeMounts:
            - name: app-logs
              mountPath: /var/log/app
              readOnly: true
          mainContainerVolumeMounts:
            - name: app-logs
              mountPath: /app/logs
```
