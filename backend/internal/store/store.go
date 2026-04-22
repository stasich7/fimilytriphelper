package store

import (
	"context"
	"database/sql"
	"embed"
	"errors"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

//go:embed schema.sql
var schemaFS embed.FS

var ErrNotFound = errors.New("not found")

type Repository struct {
	db *sql.DB
}

func OpenPostgres(ctx context.Context, dsn string) (*sql.DB, error) {
	var lastErr error

	for attempt := 0; attempt < 30; attempt++ {
		db, err := sql.Open("pgx", dsn)
		if err == nil {
			pingCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
			pingErr := db.PingContext(pingCtx)
			cancel()
			if pingErr == nil {
				return db, nil
			}

			lastErr = pingErr
			db.Close()
		} else {
			lastErr = err
		}

		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(time.Second):
		}
	}

	return nil, fmt.Errorf("connect postgres: %w", lastErr)
}

func EnsureSchema(ctx context.Context, db *sql.DB) error {
	schema, err := schemaFS.ReadFile("schema.sql")
	if err != nil {
		return fmt.Errorf("read schema: %w", err)
	}

	if _, err := db.ExecContext(ctx, string(schema)); err != nil {
		return fmt.Errorf("exec schema: %w", err)
	}

	return nil
}

func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}
