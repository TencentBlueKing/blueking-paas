package builder

import (
	"fmt"
	"net/url"
	"os"
	"path/filepath"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/fs"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/http"
	"github.com/go-logr/logr"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/handler"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/plan"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// BuildExecutor execute the process which build the source code to artifact
type BuildExecutor struct {
	sourceURL string
	destURL   string
	handler   handler.RuntimeHandler

	logger logr.Logger
}

// Execute run build process
func (b *BuildExecutor) Execute() error {
	appDir := b.handler.GetAppDir()

	// 获取源码
	if err := b.fetchSource(appDir); err != nil {
		return err
	}

	// 准备构建计划
	buildPlan, err := plan.PrepareBuildPlan(appDir)
	if err != nil {
		return err
	}

	// 执行构建, 生成 artifact
	artifactTGZ, err := b.handler.Build(buildPlan)
	if err != nil {
		return err
	}

	return b.pushArtifact(artifactTGZ)
}

// fetchSource fetch the source code to destDir
func (b *BuildExecutor) fetchSource(destDir string) error {
	parsedURL, err := url.Parse(b.sourceURL)
	if err != nil {
		return err
	}

	switch parsedURL.Scheme {
	case "file":
		// TODO 重构 cnb-builder-shim/pkg/fetcher/fs 以支持非压缩文件, 简化此处代码
		filePath := parsedURL.Path

		fileInfo, err := os.Stat(filePath)
		if err != nil {
			return err
		}

		if !fileInfo.IsDir() {
			if err = fs.NewFetcher(b.logger).Fetch(filePath, destDir); err != nil {
				return err
			} else {
				return nil
			}
		}

		// 如果是文件目录, 目录不同时, 直接将源码拷贝到 destDir 下
		if filePath != destDir {
			return utils.CopyDir(filePath, destDir)
		}
		return nil

	case "http", "https":
		if err := http.NewFetcher(b.logger).Fetch(b.sourceURL, destDir); err != nil {
			return err
		}
	default:
		return fmt.Errorf("not support source-url scheme: %s", parsedURL.Scheme)
	}

	return nil
}

func (b *BuildExecutor) pushArtifact(artifactTGZ string) error {
	parsedURL, err := url.Parse(b.destURL)
	if err != nil {
		return err
	}

	switch parsedURL.Scheme {
	case "file":
		filePath := parsedURL.Path

		fileName := filepath.Base(filePath)
		if filepath.Ext(fileName) == ".tgz" {
			if err = os.MkdirAll(filepath.Dir(filePath), 0o744); err != nil {
				return err
			}
			return utils.CopyFile(artifactTGZ, filePath)
		}

		// 假定 filePath 是目录处理, 否则出错
		if err = os.MkdirAll(filePath, 0o744); err != nil {
			return err
		}
		return utils.CopyFile(artifactTGZ, filepath.Join(filePath, filepath.Base(artifactTGZ)))

	default:
		// TODO push to bkrepo
		return fmt.Errorf("not support dest-url scheme: %s", parsedURL.Scheme)
	}
}

// NewBuildExecutor create a new buildExecutor
func NewBuildExecutor(logger logr.Logger, sourceURL, destURL string) (*BuildExecutor, error) {
	if h, err := handler.NewRuntimeHandler(); err != nil {
		return nil, err
	} else {
		return &BuildExecutor{logger: logger, sourceURL: sourceURL, destURL: destURL, handler: h}, nil
	}
}
