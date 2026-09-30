package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
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

func TestParseValid(t *testing.T) {
	cfg, err := Parse([]byte(validConfig))
	if err != nil {
		t.Fatal(err)
	}
	if cfg.AdminListen != ":9090" || cfg.UpstreamTokenMaxTTL != 10*time.Minute || cfg.UploadSession.TTL != time.Hour {
		t.Fatalf("defaults not applied: %+v", cfg)
	}
	u, err := cfg.Upstreams[1].ParseURL()
	if err != nil || u.String() != "http://registry.local:5000" {
		t.Fatalf("ParseURL = %v, %v", u, err)
	}
}

func TestExampleConfigIsValid(t *testing.T) {
	if _, err := Load("../../config.example.yaml"); err != nil {
		t.Fatal(err)
	}
}

func TestParseRejects(t *testing.T) {
	cases := map[string]struct {
		old, new string
		want     string
	}{
		"unknown field":      {"listen:", "lsiten:", "field lsiten not found"},
		"missing tls":        {"  cert_file: /tls/tls.crt\n", "", "tls.cert_file and tls.key_file are required"},
		"tls with plain":     {"listen: \":8443\"", "plain_http: true", "mutually exclusive"},
		"audience prefix":    {"bkpaas-registry-proxy:default-main", "default-main", "audience must be"},
		"audience no name":   {"bkpaas-registry-proxy:default-main", "bkpaas-registry-proxy:", "audience must be"},
		"missing jwks":       {"jwks_file: /jwks/jwks.json", "", "jwks_file is required"},
		"missing creds":      {"upstream_docker_config_file: /secrets/config.json", "", "upstream_docker_config_file is required"},
		"missing upload key": {"  key_file: /secrets/upload.key", "  ttl: 1h", "upload_session.key_file is required"},
		"alias mismatch":     {"alias: mirrors-example-com", "alias: mirrors", `must equal "mirrors-example-com"`},
		"alias with dot":     {"alias: mirrors-example-com", "alias: mirrors.example.com", "must equal"},
		"url with path":      {"https://mirrors.example.com", "https://mirrors.example.com/v2", "without path"},
		"url scheme":         {"https://mirrors.example.com", "ftp://mirrors.example.com", "scheme must be"},
		"duplicated alias":   {"http://registry.local:5000", "https://mirrors.example.com", "duplicated alias"},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			raw := strings.Replace(validConfig, tc.old, tc.new, 1)
			if name == "duplicated alias" {
				raw = strings.Replace(raw, "alias: registry-local-5000", "alias: mirrors-example-com", 1)
			}
			_, err := Parse([]byte(raw))
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("err = %v, want containing %q", err, tc.want)
			}
		})
	}
	if _, err := Parse([]byte("audience: x\n")); err == nil || !strings.Contains(err.Error(), "at least one upstream") {
		t.Fatalf("empty config: err = %v", err)
	}
}

func TestReadUploadSessionKeys(t *testing.T) {
	dir := t.TempDir()
	good := filepath.Join(dir, "good")
	short := filepath.Join(dir, "short")
	_ = os.WriteFile(good, []byte(strings.Repeat("k", 32)+"\n"), 0o600)
	_ = os.WriteFile(short, []byte("short\n"), 0o600)

	cfg := &Config{UploadSession: UploadSessionConfig{KeyFile: good}}
	if k, _, err := cfg.ReadUploadSessionKeys(); err != nil || len(k) != 32 {
		t.Fatalf("key len = %d, err = %v", len(k), err)
	}
	cfg.UploadSession.PreviousKeyFile = short
	if _, _, err := cfg.ReadUploadSessionKeys(); err == nil {
		t.Fatal("short previous key must be rejected")
	}
	cfg.UploadSession.KeyFile = filepath.Join(dir, "missing")
	if _, _, err := cfg.ReadUploadSessionKeys(); err == nil {
		t.Fatal("missing key file must be rejected")
	}
}
