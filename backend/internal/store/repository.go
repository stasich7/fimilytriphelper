package store

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/user/familytriphelper/backend/internal/domain"
	"github.com/user/familytriphelper/backend/internal/plan"
)

type Overview struct {
	Trip           *domain.Trip        `json:"trip,omitempty"`
	CurrentVersion *domain.PlanVersion `json:"currentVersion,omitempty"`
	Stats          OverviewStats       `json:"stats"`
}

type OverviewStats struct {
	Items        int `json:"items"`
	Comments     int `json:"comments"`
	OpenComments int `json:"openComments"`
}

type VersionDetails struct {
	Version  domain.PlanVersion `json:"version"`
	Items    []domain.PlanItem  `json:"items"`
	Comments []domain.Comment   `json:"comments"`
}

type ItemDetails struct {
	Item     domain.PlanItem  `json:"item"`
	Comments []domain.Comment `json:"comments"`
}

type ImportResult struct {
	VersionID     int64  `json:"versionID"`
	VersionCode   string `json:"versionCode"`
	ImportedItems int    `json:"importedItems"`
}

type GuestLookup struct {
	Participant domain.Participant `json:"participant"`
}

func (r *Repository) GetOverview(ctx context.Context) (Overview, error) {
	var overview Overview
	var trip domain.Trip

	err := r.db.QueryRowContext(ctx, `
		SELECT id, slug, title, status, created_at, updated_at
		FROM trips
		WHERE singleton_key = 'active'
	`).Scan(&trip.ID, &trip.Slug, &trip.Title, &trip.Status, &trip.CreatedAt, &trip.UpdatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return overview, nil
		}
		return Overview{}, fmt.Errorf("select trip: %w", err)
	}
	overview.Trip = &trip

	var currentVersion domain.PlanVersion
	err = r.db.QueryRowContext(ctx, `
		SELECT id, version_code, title, created_at
		FROM plan_versions
		WHERE trip_id = $1
		ORDER BY created_at DESC, id DESC
		LIMIT 1
	`, trip.ID).Scan(&currentVersion.ID, &currentVersion.VersionCode, &currentVersion.Title, &currentVersion.CreatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return overview, nil
		}
		return Overview{}, fmt.Errorf("select current version: %w", err)
	}
	overview.CurrentVersion = &currentVersion

	if err := r.db.QueryRowContext(ctx, `
		SELECT COUNT(*)
		FROM plan_items
		WHERE plan_version_id = $1
	`, currentVersion.ID).Scan(&overview.Stats.Items); err != nil {
		return Overview{}, fmt.Errorf("count items: %w", err)
	}

	if err := r.db.QueryRowContext(ctx, `
		SELECT COUNT(*)
		FROM comments
		WHERE plan_version_id = $1
	`, currentVersion.ID).Scan(&overview.Stats.Comments); err != nil {
		return Overview{}, fmt.Errorf("count comments: %w", err)
	}

	overview.Stats.OpenComments = overview.Stats.Comments

	return overview, nil
}

func (r *Repository) ListVersions(ctx context.Context) ([]domain.PlanVersion, error) {
	rows, err := r.db.QueryContext(ctx, `
		SELECT id, version_code, title, created_at
		FROM plan_versions
		ORDER BY created_at DESC, id DESC
	`)
	if err != nil {
		return nil, fmt.Errorf("list versions: %w", err)
	}
	defer rows.Close()

	var versions []domain.PlanVersion
	for rows.Next() {
		var version domain.PlanVersion
		if err := rows.Scan(&version.ID, &version.VersionCode, &version.Title, &version.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan version: %w", err)
		}
		versions = append(versions, version)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate versions: %w", err)
	}

	return versions, nil
}

func (r *Repository) GetVersion(ctx context.Context, versionID int64) (VersionDetails, error) {
	details := VersionDetails{
		Items:    []domain.PlanItem{},
		Comments: []domain.Comment{},
	}

	err := r.db.QueryRowContext(ctx, `
		SELECT id, version_code, title, created_at
		FROM plan_versions
		WHERE id = $1
	`, versionID).Scan(&details.Version.ID, &details.Version.VersionCode, &details.Version.Title, &details.Version.CreatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return VersionDetails{}, ErrNotFound
		}
		return VersionDetails{}, fmt.Errorf("select version: %w", err)
	}

	rows, err := r.db.QueryContext(ctx, `
		SELECT id, stable_key, type, title, body_markdown, created_at, updated_at
		FROM plan_items
		WHERE plan_version_id = $1
		ORDER BY type ASC, id ASC
	`, versionID)
	if err != nil {
		return VersionDetails{}, fmt.Errorf("select version items: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var item domain.PlanItem
		if err := rows.Scan(&item.ID, &item.StableKey, &item.Type, &item.Title, &item.BodyMarkdown, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return VersionDetails{}, fmt.Errorf("scan version item: %w", err)
		}
		details.Items = append(details.Items, item)
	}

	if err := rows.Err(); err != nil {
		return VersionDetails{}, fmt.Errorf("iterate version items: %w", err)
	}

	commentRows, err := r.db.QueryContext(ctx, `
		SELECT c.id, p.display_name, c.body, c.created_at
		FROM comments c
		JOIN participants p ON p.id = c.participant_id
		WHERE c.plan_version_id = $1 AND c.plan_item_id IS NULL
		ORDER BY c.created_at ASC, c.id ASC
	`, versionID)
	if err != nil {
		return VersionDetails{}, fmt.Errorf("select version comments: %w", err)
	}
	defer commentRows.Close()

	for commentRows.Next() {
		var comment domain.Comment
		if err := commentRows.Scan(&comment.ID, &comment.Author, &comment.Body, &comment.CreatedAt); err != nil {
			return VersionDetails{}, fmt.Errorf("scan version comment: %w", err)
		}
		details.Comments = append(details.Comments, comment)
	}

	if err := commentRows.Err(); err != nil {
		return VersionDetails{}, fmt.Errorf("iterate version comments: %w", err)
	}

	return details, nil
}

