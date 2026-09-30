// Package upstream 管理代理转发的真实仓库：别名、连接与上游鉴权。
package upstream

import (
	"crypto/tls"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"golang.org/x/sync/singleflight"
)

// Spec 描述一个上游，由配置转换而来
type Spec struct {
	Alias         string
	URL           *url.URL
	SkipTLSVerify bool
}

// Options 是所有上游共用的连接与鉴权参数
type Options struct {
	// TokenMaxTTL 是上游 Authorization 的最长缓存时间
	TokenMaxTTL time.Duration
	// ResponseHeaderTimeout 是发完请求后等待上游响应头的超时，不限制响应体的传输时长
	ResponseHeaderTimeout time.Duration
	// AuthTimeout 是一次换取上游 Authorization（质询 + 换 token）的总超时
	AuthTimeout time.Duration
}

// Upstream 是一个已配置的上游仓库
type Upstream struct {
	Alias string
	URL   *url.URL
	// Transport 专用于该上游，TLS 配置按上游区分
	Transport *http.Transport

	cred        *Credential
	authClient  *http.Client
	maxTTL      time.Duration
	authTimeout time.Duration
	now         func() time.Time

	mu        sync.Mutex
	cache     map[string]cachedAuth
	challenge *cachedChallenge
	flight    singleflight.Group
}

// HasCredential 返回代理是否持有该上游的凭证
func (u *Upstream) HasCredential() bool { return u.cred != nil }

// FromSpecs 按配置创建全部上游，返回以别名为键的 map；creds 的键为小写主机名（含端口）。
// 返回的 map 创建后只读，可并发访问。
func FromSpecs(specs []Spec, creds map[string]Credential, opts Options) (map[string]*Upstream, error) {
	if opts.AuthTimeout == 0 {
		opts.AuthTimeout = 30 * time.Second
	}
	byAlias := make(map[string]*Upstream, len(specs))
	for _, spec := range specs {
		if spec.URL == nil || spec.URL.Host == "" {
			return nil, fmt.Errorf("upstream %q: url is required", spec.Alias)
		}
		if _, dup := byAlias[spec.Alias]; dup {
			return nil, fmt.Errorf("duplicated upstream alias %q", spec.Alias)
		}
		tr := newTransport(spec.SkipTLSVerify, opts.ResponseHeaderTimeout)
		u := &Upstream{
			Alias:       spec.Alias,
			URL:         spec.URL,
			Transport:   tr,
			authClient:  &http.Client{Transport: tr, Timeout: opts.AuthTimeout},
			maxTTL:      opts.TokenMaxTTL,
			authTimeout: opts.AuthTimeout,
			now:         time.Now,
			cache:       map[string]cachedAuth{},
		}
		if c, ok := creds[strings.ToLower(spec.URL.Host)]; ok {
			u.cred = &c
		}
		byAlias[spec.Alias] = u
	}
	return byAlias, nil
}

// Aliases 返回全部别名的集合，供授权策略判断上游是否已配置
func Aliases(byAlias map[string]*Upstream) map[string]bool {
	out := make(map[string]bool, len(byAlias))
	for a := range byAlias {
		out[a] = true
	}
	return out
}

func newTransport(skipTLSVerify bool, responseHeaderTimeout time.Duration) *http.Transport {
	return &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   10 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		ForceAttemptHTTP2: true,
		// 不自动协商 gzip：响应体与 Content-Length 原样透传给客户端，Accept-Encoding 由客户端决定
		DisableCompression:    true,
		MaxIdleConns:          256,
		MaxIdleConnsPerHost:   64,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: time.Second,
		ResponseHeaderTimeout: responseHeaderTimeout,
		TLSClientConfig: &tls.Config{
			MinVersion: tls.VersionTLS12,
			// 对应平台仓库的 skip_tls_verify 配置
			InsecureSkipVerify: skipTLSVerify, //nolint:gosec
		},
	}
}
