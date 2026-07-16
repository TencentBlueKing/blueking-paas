package pv

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func doStat(router *gin.Engine, req StatRequest) *httptest.ResponseRecorder {
	body, _ := json.Marshal(req)
	w := httptest.NewRecorder()
	httpReq, _ := http.NewRequest(http.MethodPost, "/files/stat", bytes.NewReader(body))
	httpReq.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, httpReq)
	return w
}

var _ = Describe("StatFile", func() {
	var (
		router   *gin.Engine
		rootDir  string
		jailRoot string
	)

	BeforeEach(func() {
		rootDir, jailRoot = newTestEnv()
		router = newTestRouter()
		router.POST("/files/stat", StatFile)
	})

	AfterEach(func() {
		os.RemoveAll(rootDir) // nolint
	})

	It("returns metadata for an existing file", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "report.html"), []byte("<html>"), 0o644)).To(Succeed())

		w := doStat(router, StatRequest{BasePath: testBasePath, RelPath: "report.html"})
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp StatResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Exists).To(BeTrue())
		Expect(resp.Size).To(Equal(int64(6)))
		Expect(resp.Mime).To(Equal("text/html"))
	})

	It("returns 200 with exists=false for a missing file", func() {
		w := doStat(router, StatRequest{BasePath: testBasePath, RelPath: "nope.txt"})
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp StatResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Exists).To(BeFalse())
	})

	It("rejects a jail escape with 403", func() {
		w := doStat(router, StatRequest{BasePath: testBasePath, RelPath: "../../etc/passwd"})
		Expect(w.Code).To(Equal(http.StatusForbidden))
	})
})
