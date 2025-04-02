package container

import (
	"encoding/json"
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/plan"
)

var _ = Describe("writeArtifactJsonFile", func() {
	var artifactJsonDir string

	BeforeEach(func() {
		artifactJsonDir, _ = os.MkdirTemp("", "tmp")
	})
	AfterEach(func() {
		Expect(os.RemoveAll(artifactJsonDir)).To(BeNil())
	})

	It("Each module uses its own independent image tar", func() {
		buildPlan := plan.BuildPlan{Steps: []*plan.ModuleBuildStep{
			{
				ModuleNames:        []string{"module1"},
				OutPutImageTarName: "module1.tar",
			},
			{
				ModuleNames:        []string{"module2"},
				OutPutImageTarName: "module2.tar",
			},
		}}
		Expect(writeArtifactJsonFile(&buildPlan, artifactJsonDir)).To(BeNil())

		fileContent, _ := os.ReadFile(filepath.Join(artifactJsonDir, "artifact.json"))
		var dataMap map[string]interface{}
		Expect(json.Unmarshal(fileContent, &dataMap)).To(BeNil())

		Expect(dataMap["module1"]).To(Equal("module1.tar"))
		Expect(dataMap["module2"]).To(Equal("module2.tar"))
	})

	It("Some module uses the same image tar", func() {
		buildPlan := plan.BuildPlan{Steps: []*plan.ModuleBuildStep{
			{
				ModuleNames:        []string{"module1", "module2"},
				OutPutImageTarName: "module1.tar",
			},
			{
				ModuleNames:        []string{"module3"},
				OutPutImageTarName: "module3.tar",
			},
		}}
		Expect(writeArtifactJsonFile(&buildPlan, artifactJsonDir)).To(BeNil())

		fileContent, _ := os.ReadFile(filepath.Join(artifactJsonDir, "artifact.json"))
		var dataMap map[string]interface{}
		Expect(json.Unmarshal(fileContent, &dataMap)).To(BeNil())

		Expect(dataMap["module1"]).To(Equal("module1.tar"))
		Expect(dataMap["module2"]).To(Equal("module1.tar"))
		Expect(dataMap["module3"]).To(Equal("module3.tar"))
	})
})
