package http

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"

	"github.com/user/familytriphelper/backend/internal/plan"
	"github.com/user/familytriphelper/backend/internal/store"
)

func (r *Router) handleHealthz(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok",
	})
}

func (r *Router) handleOverview(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodGet {
		writeMethodNotAllowed(w, http.MethodGet)
		return
	}

	overview, err := r.repo.GetOverview(req.Context())
	if err != nil {
		writeServerError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, overview)
}

func (r *Router) handleVersions(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodGet {
		writeMethodNotAllowed(w, http.MethodGet)
		return
	}

	versions, err := r.repo.ListVersions(req.Context())
	if err != nil {
		writeServerError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"versions": versions})
}

func (r *Router) handleVersionByID(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodGet {
		writeMethodNotAllowed(w, http.MethodGet)
		return
	}

	versionID, err := parseInt64PathParam(req.URL.Path, "/api/v1/versions/")
	if err != nil {
		writeBadRequest(w, err.Error())
		return
	}

	details, err := r.repo.GetVersion(req.Context(), versionID)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeNotFound(w)
			return
		}
		writeServerError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, details)
}

func (r *Router) handleItemByID(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodGet {
		writeMethodNotAllowed(w, http.MethodGet)
		return
	}

	itemID, err := parseInt64PathParam(req.URL.Path, "/api/v1/items/")
	if err != nil {
		writeBadRequest(w, err.Error())
		return
	}

	details, err := r.repo.GetItem(req.Context(), itemID)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeNotFound(w)
			return
		}
		writeServerError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, details)
}

func (r *Router) handleGuestByToken(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodGet {
		writeMethodNotAllowed(w, http.MethodGet)
		return
	}

	guestToken := strings.TrimPrefix(req.URL.Path, "/api/v1/guests/")
	guestToken = strings.TrimSpace(guestToken)
	if guestToken == "" || guestToken == req.URL.Path {
		writeBadRequest(w, "guest token is missing")
		return
	}

	guest, err := r.repo.GetGuestByToken(req.Context(), guestToken)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeNotFound(w)
			return
		}
		writeServerError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, guest)
}

func (r *Router) handleCreateComment(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodPost {
		writeMethodNotAllowed(w, http.MethodPost)
		return
	}

	var payload struct {
		GuestToken    string `json:"guestToken"`
		PlanVersionID int64  `json:"planVersionID"`
		PlanItemID    int64  `json:"planItemID"`
		Body          string `json:"body"`
	}
	if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
		writeBadRequest(w, "invalid JSON body")
		return
	}

	comment, err := r.repo.CreateCommentByGuestToken(req.Context(), payload.GuestToken, payload.PlanVersionID, payload.PlanItemID, payload.Body)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeNotFound(w)
			return
		}
		writeBadRequest(w, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, map[string]any{
		"comment": comment,
	})
}

func (r *Router) handleToolsUnlock(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodPost {
		writeMethodNotAllowed(w, http.MethodPost)
		return
	}

	var payload struct {
		PIN string `json:"pin"`
	}
	if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
		writeBadRequest(w, "invalid JSON body")
		return
	}

	if strings.TrimSpace(payload.PIN) != r.config.ToolsPIN {
		writeJSON(w, http.StatusForbidden, map[string]string{
			"error":   "invalid_pin",
			"message": "Неверный пин-код.",
		})
		return
	}

	writeJSON(w, http.StatusOK, map[string]bool{
		"ok": true,
	})
}

func (r *Router) handleToolsGuests(w http.ResponseWriter, req *http.Request) {
	switch req.Method {
	case http.MethodGet:
		guests, err := r.repo.ListGuests(req.Context())
		if err != nil {
			writeServerError(w, err)
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{
			"guests": guests,
		})
	case http.MethodPost:
		var payload struct {
			DisplayName string `json:"displayName"`
		}
		if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
			writeBadRequest(w, "invalid JSON body")
			return
		}

		guest, err := r.repo.CreateManagedGuest(req.Context(), payload.DisplayName)
		if err != nil {
			writeBadRequest(w, err.Error())
			return
		}

		writeJSON(w, http.StatusCreated, map[string]any{
			"guest": guest,
		})
	default:
		writeMethodNotAllowed(w, "GET, POST")
	}
}

