package pv

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strconv"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func doList(router *gin.Engine, req ListRequest) *httptest.ResponseRecorder {
	q := url.Values{}
	q.Set("base_path", req.BasePath)
	if req.RelPath != "" {
		q.Set("rel_path", req.RelPath)
	}
	if req.Recursive {
		q.Set("is_recursive", "true")
	}
	if req.Page != 0 {
		q.Set("page", strconv.Itoa(req.Page))
	}
	if req.PageSize != 0 {
		q.Set("page_size", strconv.Itoa(req.PageSize))
	}
	w := httptest.NewRecorder()
	httpReq, _ := http.NewRequest(http.MethodGet, "/files/list?"+q.Encode(), nil)
	router.ServeHTTP(w, httpReq)
	return w
}

var _ = Describe("ListFiles", func() {
	var (
		router   *gin.Engine
		rootDir  string
		jailRoot string
	)

	BeforeEach(func() {
		rootDir, jailRoot = newTestEnv()
		router = newTestRouter()
		router.GET("/files/list", ListFiles)
	})

	AfterEach(func() {
		os.RemoveAll(rootDir) // nolint
	})

	It("lists files non-recursively", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("a"), 0o644)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(jailRoot, "b.json"), []byte("{}"), 0o644)).To(Succeed())
		Expect(os.MkdirAll(filepath.Join(jailRoot, "sub"), 0o755)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(jailRoot, "sub", "c.txt"), []byte("c"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath})
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		// a.txt, b.json, sub -> 3 top-level entries, sub/c.txt excluded
		Expect(resp.Count).To(Equal(3))
		Expect(resp.Results).To(HaveLen(3))
	})

	It("infers mime by extension", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "report.html"), []byte("<html>"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Results[0].Mime).To(Equal("text/html"))
	})

	// .txt 等常见文本扩展名不在 Go 标准库内置表内, 且 alpine 运行镜像无 /etc/mime.types,
	// 必须由内置兜底表识别, 否则会被误报为 application/octet-stream。
	It("infers plain text mime for .txt via builtin fallback", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("HI"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Results[0].Mime).To(Equal("text/plain"))
	})

	It("lists recursively including nested files", func() {
		Expect(os.MkdirAll(filepath.Join(jailRoot, "sub"), 0o755)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("a"), 0o644)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(jailRoot, "sub", "c.txt"), []byte("c"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath, Recursive: true})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		// a.txt, sub, sub/c.txt
		Expect(resp.Count).To(Equal(3))
	})

	It("handles an empty directory", func() {
		w := doList(router, ListRequest{BasePath: testBasePath})
		Expect(w.Code).To(Equal(http.StatusOK))
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Count).To(Equal(0))
		Expect(resp.Results).NotTo(BeNil())
	})

	It("clamps page_size to the max and paginates", func() {
		for i := 0; i < 10; i++ {
			name := filepath.Join(jailRoot, string(rune('a'+i))+".txt")
			Expect(os.WriteFile(name, []byte("x"), 0o644)).To(Succeed())
		}
		w := doList(router, ListRequest{BasePath: testBasePath, Page: 1, PageSize: 100000})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Count).To(Equal(10))
		Expect(resp.Results).To(HaveLen(10)) // all 10 fit under clamped 500
	})

	It("returns 404 for a missing directory", func() {
		w := doList(router, ListRequest{BasePath: testBasePath, RelPath: "does-not-exist"})
		Expect(w.Code).To(Equal(http.StatusNotFound))
	})

	It("returns 400 when the path is a file, not a directory", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("a"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath, RelPath: "a.txt"})
		Expect(w.Code).To(Equal(http.StatusBadRequest))
	})

	It("returns 400 when a file path is listed recursively", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("a"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath, RelPath: "a.txt", Recursive: true})
		Expect(w.Code).To(Equal(http.StatusBadRequest))
	})

	It("rejects a jail escape with 403", func() {
		w := doList(router, ListRequest{BasePath: testBasePath, RelPath: "../../"})
		Expect(w.Code).To(Equal(http.StatusForbidden))
	})

	It("rejects a directory symlink that points outside the jail", func() {
		outside := filepath.Join(rootDir, "outside")
		Expect(os.MkdirAll(outside, 0o755)).To(Succeed())
		Expect(os.Symlink(outside, filepath.Join(jailRoot, "escape"))).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath, RelPath: "escape"})
		Expect(w.Code).To(Equal(http.StatusForbidden))
	})

	It("rejects a missing base_path with 400", func() {
		w := doList(router, ListRequest{RelPath: "x"})
		Expect(w.Code).To(Equal(http.StatusBadRequest))
	})
})
