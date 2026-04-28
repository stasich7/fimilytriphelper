package store

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

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

type CodexExport struct {
	VersionID   int64  `json:"versionID"`
	VersionCode string `json:"versionCode"`
	Markdown    string `json:"markdown"`
}

type ManagedGuest struct {
	ID            int64      `json:"id"`
	DisplayName   string     `json:"displayName"`
	GuestToken    string     `json:"guestToken"`
	CreatedAt     time.Time  `json:"createdAt"`
	LastSeenAt    *time.Time `json:"lastSeenAt"`
	CommentsCount int        `json:"commentsCount"`
}

type LikeToggleResult struct {
	Liked      bool `json:"liked"`
	LikesCount int  `json:"likesCount"`
}

func (r *Repository) GetOverview(ctx context.Context, language string) (Overview, error) {
	var overview Overview
	var trip domain.Trip
	language = normalizePlanLanguage(language)

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

	versions, err := r.listVersionsByTrip(ctx, trip.ID)
	if err != nil {
		return Overview{}, err
	}
	currentVersion, ok := selectCurrentVersionForLanguage(versions, language)
	if !ok {
		return overview, nil
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

func (r *Repository) ListVersions(ctx context.Context, language string) ([]domain.PlanVersion, error) {
	language = normalizePlanLanguage(language)
	rows, err := r.db.QueryContext(ctx, `
		SELECT id, version_code, title, created_at
		FROM plan_versions
		ORDER BY created_at DESC, id DESC
	`)
	if err != nil {
		return nil, fmt.Errorf("list versions: %w", err)
	}
	defer rows.Close()

	versions := make([]domain.PlanVersion, 0)
	for rows.Next() {
		var version domain.PlanVersion
		if err := rows.Scan(&version.ID, &version.VersionCode, &version.Title, &version.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan version: %w", err)
		}
		version.Language = detectVersionLanguage(version.VersionCode)
		if version.Language != language {
			continue
		}
		versions = append(versions, version)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate versions: %w", err)
	}

	return versions, nil
}

func (r *Repository) GetVersion(ctx context.Context, versionID int64, guestToken, language string) (VersionDetails, error) {
	targetVersionID, err := r.resolveLocalizedVersionID(ctx, versionID, language)
	if err != nil {
		return VersionDetails{}, err
	}

	return r.loadVersionDetailsByID(ctx, targetVersionID, guestToken)
}

func (r *Repository) loadVersionDetailsByID(ctx context.Context, versionID int64, guestToken string) (VersionDetails, error) {
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
	details.Version.Language = detectVersionLanguage(details.Version.VersionCode)

	rows, err := r.db.QueryContext(ctx, `
		WITH current_guest AS (
			SELECT id
			FROM participants
			WHERE guest_token = NULLIF($2, '')
			LIMIT 1
		)
		SELECT
			pi.id,
			pi.plan_version_id,
			pi.stable_key,
			pi.type,
			pi.title,
			pi.body_markdown,
			COUNT(il.participant_id) AS likes_count,
			EXISTS (
				SELECT 1
				FROM item_likes current_like
				WHERE current_like.plan_item_id = pi.id
					AND current_like.participant_id = (SELECT id FROM current_guest)
			) AS liked_by_current_guest,
			pi.created_at,
			pi.updated_at
		FROM plan_items pi
		LEFT JOIN item_likes il ON il.plan_item_id = pi.id
		WHERE pi.plan_version_id = $1
		GROUP BY pi.id, pi.plan_version_id, pi.stable_key, pi.type, pi.title, pi.body_markdown, pi.created_at, pi.updated_at
		ORDER BY pi.type ASC, pi.id ASC
	`, versionID, strings.TrimSpace(guestToken))
	if err != nil {
		return VersionDetails{}, fmt.Errorf("select version items: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var item domain.PlanItem
		if err := rows.Scan(
			&item.ID,
			&item.PlanVersionID,
			&item.StableKey,
			&item.Type,
			&item.Title,
			&item.BodyMarkdown,
			&item.LikesCount,
			&item.LikedByCurrentGuest,
			&item.CreatedAt,
			&item.UpdatedAt,
		); err != nil {
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

func (r *Repository) ToggleItemLikeByGuestToken(ctx context.Context, itemID int64, guestToken string) (LikeToggleResult, error) {
	token := strings.TrimSpace(guestToken)
	if token == "" {
		return LikeToggleResult{}, fmt.Errorf("guest token is required")
	}

	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return LikeToggleResult{}, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	var participantID int64
	if err := tx.QueryRowContext(ctx, `
		SELECT id
		FROM participants
		WHERE guest_token = $1
	`, token).Scan(&participantID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return LikeToggleResult{}, ErrNotFound
		}
		return LikeToggleResult{}, fmt.Errorf("select participant by token: %w", err)
	}

	var itemExists bool
	if err := tx.QueryRowContext(ctx, `
		SELECT EXISTS (
			SELECT 1
			FROM plan_items
			WHERE id = $1
		)
	`, itemID).Scan(&itemExists); err != nil {
		return LikeToggleResult{}, fmt.Errorf("select item exists: %w", err)
	}
	if !itemExists {
		return LikeToggleResult{}, ErrNotFound
	}

	result, err := tx.ExecContext(ctx, `
		DELETE FROM item_likes
		WHERE plan_item_id = $1 AND participant_id = $2
	`, itemID, participantID)
	if err != nil {
		return LikeToggleResult{}, fmt.Errorf("delete item like: %w", err)
	}

	affected, err := result.RowsAffected()
	if err != nil {
		return LikeToggleResult{}, fmt.Errorf("delete item like rows affected: %w", err)
	}

	liked := false
	if affected == 0 {
		if _, err := tx.ExecContext(ctx, `
			INSERT INTO item_likes (plan_item_id, participant_id)
			VALUES ($1, $2)
			ON CONFLICT (plan_item_id, participant_id) DO NOTHING
		`, itemID, participantID); err != nil {
			return LikeToggleResult{}, fmt.Errorf("insert item like: %w", err)
		}
		liked = true
	}

	if _, err := tx.ExecContext(ctx, `
		UPDATE participants
		SET last_seen_at = now()
		WHERE id = $1
	`, participantID); err != nil {
		return LikeToggleResult{}, fmt.Errorf("touch participant last_seen_at: %w", err)
	}

	var likesCount int
	if err := tx.QueryRowContext(ctx, `
		SELECT COUNT(*)
		FROM item_likes
		WHERE plan_item_id = $1
	`, itemID).Scan(&likesCount); err != nil {
		return LikeToggleResult{}, fmt.Errorf("count item likes: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return LikeToggleResult{}, fmt.Errorf("commit item like: %w", err)
	}

	return LikeToggleResult{
		Liked:      liked,
		LikesCount: likesCount,
	}, nil
}

func (r *Repository) GetItem(ctx context.Context, itemID int64, guestToken, language string) (ItemDetails, error) {
	targetItemID, err := r.resolveLocalizedItemID(ctx, itemID, language)
	if err != nil {
		return ItemDetails{}, err
	}

	return r.loadItemDetailsByID(ctx, targetItemID, guestToken)
}

func (r *Repository) loadItemDetailsByID(ctx context.Context, itemID int64, guestToken string) (ItemDetails, error) {
	details := ItemDetails{
		Comments: []domain.Comment{},
	}

	err := r.db.QueryRowContext(ctx, `
		WITH current_guest AS (
			SELECT id
			FROM participants
			WHERE guest_token = NULLIF($2, '')
			LIMIT 1
		)
		SELECT
			pi.id,
			pi.plan_version_id,
			pi.stable_key,
			pi.type,
			pi.title,
			pi.body_markdown,
			COUNT(il.participant_id) AS likes_count,
			EXISTS (
				SELECT 1
				FROM item_likes current_like
				WHERE current_like.plan_item_id = pi.id
					AND current_like.participant_id = (SELECT id FROM current_guest)
			) AS liked_by_current_guest,
			pi.created_at,
			pi.updated_at
		FROM plan_items pi
		LEFT JOIN item_likes il ON il.plan_item_id = pi.id
		WHERE pi.id = $1
		GROUP BY pi.id, pi.plan_version_id, pi.stable_key, pi.type, pi.title, pi.body_markdown, pi.created_at, pi.updated_at
	`, itemID, strings.TrimSpace(guestToken)).Scan(
		&details.Item.ID,
		&details.Item.PlanVersionID,
		&details.Item.StableKey,
		&details.Item.Type,
		&details.Item.Title,
		&details.Item.BodyMarkdown,
		&details.Item.LikesCount,
		&details.Item.LikedByCurrentGuest,
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

	tripID, err := r.getActiveTripID(ctx)
	if err != nil {
		return domain.Participant{}, "", err
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

func (r *Repository) ListGuests(ctx context.Context) ([]ManagedGuest, error) {
	tripID, err := r.getActiveTripID(ctx)
	if err != nil {
		return nil, err
	}

	rows, err := r.db.QueryContext(ctx, `
		SELECT
			p.id,
			p.display_name,
			p.guest_token,
			p.created_at,
			p.last_seen_at,
			COUNT(c.id) AS comments_count
		FROM participants p
		LEFT JOIN comments c ON c.participant_id = p.id
		WHERE p.trip_id = $1
		GROUP BY p.id, p.display_name, p.guest_token, p.created_at, p.last_seen_at
		ORDER BY p.created_at DESC, p.id DESC
	`, tripID)
	if err != nil {
		return nil, fmt.Errorf("list guests: %w", err)
	}
	defer rows.Close()

	guests := make([]ManagedGuest, 0)
	for rows.Next() {
		var (
			guest    ManagedGuest
			lastSeen sql.NullTime
		)
		if err := rows.Scan(
			&guest.ID,
			&guest.DisplayName,
			&guest.GuestToken,
			&guest.CreatedAt,
			&lastSeen,
			&guest.CommentsCount,
		); err != nil {
			return nil, fmt.Errorf("scan guest: %w", err)
		}
		if lastSeen.Valid {
			value := lastSeen.Time
			guest.LastSeenAt = &value
		}
		guests = append(guests, guest)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate guests: %w", err)
	}

	return guests, nil
}

func (r *Repository) CreateManagedGuest(ctx context.Context, displayName string) (ManagedGuest, error) {
	participant, token, err := r.CreateGuest(ctx, displayName)
	if err != nil {
		return ManagedGuest{}, err
	}

	return ManagedGuest{
		ID:            participant.ID,
		DisplayName:   participant.DisplayName,
		GuestToken:    token,
		CreatedAt:     participant.CreatedAt,
		LastSeenAt:    nil,
		CommentsCount: 0,
	}, nil
}

func (r *Repository) DeleteGuest(ctx context.Context, guestID int64) error {
	var commentsCount int
	err := r.db.QueryRowContext(ctx, `
		SELECT COUNT(*)
		FROM comments
		WHERE participant_id = $1
	`, guestID).Scan(&commentsCount)
	if err != nil {
		return fmt.Errorf("count guest comments: %w", err)
	}
	if commentsCount > 0 {
		return fmt.Errorf("guest has comments and cannot be deleted")
	}

	result, err := r.db.ExecContext(ctx, `
		DELETE FROM participants
		WHERE id = $1
	`, guestID)
	if err != nil {
		return fmt.Errorf("delete guest: %w", err)
	}

	affected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete guest rows affected: %w", err)
	}
	if affected == 0 {
		return ErrNotFound
	}

	return nil
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

func (r *Repository) ExportCodex(ctx context.Context, versionRef string) (CodexExport, error) {
	versionRef = strings.TrimSpace(versionRef)
	if versionRef == "" {
		return CodexExport{}, fmt.Errorf("version reference is required")
	}

	versionID, versionCode, err := r.resolveVersionRef(ctx, versionRef)
	if err != nil {
		return CodexExport{}, err
	}

	versionDetails, err := r.GetVersion(ctx, versionID, "", detectVersionLanguage(versionCode))
	if err != nil {
		return CodexExport{}, err
	}

	itemComments, err := r.listExportItemComments(ctx, versionID)
	if err != nil {
		return CodexExport{}, err
	}

	itemByID := make(map[int64]domain.PlanItem, len(versionDetails.Items))
	for _, item := range versionDetails.Items {
		itemByID[item.ID] = item
	}

	var builder strings.Builder
	builder.WriteString("Trip: ")
	builder.WriteString(versionDetails.Version.Title)
	builder.WriteString("\n")
	builder.WriteString("Version: ")
	builder.WriteString(versionCode)
	builder.WriteString("\n")

	builder.WriteString("\n## Version comments\n")
	if len(versionDetails.Comments) == 0 {
		builder.WriteString("No comments.\n")
	} else {
		for index, comment := range versionDetails.Comments {
			writeExportComment(&builder, index+1, comment)
		}
	}

	builder.WriteString("\n## Item comments\n")
	if len(itemComments) == 0 {
		builder.WriteString("No comments.\n")
	} else {
		itemIDs := make([]int64, 0, len(itemComments))
		for itemID := range itemComments {
			itemIDs = append(itemIDs, itemID)
		}
		sort.Slice(itemIDs, func(i, j int) bool { return itemIDs[i] < itemIDs[j] })

		for _, itemID := range itemIDs {
			item, ok := itemByID[itemID]
			if !ok {
				continue
			}

			builder.WriteString("\n### stable_key=")
			builder.WriteString(item.StableKey)
			builder.WriteString("\n")
			builder.WriteString("title=")
			builder.WriteString(item.Title)
			builder.WriteString("\n\n")

			for index, comment := range itemComments[itemID] {
				writeExportComment(&builder, index+1, comment)
			}
		}
	}

	return CodexExport{
		VersionID:   versionID,
		VersionCode: versionCode,
		Markdown:    builder.String(),
	}, nil
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

func (r *Repository) getActiveTripID(ctx context.Context) (int64, error) {
	var tripID int64
	err := r.db.QueryRowContext(ctx, `
		SELECT id
		FROM trips
		WHERE singleton_key = 'active'
	`).Scan(&tripID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, fmt.Errorf("active trip is not initialized")
		}
		return 0, fmt.Errorf("select active trip: %w", err)
	}

	return tripID, nil
}

func normalizePlanLanguage(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "en":
		return "en"
	default:
		return "ru"
	}
}

func detectVersionLanguage(versionCode string) string {
	if strings.HasSuffix(strings.ToLower(strings.TrimSpace(versionCode)), "-en") {
		return "en"
	}

	return "ru"
}

func splitVersionCode(versionCode string) (string, string) {
	normalized := strings.TrimSpace(versionCode)
	language := detectVersionLanguage(normalized)
	if language == "en" {
		return strings.TrimSuffix(normalized, "-en"), "en"
	}

	return normalized, "ru"
}

func buildLocalizedVersionCode(baseCode, language string) string {
	if normalizePlanLanguage(language) == "en" {
		return fmt.Sprintf("%s-en", baseCode)
	}

	return baseCode
}

func selectCurrentVersionForLanguage(versions []domain.PlanVersion, language string) (domain.PlanVersion, bool) {
	for _, version := range versions {
		if version.Language == language {
			return version, true
		}
	}

	return domain.PlanVersion{}, false
}

func (r *Repository) listVersionsByTrip(ctx context.Context, tripID int64) ([]domain.PlanVersion, error) {
	rows, err := r.db.QueryContext(ctx, `
		SELECT id, version_code, title, created_at
		FROM plan_versions
		WHERE trip_id = $1
		ORDER BY created_at DESC, id DESC
	`, tripID)
	if err != nil {
		return nil, fmt.Errorf("list versions by trip: %w", err)
	}
	defer rows.Close()

	versions := make([]domain.PlanVersion, 0)
	for rows.Next() {
		var version domain.PlanVersion
		if err := rows.Scan(&version.ID, &version.VersionCode, &version.Title, &version.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan trip version: %w", err)
		}
		version.Language = detectVersionLanguage(version.VersionCode)
		versions = append(versions, version)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate trip versions: %w", err)
	}

	return versions, nil
}

func (r *Repository) resolveLocalizedVersionID(ctx context.Context, versionID int64, language string) (int64, error) {
	language = normalizePlanLanguage(language)

	var (
		tripID      int64
		versionCode string
	)

	err := r.db.QueryRowContext(ctx, `
		SELECT trip_id, version_code
		FROM plan_versions
		WHERE id = $1
	`, versionID).Scan(&tripID, &versionCode)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, ErrNotFound
		}
		return 0, fmt.Errorf("select version for language resolution: %w", err)
	}

	baseCode, _ := splitVersionCode(versionCode)
	targetCode := buildLocalizedVersionCode(baseCode, language)
	if targetCode == versionCode {
		return versionID, nil
	}

	var targetVersionID int64
	err = r.db.QueryRowContext(ctx, `
		SELECT id
		FROM plan_versions
		WHERE trip_id = $1 AND version_code = $2
	`, tripID, targetCode).Scan(&targetVersionID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, ErrNotFound
		}
		return 0, fmt.Errorf("select localized version: %w", err)
	}

	return targetVersionID, nil
}

func (r *Repository) resolveLocalizedItemID(ctx context.Context, itemID int64, language string) (int64, error) {
	language = normalizePlanLanguage(language)

	var (
		tripID      int64
		stableKey   string
		versionCode string
	)

	err := r.db.QueryRowContext(ctx, `
		SELECT pi.trip_id, pi.stable_key, pv.version_code
		FROM plan_items pi
		JOIN plan_versions pv ON pv.id = pi.plan_version_id
		WHERE pi.id = $1
	`, itemID).Scan(&tripID, &stableKey, &versionCode)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, ErrNotFound
		}
		return 0, fmt.Errorf("select item for language resolution: %w", err)
	}

	baseCode, _ := splitVersionCode(versionCode)
	targetCode := buildLocalizedVersionCode(baseCode, language)
	if targetCode == versionCode {
		return itemID, nil
	}

	var targetItemID int64
	err = r.db.QueryRowContext(ctx, `
		SELECT localized_item.id
		FROM plan_items localized_item
		JOIN plan_versions localized_version ON localized_version.id = localized_item.plan_version_id
		WHERE localized_item.trip_id = $1
			AND localized_item.stable_key = $2
			AND localized_version.version_code = $3
		LIMIT 1
	`, tripID, stableKey, targetCode).Scan(&targetItemID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, ErrNotFound
		}
		return 0, fmt.Errorf("select localized item: %w", err)
	}

	return targetItemID, nil
}

func (r *Repository) resolveVersionRef(ctx context.Context, versionRef string) (int64, string, error) {
	if parsedID, err := strconv.ParseInt(versionRef, 10, 64); err == nil {
		var versionCode string
		err = r.db.QueryRowContext(ctx, `
			SELECT version_code
			FROM plan_versions
			WHERE id = $1
		`, parsedID).Scan(&versionCode)
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return 0, "", ErrNotFound
			}
			return 0, "", fmt.Errorf("select version by id: %w", err)
		}

		return parsedID, versionCode, nil
	}

	var (
		versionID   int64
		versionCode string
	)
	err := r.db.QueryRowContext(ctx, `
		SELECT id, version_code
		FROM plan_versions
		WHERE version_code = $1
	`, versionRef).Scan(&versionID, &versionCode)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, "", ErrNotFound
		}
		return 0, "", fmt.Errorf("select version by code: %w", err)
	}

	return versionID, versionCode, nil
}

