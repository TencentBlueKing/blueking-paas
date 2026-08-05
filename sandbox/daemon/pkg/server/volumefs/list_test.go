package volumefs

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"time"

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
	if req.Since != "" {
		q.Set("since", req.Since)
	}
	if req.Until != "" {
		q.Set("until", req.Until)
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

	It("reports file and directory totals in extra_data", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("a"), 0o644)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(jailRoot, "b.json"), []byte("{}"), 0o644)).To(Succeed())
		Expect(os.MkdirAll(filepath.Join(jailRoot, "sub"), 0o755)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath, PageSize: 1})
		Expect(w.Code).To(Equal(http.StatusOK))

		var payload struct {
			Count     int        `json:"count"`
			Results   []FileItem `json:"results"`
			ExtraData struct {
				Files     int `json:"files"`
				Directory int `json:"directory"`
			} `json:"extra_data"`
		}
		Expect(json.Unmarshal(w.Body.Bytes(), &payload)).To(Succeed())
		Expect(payload.Count).To(Equal(3))
		Expect(payload.Results).To(HaveLen(1))
		Expect(payload.ExtraData.Files).To(Equal(2))
		Expect(payload.ExtraData.Directory).To(Equal(1))
	})

	It("infers mime by extension", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "report.html"), []byte("<html>"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Results[0].Mime).To(HavePrefix("text/html"))
	})

	// .txt 等常见文本扩展名不在 Go 标准库内置表内, 且 alpine 运行镜像无 /etc/mime.types,
	// 必须由内置兜底表识别, 否则会被误报为 application/octet-stream。
	It("infers plain text mime for .txt via builtin fallback", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("HI"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Results[0].Mime).To(HavePrefix("text/plain"))
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

	It("sorts the complete recursive result before paginating", func() {
		Expect(os.MkdirAll(filepath.Join(jailRoot, "a"), 0o755)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(jailRoot, "a", "nested.txt"), []byte("nested"), 0o644)).To(Succeed())
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("a"), 0o644)).To(Succeed())

		w := doList(router, ListRequest{BasePath: testBasePath, Recursive: true, PageSize: 2})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Results).To(HaveLen(2))
		Expect(resp.Results[0].Path).To(Equal("a"))
		Expect(resp.Results[1].Path).To(Equal("a.txt"))
	})

	It("filters entries in an inclusive since/until range before paginating", func() {
		older := filepath.Join(jailRoot, "older.txt")
		atSince := filepath.Join(jailRoot, "at-since.txt")
		inRange := filepath.Join(jailRoot, "in-range.txt")
		atUntil := filepath.Join(jailRoot, "at-until.txt")
		newer := filepath.Join(jailRoot, "newer.txt")
		for _, path := range []string{older, atSince, inRange, atUntil, newer} {
			Expect(os.WriteFile(path, []byte("x"), 0o644)).To(Succeed())
		}

		since := time.Date(2026, time.June, 24, 10, 23, 11, 0, time.UTC)
		until := since.Add(2 * time.Second)
		Expect(os.Chtimes(older, since.Add(-time.Second), since.Add(-time.Second))).To(Succeed())
		Expect(os.Chtimes(atSince, since, since)).To(Succeed())
		Expect(os.Chtimes(inRange, since.Add(time.Second), since.Add(time.Second))).To(Succeed())
		Expect(os.Chtimes(atUntil, until, until)).To(Succeed())
		Expect(os.Chtimes(newer, until.Add(time.Second), until.Add(time.Second))).To(Succeed())

		w := doList(router, ListRequest{
			BasePath: testBasePath,
			Since:    since.Format(time.RFC3339),
			Until:    until.Format(time.RFC3339),
			PageSize: 1,
		})
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Count).To(Equal(3))
		Expect(resp.Results).To(ConsistOf(HaveField("Path", "at-since.txt")))
	})

	It("rejects invalid since and until filters", func() {
		w := doList(router, ListRequest{BasePath: testBasePath, Since: "not-a-time"})
		Expect(w.Code).To(Equal(http.StatusBadRequest))

		w = doList(router, ListRequest{BasePath: testBasePath, Until: "not-a-time"})
		Expect(w.Code).To(Equal(http.StatusBadRequest))
	})

	It("rejects a since value after until", func() {
		w := doList(router, ListRequest{
			BasePath: testBasePath,
			Since:    "2026-06-25T00:00:00Z",
			Until:    "2026-06-24T00:00:00Z",
		})
		Expect(w.Code).To(Equal(http.StatusBadRequest))
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
		for i := 0; i <= maxPageSize; i++ {
			name := filepath.Join(jailRoot, fmt.Sprintf("%03d.txt", i))
			Expect(os.WriteFile(name, []byte("x"), 0o644)).To(Succeed())
		}
		w := doList(router, ListRequest{BasePath: testBasePath, Page: 1, PageSize: 100000})
		var resp ListResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Count).To(Equal(maxPageSize + 1))
		Expect(resp.Results).To(HaveLen(maxPageSize))

		w = doList(router, ListRequest{BasePath: testBasePath, Page: 2, PageSize: maxPageSize})
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Count).To(Equal(maxPageSize + 1))
		Expect(resp.Results).To(HaveLen(1))
		Expect(resp.Results[0].Path).To(Equal(fmt.Sprintf("%03d.txt", maxPageSize)))
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
