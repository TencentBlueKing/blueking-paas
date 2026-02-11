package httputil

import (
	"errors"
	"log/slog"
	"net/http"
	"runtime"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

const maxStackTraceSize = 64 * 1024 // 64 KB

// TODO: 需要忽略的路径
var ignoreLoggingPaths = map[string]bool{}

// ErrorMiddleware handles errors
func ErrorMiddleware() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		ctx.Next()

		if len(ctx.Errors) > 0 {
			err := ctx.Errors.Last()
			statusCode := ctx.Writer.Status()

			errorResponse := ErrorResponse{
				Message:   err.Error(),
				Timestamp: time.Now(),
				Path:      ctx.Request.URL.Path,
				Method:    ctx.Request.Method,
			}

			ctx.Header("Content-Type", "application/json")
			ctx.AbortWithStatusJSON(statusCode, errorResponse)
		}
	}
}

// LoggingMiddleware logs requests
func LoggingMiddleware() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		startTime := time.Now()
		ctx.Next()
		endTime := time.Now()
		latencyTime := endTime.Sub(startTime)
		reqMethod := ctx.Request.Method
		reqUri := ctx.Request.RequestURI
		statusCode := ctx.Writer.Status()

		if len(ctx.Errors) > 0 {
			slog.Error("API ERROR",
				"method", reqMethod,
				"URI", reqUri,
				"status", statusCode,
				"latency", latencyTime,
				"error", ctx.Errors.String(),
			)
		} else {
			fullPath := ctx.FullPath()
			if ignoreLoggingPaths[fullPath] {
				slog.Debug("API REQUEST",
					"method", reqMethod,
					"URI", reqUri,
					"status", statusCode,
					"latency", latencyTime,
				)
			} else {
				slog.Info("API REQUEST",
					"method", reqMethod,
					"URI", reqUri,
					"status", statusCode,
					"latency", latencyTime,
				)
			}
		}
	}
}

// TokenAuthMiddleware checks token
func TokenAuthMiddleware(token string) gin.HandlerFunc {
	return func(c *gin.Context) {
		authorizationHeader := c.GetHeader("Authorization")

		if !strings.HasPrefix(authorizationHeader, "Bearer ") {
			UnauthorizedResponse(c, errors.New("missing Bearer prefix in authorization header"))
			return
		}

		reqToken := strings.TrimPrefix(authorizationHeader, "Bearer ")
		if reqToken == "" {
			UnauthorizedResponse(c, errors.New("missing authorization token"))
			return
		}
		if reqToken != token {
			UnauthorizedResponse(c, errors.New("invalid authorization token"))
			return
		}

		c.Next()
	}
}

// Recovery recovers from panics
func Recovery() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				if errType, ok := err.(error); ok && errors.Is(errType, http.ErrAbortHandler) {
					// Do nothing, the request was aborted
					return
				}

				slog.Error("panic recovered", "error", err)
				// print caller stack
				buf := make([]byte, maxStackTraceSize)
				stackSize := runtime.Stack(buf, false)
				slog.Error("stack trace", "stack", string(buf[:stackSize]))

				if ctx.Writer.Written() {
					return
				}

				ctx.AbortWithStatus(http.StatusInternalServerError)
			}
		}()
		ctx.Next()
	}
}
