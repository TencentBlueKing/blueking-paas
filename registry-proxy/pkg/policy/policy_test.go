package policy

import (
	"encoding/json"
	"net/http"
	"net/url"
	"os"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

// 用例移植自参考实现 reference/policy_test.go，样例取自 samples/

const (
	app   = "/v2/mirrors-example-com/bkpaas/docker/demo/default"
	cache = "/v2/mirrors-example-com/bkpaas/docker/demo/default/dockerbuild-cache"
	other = "/v2/mirrors-example-com/bkpaas/docker/other-app/default"
	base  = "/v2/mirrors-example-com/python/python"
)

func loadSampleClaims(name string) *buildtoken.Claims {
	raw, err := os.ReadFile("testdata/" + name)
	Expect(err).NotTo(HaveOccurred())
	c := &buildtoken.Claims{}
	Expect(json.Unmarshal(raw, c)).To(Succeed())
	return c
}

func decide(c *buildtoken.Claims, method, path, query string) Decision {
	q, _ := url.ParseQuery(query)
	return Decide(c, map[string]bool{"mirrors-example-com": true}, method, oci.ParseRoute(method, path, q))
}

var (
	allow      = Decision{}
	allowMount = Decision{DropMount: true}
)

func deny(status int, reason string) Decision { return Decision{Status: status, Deny: reason} }

var _ = Describe("Decide", func() {
	Context("with kaniko claims", func() {
		var claims *buildtoken.Claims

		BeforeEach(func() { claims = loadSampleClaims("claims-kaniko.json") })

		DescribeTable("acceptance: push, unauthorized tag, pull_deny, pull and DELETE",
			func(method, path string, want Decision) {
				Expect(decide(claims, method, path, "")).To(Equal(want))
			},
			Entry("推送授权仓库", http.MethodPut, app+"/manifests/main-3f2a1bc", allow),
			Entry("推送未授权 tag", http.MethodPut, app+"/manifests/latest", deny(403, oci.DenyTagNotGranted)),
			Entry("拉取 pull_deny 前缀", http.MethodGet, other+"/manifests/v1", deny(403, oci.DenyPullDenied)),
			Entry("拉取 pull 前缀", http.MethodGet, base+"/manifests/3.10-slim", allow),
			Entry("DELETE", http.MethodDelete, app+"/manifests/main-3f2a1bc", deny(403, oci.DenyDeleteNotAllowed)),
		)

		DescribeTable("push",
			func(method, path, query string, want Decision) {
				Expect(decide(claims, method, path, query)).To(Equal(want))
			},
			Entry("缓存仓库任意 tag", http.MethodPut, cache+"/manifests/0f3c9a", "", allow),
			Entry("缓存仓库按 digest 推送", http.MethodPut, cache+"/manifests/sha256:ab12", "", allow),
			Entry("产物仓库按 digest 推送", http.MethodPut, app+"/manifests/sha256:ab12", "", deny(403, oci.DenyTagNotGranted)),
			Entry("未授权仓库发起上传", http.MethodPost, other+"/blobs/uploads/", "", deny(403, oci.DenyPushNotGranted)),
			Entry("pull 前缀仓库不可推送", http.MethodPost, base+"/blobs/uploads/", "", deny(403, oci.DenyPushNotGranted)),
			Entry("上传会话续传", http.MethodPatch, app+"/blobs/uploads/s1", "", allow),
			Entry("上传会话完成", http.MethodPut, app+"/blobs/uploads/s1", "digest=sha256:ab12", allow),
			Entry("DELETE 上传会话", http.MethodDelete, app+"/blobs/uploads/s1", "", deny(403, oci.DenyDeleteNotAllowed)),
			Entry("同上游可读来源 mount", http.MethodPost, app+"/blobs/uploads/",
				"mount=sha256:ab12&from=mirrors-example-com/python/python", allow),
			Entry("mount 来源命中 pull_deny 降级", http.MethodPost, app+"/blobs/uploads/",
				"mount=sha256:ab12&from=mirrors-example-com/bkpaas/docker/other-app/default", allowMount),
			Entry("跨上游 mount 降级", http.MethodPost, app+"/blobs/uploads/",
				"mount=sha256:ab12&from=docker-io/library/python", allowMount),
		)

		DescribeTable("pull",
			func(method, path string, want Decision) {
				Expect(decide(claims, method, path, "")).To(Equal(want))
			},
			Entry("push 授权先于 pull_deny：读本应用产物", http.MethodHead, app+"/manifests/main-3f2a1bc", allow),
			Entry("push 授权先于 pull_deny：读本应用缓存 blob", http.MethodGet, cache+"/blobs/sha256:ab12", allow),
			Entry("本应用其他模块同样被 pull_deny", http.MethodGet,
				"/v2/mirrors-example-com/bkpaas/docker/demo/worker/manifests/v1", deny(403, oci.DenyPullDenied)),
			Entry("pull_deny 前缀以 / 结尾，不误伤同名前缀", http.MethodGet,
				"/v2/mirrors-example-com/bkpaas/docker-base/python/manifests/3", allow),
			Entry("tags list", http.MethodGet, base+"/tags/list", allow),
		)

		DescribeTable("routes",
			func(method, path string, want Decision) {
				Expect(decide(claims, method, path, "")).To(Equal(want))
			},
			Entry("探活", http.MethodGet, "/v2/", allow),
			Entry("探活不支持的方法", http.MethodPost, "/v2/", deny(404, oci.DenyRouteNotFound)),
			Entry("_catalog", http.MethodGet, "/v2/_catalog", deny(404, oci.DenyRouteNotFound)),
			Entry("非 v2 路由", http.MethodGet, "/api/v1/projects", deny(404, oci.DenyRouteNotFound)),
			Entry("仓库名大写", http.MethodGet, "/v2/mirrors-example-com/Python/python/manifests/3", deny(404, oci.DenyRouteNotFound)),
			Entry("只有别名没有仓库", http.MethodGet, "/v2/mirrors-example-com/manifests/3", deny(404, oci.DenyRouteNotFound)),
			Entry("路由不支持的方法", http.MethodPost, base+"/manifests/3", deny(404, oci.DenyRouteNotFound)),
			Entry("未知上游别名", http.MethodGet, "/v2/docker-io/library/python/manifests/3", deny(403, oci.DenyUnknownUpstream)),
			Entry("别名写成主机名", http.MethodGet, "/v2/mirrors.example.com/python/python/manifests/3",
				deny(403, oci.DenyUnknownUpstream)),
		)
	})

	Context("with exact pull entries", func() {
		claims := &buildtoken.Claims{Pull: []string{"mirrors-example-com/python/python"}}

		DescribeTable("pull",
			func(path string, want Decision) {
				Expect(decide(claims, http.MethodGet, path, "")).To(Equal(want))
			},
			Entry("精确匹配命中", base+"/manifests/3", allow),
			Entry("精确匹配不含子路径", base+"-slim/manifests/3", deny(403, oci.DenyPullNotGranted)),
			Entry("其余一律拒绝", "/v2/mirrors-example-com/library/busybox/manifests/1", deny(403, oci.DenyPullNotGranted)),
		)
	})

	Context("with CNB claims", func() {
		var claims *buildtoken.Claims

		BeforeEach(func() { claims = loadSampleClaims("claims-cnb.json") })

		DescribeTable("push",
			func(method, path string, want Decision) {
				Expect(decide(claims, method, path, "")).To(Equal(want))
			},
			Entry("推送产物 tag", http.MethodPut, app+"/manifests/main-3f2a1bc", allow),
			Entry("推送缓存 tag", http.MethodPut, app+"/manifests/cnb-build-cache", allow),
			Entry("其他 tag", http.MethodPut, app+"/manifests/latest", deny(403, oci.DenyTagNotGranted)),
			Entry("不再有独立缓存仓库", http.MethodPost, cache+"/blobs/uploads/", deny(403, oci.DenyPushNotGranted)),
		)
	})
})
