package plan_test

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/plan"
)

var _ = Describe("PrepareBuildPlan", func() {
	// 设置全局配置
	config.SetGlobalConfig()

	var sourceDir string

	BeforeEach(func() {
		sourceDir, _ = os.MkdirTemp("", "tmp")
	})
	AfterEach(func() {
		os.RemoveAll(sourceDir)
	})

	It("prepare build plan", func() {
		content := []byte(`specVersion: 3
appVersion: 1.0.0
app:
  bkAppCode: test-app-code
modules:
  - name: web
    language: python
    sourceDir: python
    spec:
      processes:
        - name: web-process
          procCommand: python main.py
      configuration:
          env:
            - name: key1
              value: value1
  - name: worker
    language: python
    sourceDir: python
    spec:
      processes:
        - name: celery
          procCommand: celery worker
  - name: api
    language: go
    sourceDir: backend
    spec:
      processes:
        - name: api-process
          procCommand: go run main.go`)

		Expect(os.WriteFile(filepath.Join(sourceDir, "app_desc.yaml"), content, 0o644))
		buildPlan, err := plan.PrepareBuildPlan(sourceDir)
		Expect(err).To(BeNil())

		Expect(buildPlan.AppCode).To(Equal("test-app-code"))
		Expect(buildPlan.AppDescPath).To(Equal(filepath.Join(sourceDir, "app_desc.yaml")))
		Expect(buildPlan.LogoFilePath).To(Equal(""))
		Expect(buildPlan.Procfile["api-api-process"]).To(Equal("go run main.go"))
		Expect(buildPlan.Procfile["worker-celery"]).To(Equal("celery worker"))
		Expect(buildPlan.Procfile["web-web-process"]).To(Equal("python main.py"))

		Expect(buildPlan.Steps).To(HaveLen(2))
		if buildPlan.Steps[0].RequiredBuildpacks == "tgz bk-buildpack-python ... v213" {
			Expect(buildPlan.Steps[0].ModuleNames).To(Equal([]string{"web", "worker"}))
			Expect(buildPlan.Steps[0].OutPutImageTarName).To(Equal("web.tar"))

			Expect(buildPlan.Steps[1].ModuleNames).To(Equal([]string{"api"}))

			Expect(buildPlan.Steps[1].RequiredBuildpacks).To(Equal("tgz bk-buildpack-go ... v191"))
			Expect(buildPlan.Steps[1].OutPutImageTarName).To(Equal("api.tar"))

		} else {
			Expect(buildPlan.Steps[0].ModuleNames).To(Equal([]string{"api"}))
			Expect(buildPlan.Steps[0].OutPutImageTarName).To(Equal("api.tar"))

			Expect(buildPlan.Steps[1].ModuleNames).To(Equal([]string{"web", "worker"}))
			Expect(buildPlan.Steps[1].RequiredBuildpacks).To(Equal("tgz bk-buildpack-python ... v213"))
			Expect(buildPlan.Steps[1].OutPutImageTarName).To(Equal("web.tar"))
		}
	})
})
