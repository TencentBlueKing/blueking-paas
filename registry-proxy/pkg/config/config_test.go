package config

import (
	"os"
	"path/filepath"
	"strings"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

const validConfig = `
listen: ":8443"
tls:
  cert_file: /tls/tls.crt
  key_file: /tls/tls.key
audience: "bkpaas-registry-proxy:default-main"
jwks_file: /jwks/jwks.json
upstream_docker_config_file: /secrets/config.json
upload_session:
  key_file: /secrets/upload.key
upstreams:
  - alias: mirrors-example-com
    url: https://mirrors.example.com
  - alias: registry-local-5000
    url: http://registry.local:5000
    skip_tls_verify: true
`

var _ = Describe("Parse", func() {
	It("applies defaults to a valid config", func() {
		cfg, err := Parse([]byte(validConfig))
		Expect(err).NotTo(HaveOccurred())
		Expect(cfg.AdminListen).To(Equal(":9090"))
		Expect(cfg.UpstreamTokenMaxTTL).To(Equal(10 * time.Minute))
		Expect(cfg.UploadSession.TTL).To(Equal(time.Hour))

		u, err := cfg.Upstreams[1].ParseURL()
		Expect(err).NotTo(HaveOccurred())
		Expect(u.String()).To(Equal("http://registry.local:5000"))
	})

	It("accepts config.example.yaml", func() {
		_, err := Load("../../config.example.yaml")
		Expect(err).NotTo(HaveOccurred())
	})

	DescribeTable("rejects",
		func(replacements []string, want string) {
			raw := strings.NewReplacer(replacements...).Replace(validConfig)
			_, err := Parse([]byte(raw))
			Expect(err).To(MatchError(ContainSubstring(want)))
		},
		Entry("unknown field", []string{"listen:", "lsiten:"}, "field lsiten not found"),
		Entry("missing tls", []string{"  cert_file: /tls/tls.crt\n", ""}, "tls.cert_file and tls.key_file are required"),
		Entry("tls with plain_http", []string{`listen: ":8443"`, "plain_http: true"}, "mutually exclusive"),
		Entry("audience without prefix", []string{"bkpaas-registry-proxy:default-main", "default-main"}, "audience must be"),
		Entry("audience without cluster", []string{"bkpaas-registry-proxy:default-main", "bkpaas-registry-proxy:"}, "audience must be"),
		Entry("missing jwks", []string{"jwks_file: /jwks/jwks.json", ""}, "jwks_file is required"),
		Entry("missing upstream credentials", []string{"upstream_docker_config_file: /secrets/config.json", ""},
			"upstream_docker_config_file is required"),
		Entry("missing upload key", []string{"  key_file: /secrets/upload.key", "  ttl: 1h"}, "upload_session.key_file is required"),
		Entry("alias mismatch", []string{"alias: mirrors-example-com", "alias: mirrors"}, `must equal "mirrors-example-com"`),
		Entry("alias with dot", []string{"alias: mirrors-example-com", "alias: mirrors.example.com"}, "must equal"),
		Entry("url with path", []string{"https://mirrors.example.com", "https://mirrors.example.com/v2"}, "without path"),
		Entry("url scheme", []string{"https://mirrors.example.com", "ftp://mirrors.example.com"}, "scheme must be"),
		Entry("duplicated alias", []string{
			"http://registry.local:5000", "https://mirrors.example.com",
			"alias: registry-local-5000", "alias: mirrors-example-com",
		}, "duplicated alias"),
	)

	It("rejects a config without upstreams", func() {
		_, err := Parse([]byte("audience: x\n"))
		Expect(err).To(MatchError(ContainSubstring("at least one upstream")))
	})
})

var _ = Describe("ReadUploadSessionKeys", func() {
	var good, short string

	BeforeEach(func() {
		dir := GinkgoT().TempDir()
		good, short = filepath.Join(dir, "good"), filepath.Join(dir, "short")
		Expect(os.WriteFile(good, []byte(strings.Repeat("k", 32)+"\n"), 0o600)).To(Succeed())
		Expect(os.WriteFile(short, []byte("short\n"), 0o600)).To(Succeed())
	})

	It("trims whitespace from the key", func() {
		cfg := &Config{UploadSession: UploadSessionConfig{KeyFile: good}}
		k, _, err := cfg.ReadUploadSessionKeys()
		Expect(err).NotTo(HaveOccurred())
		Expect(k).To(HaveLen(32))
	})

	It("rejects a short previous key", func() {
		cfg := &Config{UploadSession: UploadSessionConfig{KeyFile: good, PreviousKeyFile: short}}
		_, _, err := cfg.ReadUploadSessionKeys()
		Expect(err).To(HaveOccurred())
	})

	It("rejects a missing key file", func() {
		cfg := &Config{UploadSession: UploadSessionConfig{KeyFile: filepath.Join(filepath.Dir(good), "missing")}}
		_, _, err := cfg.ReadUploadSessionKeys()
		Expect(err).To(HaveOccurred())
	})
})
