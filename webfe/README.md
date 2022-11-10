# 如何构建前端镜像

## 构建 npm & Nginx 的基础镜像

我们先构建出一个包含 npm & nginx 的基础镜像

```bash
docker build --network host -f Dockerfile.build . -t mirrors.tencent.com/blueking/paas-webfe:image-base
```

## 运行镜像构建

在基础镜像之上，我们会安装依赖 & 代码构建
```bash
# prod
docker build --network host -f Dockerfile . -t mirrors.tencent.com/blueking/webfe-{env}:{tag}

# stag
docker build --network host -f Dockerfile.stag . -t mirrors.tencent.com/blueking/webfe-{env}:{tag}
```
