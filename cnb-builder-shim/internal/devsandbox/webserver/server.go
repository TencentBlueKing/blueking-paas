/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package webserver

import (
	"fmt"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/caarlos0/env/v10"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/go-logr/logr"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/config"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/processctl"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/vcs"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/webserver/service"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

type envConfig struct {
	DevServerAddr string `env:"DEV_SERVER_ADDR" envDefault:":8000"`
	Token         string `env:"TOKEN" envDefault:"jwram1lpbnuugmcv"`
	UploadDir     string `env:"UPLOAD_DIR" envDefault:"/cnb/devsandbox/src"`
}

// WebServer 实现了 DevWatchServer 接口, 提供 Web 服务
type WebServer struct {
	server *gin.Engine
	lg     *logr.Logger
	ch     chan devsandbox.AppReloadEvent
	env    envConfig
}

// New creates a new WebServer instance.
//
// It takes a pointer to a Logger object as a parameter and returns a pointer to a WebServer object.
func New(lg *logr.Logger) (*WebServer, error) {
	cfg := envConfig{}
	if err := env.Parse(&cfg); err != nil {
		return nil, err
	}

	r := gin.Default()
	corsConfig := config.G.Service.CORS
	// 添加跨域中间件
	r.Use(cors.New(cors.Config{
		AllowOrigins:     corsConfig.AllowOrigins,     // 允许所有来源
		AllowMethods:     corsConfig.AllowMethods,     // 允许的HTTP方法
		AllowHeaders:     corsConfig.AllowHeaders,     // 允许的请求头
		ExposeHeaders:    corsConfig.ExposeHeaders,    // 暴露的响应头
		AllowCredentials: corsConfig.AllowCredentials, // 凭证共享
		MaxAge:           12 * time.Hour,              // 预检请求缓存时间
	}))
	// 添加健康检查接口，不需要 token 验证
	r.GET("/healthz", HealthzHandler())

	// 添加 token 验证中间件
	r.Use(tokenAuthMiddleware(cfg.Token))

	s := &WebServer{
		server: r,
		lg:     lg,
		// unbuffered channel
		ch:  make(chan devsandbox.AppReloadEvent),
		env: cfg,
	}
	mgr := service.NewDeployManager()
	r.POST("/deploys", DeployHandler(s, mgr))
	r.GET("/deploys/:deployID/results", ResultHandler(mgr))
	r.GET("/app_logs", AppLogHandler())
	r.GET("/processes/status", ProcessStatusHandler())
	r.GET("/processes/list", ProcessListHandler())
	r.DELETE("/processes/:processName", ProcessStopHandler())
	r.POST("/processes/:processName", ProcessStartHandler())
	r.GET("/codes/diffs", CodeDiffsHandler())
	r.GET("/codes/commit", CodeCommitHandler())

	return s, nil
}

// Start starts the WebServer.
//
// It returns an error if the server fails to run.
func (s *WebServer) Start() error {
	return s.server.Run(s.env.DevServerAddr)
}

// ReadReloadEvent blocking read on reload event
func (s *WebServer) ReadReloadEvent() (devsandbox.AppReloadEvent, error) {
	return <-s.ch, nil
}

func tokenAuthMiddleware(token string) gin.HandlerFunc {
	return func(c *gin.Context) {
		authorizationHeader := c.GetHeader("Authorization")

		reqToken := strings.TrimPrefix(authorizationHeader, "Bearer ")
		if reqToken == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"message": "missing authorization token"})
			c.Abort()
			return
		}
		if reqToken != token {
			c.JSON(http.StatusUnauthorized, gin.H{"message": "invalid authorization token"})
			c.Abort()
			return
		}

		c.Next()
	}
}

// DeployHandler handles the deployment of a file to the web server.
// TODO 将本地源码部署的方式与请求传输源码文件的方式进行接口上的拆分
func DeployHandler(s *WebServer, svc service.DeployServiceHandler) gin.HandlerFunc {
	return func(c *gin.Context) {
		var srcFilePath string
		switch config.G.SourceCode.FetchMethod {
		case config.HTTP:
			// 创建临时文件夹
			tmpDir, err := os.MkdirTemp("", "source-*")
			if err != nil {
				c.JSON(
					http.StatusInternalServerError,
					gin.H{"message": fmt.Sprintf("create tmp dir err: %s", err.Error())},
				)
				return
			}
			defer os.RemoveAll(tmpDir)

			file, err := c.FormFile("file")
			if err != nil {
				c.JSON(
					http.StatusInternalServerError,
					gin.H{"message": fmt.Sprintf("get form err: %s", err.Error())},
				)
				return
			}

			fileName := filepath.Base(file.Filename)
			dst := path.Join(s.env.UploadDir, fileName)
			if len(dst) > 0 && dst[len(dst)-1] == '.' {
				c.JSON(
					http.StatusBadRequest,
					gin.H{"message": fmt.Sprintf("invalid file name: %s", file.Filename)},
				)
				return
			}

			if err = c.SaveUploadedFile(file, dst); err != nil {
				c.JSON(
					http.StatusInternalServerError,
					gin.H{"message": fmt.Sprintf("upload file err: %s", err.Error())},
				)
				return
			}
			// 解压文件到临时目录
			if err = utils.Unzip(dst, tmpDir); err != nil {
				c.JSON(
					http.StatusInternalServerError,
					gin.H{"message": fmt.Sprintf("unzip file err: %s", err.Error())},
				)
				return
			}
			srcFilePath = path.Join(tmpDir, strings.TrimSuffix(fileName, filepath.Ext(fileName)))
		case config.BK_REPO:
			srcFilePath = config.G.SourceCode.Workspace
		case config.GIT:
			fallthrough
		default:
			errMsg := fmt.Sprintf("unsupported source fetch method: %s", config.G.SourceCode.FetchMethod)
			c.JSON(http.StatusBadRequest, gin.H{"message": errMsg})
			return
		}

		status, err := svc.Deploy(srcFilePath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("deploy error: %s", err.Error())})
			return
		}

		select {
		case s.ch <- devsandbox.AppReloadEvent{
			ID:       status.DeployID,
			Rebuild:  status.StepOpts.Rebuild,
			Relaunch: status.StepOpts.Relaunch,
		}:
			c.JSON(http.StatusOK, gin.H{"deployID": status.DeployID})
		default:
			c.JSON(
				http.StatusTooManyRequests,
				gin.H{"message": "app is deploying, please wait for a while and try again."},
			)
		}
	}
}

