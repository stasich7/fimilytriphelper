package http

import (
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"

	"github.com/user/familytriphelper/backend/internal/config"
	"github.com/user/familytriphelper/backend/internal/store"
)

type Router struct {
	config config.Config
	repo   *store.Repository
}

func NewRouter(cfg config.Config, repo *store.Repository) http.Handler {
	app := &Router{
		config: cfg,
		repo:   repo,
	}

	apiMux := http.NewServeMux()

	apiMux.HandleFunc("/api/v1/healthz", app.handleHealthz)
	apiMux.HandleFunc("/api/v1/overview", app.handleOverview)
	apiMux.HandleFunc("/api/v1/versions", app.handleVersions)
	apiMux.HandleFunc("/api/v1/versions/", app.handleVersionByID)
	apiMux.HandleFunc("/api/v1/items/", app.handleItemByID)
	apiMux.HandleFunc("/api/v1/guests/", app.handleGuestByToken)
	apiMux.HandleFunc("/api/v1/comments", app.handleCreateComment)
	apiMux.HandleFunc("/api/v1/imports/markdown", app.handleImportMarkdown)
	apiMux.HandleFunc("/api/v1/exports/codex", app.handleExportCodex)

	rootMux := http.NewServeMux()
	rootMux.Handle("/api/", app.withCORS(apiMux))
	rootMux.Handle("/", newStaticHandler(cfg.StaticDir))

	return rootMux
}

func (r *Router) withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		origin := req.Header.Get("Origin")
		if origin != "" && r.config.FrontendOrigin != "" && strings.EqualFold(origin, r.config.FrontendOrigin) {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			w.Header().Set("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
		}

		if req.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		next.ServeHTTP(w, req)
	})
}

func newStaticHandler(staticDir string) http.Handler {
	if staticDir == "" {
		return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
			http.Error(w, "static assets are not configured", http.StatusNotFound)
		})
	}

	fileServer := http.FileServer(http.Dir(staticDir))

	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodGet && req.Method != http.MethodHead {
			http.NotFound(w, req)
			return
		}

		requestPath := strings.TrimPrefix(path.Clean("/"+req.URL.Path), "/")
		if requestPath != "" {
			fullPath := filepath.Join(staticDir, requestPath)
			if info, err := os.Stat(fullPath); err == nil && !info.IsDir() {
				fileServer.ServeHTTP(w, req)
				return
			}
		}

		indexPath := filepath.Join(staticDir, "index.html")
		if _, err := os.Stat(indexPath); err != nil {
			http.NotFound(w, req)
			return
		}

		http.ServeFile(w, req, indexPath)
	})
}
