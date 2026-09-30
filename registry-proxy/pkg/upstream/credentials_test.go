package upstream

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeFile(t *testing.T, content string) string {
	t.Helper()
	p := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(p, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	return p
}

func TestLoadCredentials(t *testing.T) {
	p := writeFile(t, `{"auths": {
		"Mirrors.Example.com": {"username": "u1", "password": "p1"},
		"https://registry.example.com:8443/v2/": {"auth": "dTI6cDI6d2l0aDpjb2xvbg=="},
		"static.example.com": {"registrytoken": "rt"}
	}}`)
	creds, err := LoadCredentials(p)
	if err != nil {
		t.Fatal(err)
	}
	if c := creds["mirrors.example.com"]; c.Username != "u1" || c.Password != "p1" {
		t.Errorf("mirrors = %+v", c)
	}
	if c := creds["registry.example.com:8443"]; c.Username != "u2" || c.Password != "p2:with:colon" {
		t.Errorf("registry = %+v", c)
	}
	if c := creds["static.example.com"]; c.RegistryToken != "rt" {
		t.Errorf("static = %+v", c)
	}
}

func TestLoadCredentialsRejects(t *testing.T) {
	cases := map[string]string{
		"identitytoken": `{"auths": {"a.com": {"identitytoken": "x"}}}`,
		"empty entry":   `{"auths": {"a.com": {}}}`,
		"bad auth":      `{"auths": {"a.com": {"auth": "!!"}}}`,
		"duplicated":    `{"auths": {"a.com": {"auth": "YTpi"}, "https://a.com": {"auth": "YTpi"}}}`,
		"invalid json":  `{"auths": {"a.com": {"password": "s3cr3t"`,
	}
	for name, content := range cases {
		t.Run(name, func(t *testing.T) {
			_, err := LoadCredentials(writeFile(t, content))
			if err == nil {
				t.Fatal("want error")
			}
			if strings.Contains(err.Error(), "s3cr3t") {
				t.Fatal("error must not contain credentials")
			}
		})
	}
}

func TestCredentialStringIsRedacted(t *testing.T) {
	c := Credential{Username: "u", Password: "p"}
	if s := c.String(); strings.Contains(s, "p") && s != "<redacted>" {
		t.Fatalf("String() = %q", s)
	}
}

func TestAliasOf(t *testing.T) {
	ok := map[string]string{
		"mirrors.example.com": "mirrors-example-com",
		"docker.example.com":  "docker-example-com",
		"registry.local:5000": "registry-local-5000",
		"127.0.0.1:25001":     "127-0-0-1-25001",
		"Hub.Example.COM":     "hub-example-com",
		"xn--fiq228c.com":     "xn--fiq228c-com",
	}
	for host, want := range ok {
		if got, err := AliasOf(host); err != nil || got != want {
			t.Errorf("AliasOf(%q) = %q, %v; want %q", host, got, err, want)
		}
	}
	for _, host := range []string{"", "[::1]:5000", "a_b.com", "-a.com", "a.com."} {
		if got, err := AliasOf(host); err == nil {
			t.Errorf("AliasOf(%q) = %q, want error", host, got)
		}
	}
}
