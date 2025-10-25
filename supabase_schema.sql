-- Supabase schema for Carlos Wine Collection
-- Run this in Supabase SQL Editor

-- Storage table
CREATE TABLE storage (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    zones JSONB NOT NULL,
    total_positions INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Positions table
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    storage_id TEXT NOT NULL REFERENCES storage(id),
    zone TEXT NOT NULL,
    identifier TEXT NOT NULL,
    is_occupied BOOLEAN DEFAULT FALSE,
    wine_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Wines table
CREATE TABLE wines (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    position_id TEXT REFERENCES positions(id),
    added_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consumed BOOLEAN DEFAULT FALSE,
    consumed_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add indexes for better performance
CREATE INDEX idx_wines_consumed ON wines(consumed);
CREATE INDEX idx_wines_position ON wines(position_id);
CREATE INDEX idx_positions_occupied ON positions(is_occupied);
CREATE INDEX idx_positions_storage ON positions(storage_id);
