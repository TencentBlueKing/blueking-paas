package main

import (
	"fmt"
	"io"
	"log/slog"
	"os"
	"os/exec"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server"
)

// entrypointManager manages the lifecycle of an entrypoint command,
// including starting, logging, and graceful shutdown.
type entrypointManager struct {
	cmd *exec.Cmd
	wg  sync.WaitGroup
	// closed when the command completes
	done      chan struct{}
	logFile   *os.File
	logWriter io.Writer
	errWriter io.Writer
}

// newEntrypointManager creates a new entrypointManager with the given log file path.
// If logFilePath is empty, stdout/stderr will be used.
func newEntrypointManager(logFilePath string) *entrypointManager {
	em := &entrypointManager{
		done:      make(chan struct{}),
		logWriter: os.Stdout,
		errWriter: os.Stderr,
	}

	if logFilePath == "" {
		return em
	}

	logFile, err := os.OpenFile(logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		slog.Error("Failed to open log file, fallback to STDOUT and STDERR", "path", logFilePath, "error", err)
		return em
	}

	em.logFile = logFile
	em.logWriter = logFile
	em.errWriter = logFile
	return em
}

// Start starts the entrypoint command with the given arguments.
// The command runs in a background goroutine to prevent blocking and ensure proper reaping.
func (em *entrypointManager) Start(args []string) {
	if len(args) == 0 {
		return
	}

	em.cmd = exec.Command(args[0], args[1:]...)
	em.cmd.Env = os.Environ()
	em.cmd.Stdout = em.logWriter
	em.cmd.Stderr = em.errWriter

	if err := em.cmd.Start(); err != nil {
		fmt.Fprintf(em.errWriter, "failed to start command: %v\n", err) // nolint
		return
	}

	// Wait for the command in a background goroutine.
	// This ensures the child process is properly reaped (preventing zombies)
	// while allowing the daemon to continue initialization without blocking.
	em.wg.Add(1)
	go func() {
		defer em.wg.Done()
		defer close(em.done)
		if err := em.cmd.Wait(); err != nil {
			fmt.Fprintf(em.errWriter, "command exited with error: %v\n", err) // nolint
		} else {
			fmt.Fprint(em.logWriter, "Entrypoint command completed successfully\n") // nolint
		}
	}()
}

// Shutdown gracefully shuts down the entrypoint command.
// It waits for the command to complete within the given timeout, then sends SIGTERM,
// and finally SIGKILL if the command does not respond.
func (em *entrypointManager) Shutdown(shutdownTimeout, sigtermTimeout time.Duration) {
	if em.cmd == nil || em.cmd.Process == nil {
		return
	}

	slog.Info("Waiting for entrypoint command to complete...")

	if em.waitWithTimeout(shutdownTimeout) {
		slog.Info("Entrypoint command completed")
		return
	}

	// Command did not complete within timeout, send SIGTERM
	slog.Warn("Entrypoint command did not complete within timeout, sending SIGTERM...")
	if err := em.cmd.Process.Signal(syscall.SIGTERM); err != nil {
		slog.Error("Failed to send SIGTERM to entrypoint command", "error", err)
	}

	if em.waitWithTimeout(sigtermTimeout) {
		slog.Info("Entrypoint command terminated gracefully")
		return
	}

	// Command did not respond to SIGTERM, send SIGKILL
	slog.Warn("Entrypoint command did not respond to SIGTERM, sending SIGKILL...")
	if err := em.cmd.Process.Kill(); err != nil {
		slog.Error("Failed to kill entrypoint command", "error", err)
	}
	em.wg.Wait()
	slog.Info("Entrypoint command killed")
}

// waitWithTimeout waits for the command to complete within the given timeout.
// Returns true if the command completed, false if the timeout was reached.
func (em *entrypointManager) waitWithTimeout(timeout time.Duration) bool {
	select {
	case <-em.done:
		return true
	case <-time.After(timeout):
		return false
	}
}

// Close closes the log file if it was opened.
func (em *entrypointManager) Close() {
	if em.logFile != nil {
		em.logFile.Close() // nolint
	}
}

func main() {
	errChan := make(chan error)

	cfg, err := config.Load()
	if err != nil {
		slog.Error("Failed to load config", "error", err)
		panic(err)
	}

	var logWriter io.Writer

	logFile, err := os.OpenFile(cfg.DaemonLogFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		slog.Error("Failed to open log file", "path", cfg.DaemonLogFilePath, "error", err)
	} else {
		defer logFile.Close() // nolint
		logWriter = logFile
	}

	initLogs(logWriter)

	// If workdir in image is not set, use user home as workdir
	if cfg.UserHomeAsWorkDir {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			slog.Warn("failed to get home directory", "error", err)
		} else {
			err = os.Chdir(homeDir)
			if err != nil {
				slog.Warn("failed to change working directory to home directory", "error", err)
			}
		}
	}

	// Initialize and start entrypoint command
	entrypoint := newEntrypointManager(cfg.EntrypointLogFilePath)
	defer entrypoint.Close()

	// entrypoint 并非指 daemon 服务本身, 而是用户镜像的自定义启动命令(如 `start web`), 此时沙箱环境的启动命令变成 `./daemon start web`
	// 实际上, entrypoint 会作为 daemon 的子进程被拉起并托管
	entrypoint.Start(os.Args[1:])

	// Start the main server in a go routine
	go func() {
		err := server.Start()
		if err != nil {
			errChan <- err
		}
	}()

	// Set up signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Wait for either an error or shutdown signal
	select {
	case err := <-errChan:
		slog.Error("Error", "error", err)
	case sig := <-sigChan:
		slog.Info("Received signal, shutting down gracefully...", "signal", sig)
	}

	// Gracefully shutdown entrypoint command
	entrypoint.Shutdown(cfg.EntrypointShutdownTimeout, cfg.SigtermShutdownTimeout)

	slog.Info("Shutdown complete")
}

func initLogs(logWriter io.Writer) {
	logLevel := config.ParseLogLevel(config.G.LogLevel)
	handler := config.NewMultiWriterHandler(logLevel, os.Stdout, logWriter)
	slog.SetDefault(slog.New(handler))
}
