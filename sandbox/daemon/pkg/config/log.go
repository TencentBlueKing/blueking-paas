package config

import (
	"io"

	log "github.com/sirupsen/logrus"
)

// LogFormatter represents the log formatter
type LogFormatter struct {
	TextFormatter *log.TextFormatter
	LogFileWriter io.Writer
}

// Format formats the log entry
func (f *LogFormatter) Format(entry *log.Entry) ([]byte, error) {
	formatted, err := f.TextFormatter.Format(entry)
	if err != nil {
		return nil, err
	}

	if f.LogFileWriter != nil {
		_, err = f.LogFileWriter.Write(formatted)
		if err != nil {
			return nil, err
		}
	}

	return []byte(formatted), nil
}
