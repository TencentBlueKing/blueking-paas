// Package config 加载并校验镜像代理的配置文件。
//
// 凡是影响安全或转发目标的配置都没有缺省值：缺失或非法时启动失败，不以默认值运行。
package config

import (
	"bytes"
	"errors"
	"fmt"
	"net/url"
	"os"
	"strings"
	"time"

	"go.yaml.in/yaml/v3"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

// AudiencePrefix 是构建 token aud 的固定前缀，后接 apiserver 中的集群名
const AudiencePrefix = "bkpaas-registry-proxy:"

// MinUploadSessionKeyLen 是上传会话签名密钥的最小字节数
const MinUploadSessionKeyLen = 32

// Config 是代理的完整配置
type Config struct {
	// Listen 是构建容器访问的监听地址
	Listen string `yaml:"listen"`
	// AdminListen 提供 /healthz、/readyz、/metrics，明文 HTTP，不应暴露给构建 Pod
	AdminListen string `yaml:"admin_listen"`
	// TLS 为代理提供 HTTPS 的证书，与 PlainHTTP 二选一
	TLS TLSConfig `yaml:"tls"`
	// PlainHTTP 以明文 HTTP 提供服务，仅用于本地测试；构建 token 会以明文在网络中传输
	PlainHTTP bool `yaml:"plain_http"`

	// Audience 是本代理要求的构建 token aud，格式为 bkpaas-registry-proxy:<集群名>
	Audience string `yaml:"audience"`
	// JWKSFile 是 apiserver 导出的构建 token 公钥集合
	JWKSFile string `yaml:"jwks_file"`

	// UpstreamDockerConfigFile 是上游凭证，docker config.json 格式，按主机名匹配上游
	UpstreamDockerConfigFile string `yaml:"upstream_docker_config_file"`
	// UpstreamTokenMaxTTL 是上游 Authorization 的最长缓存时间，上游返回的 expires_in 更短时以其为准
	UpstreamTokenMaxTTL time.Duration `yaml:"upstream_token_max_ttl"`
	// UpstreamResponseHeaderTimeout 是发出请求（含请求体）后等待上游响应头的超时
	UpstreamResponseHeaderTimeout time.Duration    `yaml:"upstream_response_header_timeout"`
	Upstreams                     []UpstreamConfig `yaml:"upstreams"`

	UploadSession UploadSessionConfig `yaml:"upload_session"`

	// ShutdownTimeout 是收到退出信号后等待在途请求结束的最长时间
	ShutdownTimeout time.Duration `yaml:"shutdown_timeout"`
}

type TLSConfig struct {
	CertFile string `yaml:"cert_file"`
	KeyFile  string `yaml:"key_file"`
}

// UpstreamConfig 对应配置中的 upstreams[] 字段
type UpstreamConfig struct {
	// Alias 必须等于按 URL 主机推导的别名
	Alias string `yaml:"alias"`
	// URL 形如 https://<主机>，协议即上游使用的协议
	URL           string `yaml:"url"`
	SkipTLSVerify bool   `yaml:"skip_tls_verify"`
}

// UploadSessionConfig 配置上传会话 token 的签名。多副本之间必须使用相同的密钥，
// 否则上传会话落到其他副本时无法继续。
type UploadSessionConfig struct {
	KeyFile string `yaml:"key_file"`
	// PreviousKeyFile 为轮换前的旧密钥，只用于校验在途的上传会话
	PreviousKeyFile string        `yaml:"previous_key_file"`
	TTL             time.Duration `yaml:"ttl"`
}

// Load 读取、补全缺省值并校验配置文件
func Load(path string) (*Config, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}
	return Parse(raw)
}

// Parse 解析配置内容，拒绝未知字段
func Parse(raw []byte) (*Config, error) {
	cfg := &Config{}
	dec := yaml.NewDecoder(bytes.NewReader(raw))
	dec.KnownFields(true)
	if err := dec.Decode(cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}
	cfg.setDefaults()
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	return cfg, nil
}

