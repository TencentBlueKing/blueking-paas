package process

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/bkpaas/sandbox/daemon/pkg/config"
	"github.com/bkpaas/sandbox/daemon/pkg/server/httputil"
)

var _ = Describe("parseCommand", func() {
	Context("basic command parsing", func() {
		It("should parse simple command correctly", func() {
			result := parseCommand("echo hello")
			Expect(result).To(Equal([]string{"echo", "hello"}))
		})

		It("should parse command with multiple arguments", func() {
			result := parseCommand("ls -la /tmp")
			Expect(result).To(Equal([]string{"ls", "-la", "/tmp"}))
		})

		It("should handle multiple spaces", func() {
			result := parseCommand("echo   hello   world")
			Expect(result).To(Equal([]string{"echo", "hello", "world"}))
		})

		It("should handle leading and trailing spaces", func() {
			result := parseCommand("  echo hello  ")
			Expect(result).To(Equal([]string{"echo", "hello"}))
		})
	})

	Context("double quote handling", func() {
		It("should parse double quoted arguments", func() {
			result := parseCommand(`echo "hello world"`)
			Expect(result).To(Equal([]string{"echo", "hello world"}))
		})

		It("should handle multiple double quoted arguments", func() {
			result := parseCommand(`echo "hello world" "foo bar"`)
			Expect(result).To(Equal([]string{"echo", "hello world", "foo bar"}))
		})

		It("should handle single quotes inside double quotes", func() {
			result := parseCommand(`echo "it's working"`)
			Expect(result).To(Equal([]string{"echo", "it's working"}))
		})

		It("should handle empty double quotes", func() {
			result := parseCommand(`echo ""`)
			Expect(result).To(Equal([]string{"echo"}))
		})
	})

	Context("single quote handling", func() {
		It("should parse single quoted arguments", func() {
			result := parseCommand(`echo 'hello world'`)
			Expect(result).To(Equal([]string{"echo", "hello world"}))
		})

		It("should handle multiple single quoted arguments", func() {
			result := parseCommand(`echo 'hello world' 'foo bar'`)
			Expect(result).To(Equal([]string{"echo", "hello world", "foo bar"}))
		})

		It("should handle double quotes inside single quotes", func() {
			result := parseCommand(`echo 'say "hello"'`)
			Expect(result).To(Equal([]string{"echo", `say "hello"`}))
		})

		It("should handle empty single quotes", func() {
			result := parseCommand(`echo ''`)
			Expect(result).To(Equal([]string{"echo"}))
		})
	})

	Context("mixed quote handling", func() {
		It("should handle mixed quotes", func() {
			result := parseCommand(`echo "hello" 'world'`)
			Expect(result).To(Equal([]string{"echo", "hello", "world"}))
		})

		It("should handle nested different types of quotes", func() {
			result := parseCommand(`echo "it's a 'test'" 'and "another"'`)
			Expect(result).To(Equal([]string{"echo", "it's a 'test'", `and "another"`}))
		})
	})

	Context("edge cases", func() {
		It("should return empty slice for empty string", func() {
			result := parseCommand("")
			Expect(result).To(BeEmpty())
		})

		It("should return empty slice for whitespace only string", func() {
			result := parseCommand("   ")
			Expect(result).To(BeEmpty())
		})

		It("should handle single command", func() {
			result := parseCommand("ls")
			Expect(result).To(Equal([]string{"ls"}))
		})

		It("should handle unclosed double quotes", func() {
			result := parseCommand(`echo "hello world`)
			Expect(result).To(Equal([]string{"echo", "hello world"}))
		})

		It("should handle unclosed single quotes", func() {
			result := parseCommand(`echo 'hello world`)
			Expect(result).To(Equal([]string{"echo", "hello world"}))
		})
	})

	Context("complex command scenarios", func() {
		It("should parse command with path", func() {
			result := parseCommand(`/usr/bin/python -c "print('hello')"`)
			Expect(result).To(Equal([]string{"/usr/bin/python", "-c", "print('hello')"}))
		})

		It("should parse command with special characters", func() {
			result := parseCommand(`grep "error.*warning" /var/log/app.log`)
			Expect(result).To(Equal([]string{"grep", "error.*warning", "/var/log/app.log"}))
		})

		It("should handle consecutive quoted arguments", func() {
			result := parseCommand(`cmd "arg1""arg2"`)
			Expect(result).To(Equal([]string{"cmd", "arg1arg2"}))
		})

		It("should handle quotes with non-space characters", func() {
			result := parseCommand(`echo prefix"quoted"suffix`)
			Expect(result).To(Equal([]string{"echo", "prefixquotedsuffix"}))
		})
	})
})

