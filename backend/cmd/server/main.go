package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/user/familytriphelper/backend/internal/config"
	apphttp "github.com/user/familytriphelper/backend/internal/http"
	"github.com/user/familytriphelper/backend/internal/store"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()

	db, err := store.OpenPostgres(ctx, cfg.DatabaseDSN)
	if err != nil {
		log.Fatalf("open postgres: %v", err)
	}
	defer db.Close()

	if err := store.EnsureSchema(ctx, db); err != nil {
		log.Fatalf("ensure schema: %v", err)
	}

	repository := store.NewRepository(db)
	if handled, err := maybeRunCLI(ctx, repository); err != nil {
		log.Fatalf("run CLI command: %v", err)
	} else if handled {
		return
	}

	router := apphttp.NewRouter(cfg, repository)

	server := &http.Server{
		Addr:              cfg.Address,
		Handler:           router,
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		log.Printf("starting server on %s", cfg.Address)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen and serve: %v", err)
		}
	}()

	<-ctx.Done()

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("shutdown error: %v", err)
	}
}

func maybeRunCLI(ctx context.Context, repository *store.Repository) (bool, error) {
	if len(os.Args) < 2 {
		return false, nil
	}

	switch os.Args[1] {
	case "create-guest":
		fs := flag.NewFlagSet("create-guest", flag.ContinueOnError)
		name := fs.String("name", "", "guest display name")
		baseURL := fs.String("base-url", "http://localhost", "public service base URL")
		if err := fs.Parse(os.Args[2:]); err != nil {
			return true, err
		}

		participant, token, err := repository.CreateGuest(ctx, *name)
		if err != nil {
			return true, err
		}

		link := fmt.Sprintf("%s/guest/%s", strings.TrimRight(*baseURL, "/"), token)
		fmt.Printf("Guest created\nName: %s\nID: %d\nLink: %s\n", participant.DisplayName, participant.ID, link)
		return true, nil
	default:
		return false, nil
	}
}
