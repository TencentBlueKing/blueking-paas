package volumefs

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func doExport(router *gin.Engine, req ExportFileRequest) *httptest.ResponseRecorder {
	body, _ := json.Marshal(req)
	w := httptest.NewRecorder()
	httpReq, _ := http.NewRequest(http.MethodPost, "/files/export", bytes.NewReader(body))
	httpReq.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, httpReq)
	return w
}

var _ = Describe("ExportFile", func() {
	var (
		router   *gin.Engine
		rootDir  string
		jailRoot string
	)

	BeforeEach(func() {
		rootDir, jailRoot = newTestEnv()
		router = newTestRouter()
		router.POST("/files/export", ExportFile)
	})

	AfterEach(func() {
		os.RemoveAll(rootDir) // nolint
	})

	It("uploads the file via PUT and returns sha256/size", func() {
		content := []byte("artifact content")
		Expect(os.WriteFile(filepath.Join(jailRoot, "out.bin"), content, 0o644)).To(Succeed())

		var received []byte
		var gotMethod string
		upstream := httptest.NewServer(http.HandlerFunc(func(rw http.ResponseWriter, r *http.Request) {
			gotMethod = r.Method
			received, _ = io.ReadAll(r.Body)
			rw.WriteHeader(http.StatusOK)
		}))
		defer upstream.Close()

		w := doExport(router, ExportFileRequest{BasePath: testBasePath, RelPath: "out.bin", UploadURL: upstream.URL})
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp ExportFileResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())

		sum := sha256.Sum256(content)
		Expect(resp.Sha256).To(Equal(hex.EncodeToString(sum[:])))
		Expect(resp.Size).To(Equal(int64(len(content))))
		Expect(gotMethod).To(Equal(http.MethodPut))
		Expect(received).To(Equal(content))
	})

	It("returns 502 when the upstream upload fails", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "out.bin"), []byte("x"), 0o644)).To(Succeed())

		upstream := httptest.NewServer(http.HandlerFunc(func(rw http.ResponseWriter, r *http.Request) {
			rw.WriteHeader(http.StatusInternalServerError)
		}))
		defer upstream.Close()

		w := doExport(router, ExportFileRequest{BasePath: testBasePath, RelPath: "out.bin", UploadURL: upstream.URL})
		Expect(w.Code).To(Equal(http.StatusBadGateway))
	})

	It("returns 413 when the file exceeds exportMaxSize", func() {
		// 用 truncate 造稀疏大文件(不实际写盘), 仅用于触发 size 超限。
		bigPath := filepath.Join(jailRoot, "big.bin")
		f, err := os.Create(bigPath)
		Expect(err).NotTo(HaveOccurred())
		Expect(f.Truncate(exportMaxSize + 1)).To(Succeed())
		Expect(f.Close()).To(Succeed())

		w := doExport(router, ExportFileRequest{BasePath: testBasePath, RelPath: "big.bin", UploadURL: "http://unused"})
		Expect(w.Code).To(Equal(http.StatusRequestEntityTooLarge))
	})

	It("returns 404 for a missing file", func() {
		w := doExport(router, ExportFileRequest{BasePath: testBasePath, RelPath: "nope.bin", UploadURL: "http://unused"})
		Expect(w.Code).To(Equal(http.StatusNotFound))
	})

	It("rejects a jail escape with 403", func() {
		w := doExport(router, ExportFileRequest{BasePath: testBasePath, RelPath: "../../etc/passwd", UploadURL: "http://unused"})
		Expect(w.Code).To(Equal(http.StatusForbidden))
	})
})
