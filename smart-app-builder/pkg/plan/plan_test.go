package plan_test

import (
	"os"
	"path/filepath"
	"slices"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/plan"
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

		procfile := buildPlan.GenerateProcfile()
		Expect(procfile["api-api-process"]).To(Equal("go run main.go"))
		Expect(procfile["worker-celery"]).To(Equal("celery worker"))
		Expect(procfile["web-web-process"]).To(Equal("python main.py"))

		Expect(buildPlan.BuildGroups).To(HaveLen(2))

		slices.SortFunc(buildPlan.BuildGroups, func(a, b *plan.ModuleBuildGroup) int {
			return strings.Compare(a.RequiredBuildpacks, b.RequiredBuildpacks)
		})

		Expect(buildPlan.BuildGroups[0].ModuleNames).To(Equal([]string{"api"}))
		Expect(buildPlan.BuildGroups[0].RequiredBuildpacks).To(Equal("oci-embedded bk-buildpack-go ... v216"))
		Expect(buildPlan.BuildGroups[0].OutputImageTarName).To(Equal("api.tar"))

		Expect(buildPlan.BuildGroups[1].ModuleNames).To(Equal([]string{"web", "worker"}))
		Expect(buildPlan.BuildGroups[1].RequiredBuildpacks).To(Equal("oci-embedded bk-buildpack-python ... v213"))
		Expect(buildPlan.BuildGroups[1].OutputImageTarName).To(Equal("web.tar"))
	})
})
