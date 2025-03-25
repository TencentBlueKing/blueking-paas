package handler

import (
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/handler/container"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/plan"
)

// RuntimeHandler is build handler
type RuntimeHandler interface {
	// GetAppDir return the source code directory
	GetAppDir() string
	// Build will build the source code by plan, return the artifact({app_code}.tgz) file path
	Build(buildPlan *plan.BuildPlan) (string, error)
}

// NewRuntimeHandler return RuntimeHandler
func NewRuntimeHandler() (RuntimeHandler, error) {
	return container.NewRuntimeHandler()
}