// ResultHandler is a function that get the result of a deployment.
func ResultHandler(svc service.DeployServiceHandler) gin.HandlerFunc {
	return func(c *gin.Context) {
		deployID := c.Param("deployID")
		withLog, _ := strconv.ParseBool(c.Query("log"))

		result, err := svc.Result(deployID, withLog)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": fmt.Sprintf("get result error: %s", err.Error())})
			return
		}

		if withLog {
			c.JSON(http.StatusOK, gin.H{"status": result.Status, "log": result.Log})
		} else {
			c.JSON(http.StatusOK, gin.H{"status": result.Status})
		}
	}
}

// AppLogHandler 获取 app 日志
func AppLogHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		var queryParams LogQueryParams
		if err := c.ShouldBindQuery(&queryParams); err != nil {
			// 验证失败
			c.JSON(http.StatusBadRequest, gin.H{
				"message": "查询参数无效，lines 必须是 1 到 200 之间的整数",
			})
			return
		}
		// 读取日志
		logs, err := service.GetAppLogs(service.DefaultAppLogDir, queryParams.Lines)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("get app log error: %s", err.Error())})
			return
		}
		c.JSON(http.StatusOK, gin.H{"logs": logs})
	}
}

// ProcessStatusHandler ...
func ProcessStatusHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		processCtl, err := processctl.New()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("get status error: %s", err.Error())})
			return
		}
		status, err := processCtl.Status()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("get status error: %s", err.Error())})
			return
		}
		c.JSON(http.StatusOK, gin.H{"status": status})
	}
}

// ProcessListHandler ...
func ProcessListHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		appDescFilePath := path.Join(config.G.SourceCode.Workspace, "app_desc.yaml")
		appDesc, err := appdesc.UnmarshalToAppDesc(appDescFilePath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("list process error: %s", err.Error())})
			return
		}

		c.JSON(http.StatusOK, gin.H{"processes": appDesc.GetProcesses()})
	}
}

// ProcessStopHandler ...
func ProcessStopHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		processName := c.Param("processName")

		processCtl, err := processctl.New()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("stop process error: %s", err.Error())})
			return
		}

		err = processCtl.Stop(processName)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("stop process error: %s", err.Error())})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "ok"})
	}
}

// ProcessStartHandler ...
func ProcessStartHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		processName := c.Param("processName")

		processCtl, err := processctl.New()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("start process error: %s", err.Error())})
			return
		}

		err = processCtl.Start(processName)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": fmt.Sprintf("start process error: %s", err.Error())})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "ok"})
	}
}

// CodeDiffsHandler 提供文件变更信息
func CodeDiffsHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 由于目前 HTTP 附带文件的源码初始化逻辑不同，暂时不支持
		// TODO 后续重构时需要统一
		if config.G.SourceCode.FetchMethod != config.BK_REPO {
			c.JSON(
				http.StatusBadRequest,
				gin.H{"message": fmt.Sprintf("unsupported fetch method: %s", config.G.SourceCode.FetchMethod)},
			)
			return
		}

		// 初始化
		opts := []vcs.Option{}
		if c.Query("content") == "true" {
			opts = append(opts, vcs.WithContent())
		}
		verCtrl := vcs.New(config.G.SourceCode.Workspace, opts...)

		// 获取文件变更信息
		files, err := verCtrl.Diff()
		if err != nil {
			c.JSON(
				http.StatusInternalServerError,
				gin.H{"message": fmt.Sprintf("failed to diff files: %s", err)},
			)
			return
		}
		// 如果指定 tree 为 true，则返回目录树格式
		if c.Query("tree") == "true" {
			c.JSON(http.StatusOK, gin.H{"total": len(files), "tree": files.AsTree()})
			return
		}
		// 默认返回变更文件列表
		c.JSON(http.StatusOK, gin.H{"total": len(files), "files": files})
	}
}

// CodeCommitHandler 提交文件变更
func CodeCommitHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 由于目前 HTTP 附带文件的源码初始化逻辑不同，暂时不支持
		// TODO 后续重构时需要统一
		if config.G.SourceCode.FetchMethod != config.BK_REPO {
			c.JSON(
				http.StatusBadRequest,
				gin.H{"message": fmt.Sprintf("unsupported fetch method: %s", config.G.SourceCode.FetchMethod)},
			)
			return
		}

		commitMsg := c.Query("message")
		if commitMsg == "" {
			c.JSON(http.StatusBadRequest, gin.H{"message": "commit message is empty"})
			return
		}
		// 提交变更
		if err := vcs.New(config.G.SourceCode.Workspace).Commit(commitMsg); err != nil {
			c.JSON(
				http.StatusInternalServerError,
				gin.H{"message": fmt.Sprintf("failed to commit files: %s", err)},
			)
			return
		}
		c.JSON(http.StatusOK, gin.H{"message": "ok"})
	}
}

// HealthzHandler ...
func HealthzHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "active"})
	}
}

var _ devsandbox.DevWatchServer = (*WebServer)(nil)