func (c *Config) setDefaults() {
	if c.Listen == "" {
		c.Listen = ":8443"
	}
	if c.AdminListen == "" {
		c.AdminListen = ":9090"
	}
	if c.UpstreamTokenMaxTTL == 0 {
		c.UpstreamTokenMaxTTL = 10 * time.Minute
	}
	if c.UpstreamResponseHeaderTimeout == 0 {
		c.UpstreamResponseHeaderTimeout = 5 * time.Minute
	}
	if c.UploadSession.TTL == 0 {
		c.UploadSession.TTL = time.Hour
	}
	if c.ShutdownTimeout == 0 {
		c.ShutdownTimeout = 30 * time.Second
	}
}

// Validate 校验配置，返回所有问题而不是只返回第一个
func (c *Config) Validate() error {
	var errs []error
	add := func(format string, args ...any) { errs = append(errs, fmt.Errorf(format, args...)) }

	hasTLS := c.TLS.CertFile != "" || c.TLS.KeyFile != ""
	switch {
	case c.PlainHTTP && hasTLS:
		add("tls and plain_http are mutually exclusive")
	case !c.PlainHTTP && (c.TLS.CertFile == "" || c.TLS.KeyFile == ""):
		add("tls.cert_file and tls.key_file are required (set plain_http only for local testing)")
	}
	if c.Listen == c.AdminListen {
		add("listen and admin_listen must be different")
	}

	if name, ok := strings.CutPrefix(c.Audience, AudiencePrefix); !ok || name == "" {
		add("audience must be %q, got %q", AudiencePrefix+"<cluster>", c.Audience)
	}
	if c.JWKSFile == "" {
		add("jwks_file is required")
	}
	if c.UpstreamDockerConfigFile == "" {
		add("upstream_docker_config_file is required")
	}
	if c.UploadSession.KeyFile == "" {
		add("upload_session.key_file is required")
	}
	if c.UpstreamTokenMaxTTL < 0 || c.UpstreamResponseHeaderTimeout < 0 || c.UploadSession.TTL < 0 || c.ShutdownTimeout < 0 {
		add("durations must not be negative")
	}

	if len(c.Upstreams) == 0 {
		add("at least one upstream is required")
	}
	seen := map[string]bool{}
	for i, u := range c.Upstreams {
		if err := u.validate(); err != nil {
			add("upstreams[%d]: %w", i, err)
			continue
		}
		if seen[u.Alias] {
			add("upstreams[%d]: duplicated alias %q", i, u.Alias)
		}
		seen[u.Alias] = true
	}
	return errors.Join(errs...)
}

func (u UpstreamConfig) validate() error {
	parsed, err := u.ParseURL()
	if err != nil {
		return err
	}
	want, err := upstream.AliasOf(parsed.Host)
	if err != nil {
		return err
	}
	if u.Alias != want {
		return fmt.Errorf("alias %q must equal %q derived from host %q", u.Alias, want, parsed.Host)
	}
	return nil
}

// ParseURL 解析上游地址，只接受 scheme://host[:port]，不带路径、查询与用户信息
func (u UpstreamConfig) ParseURL() (*url.URL, error) {
	parsed, err := url.Parse(u.URL)
	if err != nil {
		return nil, fmt.Errorf("invalid url %q: %w", u.URL, err)
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return nil, fmt.Errorf("url %q: scheme must be http or https", u.URL)
	}
	if parsed.Host == "" || parsed.User != nil || parsed.RawQuery != "" || parsed.Fragment != "" ||
		(parsed.Path != "" && parsed.Path != "/") {
		return nil, fmt.Errorf("url %q: must be scheme://host[:port] without path, query or userinfo", u.URL)
	}
	parsed.Path = ""
	parsed.Host = strings.ToLower(parsed.Host)
	return parsed, nil
}

// ReadUploadSessionKeys 读取上传会话签名密钥，去掉首尾空白后必须不少于 32 字节
func (c *Config) ReadUploadSessionKeys() (primary, previous []byte, err error) {
	if primary, err = readKey(c.UploadSession.KeyFile); err != nil {
		return nil, nil, err
	}
	if c.UploadSession.PreviousKeyFile != "" {
		if previous, err = readKey(c.UploadSession.PreviousKeyFile); err != nil {
			return nil, nil, err
		}
	}
	return primary, previous, nil
}

func readKey(path string) ([]byte, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read upload session key: %w", err)
	}
	key := bytes.TrimSpace(raw)
	if len(key) < MinUploadSessionKeyLen {
		return nil, fmt.Errorf("upload session key %s is shorter than %d bytes", path, MinUploadSessionKeyLen)
	}
	return key, nil
}
