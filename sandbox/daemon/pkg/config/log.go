package config

import (
	"context"
	"io"
	"log/slog"
	"os"
	"strings"
)

// MultiWriter is a slog.Handler that writes to multiple writers
type MultiWriter struct {
	handler slog.Handler
	writers []io.Writer
}

// NewMultiWriterHandler creates a handler that writes to multiple destinations
func NewMultiWriterHandler(level slog.Level, writers ...io.Writer) *MultiWriter {
	// Filter out nil writers
	validWriters := make([]io.Writer, 0, len(writers))
	for _, w := range writers {
		if w != nil {
			validWriters = append(validWriters, w)
		}
	}

	// Default to stdout if no valid writers
	if len(validWriters) == 0 {
		validWriters = []io.Writer{os.Stdout}
	}

	multiWriter := io.MultiWriter(validWriters...)
	handler := slog.NewTextHandler(multiWriter, &slog.HandlerOptions{
		Level: level,
	})

	return &MultiWriter{
		handler: handler,
		writers: validWriters,
	}
}

func (m *MultiWriter) Enabled(ctx context.Context, level slog.Level) bool {
	return m.handler.Enabled(ctx, level)
}

func (m *MultiWriter) Handle(ctx context.Context, r slog.Record) error {
	return m.handler.Handle(ctx, r)
}

func (m *MultiWriter) WithAttrs(attrs []slog.Attr) slog.Handler {
	return &MultiWriter{
		handler: m.handler.WithAttrs(attrs),
		writers: m.writers,
	}
}

func (m *MultiWriter) WithGroup(name string) slog.Handler {
	return &MultiWriter{
		handler: m.handler.WithGroup(name),
		writers: m.writers,
	}
}

// ParseLogLevel parses a log level string to slog.Level
func ParseLogLevel(levelStr string) slog.Level {
	switch strings.ToLower(levelStr) {
	case "debug":
		return slog.LevelDebug
	case "info":
		return slog.LevelInfo
	case "warn", "warning":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelWarn
	}
}
