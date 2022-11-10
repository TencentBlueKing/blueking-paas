# 本地开发

> 推荐 node 版本 12.16.1

#### 安装依赖包
```
npm install
```

#### 配置host
```
127.0.0.1 bkpaas-dev.example.com（看具体环境使用的域名）
```

### 配置环境变量
```
# apiserver 模块的域名
export BK_PAAS3_URL="http://bkpaas.example.com"
# 登录服务地址
export BK_LOGIN_URL="http://paas.example.com/login"
```

#### 启动服务
```
// 版本代号: te 代表腾讯内部版本、ee 代表外部版本
// 如果 run te 版本，需要在 package_vue 目录下添加 webfe-settings
// 从 webfe-settings 项目获取

npm run dev:(版本代号)
```

#### 如何访问
启动后，本地访问地址示例 `http://bkpaas-dev.example.com:{port}`, 其中 `port` 的值配置在 `webfe/package_vue/config/index.js` 中


# 打包构建
```
// 版本代号: te代表腾讯内部版本、ee代表外部版本
npm run build:(版本代号)
```
命令执行完成后在项目根目录生成dist目录，包括前端运行的js、css等资源
