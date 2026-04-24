CREATE TABLE item_likes (
    plan_item_id BIGINT NOT NULL REFERENCES plan_items(id) ON DELETE CASCADE,
    participant_id BIGINT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (plan_item_id, participant_id)
);

CREATE INDEX idx_item_likes_participant
    ON item_likes (participant_id);
