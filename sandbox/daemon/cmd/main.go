package main

import (
	"context"
	"fmt"
	"io"
	golog "log"
	"os"
	"os/exec"
	"os/signal"
	"sync"
	"syscall"
	"time"

	log "github.com/sirupsen/logrus"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server"
)

// entrypointManager manages the lifecycle of an entrypoint command,
// including starting, logging, and graceful shutdown.
type entrypointManager struct {
	cmd       *exec.Cmd
	wg        sync.WaitGroup
	logFile   *os.File
	logWriter io.Writer
	errWriter io.Writer
}

// newEntrypointManager creates a new entrypointManager with the given log file path.
// If logFilePath is empty, stdout/stderr will be used.
func newEntrypointManager(logFilePath string) *entrypointManager {
	em := &entrypointManager{
		logWriter: os.Stdout,
		errWriter: os.Stderr,
	}

	if logFilePath == "" {
		return em
	}

	logFile, err := os.OpenFile(logFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		log.Errorf("Failed to open log file at %s due to %v, fallback to STDOUT and STDERR", logFilePath, err)
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

	log.Info("Waiting for entrypoint command to complete...")

	if em.waitWithTimeout(shutdownTimeout) {
		log.Info("Entrypoint command completed")
		return
	}

	// Command did not complete within timeout, send SIGTERM
	log.Warn("Entrypoint command did not complete within timeout, sending SIGTERM...")
	if err := em.cmd.Process.Signal(syscall.SIGTERM); err != nil {
		log.Errorf("Failed to send SIGTERM to entrypoint command: %v", err)
	}

	if em.waitWithTimeout(sigtermTimeout) {
		log.Info("Entrypoint command terminated gracefully")
		return
	}

	// Command did not respond to SIGTERM, send SIGKILL
	log.Warn("Entrypoint command did not respond to SIGTERM, sending SIGKILL...")
	if err := em.cmd.Process.Kill(); err != nil {
		log.Errorf("Failed to kill entrypoint command: %v", err)
	}
	em.wg.Wait()
	log.Info("Entrypoint command killed")
}

// waitWithTimeout waits for the command to complete within the given timeout.
// Returns true if the command completed, false if the timeout was reached.
func (em *entrypointManager) waitWithTimeout(timeout time.Duration) bool {
	done := make(chan struct{})
	go func() {
		em.wg.Wait()
		close(done)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	select {
	case <-done:
		return true
	case <-ctx.Done():
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
		panic(err)
	}

	var logWriter io.Writer

	logFile, err := os.OpenFile(cfg.DaemonLogFilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		log.Error("Failed to open log file at ", cfg.DaemonLogFilePath)
	} else {
		defer logFile.Close() // nolint
		logWriter = logFile
	}

	initLogs(logWriter)

	// If workdir in image is not set, use user home as workdir
	if cfg.UserHomeAsWorkDir {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			log.Warnf("failed to get home directory: %v", err)
		} else {
			err = os.Chdir(homeDir)
			if err != nil {
				log.Warnf("failed to change working directory to home directory: %v", err)
			}
		}
	}

	// Initialize and start entrypoint command
	entrypoint := newEntrypointManager(cfg.EntrypointLogFilePath)
	defer entrypoint.Close()
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
		log.Errorf("Error: %v", err)
	case sig := <-sigChan:
		log.Infof("Received signal %v, shutting down gracefully...", sig)
	}

	// Gracefully shutdown entrypoint command
	entrypoint.Shutdown(cfg.EntrypointShutdownTimeout, cfg.SigtermShutdownTimeout)

	log.Info("Shutdown complete")
}

func initLogs(logWriter io.Writer) {
	logLevel := log.WarnLevel

	logLevelEnv, logLevelSet := os.LookupEnv("LOG_LEVEL")

	if logLevelSet {
		var err error
		logLevel, err = log.ParseLevel(logLevelEnv)
		if err != nil {
			logLevel = log.WarnLevel
		}
	}

	log.SetLevel(logLevel)
	logFormatter := &config.LogFormatter{
		TextFormatter: &log.TextFormatter{
			ForceColors: true,
		},
		LogFileWriter: logWriter,
	}

	log.SetFormatter(logFormatter)

	golog.SetOutput(log.New().WriterLevel(log.DebugLevel))
}