func (r *Repository) listExportItemComments(ctx context.Context, versionID int64) (map[int64][]domain.Comment, error) {
	rows, err := r.db.QueryContext(ctx, `
		SELECT c.plan_item_id, c.id, p.display_name, c.body, c.created_at
		FROM comments c
		JOIN participants p ON p.id = c.participant_id
		WHERE c.plan_version_id = $1 AND c.plan_item_id IS NOT NULL
		ORDER BY c.plan_item_id ASC, c.created_at ASC, c.id ASC
	`, versionID)
	if err != nil {
		return nil, fmt.Errorf("select item comments for export: %w", err)
	}
	defer rows.Close()

	result := map[int64][]domain.Comment{}
	for rows.Next() {
		var (
			itemID  int64
			comment domain.Comment
		)
		if err := rows.Scan(&itemID, &comment.ID, &comment.Author, &comment.Body, &comment.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan item comment for export: %w", err)
		}
		result[itemID] = append(result[itemID], comment)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate item comments for export: %w", err)
	}

	return result, nil
}

func writeExportComment(builder *strings.Builder, index int, comment domain.Comment) {
	builder.WriteString(strconv.Itoa(index))
	builder.WriteString(". author=")
	builder.WriteString(comment.Author)
	builder.WriteString("\n")
	builder.WriteString("   created_at=")
	builder.WriteString(comment.CreatedAt.In(time.UTC).Format(time.RFC3339))
	builder.WriteString("\n")
	builder.WriteString("   text=")
	builder.WriteString(comment.Body)
	builder.WriteString("\n\n")
}
