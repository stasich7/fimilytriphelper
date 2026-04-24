package domain

import "time"

type Trip struct {
	ID        int64     `json:"id"`
	Slug      string    `json:"slug"`
	Title     string    `json:"title"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"createdAt"`
	UpdatedAt time.Time `json:"updatedAt"`
}

type PlanVersion struct {
	ID          int64     `json:"id"`
	VersionCode string    `json:"versionCode"`
	Title       string    `json:"title"`
	CreatedAt   time.Time `json:"createdAt"`
}

type PlanItem struct {
	ID                  int64     `json:"id"`
	PlanVersionID       int64     `json:"planVersionID"`
	StableKey           string    `json:"stableKey"`
	Type                string    `json:"type"`
	Title               string    `json:"title"`
	BodyMarkdown        string    `json:"bodyMarkdown"`
	LikesCount          int       `json:"likesCount"`
	LikedByCurrentGuest bool      `json:"likedByCurrentGuest"`
	CreatedAt           time.Time `json:"createdAt"`
	UpdatedAt           time.Time `json:"updatedAt"`
}

type Participant struct {
	ID          int64     `json:"id"`
	DisplayName string    `json:"displayName"`
	CreatedAt   time.Time `json:"createdAt"`
	LastSeenAt  time.Time `json:"lastSeenAt"`
}

type Comment struct {
	ID        int64     `json:"id"`
	Author    string    `json:"author"`
	Body      string    `json:"body"`
	CreatedAt time.Time `json:"createdAt"`
}