var _ = Describe("ExecuteCommand", func() {
	var (
		router *gin.Engine
		w      *httptest.ResponseRecorder

		url string
	)

	BeforeEach(func() {
		gin.SetMode(gin.TestMode)

		config.G = &config.Config{
			MaxExecTimeout: 10 * time.Second,
		}

		url = "/process/execute"

		router = gin.New()
		router.Use(httputil.ErrorMiddleware())
		router.POST(url, ExecuteCommand)

		w = httptest.NewRecorder()
	})

	Context("normal command execution", func() {
		It("should execute simple command and return output", func() {
			reqBody := ExecuteRequest{
				Command: "echo hello",
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			var resp ExecuteResponse
			err := json.Unmarshal(w.Body.Bytes(), &resp)
			Expect(err).NotTo(HaveOccurred())
			Expect(resp.ExitCode).To(Equal(0))
			Expect(resp.Output).To(ContainSubstring("hello"))
		})

		It("should handle command with arguments", func() {
			reqBody := ExecuteRequest{
				Command: "echo -n test",
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			var resp ExecuteResponse
			err := json.Unmarshal(w.Body.Bytes(), &resp)
			Expect(err).NotTo(HaveOccurred())
			Expect(resp.ExitCode).To(Equal(0))
			Expect(resp.Output).To(Equal("test"))
		})

		It("should handle custom working directory", func() {
			tmpDir, err := os.MkdirTemp("", "test-cwd-*")
			Expect(err).NotTo(HaveOccurred())
			defer os.RemoveAll(tmpDir) // nolint

			reqBody := ExecuteRequest{
				Command: "pwd",
				Cwd:     &tmpDir,
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			var resp ExecuteResponse
			err = json.Unmarshal(w.Body.Bytes(), &resp)
			Expect(err).NotTo(HaveOccurred())
			Expect(resp.ExitCode).To(Equal(0))
			Expect(resp.Output).To(ContainSubstring(tmpDir))
		})
	})

	Context("command execution failure", func() {
		It("should return non-zero exit code when command fails", func() {
			reqBody := ExecuteRequest{
				Command: "false",
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			var resp ExecuteResponse
			err := json.Unmarshal(w.Body.Bytes(), &resp)
			Expect(err).NotTo(HaveOccurred())
			Expect(resp.ExitCode).NotTo(Equal(0))
		})

		It("should return error output when command does not exist", func() {
			reqBody := ExecuteRequest{
				Command: "nonexistentcommand12345",
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			var resp ExecuteResponse
			err := json.Unmarshal(w.Body.Bytes(), &resp)
			Expect(err).NotTo(HaveOccurred())
			Expect(resp.ExitCode).To(Equal(-1))
		})
	})

	Context("timeout handling", func() {
		It("should return timeout error when command times out", func() {
			timeout := uint32(1)
			reqBody := ExecuteRequest{
				Command: "sleep 5",
				Timeout: &timeout,
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusRequestTimeout))
			Expect(w.Body.String()).To(ContainSubstring("timeout"))
		})

		It("should use custom timeout duration", func() {
			timeout := uint32(2)
			reqBody := ExecuteRequest{
				Command: "sleep 1",
				Timeout: &timeout,
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			var resp ExecuteResponse
			err := json.Unmarshal(w.Body.Bytes(), &resp)
			Expect(err).NotTo(HaveOccurred())
			Expect(resp.ExitCode).To(Equal(0))
		})
	})

	Context("request validation", func() {
		It("should reject empty request body", func() {
			req, _ := http.NewRequest("POST", "/process/execute", bytes.NewBuffer([]byte("")))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("empty"))
		})

		It("should reject empty command", func() {
			reqBody := ExecuteRequest{
				Command: "",
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})

		It("should reject whitespace-only command", func() {
			reqBody := ExecuteRequest{
				Command: "   ",
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("empty command"))
		})

		It("should reject invalid JSON", func() {
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer([]byte("invalid json")))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})
	})

	Context("complex command scenarios", func() {
		It("should handle quoted commands", func() {
			reqBody := ExecuteRequest{
				Command: `echo "hello world"`,
			}
			body, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			var resp ExecuteResponse
			err := json.Unmarshal(w.Body.Bytes(), &resp)
			Expect(err).NotTo(HaveOccurred())
			Expect(resp.ExitCode).To(Equal(0))
			Expect(resp.Output).To(ContainSubstring("hello world"))
		})
	})
})
