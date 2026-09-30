package policy

import (
	"encoding/json"
	"net/http"
	"net/url"
	"os"
	"testing"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

// 用例移植自参考实现 reference/policy_test.go，样例取自 samples/

func loadSampleClaims(t *testing.T, name string) *buildtoken.Claims {
	t.Helper()
	raw, err := os.ReadFile("testdata/" + name)
	if err != nil {
		t.Fatal(err)
	}
	c := &buildtoken.Claims{}
	if err := json.Unmarshal(raw, c); err != nil {
		t.Fatal(err)
	}
	return c
}

const (
	app   = "/v2/mirrors-example-com/bkpaas/docker/demo/default"
	cache = "/v2/mirrors-example-com/bkpaas/docker/demo/default/dockerbuild-cache"
	other = "/v2/mirrors-example-com/bkpaas/docker/other-app/default"
	base  = "/v2/mirrors-example-com/python/python"
)

type policyCase struct {
	name      string
	method    string
	path      string
	query     string
	status    int
	deny      string
	dropMount bool
}

func runCases(t *testing.T, c *buildtoken.Claims, cases []policyCase) {
	t.Helper()
	upstreams := map[string]bool{"mirrors-example-com": true}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			q, _ := url.ParseQuery(tc.query)
			d := Decide(c, upstreams, tc.method, oci.ParseRoute(tc.method, tc.path, q))
			if d.Status != tc.status || d.Deny != tc.deny || d.DropMount != tc.dropMount {
				t.Fatalf("got status=%d deny=%q dropMount=%v, want status=%d deny=%q dropMount=%v",
					d.Status, d.Deny, d.DropMount, tc.status, tc.deny, tc.dropMount)
			}
		})
	}
}

// 推送、未授权 tag、pull_deny、pull、DELETE 五类请求
func TestAcceptanceFiveClasses(t *testing.T) {
	runCases(t, loadSampleClaims(t, "claims-kaniko.json"), []policyCase{
		{"推送授权仓库", http.MethodPut, app + "/manifests/main-3f2a1bc", "", 0, "", false},
		{"推送未授权 tag", http.MethodPut, app + "/manifests/latest", "", 403, oci.DenyTagNotGranted, false},
		{"拉取 pull_deny 前缀", http.MethodGet, other + "/manifests/v1", "", 403, oci.DenyPullDenied, false},
		{"拉取 pull 前缀", http.MethodGet, base + "/manifests/3.10-slim", "", 0, "", false},
		{"DELETE", http.MethodDelete, app + "/manifests/main-3f2a1bc", "", 403, oci.DenyDeleteNotAllowed, false},
	})
}

func TestPushRules(t *testing.T) {
	runCases(t, loadSampleClaims(t, "claims-kaniko.json"), []policyCase{
		{"缓存仓库任意 tag", http.MethodPut, cache + "/manifests/0f3c9a", "", 0, "", false},
		{"缓存仓库按 digest 推送", http.MethodPut, cache + "/manifests/sha256:ab12", "", 0, "", false},
		{"产物仓库按 digest 推送", http.MethodPut, app + "/manifests/sha256:ab12", "", 403, oci.DenyTagNotGranted, false},
		{"未授权仓库发起上传", http.MethodPost, other + "/blobs/uploads/", "", 403, oci.DenyPushNotGranted, false},
		{"pull 前缀仓库不可推送", http.MethodPost, base + "/blobs/uploads/", "", 403, oci.DenyPushNotGranted, false},
		{"上传会话续传", http.MethodPatch, app + "/blobs/uploads/s1", "", 0, "", false},
		{"上传会话完成", http.MethodPut, app + "/blobs/uploads/s1", "digest=sha256:ab12", 0, "", false},
		{"DELETE 上传会话", http.MethodDelete, app + "/blobs/uploads/s1", "", 403, oci.DenyDeleteNotAllowed, false},
		{"同上游可读来源 mount", http.MethodPost, app + "/blobs/uploads/", "mount=sha256:ab12&from=mirrors-example-com/python/python", 0, "", false},
		{"mount 来源命中 pull_deny 降级", http.MethodPost, app + "/blobs/uploads/", "mount=sha256:ab12&from=mirrors-example-com/bkpaas/docker/other-app/default", 0, "", true},
		{"跨上游 mount 降级", http.MethodPost, app + "/blobs/uploads/", "mount=sha256:ab12&from=docker-io/library/python", 0, "", true},
	})
}

