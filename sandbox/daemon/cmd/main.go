package main

import (
	"context"
	"errors"
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

// runPreStartScript executes the pre-start script via "sh" synchronously before the entrypoint.
// It is designed for one-time initialization tasks that must complete before the main
// server starts, such as installing dependencies, generating configuration files.
// Returns nil if the script does not exist (skip) or executes successfully.
func runPreStartScript(scriptPath string, timeout time.Duration) error {
	if _, err := os.Stat(scriptPath); errors.Is(err, os.ErrNotExist) {
		slog.Info("Pre-start script not found, skipping", "path", scriptPath)
		return nil
	}

	slog.Info("Running pre-start script", "path", scriptPath, "timeout", timeout)

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "sh", scriptPath)
	cmd.Env = os.Environ()
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("pre-start script failed: %w", err)
	}

	slog.Info("Pre-start script completed successfully")
	return nil
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

	// Run pre-start script before entrypoint, exit if it fails
	if err := runPreStartScript(cfg.PreStartScriptPath, cfg.PreStartTimeout); err != nil {
		slog.Error("Pre-start script failed, exiting", "path", cfg.PreStartScriptPath, "error", err)
		os.Exit(1)
	}

	// Initialize and start entrypoint command
	entrypoint := newEntrypointManager(cfg.EntrypointLogFilePath)
	defer entrypoint.Close()

	// entrypoint 并非指 daemon 服务本身, 而是用户镜像的自定义启动命令(如 `start web`), 此时沙箱环境的启动命令变成 `./daemon start web`
	// 实际上, entrypoint 会作为 daemon 的子进程被拉起并托管
	// 当 os.Args[1:] 为空时, 尝试使用默认的 entrypoint 脚本
	entrypointArgs := os.Args[1:]
	if len(entrypointArgs) == 0 {
		if _, err := os.Stat(cfg.DefaultEntrypointPath); err == nil {
			slog.Info("No entrypoint args provided, using default entrypoint script", "path", cfg.DefaultEntrypointPath)
			entrypointArgs = []string{"sh", cfg.DefaultEntrypointPath}
		}
	}
	entrypoint.Start(entrypointArgs)

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
