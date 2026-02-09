package server

import (
	"fmt"

	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"
	swaggerfiles "github.com/swaggo/files"
	ginswagger "github.com/swaggo/gin-swagger"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/docs"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/fs"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/process"
)

// Start starts the main server.
//
// It returns an error if the server fails to run.
func Start() error {
	docs.SwaggerInfo.Description = "BKPaaS Sandbox Daemon API"
	docs.SwaggerInfo.Title = "BKPaaS Sandbox Daemon API"
	docs.SwaggerInfo.BasePath = "/"

	// Set Gin to release mode in production
	if config.G.Environment == "prod" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()

	r.Use(httputil.Recovery())
	r.Use(httputil.ErrorMiddleware())
	r.Use(httputil.LoggingMiddleware())

	binding.Validator = new(httputil.DefaultValidator)

	if config.G.Environment != "prod" {
		r.GET("/swagger/*any", ginswagger.WrapHandler(swaggerfiles.Handler))
	}

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		httputil.SuccessResponse(c, map[string]string{"status": "ok"})
	})

	// 添加 token 验证中间件
	r.Use(httputil.TokenAuthMiddleware(config.G.Token))

	// 执行命令
	r.POST("/process/execute", process.ExecuteCommand)

	// 文件操作
	fsController := r.Group("/files")
	// 上传文件
	fsController.POST("/upload", fs.UploadFile)
	// 下载文件
	fsController.GET("/download", fs.DownloadFile)
	// 创建文件夹
	fsController.POST("/folder", fs.CreateFolder)
	// 删除文件
	fsController.DELETE("/", fs.DeleteFile)

	return r.Run(fmt.Sprintf(":%d", config.G.ServerPort))
}