func (r *Router) handleToolsGuestByID(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodDelete {
		writeMethodNotAllowed(w, http.MethodDelete)
		return
	}

	guestID, err := parseInt64PathParam(req.URL.Path, "/api/v1/tools/guests/")
	if err != nil {
		writeBadRequest(w, err.Error())
		return
	}

	if err := r.repo.DeleteGuest(req.Context(), guestID); err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeNotFound(w)
			return
		}
		writeBadRequest(w, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]bool{
		"deleted": true,
	})
}

func (r *Router) handleImportMarkdown(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodPost {
		writeMethodNotAllowed(w, http.MethodPost)
		return
	}

	source, err := decodeImportSource(req)
	if err != nil {
		writeBadRequest(w, err.Error())
		return
	}

	doc, err := plan.ParseMarkdown(source)
	if err != nil {
		writeBadRequest(w, err.Error())
		return
	}

	result, err := r.repo.ImportPlan(req.Context(), doc)
	if err != nil {
		writeBadRequest(w, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, result)
}

func (r *Router) handleExportCodex(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodGet {
		writeMethodNotAllowed(w, http.MethodGet)
		return
	}

	versionRef := strings.TrimSpace(req.URL.Query().Get("versionId"))
	if versionRef == "" {
		versionRef = strings.TrimSpace(req.URL.Query().Get("version"))
	}
	if versionRef == "" {
		writeBadRequest(w, "versionId or version is required")
		return
	}

	exportResult, err := r.repo.ExportCodex(req.Context(), versionRef)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeNotFound(w)
			return
		}
		writeBadRequest(w, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, exportResult)
}

func writeMethodNotAllowed(w http.ResponseWriter, allowed string) {
	w.Header().Set("Allow", allowed)
	writeJSON(w, http.StatusMethodNotAllowed, map[string]string{
		"error": "method_not_allowed",
	})
}

func writeBadRequest(w http.ResponseWriter, message string) {
	writeJSON(w, http.StatusBadRequest, map[string]string{
		"error":   "bad_request",
		"message": message,
	})
}

func writeNotFound(w http.ResponseWriter) {
	writeJSON(w, http.StatusNotFound, map[string]string{
		"error": "not_found",
	})
}

func writeServerError(w http.ResponseWriter, err error) {
	writeJSON(w, http.StatusInternalServerError, map[string]string{
		"error":   "internal_error",
		"message": err.Error(),
	})
}

func parseInt64PathParam(pathValue, prefix string) (int64, error) {
	value := strings.TrimPrefix(pathValue, prefix)
	if value == "" || value == pathValue {
		return 0, errors.New("path parameter is missing")
	}

	parsed, err := strconv.ParseInt(value, 10, 64)
	if err != nil {
		return 0, errors.New("path parameter must be an integer")
	}

	return parsed, nil
}

func decodeImportSource(req *http.Request) (string, error) {
	contentType := strings.ToLower(strings.TrimSpace(req.Header.Get("Content-Type")))
	if strings.HasPrefix(contentType, "application/json") {
		var payload struct {
			Source string `json:"source"`
		}
		if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
			return "", err
		}
		if strings.TrimSpace(payload.Source) == "" {
			return "", errors.New("source is required")
		}
		return payload.Source, nil
	}

	body, err := io.ReadAll(req.Body)
	if err != nil {
		return "", err
	}
	if strings.TrimSpace(string(body)) == "" {
		return "", errors.New("request body is empty")
	}
	return string(body), nil
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)

	if err := json.NewEncoder(w).Encode(payload); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