func (r *Repository) GetItem(ctx context.Context, itemID int64) (ItemDetails, error) {
	details := ItemDetails{
		Comments: []domain.Comment{},
	}

	err := r.db.QueryRowContext(ctx, `
		SELECT id, stable_key, type, title, body_markdown, created_at, updated_at
		FROM plan_items
		WHERE id = $1
	`, itemID).Scan(
		&details.Item.ID,
		&details.Item.StableKey,
		&details.Item.Type,
		&details.Item.Title,
		&details.Item.BodyMarkdown,
		&details.Item.CreatedAt,
		&details.Item.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return ItemDetails{}, ErrNotFound
		}
		return ItemDetails{}, fmt.Errorf("select item: %w", err)
	}

	rows, err := r.db.QueryContext(ctx, `
		SELECT c.id, p.display_name, c.body, c.created_at
		FROM comments c
		JOIN participants p ON p.id = c.participant_id
		WHERE c.plan_item_id = $1
		ORDER BY c.created_at ASC, c.id ASC
	`, itemID)
	if err != nil {
		return ItemDetails{}, fmt.Errorf("select comments: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var comment domain.Comment
		if err := rows.Scan(&comment.ID, &comment.Author, &comment.Body, &comment.CreatedAt); err != nil {
			return ItemDetails{}, fmt.Errorf("scan comment: %w", err)
		}
		details.Comments = append(details.Comments, comment)
	}

	if err := rows.Err(); err != nil {
		return ItemDetails{}, fmt.Errorf("iterate comments: %w", err)
	}

	return details, nil
}

func (r *Repository) GetGuestByToken(ctx context.Context, guestToken string) (GuestLookup, error) {
	var (
		guest    GuestLookup
		lastSeen sql.NullTime
	)

	err := r.db.QueryRowContext(ctx, `
		SELECT id, display_name, created_at, last_seen_at
		FROM participants
		WHERE guest_token = $1
	`, strings.TrimSpace(guestToken)).Scan(
		&guest.Participant.ID,
		&guest.Participant.DisplayName,
		&guest.Participant.CreatedAt,
		&lastSeen,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return GuestLookup{}, ErrNotFound
		}
		return GuestLookup{}, fmt.Errorf("select guest: %w", err)
	}

	if lastSeen.Valid {
		guest.Participant.LastSeenAt = lastSeen.Time
	}

	return guest, nil
}

func (r *Repository) CreateGuest(ctx context.Context, displayName string) (domain.Participant, string, error) {
	name := strings.TrimSpace(displayName)
	if name == "" {
		return domain.Participant{}, "", fmt.Errorf("display name is required")
	}

	var tripID int64
	err := r.db.QueryRowContext(ctx, `
		SELECT id
		FROM trips
		WHERE singleton_key = 'active'
	`).Scan(&tripID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Participant{}, "", fmt.Errorf("active trip is not initialized")
		}
		return domain.Participant{}, "", fmt.Errorf("select active trip: %w", err)
	}

	for attempt := 0; attempt < 5; attempt++ {
		token, err := generateGuestToken()
		if err != nil {
			return domain.Participant{}, "", err
		}

		var participant domain.Participant
		insertErr := r.db.QueryRowContext(ctx, `
			INSERT INTO participants (trip_id, display_name, guest_token)
			VALUES ($1, $2, $3)
			RETURNING id, display_name, created_at
		`, tripID, name, token).Scan(
			&participant.ID,
			&participant.DisplayName,
			&participant.CreatedAt,
		)
		if insertErr == nil {
			return participant, token, nil
		}

		if strings.Contains(insertErr.Error(), "participants_guest_token_key") {
			continue
		}

		return domain.Participant{}, "", fmt.Errorf("insert participant: %w", insertErr)
	}

	return domain.Participant{}, "", fmt.Errorf("could not generate a unique guest token")
}

