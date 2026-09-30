package volumefs

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

// testVolumeBasePath is a valid volume base path: "app/" plus 32 lowercase hex chars,
// i.e. what Volume.storage_path produces on the apiserver side.
const testVolumeBasePath = "app/0123456789abcdef0123456789abcdef"

func doDeleteVolume(router *gin.Engine, basePath string) *httptest.ResponseRecorder {
	q := url.Values{}
	if basePath != "" {
		q.Set("base_path", basePath)
	}
	w := httptest.NewRecorder()
	httpReq, _ := http.NewRequest(http.MethodDelete, "/files/volume?"+q.Encode(), nil)
	router.ServeHTTP(w, httpReq)
	return w
}

var _ = Describe("DeleteVolume", func() {
	var (
		router  *gin.Engine
		rootDir string
		volDir  string
	)

	BeforeEach(func() {
		rootDir, _ = newTestEnv()
		volDir = filepath.Join(rootDir, testVolumeBasePath)
		Expect(os.MkdirAll(filepath.Join(volDir, "nested", "deep"), 0o755)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(volDir, "a.txt"), []byte("a"), 0o644)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(volDir, "nested", "deep", "b.txt"), []byte("b"), 0o644)).To(Succeed())

		router = newTestRouter()
		router.DELETE("/files/volume", DeleteVolume)
	})

	AfterEach(func() {
		os.RemoveAll(rootDir) // nolint
	})

	It("deletes the volume directory with all nested content", func() {
		w := doDeleteVolume(router, testVolumeBasePath)
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp DeleteResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Deleted).To(BeTrue())

		_, err := os.Stat(volDir)
		Expect(os.IsNotExist(err)).To(BeTrue())

		// 同级 volume 目录与存储根都不受影响
		_, err = os.Stat(filepath.Join(rootDir, testBasePath))
		Expect(err).NotTo(HaveOccurred())
		_, err = os.Stat(rootDir)
		Expect(err).NotTo(HaveOccurred())
	})

	It("is idempotent when the volume directory does not exist", func() {
		Expect(os.RemoveAll(volDir)).To(Succeed())

		w := doDeleteVolume(router, testVolumeBasePath)
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp DeleteResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Deleted).To(BeTrue())
	})

	It("rejects a missing base_path with 400", func() {
		w := doDeleteVolume(router, "")
		Expect(w.Code).To(Equal(http.StatusBadRequest))
	})

	DescribeTable("rejects base paths outside the volume layout",
		func(basePath string) {
			w := doDeleteVolume(router, basePath)
			Expect(w.Code).To(Equal(http.StatusBadRequest))

			// 目录必须原样保留
			_, err := os.Stat(volDir)
			Expect(err).NotTo(HaveOccurred())
		},
		Entry("wrong prefix", "volumes/0123456789abcdef0123456789abcdef"),
		Entry("legacy short name", testBasePath),
		Entry("uppercase hex", "app/0123456789ABCDEF0123456789ABCDEF"),
		Entry("too short", "app/0123456789abcdef"),
		Entry("nested below a volume", testVolumeBasePath+"/nested"),
		Entry("traversal", "app/../../etc"),
		Entry("absolute path", "/app/0123456789abcdef0123456789abcdef"),
		Entry("storage root", "."),
		Entry("bare app dir", "app"),
	)

	It("refuses to delete when the volume path is a regular file", func() {
		Expect(os.RemoveAll(volDir)).To(Succeed())
		Expect(os.WriteFile(volDir, []byte("not a dir"), 0o644)).To(Succeed())

		w := doDeleteVolume(router, testVolumeBasePath)
		Expect(w.Code).To(Equal(http.StatusBadRequest))
		_, err := os.Stat(volDir)
		Expect(err).NotTo(HaveOccurred())
	})

	It("refuses to delete when the volume path is a symlink", func() {
		Expect(os.RemoveAll(volDir)).To(Succeed())
		Expect(os.Symlink(rootDir, volDir)).To(Succeed())

		w := doDeleteVolume(router, testVolumeBasePath)
		Expect(w.Code).To(Equal(http.StatusBadRequest))

		// 符号链接的目标(存储根)必须完好
		_, err := os.Stat(rootDir)
		Expect(err).NotTo(HaveOccurred())
	})
})
