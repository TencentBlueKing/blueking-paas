package config

import (
	"errors"
	"time"

	"github.com/caarlos0/env/v10"
)

// G represents the global configuration
var G *Config

// Config represents the daemon configuration
type Config struct {
	// Environment 运行环境
	Environment string `env:"ENVIRONMENT" envDefault:"stag"`
	// ServerHost daemon 服务地址
	ServerHost string `env:"SERVER_HOST" envDefault:"0.0.0.0"`
	// ServerPort daemon 服务端口
	ServerPort int `env:"SERVER_PORT" envDefault:"8000"`
	// Token 调用 daemon server 的 token
	Token string `env:"TOKEN"`

	// LogLevel 日志级别
	LogLevel string `env:"LOG_LEVEL" envDefault:"warn"`
	// DaemonLogFilePath daemon 日志文件路径
	DaemonLogFilePath string `env:"DAEMON_LOG_FILE_PATH" envDefault:"/tmp/sandbox-daemon.log"`

	// EntrypointLogFilePath entrypoint 日志文件路径
	EntrypointLogFilePath string `env:"ENTRYPOINT_LOG_FILE_PATH" envDefault:"/tmp/sandbox-entrypoint.log"`
	// EntrypointShutdownTimeout 关闭 entrypoint 的超时时间
	EntrypointShutdownTimeout time.Duration `env:"ENTRYPOINT_SHUTDOWN_TIMEOUT" envDefault:"60s"`
	// SigtermShutdownTimeout 收到 sigterm 后, 关闭的超时时间
	SigtermShutdownTimeout time.Duration `env:"SIGTERM_SHUTDOWN_TIMEOUT" envDefault:"5s"`
	// UserHomeAsWorkDir 是否使用用户 home 目录作为工作目录
	UserHomeAsWorkDir bool `env:"USER_HOME_AS_WORKDIR"`

	// MaxExecTimeout 命令行执行的最大超时时间
	MaxExecTimeout time.Duration `env:"MAX_EXEC_TIMEOUT" envDefault:"360s"`
}

// Load loads the daemon configuration
func Load() (*Config, error) {
	cfg := &Config{}
	if err := env.Parse(cfg); err != nil {
		return nil, err
	}

	if cfg.Token == "" {
		return nil, errors.New("TOKEN is empty")
	}

	// Set the global configuration
	G = cfg

	return cfg, nil
}
