## 前端本地开发与生产构建
### 本地开发
1. 新建 `${ROOT}/.bk.local.env`文件
2. 填写 BK_LOGIN_URL = '填写登录地址'
3. 填写 BK_APP_HOST = '127.0.0.0'，注意登录后 cookie 写入的域名
4. 根目录执行 `npm run dev`
5. 配置 host，打开 BK_APP_HOST 配置了域名的地址

### 生产构建
根目录执行`npm run build`

### 容器与 Helm 部署

使用 `Dockerfile.prod` 构建 Nginx 镜像，启动时替换环境变量占位符，同一镜像可跨环境部署。
Chart 位于 [`charts/app-spark-ui`](charts/app-spark-ui/)。原有 `npm run build` + `paas-server` 的 PaaS 部署方式保持可用。

## 前端项目工程介绍

### bin 目录
bin 目录下有 2 个钩子文件，可以在项目在开发者中心构建前后执行

### mock-server 目录
前端框架提供了 mock 服务，可以在 mock-server 编写 mock 服务。

### paas-server 目录
该目录使用 express 启动 web 服务。在开发者中心部署后，会使用 paas-server 启动 web 服务。登录态由后端 `/api-svc/api/accounts/userinfo/` 处理。

### src 目录
该目录编写 vue 相关代码，包含了 vue、vue-router、vue-store、pinia、api 等能力，详细编写语法可以参阅官方文档。

`src/components/project/` 是真实项目工作室。`src/components/studio/` 是 `/studio` 的 mock 实验面，和 project 的重复是有意保留的副本，删除前不要抽公共层。说明见该目录 [README](src/components/studio/README.md)。

### static 目录
如果项目中有些资源不参与打包构建，可以放到这个文件下。在项目中使用该文件的时候，使用 `/文件名` 这样的形式。

### types 目录
ts 项目会有这个目录，这里存放全局相关的 ts 文件

### .babelrc 文件
这里编写 babel 相关配置，一般可以不改动

### .bk.local.env
这里编写 dev 模式下的变量，dev 模式下优先级最高。

### .bk.development.env
这里编写 dev 模式下的变量，优先级仅次于 .bk.local.env 

### .bk.env
这里编写变量，在所有模式下生效，优先级最低

### .bk.production.env
这里编写 production 模式下的变量，优先级高于 .bk.env

### .bk.stag.env
这里编写 production 模式下的变量，且只在开发者中心的预发布环境有效，优先级高于 .bk.env 和 .bk.production.env


## 配置说明
配置文件统一在 .env 文件中进行编写。
1. 变量名需要是`BK_`开头，可以使用 `BK_XXX = $XXX` 的形式使用环境变量中的值
2. 定义好的变量，就可以在前端工程中使用 `process.env.BK_XXX` 来使用

### index.html 配置说明

蓝鲸前端开发脚手架是用来帮助我们构建蓝鲸 SaaS 应用的，同时它也支持我们构建一般的 web 单页应用。

html 文件中有几个变量（`SITE_URL`, `BK_STATIC_URL`），配置说明如下：

#### SITE_URL

前端使用的 router mode 是 `history`，因此前端路由需要根据这个变量的值来设置**路由的根路径**以及 **ajax 异步请求地址前缀**。

- 在蓝鲸 SaaS 应用和非蓝鲸 SaaS 应用中，SITE_URL 的作用均是**设置路由的根路径**。

下面看一个简单的例子理解一下（**假设您部署的蓝鲸对应域名是：http://www.bking.com ，本地开发的地址为 http://local-dev.bking.com**）：

|             | 生产环境 SITE_URL 配置（index.html）| 生产环境访问地址 | 本地开发 SITE_URL 配置（index-dev.html）| 本地开发访问地址 |
|-------------|---------------|---------------|---------------|---------------|
| 蓝鲸 SaaS 应用 | /t/open-v214/（由后端服务注入页面）| http://www.bking.com/t/open-v214/ | /（默认值为：/）| http://local-dev.bking.com |
| 非蓝鲸 SaaS 应用 | /（蓝鲸前端开发脚手架直接生成，非蓝鲸 SaaS 应用通常不会由后端服务注入页面）| http://www.bking.com | /（默认值为：/）|  http://local-dev.bking.com |

