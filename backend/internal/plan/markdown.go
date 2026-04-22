package plan

import (
	"fmt"
	"regexp"
	"strings"
)

var (
	itemHeadingPattern = regexp.MustCompile(`^## \[([^\]]+)\]\s+(.+)$`)
	metadataPattern    = regexp.MustCompile(`^([A-Za-z][A-Za-z0-9_ -]*):\s*(.+)$`)
)

type Document struct {
	TripID    string
	TripTitle string
	VersionID string
	Title     string
	Source    string
	Items     []Item
}

type Item struct {
	StableKey    string
	Title        string
	Type         string
	BodyMarkdown string
	Metadata     map[string]string
}

func ParseMarkdown(source string) (Document, error) {
	normalized := normalizeLineEndings(source)
	frontMatter, body, err := splitFrontMatter(normalized)
	if err != nil {
		return Document{}, err
	}

	doc := Document{
		TripID:    strings.TrimSpace(frontMatter["trip_id"]),
		TripTitle: strings.TrimSpace(frontMatter["trip_title"]),
		VersionID: strings.TrimSpace(frontMatter["version_id"]),
		Title:     strings.TrimSpace(frontMatter["title"]),
		Source:    normalized,
	}

	if doc.TripID == "" {
		return Document{}, fmt.Errorf("trip_id is required")
	}
	if doc.VersionID == "" {
		return Document{}, fmt.Errorf("version_id is required")
	}
	if doc.Title == "" {
		return Document{}, fmt.Errorf("title is required")
	}

	items, err := parseItems(body)
	if err != nil {
		return Document{}, err
	}
	if len(items) == 0 {
		return Document{}, fmt.Errorf("no items found")
	}

	doc.Items = items

	return doc, nil
}

func splitFrontMatter(source string) (map[string]string, string, error) {
	if !strings.HasPrefix(source, "---\n") {
		return nil, "", fmt.Errorf("front matter is required")
	}

	rest := strings.TrimPrefix(source, "---\n")
	idx := strings.Index(rest, "\n---\n")
	if idx < 0 {
		return nil, "", fmt.Errorf("front matter closing delimiter is missing")
	}

	frontMatterBlock := rest[:idx]
	body := rest[idx+len("\n---\n"):]
	metadata := make(map[string]string)

	for _, line := range strings.Split(frontMatterBlock, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		parts := strings.SplitN(line, ":", 2)
		if len(parts) != 2 {
			return nil, "", fmt.Errorf("invalid front matter line %q", line)
		}

		key := strings.TrimSpace(strings.ToLower(parts[0]))
		value := strings.TrimSpace(parts[1])
		metadata[key] = value
	}

	return metadata, strings.TrimSpace(body), nil
}

func parseItems(body string) ([]Item, error) {
	var (
		items       []Item
		currentItem *Item
		sectionBody []string
		seenKeys    = make(map[string]struct{})
	)

	finalizeCurrent := func() error {
		if currentItem == nil {
			return nil
		}

		item, err := finalizeItem(*currentItem, sectionBody)
		if err != nil {
			return err
		}

		if _, exists := seenKeys[item.StableKey]; exists {
			return fmt.Errorf("duplicate stable key %q", item.StableKey)
		}
		seenKeys[item.StableKey] = struct{}{}

		items = append(items, item)
		currentItem = nil
		sectionBody = nil
		return nil
	}

	for _, line := range strings.Split(body, "\n") {
		if matches := itemHeadingPattern.FindStringSubmatch(line); matches != nil {
			if err := finalizeCurrent(); err != nil {
				return nil, err
			}

			currentItem = &Item{
				StableKey: strings.TrimSpace(matches[1]),
				Title:     strings.TrimSpace(matches[2]),
				Metadata:  make(map[string]string),
			}
			continue
		}

		if currentItem != nil {
			sectionBody = append(sectionBody, line)
		}
	}

	if err := finalizeCurrent(); err != nil {
		return nil, err
	}

	return items, nil
}

func finalizeItem(item Item, rawLines []string) (Item, error) {
	lines := trimBlankLines(rawLines)
	bodyStart := 0

	for bodyStart < len(lines) {
		line := strings.TrimSpace(lines[bodyStart])
		if line == "" {
			bodyStart++
			continue
		}

		matches := metadataPattern.FindStringSubmatch(line)
		if matches == nil {
			break
		}

		key := strings.TrimSpace(matches[1])
		value := strings.TrimSpace(matches[2])
		item.Metadata[key] = value
		if strings.EqualFold(key, "type") {
			item.Type = normalizeType(value)
		}
		bodyStart++
	}

	if item.Type == "" {
		item.Type = "note"
	}

	item.BodyMarkdown = strings.TrimSpace(strings.Join(lines[bodyStart:], "\n"))
	if item.BodyMarkdown == "" {
		return Item{}, fmt.Errorf("item %q has empty body", item.StableKey)
	}

	return item, nil
}

func normalizeType(value string) string {
	value = strings.TrimSpace(strings.ToLower(value))
	value = strings.ReplaceAll(value, " ", "_")
	value = strings.ReplaceAll(value, "-", "_")
	return value
}

func trimBlankLines(lines []string) []string {
	start := 0
	for start < len(lines) && strings.TrimSpace(lines[start]) == "" {
		start++
	}

	end := len(lines)
	for end > start && strings.TrimSpace(lines[end-1]) == "" {
		end--
	}

	return lines[start:end]
}

func normalizeLineEndings(source string) string {
	source = strings.ReplaceAll(source, "\r\n", "\n")
	source = strings.ReplaceAll(source, "\r", "\n")
	return strings.TrimPrefix(source, "\uFEFF")
}
