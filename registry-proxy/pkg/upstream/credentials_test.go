package upstream

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func writeDockerConfig(content string) string {
	p := filepath.Join(GinkgoT().TempDir(), "config.json")
	Expect(os.WriteFile(p, []byte(content), 0o600)).To(Succeed())
	return p
}

var _ = Describe("LoadCredentials", func() {
	It("normalizes hosts and decodes every supported form", func() {
		creds, err := LoadCredentials(writeDockerConfig(`{"auths": {
			"Mirrors.Example.com": {"username": "u1", "password": "p1"},
			"https://registry.example.com:8443/v2/": {"auth": "dTI6cDI6d2l0aDpjb2xvbg=="},
			"static.example.com": {"registrytoken": "rt"}
		}}`))
		Expect(err).NotTo(HaveOccurred())
		Expect(creds).To(Equal(map[string]Credential{
			"mirrors.example.com":       {Username: "u1", Password: "p1"},
			"registry.example.com:8443": {Username: "u2", Password: "p2:with:colon"},
			"static.example.com":        {RegistryToken: "rt"},
		}))
	})

	DescribeTable("rejects without leaking credentials",
		func(content string) {
			_, err := LoadCredentials(writeDockerConfig(content))
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).NotTo(ContainSubstring("s3cr3t"))
		},
		Entry("identitytoken", `{"auths": {"a.com": {"identitytoken": "x"}}}`),
		Entry("empty entry", `{"auths": {"a.com": {}}}`),
		Entry("bad auth", `{"auths": {"a.com": {"auth": "!!"}}}`),
		Entry("duplicated host", `{"auths": {"a.com": {"auth": "YTpi"}, "https://a.com": {"auth": "YTpi"}}}`),
		Entry("invalid json", `{"auths": {"a.com": {"password": "s3cr3t"`),
	)
})

var _ = Describe("Credential", func() {
	It("is redacted when printed", func() {
		Expect(Credential{Username: "u", Password: "p"}.String()).To(Equal("<redacted>"))
	})
})

var _ = Describe("AliasOf", func() {
	DescribeTable("derives the alias from the host",
		func(host, want string) {
			Expect(AliasOf(host)).To(Equal(want))
		},
		Entry(nil, "mirrors.example.com", "mirrors-example-com"),
		Entry(nil, "docker.example.com", "docker-example-com"),
		Entry(nil, "registry.local:5000", "registry-local-5000"),
		Entry(nil, "127.0.0.1:25001", "127-0-0-1-25001"),
		Entry(nil, "Hub.Example.COM", "hub-example-com"),
		Entry(nil, "xn--fiq228c.com", "xn--fiq228c-com"),
	)

	DescribeTable("rejects hosts that do not derive a valid alias",
		func(host string) {
			_, err := AliasOf(host)
			Expect(err).To(HaveOccurred())
		},
		Entry(nil, ""),
		Entry(nil, "[::1]:5000"),
		Entry(nil, "a_b.com"),
		Entry(nil, "-a.com"),
		Entry(nil, "a.com."),
	)
})
