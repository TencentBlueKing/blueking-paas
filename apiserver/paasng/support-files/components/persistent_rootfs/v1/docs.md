## persistent_rootfs

为沙箱中的**某个容器**声明一块持久化的 rootfs 系统盘。

不声明该组件时，对应容器的 rootfs 是临时的，实例重建后回到镜像初始状态。

当前仅对 AI Agent 隔离沙箱生效。

### 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `diskSize` | string | 是 | disk-image 文件大小，即容器内看到的系统盘容量，如 `50Gi` |
| `pvcSize` | string | 是 | 承载 disk-image 的 PVC 容量，如 `60Gi` |
| `containerName` | string | 否 | 盘绑定的容器名；省略时绑定进程主容器 |

### 多容器场景

一条 `persistent_rootfs` 只服务一个容器。主容器和 sidecar 都需要持久盘时，为每个容器
各声明一条，用 `containerName` 区分：

```yaml
processes:
  - name: web
    components:
      - name: persistent_rootfs
        version: v1
        properties:
          diskSize: 50Gi
          pvcSize: 60Gi
          # 省略 containerName，默认绑定主容器

      - name: sidecar
        version: v1
        properties:
          name: worker
          image: mirrors.example.com/bkpaas/worker:v1

      - name: persistent_rootfs
        version: v1
        properties:
          containerName: worker
          diskSize: 20Gi
          pvcSize: 30Gi
```

同一 `containerName` 被声明多次时，后者覆盖前者，不会得到多块盘。

### 示例（仅主容器）

```yaml
processes:
  - name: web
    components:
      - name: persistent_rootfs
        version: v1
        properties:
          diskSize: 50Gi
          pvcSize: 60Gi
```
