package server

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"
	swaggerfiles "github.com/swaggo/files"
	ginswagger "github.com/swaggo/gin-swagger"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/docs"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/fs"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/process"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/pv"
)

// newEngine builds a gin engine with the common middlewares and validator shared
// by both the sandbox daemon and the resident daemon.
func newEngine() *gin.Engine {
	// Set Gin to release mode in production
	if config.G.Environment == "prod" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.New()

	r.Use(httputil.Recovery())
	r.Use(httputil.ErrorMiddleware())
	r.Use(httputil.LoggingMiddleware())

	binding.Validator = new(httputil.DefaultValidator)

	if config.G.Environment != "prod" {
		r.GET("/swagger/*any", ginswagger.WrapHandler(swaggerfiles.Handler))
	}

	return r
}

// Start starts the main server.
//
// It returns an error if the server fails to run.
func Start() error {
	docs.SwaggerInfo.Description = "BKPaaS Sandbox Daemon API"
	docs.SwaggerInfo.Title = "BKPaaS Sandbox Daemon API"
	docs.SwaggerInfo.BasePath = "/"

	r := newEngine()

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

	return r.Run(fmt.Sprintf("%s:%d", config.G.ServerHost, config.G.ServerPort))
}

// StartResident starts the resident daemon server.
//
// Unlike Start (which runs inside a sandbox alongside a user entrypoint), the resident
// daemon is a long-lived platform component that mounts the shared-storage root and exposes
// jailed file operations (list/stat/preview/archive/delete) to the apiserver.
//
// It runs until ctx is cancelled, then shuts the HTTP server down gracefully.
func StartResident(ctx context.Context) error {
	docs.SwaggerInfo.Description = "BKPaaS Sandbox Resident Daemon API"
	docs.SwaggerInfo.Title = "BKPaaS Sandbox Resident Daemon API"
	docs.SwaggerInfo.BasePath = "/"

	r := newEngine()

	// 健康检查(免鉴权, 供 readiness probe 使用)
	r.GET("/health", func(c *gin.Context) {
		httputil.SuccessResponse(c, map[string]string{"status": "ok"})
	})

	// 添加 token 验证中间件
	r.Use(httputil.TokenAuthMiddleware(config.G.Token))

	// 常驻 daemon 的 PV 文件操作(全部走 base_path + rel_path 路径 jail)。
	files := r.Group("/files")
	files.GET("/list", pv.ListFiles)
	files.GET("/stat", pv.StatFile)
	files.GET("/preview", pv.PreviewFile)
	files.POST("/archive", pv.ArchiveFile)
	files.DELETE("", pv.DeleteFile)

	srv := &http.Server{
		Addr:    fmt.Sprintf("%s:%d", config.G.ServerHost, config.G.ServerPort),
		Handler: r,
	}

	errChan := make(chan error, 1)
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errChan <- err
		}
	}()

	select {
	case err := <-errChan:
		return err
	case <-ctx.Done():
		slog.Info("Shutting down resident server...")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		return srv.Shutdown(shutdownCtx)
	}
}
