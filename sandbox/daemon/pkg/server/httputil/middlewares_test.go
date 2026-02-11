package httputil

import (
	"errors"
	"net/http"
	"net/http/httptest"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Middlewares", func() {
	BeforeEach(func() {
		gin.SetMode(gin.TestMode)
	})

	Describe("TokenAuthMiddleware", func() {
		var (
			router *gin.Engine
			w      *httptest.ResponseRecorder
		)

		BeforeEach(func() {
			router = gin.New()
			router.Use(ErrorMiddleware())
			w = httptest.NewRecorder()
		})

		Context("valid token", func() {
			It("should allow request to pass", func() {
				validToken := "test-token-123"
				router.Use(TokenAuthMiddleware(validToken))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", "Bearer "+validToken)

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusOK))
				Expect(w.Body.String()).To(ContainSubstring("success"))
			})

			It("should allow different token values", func() {
				customToken := "custom-secret-token"
				router.Use(TokenAuthMiddleware(customToken))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "ok"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", "Bearer "+customToken)

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusOK))
			})
		})

		Context("invalid token", func() {
			It("should reject wrong token", func() {
				validToken := "correct-token"
				router.Use(TokenAuthMiddleware(validToken))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", "Bearer wrong-token")

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusUnauthorized))
				Expect(w.Body.String()).To(ContainSubstring("invalid authorization token"))
			})

			It("should reject request without Authorization header", func() {
				router.Use(TokenAuthMiddleware("test-token"))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusUnauthorized))
				Expect(w.Body.String()).To(ContainSubstring("missing Bearer prefix in authorization header"))
			})

			It("should reject empty Authorization header", func() {
				router.Use(TokenAuthMiddleware("test-token"))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", "")

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusUnauthorized))
				Expect(w.Body.String()).To(ContainSubstring("missing Bearer prefix in authorization header"))
			})

			It("should reject Bearer prefix without token", func() {
				router.Use(TokenAuthMiddleware("test-token"))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", "Bearer ")

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusUnauthorized))
				Expect(w.Body.String()).To(ContainSubstring("missing authorization token"))
			})

			It("should reject token without Bearer prefix", func() {
				validToken := "test-token"
				router.Use(TokenAuthMiddleware(validToken))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", validToken)

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusUnauthorized))
			})
		})

		Context("edge cases", func() {
			It("should handle empty string token", func() {
				router.Use(TokenAuthMiddleware(""))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", "Bearer ")

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusUnauthorized))
			})

			It("should handle token with special characters", func() {
				specialToken := "token-with-!@#$%^&*()_+"
				router.Use(TokenAuthMiddleware(specialToken))
				router.GET("/protected", func(c *gin.Context) {
					c.JSON(http.StatusOK, gin.H{"message": "success"})
				})

				req, _ := http.NewRequest("GET", "/protected", nil)
				req.Header.Set("Authorization", "Bearer "+specialToken)

				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusOK))
			})
		})
	})

	Describe("ErrorMiddleware", func() {
		var (
			router *gin.Engine
			w      *httptest.ResponseRecorder
		)

		BeforeEach(func() {
			router = gin.New()
			router.Use(ErrorMiddleware())
			w = httptest.NewRecorder()
		})

		It("should format error response correctly", func() {
			router.GET("/error", func(c *gin.Context) {
				BadRequestResponse(c, errors.New("test error message"))
			})

			req, _ := http.NewRequest("GET", "/error", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("test error message"))
			Expect(w.Body.String()).To(ContainSubstring("timestamp"))
			Expect(w.Body.String()).To(ContainSubstring("path"))
			Expect(w.Body.String()).To(ContainSubstring("method"))
			Expect(w.Header().Get("Content-Type")).To(ContainSubstring("application/json"))
		})

		It("should include correct path and method", func() {
			router.POST("/api/test", func(c *gin.Context) {
				NotFoundResponse(c, errors.New("not found"))
			})

			req, _ := http.NewRequest("POST", "/api/test", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusNotFound))
			Expect(w.Body.String()).To(ContainSubstring("/api/test"))
			Expect(w.Body.String()).To(ContainSubstring("POST"))
		})

		It("should not affect successful responses", func() {
			router.GET("/success", func(c *gin.Context) {
				c.JSON(http.StatusOK, gin.H{"status": "ok"})
			})

			req, _ := http.NewRequest("GET", "/success", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Body.String()).To(ContainSubstring("ok"))
			Expect(w.Body.String()).NotTo(ContainSubstring("timestamp"))
		})

		It("should handle multiple errors and return last one", func() {
			router.GET("/multiple-errors", func(c *gin.Context) {
				c.Error(errors.New("first error"))  // nolint
				c.Error(errors.New("second error")) // nolint
				BadRequestResponse(c, errors.New("last error"))
			})

			req, _ := http.NewRequest("GET", "/multiple-errors", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("last error"))
		})
	})

	Describe("Recovery", func() {
		var (
			router *gin.Engine
			w      *httptest.ResponseRecorder
		)

		BeforeEach(func() {
			router = gin.New()
			router.Use(Recovery())
			w = httptest.NewRecorder()
		})

		It("should catch panic and return 500", func() {
			router.GET("/panic", func(c *gin.Context) {
				panic("something went wrong")
			})

			req, _ := http.NewRequest("GET", "/panic", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusInternalServerError))
		})

		It("should catch different types of panic", func() {
			router.GET("/panic-int", func(c *gin.Context) {
				panic(42)
			})

			req, _ := http.NewRequest("GET", "/panic-int", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusInternalServerError))
		})

		It("should catch error type panic", func() {
			router.GET("/panic-error", func(c *gin.Context) {
				panic(errors.New("error panic"))
			})

			req, _ := http.NewRequest("GET", "/panic-error", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusInternalServerError))
		})

		It("should not affect normal requests", func() {
			router.GET("/normal", func(c *gin.Context) {
				c.JSON(http.StatusOK, gin.H{"status": "ok"})
			})

			req, _ := http.NewRequest("GET", "/normal", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Body.String()).To(ContainSubstring("ok"))
		})

		It("should not write response after panic if already written", func() {
			router.GET("/panic-after-write", func(c *gin.Context) {
				c.JSON(http.StatusOK, gin.H{"status": "ok"})
				panic("panic after write")
			})

			req, _ := http.NewRequest("GET", "/panic-after-write", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
		})
	})

	Describe("LoggingMiddleware", func() {
		var (
			router *gin.Engine
			w      *httptest.ResponseRecorder
		)

		BeforeEach(func() {
			router = gin.New()
			router.Use(LoggingMiddleware())
			w = httptest.NewRecorder()
		})

		It("should log successful requests", func() {
			router.GET("/test", func(c *gin.Context) {
				c.JSON(http.StatusOK, gin.H{"status": "ok"})
			})

			req, _ := http.NewRequest("GET", "/test", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
		})

		It("should log error requests", func() {
			router.Use(ErrorMiddleware())
			router.GET("/error", func(c *gin.Context) {
				BadRequestResponse(c, errors.New("test error"))
			})

			req, _ := http.NewRequest("GET", "/error", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})

		It("should not affect response content", func() {
			router.GET("/data", func(c *gin.Context) {
				c.JSON(http.StatusOK, gin.H{"data": "test"})
			})

			req, _ := http.NewRequest("GET", "/data", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Body.String()).To(ContainSubstring("test"))
		})
	})
})
