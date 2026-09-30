// registry-proxy 是构建镜像代理：构建容器只持有 apiserver 签发的构建 token，
// 代理校验授权后以自身持有的上游凭证把 OCI Distribution v2 请求转发给真实仓库。
package main

import (
	"context"
	"crypto/tls"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/authz"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/config"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/proxy"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

var version = "dev"

func main() {
	configPath := flag.String("config", "/etc/registry-proxy/config.yaml", "配置文件路径")
	flag.Parse()

	// 运行日志输出到标准错误，标准输出只留给审计日志
	logger := slog.New(slog.NewJSONHandler(os.Stderr, nil))
	if err := run(*configPath, logger); err != nil {
		logger.Error("registry-proxy exited", "error", err)
		os.Exit(1)
	}
}

func run(configPath string, logger *slog.Logger) error {
	cfg, err := config.Load(configPath)
	if err != nil {
		return err
	}
	keys, err := buildtoken.LoadJWKSFile(cfg.JWKSFile)
	if err != nil {
		return err
	}
	creds, err := upstream.LoadCredentials(cfg.UpstreamDockerConfigFile)
	if err != nil {
		return err
	}
	uploadKey, previousUploadKey, err := cfg.ReadUploadSessionKeys()
	if err != nil {
		return err
	}

	specs := make([]upstream.Spec, 0, len(cfg.Upstreams))
	for _, u := range cfg.Upstreams {
		parsed, _ := u.ParseURL() // 已在 config.Validate 中校验
		specs = append(specs, upstream.Spec{Alias: u.Alias, URL: parsed, SkipTLSVerify: u.SkipTLSVerify})
	}
	upstreams, err := upstream.FromSpecs(specs, creds, upstream.Options{
		TokenMaxTTL:           cfg.UpstreamTokenMaxTTL,
		ResponseHeaderTimeout: cfg.UpstreamResponseHeaderTimeout,
	})
	if err != nil {
		return err
	}
	for _, u := range upstreams {
		logger.Info("upstream configured", "alias", u.Alias, "url", u.URL.String(), "credential", u.HasCredential())
	}

	reg := prometheus.NewRegistry()
	reg.MustRegister(collectors.NewGoCollector(), collectors.NewProcessCollector(collectors.ProcessCollectorOpts{}))
	metrics := proxy.NewMetrics(reg)
	auditor := proxy.NewJSONAuditor(os.Stdout)
	auditor.OnError = func(err error) {
		metrics.AuditFailed()
		logger.Error("write audit log failed", "error", err)
	}

	handler, err := proxy.New(proxy.Options{
		Upstreams:                upstreams,
		Authenticator:            &authz.TokenAuthenticator{Keys: keys, Audience: cfg.Audience},
		Authorizer:               &authz.PolicyAuthorizer{Upstreams: upstream.Aliases(upstreams)},
		Auditor:                  auditor,
		UploadSessionKey:         uploadKey,
		PreviousUploadSessionKey: previousUploadKey,
		UploadSessionTTL:         cfg.UploadSession.TTL,
		Metrics:                  metrics,
		Logger:                   logger,
	})
	if err != nil {
		return err
	}

	mainSrv := &http.Server{
		Handler:           handler,
		ReadHeaderTimeout: 30 * time.Second,
		// 不设置 ReadTimeout / WriteTimeout：单个 blob 可达 GB 级，传输时长不可预估
		IdleTimeout: 120 * time.Second,
		ErrorLog:    slog.NewLogLogger(logger.Handler(), slog.LevelWarn),
	}
	if !cfg.PlainHTTP {
		cert, err := tls.LoadX509KeyPair(cfg.TLS.CertFile, cfg.TLS.KeyFile)
		if err != nil {
			return fmt.Errorf("load tls certificate: %w", err)
		}
		mainSrv.TLSConfig = &tls.Config{MinVersion: tls.VersionTLS12, Certificates: []tls.Certificate{cert}}
	}

	var ready atomic.Bool
	adminMux := http.NewServeMux()
	adminMux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte("ok"))
	})
	adminMux.HandleFunc("/readyz", func(w http.ResponseWriter, _ *http.Request) {
		if !ready.Load() {
			http.Error(w, "not ready", http.StatusServiceUnavailable)
			return
		}
		_, _ = w.Write([]byte("ok"))
	})
	adminMux.Handle("/metrics", promhttp.HandlerFor(reg, promhttp.HandlerOpts{Registry: reg}))
	adminSrv := &http.Server{Handler: adminMux, ReadHeaderTimeout: 10 * time.Second}

	// 先完成监听，端口冲突等错误在启动阶段暴露
	mainLn, err := net.Listen("tcp", cfg.Listen)
	if err != nil {
		return err
	}
	adminLn, err := net.Listen("tcp", cfg.AdminListen)
	if err != nil {
		_ = mainLn.Close()
		return err
	}

	errCh := make(chan error, 2)
	go func() {
		if cfg.PlainHTTP {
			errCh <- mainSrv.Serve(mainLn)
		} else {
			errCh <- mainSrv.ServeTLS(mainLn, "", "")
		}
	}()
	go func() { errCh <- adminSrv.Serve(adminLn) }()
	ready.Store(true)
	logger.Info("registry-proxy started", "version", version, "listen", cfg.Listen,
		"admin_listen", cfg.AdminListen, "tls", !cfg.PlainHTTP, "audience", cfg.Audience)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	select {
	case err := <-errCh:
		if !errors.Is(err, http.ErrServerClosed) {
			return err
		}
	case <-ctx.Done():
	}

	ready.Store(false)
	logger.Info("shutting down", "timeout", cfg.ShutdownTimeout.String())
	shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()
	err = mainSrv.Shutdown(shutdownCtx)
	_ = adminSrv.Shutdown(shutdownCtx)
	return err
}