func TestPullRules(t *testing.T) {
	runCases(t, loadSampleClaims(t, "claims-kaniko.json"), []policyCase{
		{"push 授权先于 pull_deny：读本应用产物", http.MethodHead, app + "/manifests/main-3f2a1bc", "", 0, "", false},
		{"push 授权先于 pull_deny：读本应用缓存 blob", http.MethodGet, cache + "/blobs/sha256:ab12", "", 0, "", false},
		{"本应用其他模块同样被 pull_deny", http.MethodGet, "/v2/mirrors-example-com/bkpaas/docker/demo/worker/manifests/v1", "", 403, oci.DenyPullDenied, false},
		{"pull_deny 前缀以 / 结尾，不误伤同名前缀", http.MethodGet, "/v2/mirrors-example-com/bkpaas/docker-base/python/manifests/3", "", 0, "", false},
		{"tags list", http.MethodGet, base + "/tags/list", "", 0, "", false},
	})
	exact := &buildtoken.Claims{Pull: []string{"mirrors-example-com/python/python"}}
	runCases(t, exact, []policyCase{
		{"精确匹配命中", http.MethodGet, base + "/manifests/3", "", 0, "", false},
		{"精确匹配不含子路径", http.MethodGet, base + "-slim/manifests/3", "", 403, oci.DenyPullNotGranted, false},
		{"其余一律拒绝", http.MethodGet, "/v2/mirrors-example-com/library/busybox/manifests/1", "", 403, oci.DenyPullNotGranted, false},
	})
}

func TestRoutes(t *testing.T) {
	runCases(t, loadSampleClaims(t, "claims-kaniko.json"), []policyCase{
		{"探活", http.MethodGet, "/v2/", "", 0, "", false},
		{"探活不支持的方法", http.MethodPost, "/v2/", "", 404, oci.DenyRouteNotFound, false},
		{"_catalog", http.MethodGet, "/v2/_catalog", "", 404, oci.DenyRouteNotFound, false},
		{"非 v2 路由", http.MethodGet, "/api/v1/projects", "", 404, oci.DenyRouteNotFound, false},
		{"仓库名大写", http.MethodGet, "/v2/mirrors-example-com/Python/python/manifests/3", "", 404, oci.DenyRouteNotFound, false},
		{"只有别名没有仓库", http.MethodGet, "/v2/mirrors-example-com/manifests/3", "", 404, oci.DenyRouteNotFound, false},
		{"路由不支持的方法", http.MethodPost, base + "/manifests/3", "", 404, oci.DenyRouteNotFound, false},
		{"未知上游别名", http.MethodGet, "/v2/docker-io/library/python/manifests/3", "", 403, oci.DenyUnknownUpstream, false},
		{"别名写成主机名", http.MethodGet, "/v2/mirrors.example.com/python/python/manifests/3", "", 403, oci.DenyUnknownUpstream, false},
	})
}

func TestCNBClaims(t *testing.T) {
	runCases(t, loadSampleClaims(t, "claims-cnb.json"), []policyCase{
		{"推送产物 tag", http.MethodPut, app + "/manifests/main-3f2a1bc", "", 0, "", false},
		{"推送缓存 tag", http.MethodPut, app + "/manifests/cnb-build-cache", "", 0, "", false},
		{"其他 tag", http.MethodPut, app + "/manifests/latest", "", 403, oci.DenyTagNotGranted, false},
		{"不再有独立缓存仓库", http.MethodPost, cache + "/blobs/uploads/", "", 403, oci.DenyPushNotGranted, false},
	})
}
