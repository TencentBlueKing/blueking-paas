package server

import (
	"fmt"

	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"

	"github.com/bkpaas/sandbox/daemon/pkg/config"
	"github.com/bkpaas/sandbox/daemon/pkg/server/fs"
	"github.com/bkpaas/sandbox/daemon/pkg/server/httputil"
	"github.com/bkpaas/sandbox/daemon/pkg/server/process"
)

// Start starts the main server.
//
// It returns an error if the server fails to run.
func Start() error {
	r := gin.Default()

	r.Use(httputil.Recovery())
	r.Use(httputil.ErrorMiddleware())
	r.Use(httputil.LoggingMiddleware())

	binding.Validator = new(httputil.DefaultValidator)

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
