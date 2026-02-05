package httputil

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// ErrorResponse represents the error response structure
type ErrorResponse struct {
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
	Path      string    `json:"path"`
	Method    string    `json:"method"`
}

// SuccessResponse sends a success response with data
func SuccessResponse(c *gin.Context, data any) {
	c.JSON(http.StatusOK, data)
}

// EmptySuccessResponse sends a success response without any data
func EmptySuccessResponse(c *gin.Context) {
	c.Status(http.StatusOK)
}

// CreatedSuccessResponse sends a response indicating resource creation
func CreatedSuccessResponse(c *gin.Context) {
	c.Status(http.StatusCreated)
}

// BadRequestResponse sends a bad request response
func BadRequestResponse(c *gin.Context, err error) {
	c.AbortWithError(http.StatusBadRequest, err) // nolint
}

// UnauthorizedResponse sends an unauthorized response
func UnauthorizedResponse(c *gin.Context, err error) {
	c.AbortWithError(http.StatusUnauthorized, err) // nolint
}

// ForbiddenResponse sends a forbidden response
func ForbiddenResponse(c *gin.Context, err error) {
	c.AbortWithError(http.StatusForbidden, err) // nolint
}

// NotFoundResponse sends a not found response
func NotFoundResponse(c *gin.Context, err error) {
	c.AbortWithError(http.StatusNotFound, err) // nolint
}

// NoContentResponse sends a no content response
func NoContentResponse(c *gin.Context) {
	c.Status(http.StatusNoContent)
}

// InternalErrorResponse sends an internal error response
func InternalErrorResponse(c *gin.Context, err error) {
	c.AbortWithError(http.StatusInternalServerError, err) // nolint
}

// RequestTimeoutResponse sends a request timeout error response
func RequestTimeoutResponse(c *gin.Context, err error) {
	c.AbortWithError(http.StatusRequestTimeout, err) // nolint
}