**蓝鲸 SaaS 应用中，我们建议不要修改 `${ROOT}/index.html` 中 `SITE_URL` 的值，生产环境应该由后端注入到页面中。**

#### BK_STATIC_URL

前端需要根据这个值来确定静态资源的路径（包括默认写在 html 上的 lib.bundle.js 以及 webpack 动态 inject 的 js 和 css）

还是看一个简单的例子（**假设您部署的蓝鲸对应域名是：http://www.bking.com ，本地开发的地址为 http://local-dev.bking.com**）：

|             | 生产环境 BK_STATIC_URL 配置（index.html）| 生产环境加载静态资源的路径前缀 | 本地开发 BK_STATIC_URL 配置（index-dev.html）| 本地开发加载静态资源的路径前缀 |
|-------------|---------------|---------------|---------------|---------------|
| 蓝鲸 SaaS 应用 | /t/open-v214/static/dist/（由后端服务注入页面）| http://www.bking.com/t/open-v214/static/dist/ | /（默认值为：/）| http://local-dev.bking.com/ |
| 非蓝鲸 SaaS 应用 | /（蓝鲸前端开发脚手架直接生成，非蓝鲸 SaaS 应用通常不会由后端服务注入页面）| http://www.bking.com/ | / （默认值为：/）| http://local-dev.bking.com/|

**蓝鲸 SaaS 应用中，我们建议不要修改 `${ROOT}/index.html` 中 `BK_STATIC_URL` 的值，生产环境应该由后端注入到页面中。**

### 组件库按需和全量加载的切换

蓝鲸前端开发脚手架集成了我们的 [bkui-vue] 组件库。

## 前端构建配置说明
可以在 `${ROOT}/bk.config.js` 中编写构建相关的配置，完整配置如下：
```js
{
  assetsDir: 'static',
  outputAssetsDirName: 'static',
  outputDir: 'dist',
  publicPath: '/',
  host: '127.0.0.1',
  port: 8080,
  filenameHashing: true,
  cache: true,
  https: false,
  open: false,
  runtimeCompiler: true,
  typescript: false,
  tsconfig: './tsconfig.json',
  forkTsChecker: false,
  bundleAnalysis: false,
  parseNodeModules: false,
  replaceStatic: false,
  parallel: true,
  customEnv: '',
  target: 'web',
  libraryTarget: 'umd',
  libraryName: 'MyLibrary',
  splitChunk: true,
  splitCss: true,
  clean: true,
  copy: [{
    from: './static',
    to: './dist/static',
  }],
  resource: {
    main: {
      entry: './src/main',
      html: {
        filename: 'index.html',
        template: './index.html',
      },
    },
  },
  configureWebpack: {},
  chainWebpack: config => config,
}
```
### assetsDir
项目使用的静态资源目录名

### outputAssetsDirName
构建完输出的静态资源目录名

### outputDir
构建输出目录

### publicPath
webpack 的 publicPath 配置

### host
本地开发使用的 host

### port
本地开发使用的 port

### filenameHashing
构建完的文件是否使用 hash

### cache
是否使用缓存，推荐开启，可极大提升开发效率

### https
是否启用 https。开启后本地开发可以使用 https，无需额外配置证书

### open
启动本地开发的时候，是否自动打开浏览器

### typescript
是否是 ts 项目

### tsconfig
tsconfig 地址

### forkTsChecker
是否启用独立进程处理类型检查

### bundleAnalysis
是否对构建文件进行分析

### parseNodeModules
是否对 node_modules 里面的文件进行构建

### replaceStatic
是否替换静态资源地址

### parallel
是否启用多进程构建，可以填 bool 或者 number

### customEnv
自定义变量文件地址，可以加载自定义变量

### target
可以填 web、library

### libraryTarget
webpack 的 libraryTarget

### libraryName
构建 library 的名称

### splitChunk
是否自动拆分构建文件

### splitCss
是否将 css 构建到一个独立的文件中

### clean
每次构建前，是否清除目录

### copy
复制文件配置

### resource
html 和 entry 挂载的配置

### configureWebpack
可以是函数或者对象。这里可以编写除了 loader 或者 plugin 之外的所有配置

### chainWebpack
这里编写函数，参数是 chain，需要返回修改后的 chain。使用 chain 的形式，修改 webpack 的所有配置