func (r *Repository) CreateCommentByGuestToken(ctx context.Context, guestToken string, planVersionID, planItemID int64, body string) (domain.Comment, error) {
	cleanBody := strings.TrimSpace(body)
	if cleanBody == "" {
		return domain.Comment{}, fmt.Errorf("comment body is required")
	}
	if planVersionID == 0 && planItemID == 0 {
		return domain.Comment{}, fmt.Errorf("planVersionID or planItemID is required")
	}

	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Comment{}, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	var participantID int64
	err = tx.QueryRowContext(ctx, `
		SELECT id
		FROM participants
		WHERE guest_token = $1
	`, strings.TrimSpace(guestToken)).Scan(&participantID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Comment{}, ErrNotFound
		}
		return domain.Comment{}, fmt.Errorf("select participant by token: %w", err)
	}

	var tripID int64
	if planItemID != 0 {
		err = tx.QueryRowContext(ctx, `
			SELECT trip_id, plan_version_id
			FROM plan_items
			WHERE id = $1
		`, planItemID).Scan(&tripID, &planVersionID)
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return domain.Comment{}, ErrNotFound
			}
			return domain.Comment{}, fmt.Errorf("select plan item for comment: %w", err)
		}
	} else {
		err = tx.QueryRowContext(ctx, `
			SELECT trip_id
			FROM plan_versions
			WHERE id = $1
		`, planVersionID).Scan(&tripID)
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return domain.Comment{}, ErrNotFound
			}
			return domain.Comment{}, fmt.Errorf("select version for comment: %w", err)
		}
	}

	var created domain.Comment
	err = tx.QueryRowContext(ctx, `
		INSERT INTO comments (trip_id, plan_version_id, plan_item_id, participant_id, body)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, body, created_at
	`, tripID, planVersionID, nullableInt64(planItemID), participantID, cleanBody).Scan(
		&created.ID,
		&created.Body,
		&created.CreatedAt,
	)
	if err != nil {
		return domain.Comment{}, fmt.Errorf("insert comment: %w", err)
	}

	err = tx.QueryRowContext(ctx, `
		SELECT display_name
		FROM participants
		WHERE id = $1
	`, participantID).Scan(&created.Author)
	if err != nil {
		return domain.Comment{}, fmt.Errorf("select comment author: %w", err)
	}

	if _, err := tx.ExecContext(ctx, `
		UPDATE participants
		SET last_seen_at = now()
		WHERE id = $1
	`, participantID); err != nil {
		return domain.Comment{}, fmt.Errorf("touch participant last_seen_at: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return domain.Comment{}, fmt.Errorf("commit comment: %w", err)
	}

	return created, nil
}

func (r *Repository) ImportPlan(ctx context.Context, doc plan.Document) (ImportResult, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return ImportResult{}, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	tripTitle := strings.TrimSpace(doc.TripTitle)
	if tripTitle == "" {
		tripTitle = strings.TrimSpace(doc.TripID)
	}

	var tripID int64
	err = tx.QueryRowContext(ctx, `
		INSERT INTO trips (singleton_key, slug, title)
		VALUES ('active', $1, $2)
		ON CONFLICT (singleton_key) DO UPDATE
		SET slug = EXCLUDED.slug,
		    title = EXCLUDED.title,
		    updated_at = now()
		RETURNING id
	`, doc.TripID, tripTitle).Scan(&tripID)
	if err != nil {
		return ImportResult{}, fmt.Errorf("upsert trip: %w", err)
	}

	var existingVersionID int64
	err = tx.QueryRowContext(ctx, `
		SELECT id
		FROM plan_versions
		WHERE trip_id = $1 AND version_code = $2
	`, tripID, doc.VersionID).Scan(&existingVersionID)
	if err == nil {
		return ImportResult{}, fmt.Errorf("version %q already exists", doc.VersionID)
	}
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return ImportResult{}, fmt.Errorf("check existing version: %w", err)
	}

	var versionID int64
	err = tx.QueryRowContext(ctx, `
		INSERT INTO plan_versions (trip_id, version_code, title, raw_source)
		VALUES ($1, $2, $3, $4)
		RETURNING id
	`, tripID, doc.VersionID, doc.Title, doc.Source).Scan(&versionID)
	if err != nil {
		return ImportResult{}, fmt.Errorf("insert version: %w", err)
	}

	for _, item := range doc.Items {
		metadataJSON, err := json.Marshal(item.Metadata)
		if err != nil {
			return ImportResult{}, fmt.Errorf("marshal metadata for %s: %w", item.StableKey, err)
		}

		if _, err := tx.ExecContext(ctx, `
			INSERT INTO plan_items (
			    trip_id,
			    plan_version_id,
			    stable_key,
			    type,
			    title,
			    body_markdown,
			    metadata_json
			)
			VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
		`, tripID, versionID, item.StableKey, item.Type, item.Title, item.BodyMarkdown, string(metadataJSON)); err != nil {
			return ImportResult{}, fmt.Errorf("insert item %s: %w", item.StableKey, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return ImportResult{}, fmt.Errorf("commit import: %w", err)
	}

	return ImportResult{
		VersionID:     versionID,
		VersionCode:   doc.VersionID,
		ImportedItems: len(doc.Items),
	}, nil
}

func generateGuestToken() (string, error) {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "", fmt.Errorf("generate guest token: %w", err)
	}

	return hex.EncodeToString(buf), nil
}

func nullableInt64(value int64) any {
	if value == 0 {
		return nil
	}

	return value
}
