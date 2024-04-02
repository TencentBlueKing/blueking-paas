# slugrunner image s-mart 包目录结构简介
```
.
├── README.md
├── app_desc.yaml
└── main
    ├── layer.tar.gz  # 由源码目录为 main 构建出的镜像, 多个模块指向同一个目录, 只构建一个镜像层
    ├── main.Procfile.tar.gz  # main 模块的 Procfile 文件层
    └── sidecar.Procfile.tar.gz  # sidecar 模块的 Procfile 文件层
```
 
## layer.tar.gz 内部的目录结构
```
app/
app/something
```

## main.Procfile.tar.gz 内部的目录结构
```
app/
/app/Procfile
```

## sidecar.Procfile.tar.gz 内部的目录结构
```
app/
/app/Procfile
```
