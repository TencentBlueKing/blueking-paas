package process

import (
	"bytes"
	"context"
	"errors"
	"io"
	"os/exec"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// ExecuteCommand godoc
//
//	@Summary		Execute a command
//	@Description	Execute a shell command and return the output and exit code
//	@Tags			process
//	@Accept			json
//	@Produce		json
//	@Param			request	body		ExecuteRequest	true	"Command execution request"
//	@Success		200		{object}	ExecuteResponse
//	@Router			/process/execute [post]
//
//	@id				ExecuteCommand
func ExecuteCommand(c *gin.Context) {
	var request ExecuteRequest

	if err := c.ShouldBindJSON(&request); err != nil {
		if errors.Is(err, io.EOF) {
			httputil.BadRequestResponse(c, errors.New("request body is empty or missing"))
		} else {
			httputil.BadRequestResponse(c, err)
		}
		return
	}

	cmdParts := parseCommand(request.Command)
	if len(cmdParts) == 0 {
		httputil.BadRequestResponse(c, errors.New("empty command"))
		return
	}

	timeout := config.G.MaxExecTimeout
	if request.Timeout != nil && *request.Timeout > 0 {
		timeout = time.Duration(*request.Timeout) * time.Second
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	// Execute the command
	cmd := exec.CommandContext(ctx, cmdParts[0], cmdParts[1:]...)
	if request.Cwd != nil {
		cmd.Dir = *request.Cwd
	}

	// Setpgid to allow killing the process group(include child processes)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setpgid: true,
	}
	cmd.Cancel = func() error {
		return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		// 不直接用 err 的原因是, 它是 signal: killed, 不能表示超时
		if errors.Is(ctx.Err(), context.DeadlineExceeded) {
			httputil.RequestTimeoutResponse(c, errors.New("command execution timeout"))
			return
		}
		if exitError, ok := err.(*exec.ExitError); ok {
			exitCode := exitError.ExitCode()
			httputil.SuccessResponse(c, ExecuteResponse{
				ExitCode: exitCode,
				Output:   string(output),
			})
			return
		}
		httputil.SuccessResponse(c, ExecuteResponse{
			ExitCode: -1,
			Output:   string(output),
		})
		return
	}

	if cmd.ProcessState == nil {
		httputil.SuccessResponse(c, ExecuteResponse{
			ExitCode: -1,
			Output:   string(output),
		})
		return
	}

	exitCode := cmd.ProcessState.ExitCode()
	httputil.SuccessResponse(c, ExecuteResponse{
		ExitCode: exitCode,
		Output:   string(output),
	})
}

// parseCommand splits a command string properly handling quotes.
// see detail cases in execute_test.go
func parseCommand(command string) []string {
	var args []string
	var current bytes.Buffer
	var inQuotes bool
	var quoteChar rune

	for _, r := range command {
		switch {
		case r == '"' || r == '\'':
			if !inQuotes {
				inQuotes = true
				quoteChar = r
			} else if quoteChar == r {
				inQuotes = false
				quoteChar = 0
			} else {
				current.WriteRune(r)
			}
		case r == ' ' && !inQuotes:
			if current.Len() > 0 {
				args = append(args, current.String())
				current.Reset()
			}
		default:
			current.WriteRune(r)
		}
	}

	if current.Len() > 0 {
		args = append(args, current.String())
	}

	return args
}
