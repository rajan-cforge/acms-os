# ACMS Complete Build Guide for Claude Code

**🎯 MISSION:** Build a production-ready Adaptive Context Memory System MVP from scratch  
**⏱️ TIMELINE:** 4-6 weeks  
**🛠️ APPROACH:** Test-Driven Development, No Shortcuts, Production Quality  

---

## 📋 EXECUTIVE SUMMARY

Build ACMS - a privacy-first AI memory system that:
- Stores conversation context locally with encryption
- Intelligently recalls relevant memories using vector search
- Learns what context is useful through outcome tracking
- Reduces AI token usage by 30-50%
- Complies with GDPR/HIPAA/CCPA

**Tech Stack:** Go (services) + Python (ML/AI) + PostgreSQL + Redis + Ollama

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                   Client (CLI/Web/SDK)                       │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API (HTTP/JSON)
┌────────────────────▼────────────────────────────────────────┐
│                 API Gateway (Go/Chi)                         │
│  - JWT Authentication                                        │
│  - Rate Limiting (100 req/min)                              │
│  - Request Routing                                           │
│  - Metrics (Prometheus)                                      │
└──┬────────────┬─────────────┬─────────────┬────────────────┘
   │            │             │             │
   ▼            ▼             ▼             ▼
┌──────┐   ┌──────┐   ┌─────────┐   ┌──────────┐
│Memory│   │Rehydr│   │  Admin  │   │  CRS     │
│ Svc  │   │ Svc  │   │  Svc    │   │ Engine   │
│ (Go) │   │ (Go) │   │  (Go)   │   │(Python)  │
└──┬───┘   └──┬───┘   └────┬────┘   └────┬─────┘
   │          │            │              │
   └──────────┴────────────┴──────────────┘
                     │
        ┌────────────▼─────────────┐
        │   PostgreSQL + pgvector   │
        │   (Memory Items, Users)   │
        └────────────┬──────────────┘
                     │
        ┌────────────▼─────────────┐
        │      Redis (Cache)        │
        └───────────────────────────┘
                     │
        ┌────────────▼─────────────┐
        │   Ollama (Local LLM)      │
        │   - llama3.1:8b           │
        │   - nomic-embed-text      │
        └───────────────────────────┘
```

---

## 📦 PROJECT STRUCTURE

```
acms/
├── cmd/
│   ├── api-gateway/
│   │   └── main.go                 # Main API server entry point
│   └── cli/
│       └── main.go                 # CLI tool
├── pkg/
│   ├── auth/
│   │   ├── jwt.go                  # JWT generation/validation
│   │   └── jwt_test.go
│   ├── crypto/
│   │   ├── encryption.go           # XChaCha20 encryption
│   │   └── encryption_test.go
│   ├── db/
│   │   ├── postgres.go             # Database connection
│   │   └── interface.go            # DB interface
│   ├── models/
│   │   ├── user.go                 # User model
│   │   ├── memory.go               # Memory item model
│   │   └── rehydration.go          # Rehydration models
│   ├── config/
│   │   └── config.go               # Configuration management
│   └── errors/
│       └── errors.go               # Custom error types
├── internal/
│   ├── api/
│   │   ├── server.go               # HTTP server setup
│   │   ├── handlers/
│   │   │   ├── auth.go             # Auth endpoints
│   │   │   ├── memory.go           # Memory endpoints
│   │   │   └── rehydration.go      # Rehydration endpoint
│   │   └── middleware/
│   │       ├── auth.go             # Auth middleware
│   │       └── logging.go          # Logging middleware
│   ├── memory/
│   │   ├── service.go              # Memory CRUD logic
│   │   └── service_test.go
│   └── rehydration/
│       ├── engine.go               # Rehydration logic
│       └── engine_test.go
├── services/
│   └── crs-engine/                 # Python CRS service
│       ├── src/
│       │   ├── crs/
│       │   │   ├── calculator.py   # CRS computation
│       │   │   └── __init__.py
│       │   ├── embeddings/
│       │   │   ├── generator.py    # Embedding generation
│       │   │   └── __init__.py
│       │   └── api/
│       │       └── server.py       # gRPC server
│       ├── tests/
│       │   ├── test_calculator.py
│       │   └── test_embeddings.py
│       ├── proto/
│       │   └── crs.proto           # gRPC protocol
│       ├── requirements.txt
│       └── Dockerfile
├── migrations/
│   ├── 001_init_schema.sql
│   └── 002_indexes.sql
├── tests/
│   ├── integration/
│   │   └── api_test.go
│   └── e2e/
│       └── full_flow_test.sh
├── scripts/
│   ├── setup-dev.sh
│   └── run-tests.sh
├── docker-compose.yml
├── Makefile
├── go.mod
└── README.md
```

---

## 🚀 PHASE 1: FOUNDATION (Week 1-2)

### Step 1.1: Initialize Go Module

```bash
# Create project directory
mkdir -p acms
cd acms

# Initialize Go module
go mod init github.com/your-org/acms

# Add dependencies
go get github.com/go-chi/chi/v5
go get github.com/go-chi/cors
go get github.com/golang-jwt/jwt/v5
go get github.com/jackc/pgx/v5
go get github.com/redis/go-redis/v9
go get go.uber.org/zap
go get github.com/spf13/viper
```

### Step 1.2: Configuration Management

**File: `pkg/config/config.go`**

```go
package config

import (
	"fmt"
	"github.com/spf13/viper"
)

type Config struct {
	Server   ServerConfig
	Database DatabaseConfig
	Redis    RedisConfig
	Ollama   OllamaConfig
	JWT      JWTConfig
	CRS      CRSConfig
}

type ServerConfig struct {
	Address      string
	ReadTimeout  int
	WriteTimeout int
}

type DatabaseConfig struct {
	Host     string
	Port     int
	Name     string
	User     string
	Password string
	SSLMode  string
}

type RedisConfig struct {
	Host string
	Port int
	DB   int
}

type OllamaConfig struct {
	Host string
}

type JWTConfig struct {
	Secret string
	Expiry string
}

type CRSConfig struct {
	GRPCAddress string
}

func Load() (*Config, error) {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")
	viper.AddConfigPath("./config")
	
	// Environment variables override
	viper.AutomaticEnv()
	
	// Set defaults
	viper.SetDefault("server.address", ":8080")
	viper.SetDefault("database.port", 5432)
	viper.SetDefault("redis.port", 6379)
	
	if err := viper.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}
	
	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unmarshal config: %w", err)
	}
	
	return &cfg, nil
}
```

**File: `config.yaml`**

```yaml
server:
  address: ":8080"
  read_timeout: 10
  write_timeout: 10

database:
  host: localhost
  port: 5432
  name: acms
  user: acms
  password: changeme
  ssl_mode: disable

redis:
  host: localhost
  port: 6379
  db: 0

ollama:
  host: http://localhost:11434

jwt:
  secret: your-secret-key-change-in-production
  expiry: 24h

crs:
  grpc_address: localhost:50051
```

### Step 1.3: Data Models

**File: `pkg/models/user.go`**

```go
package models

import (
	"time"
	"github.com/google/uuid"
)

type User struct {
	ID           uuid.UUID `json:"id" db:"id"`
	Email        string    `json:"email" db:"email"`
	PasswordHash string    `json:"-" db:"password_hash"`
	CreatedAt    time.Time `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time `json:"updated_at" db:"updated_at"`
}

type RegisterRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required,min=8"`
}

type LoginRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required"`
}

type AuthResponse struct {
	Token     string    `json:"token"`
	ExpiresAt time.Time `json:"expires_at"`
	User      User      `json:"user"`
}
```

**File: `pkg/models/memory.go`**

```go
package models

import (
	"time"
	"github.com/google/uuid"
)

type MemoryItem struct {
	ID          uuid.UUID `json:"id" db:"id"`
	UserID      uuid.UUID `json:"user_id" db:"user_id"`
	Content     string    `json:"content" db:"content"`
	Embedding   []float32 `json:"-" db:"embedding"`
	CRS         float64   `json:"crs" db:"crs"`
	Tier        Tier      `json:"tier" db:"tier"`
	CreatedAt   time.Time `json:"created_at" db:"created_at"`
	LastUsedAt  time.Time `json:"last_used_at" db:"last_used_at"`
	UsageCount  int       `json:"usage_count" db:"usage_count"`
	Pinned      bool      `json:"pinned" db:"pinned"`
}

type Tier string

const (
	TierShortTerm Tier = "short_term"
	TierMidTerm   Tier = "mid_term"
	TierLongTerm  Tier = "long_term"
)

type CreateMemoryRequest struct {
	Content string `json:"content" validate:"required,min=1,max=10000"`
	Pinned  bool   `json:"pinned"`
}

type UpdateMemoryRequest struct {
	Content *string `json:"content,omitempty"`
	Pinned  *bool   `json:"pinned,omitempty"`
}
```

**File: `pkg/models/rehydration.go`**

```go
package models

import (
	"time"
	"github.com/google/uuid"
)

type RehydrationRequest struct {
	Query     string  `json:"query" validate:"required,min=1"`
	MaxTokens int     `json:"max_tokens" validate:"min=100,max=4000"`
	MinCRS    float64 `json:"min_crs" validate:"min=0,max=1"`
}

type RehydrationResponse struct {
	ContextBundle string        `json:"context_bundle"`
	ItemsUsed     []uuid.UUID   `json:"items_used"`
	TokenCount    int           `json:"token_count"`
	LatencyMs     int64         `json:"latency_ms"`
}
```

### Step 1.4: Database Setup

**File: `migrations/001_init_schema.sql`**

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Memory items table
CREATE TABLE memory_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768),
    crs FLOAT DEFAULT 0.5 CHECK (crs >= 0 AND crs <= 1),
    tier VARCHAR(20) DEFAULT 'short_term' 
        CHECK (tier IN ('short_term', 'mid_term', 'long_term')),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW(),
    usage_count INT DEFAULT 0,
    pinned BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX idx_memory_user_id ON memory_items(user_id);
CREATE INDEX idx_memory_embedding ON memory_items 
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_memory_crs ON memory_items(crs DESC);
CREATE INDEX idx_memory_tier ON memory_items(tier);
CREATE INDEX idx_memory_last_used ON memory_items(last_used_at DESC);

-- Query logs
CREATE TABLE query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_text_hash VARCHAR(64) NOT NULL,
    memory_items_used UUID[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);

-- Outcomes
CREATE TABLE outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    success_score FLOAT CHECK (success_score >= 0 AND success_score <= 1),
    feedback_rating INT CHECK (feedback_rating >= -1 AND feedback_rating <= 1),
    recorded_at TIMESTAMP DEFAULT NOW()
);
```

**File: `pkg/db/postgres.go`**

```go
package db

import (
	"context"
	"fmt"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/your-org/acms/pkg/config"
)

func NewPostgresPool(cfg config.DatabaseConfig) (*pgxpool.Pool, error) {
	connStr := fmt.Sprintf(
		"host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
		cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.Name, cfg.SSLMode,
	)
	
	poolConfig, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}
	
	poolConfig.MaxConns = 25
	poolConfig.MinConns = 5
	
	pool, err := pgxpool.NewWithConfig(context.Background(), poolConfig)
	if err != nil {
		return nil, fmt.Errorf("create pool: %w", err)
	}
	
	// Test connection
	if err := pool.Ping(context.Background()); err != nil {
		return nil, fmt.Errorf("ping: %w", err)
	}
	
	return pool, nil
}
```

### Step 1.5: JWT Authentication

**File: `pkg/auth/jwt.go`**

```go
package auth

import (
	"fmt"
	"time"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type Claims struct {
	UserID uuid.UUID `json:"user_id"`
	Email  string    `json:"email"`
	jwt.RegisteredClaims
}

type JWTManager struct {
	secret []byte
	expiry time.Duration
}

func NewJWTManager(secret string, expiry time.Duration) *JWTManager {
	return &JWTManager{
		secret: []byte(secret),
		expiry: expiry,
	}
}

func (m *JWTManager) Generate(userID uuid.UUID, email string) (string, time.Time, error) {
	expiresAt := time.Now().Add(m.expiry)
	
	claims := &Claims{
		UserID: userID,
		Email:  email,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expiresAt),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
	}
	
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString(m.secret)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("sign token: %w", err)
	}
	
	return tokenString, expiresAt, nil
}

func (m *JWTManager) Validate(tokenString string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return m.secret, nil
	})
	
	if err != nil {
		return nil, fmt.Errorf("parse token: %w", err)
	}
	
	if claims, ok := token.Claims.(*Claims); ok && token.Valid {
		return claims, nil
	}
	
	return nil, fmt.Errorf("invalid token")
}
```

**File: `pkg/auth/jwt_test.go`**

```go
package auth

import (
	"testing"
	"time"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestJWTManager_Generate(t *testing.T) {
	manager := NewJWTManager("test-secret", 24*time.Hour)
	userID := uuid.New()
	email := "test@example.com"
	
	token, expiresAt, err := manager.Generate(userID, email)
	
	require.NoError(t, err)
	assert.NotEmpty(t, token)
	assert.True(t, expiresAt.After(time.Now()))
}

func TestJWTManager_Validate_Success(t *testing.T) {
	manager := NewJWTManager("test-secret", 24*time.Hour)
	userID := uuid.New()
	email := "test@example.com"
	
	token, _, err := manager.Generate(userID, email)
	require.NoError(t, err)
	
	claims, err := manager.Validate(token)
	
	require.NoError(t, err)
	assert.Equal(t, userID, claims.UserID)
	assert.Equal(t, email, claims.Email)
}

func TestJWTManager_Validate_InvalidToken(t *testing.T) {
	manager := NewJWTManager("test-secret", 24*time.Hour)
	
	_, err := manager.Validate("invalid-token")
	
	assert.Error(t, err)
}

func TestJWTManager_Validate_ExpiredToken(t *testing.T) {
	manager := NewJWTManager("test-secret", 1*time.Millisecond)
	userID := uuid.New()
	
	token, _, err := manager.Generate(userID, "test@example.com")
	require.NoError(t, err)
	
	time.Sleep(10 * time.Millisecond)
	
	_, err = manager.Validate(token)
	assert.Error(t, err)
}
```

---

## 🧠 PHASE 2: MEMORY SERVICE (Week 2-3)

### Step 2.1: Memory Service Implementation

**File: `internal/memory/service.go`**

```go
package memory

import (
	"context"
	"fmt"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/your-org/acms/pkg/models"
	"time"
)

type Service struct {
	db *pgxpool.Pool
}

func NewService(db *pgxpool.Pool) *Service {
	return &Service{db: db}
}

func (s *Service) Create(ctx context.Context, userID uuid.UUID, req *models.CreateMemoryRequest) (*models.MemoryItem, error) {
	// TODO: Generate embedding via CRS service
	// For now, use placeholder
	embedding := make([]float32, 768)
	
	item := &models.MemoryItem{
		ID:         uuid.New(),
		UserID:     userID,
		Content:    req.Content,
		Embedding:  embedding,
		CRS:        0.5,
		Tier:       models.TierShortTerm,
		CreatedAt:  time.Now(),
		LastUsedAt: time.Now(),
		UsageCount: 0,
		Pinned:     req.Pinned,
	}
	
	query := `
		INSERT INTO memory_items 
		(id, user_id, content, embedding, crs, tier, created_at, last_used_at, usage_count, pinned)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`
	
	_, err := s.db.Exec(ctx, query,
		item.ID, item.UserID, item.Content, item.Embedding,
		item.CRS, item.Tier, item.CreatedAt, item.LastUsedAt,
		item.UsageCount, item.Pinned,
	)
	
	if err != nil {
		return nil, fmt.Errorf("insert memory item: %w", err)
	}
	
	return item, nil
}

func (s *Service) Get(ctx context.Context, userID, itemID uuid.UUID) (*models.MemoryItem, error) {
	query := `
		SELECT id, user_id, content, embedding, crs, tier, 
		       created_at, last_used_at, usage_count, pinned
		FROM memory_items
		WHERE id = $1 AND user_id = $2
	`
	
	var item models.MemoryItem
	err := s.db.QueryRow(ctx, query, itemID, userID).Scan(
		&item.ID, &item.UserID, &item.Content, &item.Embedding,
		&item.CRS, &item.Tier, &item.CreatedAt, &item.LastUsedAt,
		&item.UsageCount, &item.Pinned,
	)
	
	if err != nil {
		return nil, fmt.Errorf("query memory item: %w", err)
	}
	
	return &item, nil
}

func (s *Service) List(ctx context.Context, userID uuid.UUID, limit, offset int) ([]*models.MemoryItem, error) {
	query := `
		SELECT id, user_id, content, crs, tier, 
		       created_at, last_used_at, usage_count, pinned
		FROM memory_items
		WHERE user_id = $1
		ORDER BY last_used_at DESC
		LIMIT $2 OFFSET $3
	`
	
	rows, err := s.db.Query(ctx, query, userID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("query memory items: %w", err)
	}
	defer rows.Close()
	
	var items []*models.MemoryItem
	for rows.Next() {
		var item models.MemoryItem
		if err := rows.Scan(
			&item.ID, &item.UserID, &item.Content, &item.CRS,
			&item.Tier, &item.CreatedAt, &item.LastUsedAt,
			&item.UsageCount, &item.Pinned,
		); err != nil {
			return nil, fmt.Errorf("scan row: %w", err)
		}
		items = append(items, &item)
	}
	
	return items, nil
}

func (s *Service) Update(ctx context.Context, userID, itemID uuid.UUID, req *models.UpdateMemoryRequest) error {
	// Build dynamic update query
	updates := []string{}
	args := []interface{}{itemID, userID}
	argPos := 3
	
	if req.Content != nil {
		updates = append(updates, fmt.Sprintf("content = $%d", argPos))
		args = append(args, *req.Content)
		argPos++
	}
	
	if req.Pinned != nil {
		updates = append(updates, fmt.Sprintf("pinned = $%d", argPos))
		args = append(args, *req.Pinned)
		argPos++
	}
	
	if len(updates) == 0 {
		return nil // Nothing to update
	}
	
	query := fmt.Sprintf(`
		UPDATE memory_items 
		SET %s, updated_at = NOW()
		WHERE id = $1 AND user_id = $2
	`, updates[0]) // Simplified for single update
	
	_, err := s.db.Exec(ctx, query, args...)
	if err != nil {
		return fmt.Errorf("update memory item: %w", err)
	}
	
	return nil
}

func (s *Service) Delete(ctx context.Context, userID, itemID uuid.UUID) error {
	query := `DELETE FROM memory_items WHERE id = $1 AND user_id = $2`
	
	result, err := s.db.Exec(ctx, query, itemID, userID)
	if err != nil {
		return fmt.Errorf("delete memory item: %w", err)
	}
	
	if result.RowsAffected() == 0 {
		return fmt.Errorf("memory item not found")
	}
	
	return nil
}

func (s *Service) IncrementUsage(ctx context.Context, itemID uuid.UUID) error {
	query := `
		UPDATE memory_items 
		SET usage_count = usage_count + 1, 
		    last_used_at = NOW()
		WHERE id = $1
	`
	
	_, err := s.db.Exec(ctx, query, itemID)
	return err
}
```

### Step 2.2: Memory Service Tests

**File: `internal/memory/service_test.go`**

```go
package memory

import (
	"context"
	"testing"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/your-org/acms/pkg/models"
	// Add test database setup helper
)

func TestService_Create(t *testing.T) {
	// TODO: Setup test database
	db := setupTestDB(t)
	defer teardownTestDB(t, db)
	
	service := NewService(db)
	userID := uuid.New()
	
	req := &models.CreateMemoryRequest{
		Content: "Test memory content",
		Pinned:  false,
	}
	
	item, err := service.Create(context.Background(), userID, req)
	
	require.NoError(t, err)
	assert.NotEqual(t, uuid.Nil, item.ID)
	assert.Equal(t, userID, item.UserID)
	assert.Equal(t, req.Content, item.Content)
	assert.Equal(t, 0.5, item.CRS)
	assert.Equal(t, models.TierShortTerm, item.Tier)
}

func TestService_Get_Success(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(t, db)
	
	service := NewService(db)
	userID := uuid.New()
	
	// Create item first
	created, err := service.Create(context.Background(), userID, &models.CreateMemoryRequest{
		Content: "Test content",
	})
	require.NoError(t, err)
	
	// Get item
	item, err := service.Get(context.Background(), userID, created.ID)
	
	require.NoError(t, err)
	assert.Equal(t, created.ID, item.ID)
	assert.Equal(t, created.Content, item.Content)
}

func TestService_Get_NotFound(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(t, db)
	
	service := NewService(db)
	
	_, err := service.Get(context.Background(), uuid.New(), uuid.New())
	
	assert.Error(t, err)
}

func TestService_Delete(t *testing.T) {
	db := setupTestDB(t)
	defer teardownTestDB(t, db)
	
	service := NewService(db)
	userID := uuid.New()
	
	created, err := service.Create(context.Background(), userID, &models.CreateMemoryRequest{
		Content: "Test content",
	})
	require.NoError(t, err)
	
	err = service.Delete(context.Background(), userID, created.ID)
	require.NoError(t, err)
	
	// Verify deleted
	_, err = service.Get(context.Background(), userID, created.ID)
	assert.Error(t, err)
}
```

---

## 🐍 PHASE 3: CRS ENGINE (Week 3)

### Step 3.1: CRS Calculator

**File: `services/crs-engine/src/crs/calculator.py`**

```python
"""Context Retention Score (CRS) Calculator."""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class CRSCalculator:
    """Computes Context Retention Score for memory items."""
    
    def __init__(self):
        self.weights = {
            'semantic_relevance': 0.30,
            'recency': 0.25,
            'frequency': 0.20,
            'outcome': 0.15,
            'user_pin': 0.10
        }
    
    def calculate(
        self, 
        item: Dict, 
        query_embedding: Optional[np.ndarray] = None
    ) -> float:
        """
        Calculate CRS for a memory item.
        
        Args:
            item: Memory item with fields:
                - embedding: List[float] (768-dim)
                - last_used_at: datetime
                - usage_count: int
                - outcomes: List[Dict] (optional)
                - pinned: bool
            query_embedding: Optional query vector for semantic scoring
        
        Returns:
            CRS value between 0.0 and 1.0
        """
        scores = {}
        
        # 1. Semantic relevance
        if query_embedding is not None and item.get('embedding'):
            item_embedding = np.array(item['embedding'], dtype=np.float32)
            similarity = self._cosine_similarity(query_embedding, item_embedding)
            scores['semantic_relevance'] = similarity
        else:
            scores['semantic_relevance'] = 0.5
        
        # 2. Recency (exponential decay with 30-day half-life)
        last_used = item.get('last_used_at', datetime.utcnow())
        if isinstance(last_used, str):
            last_used = datetime.fromisoformat(last_used)
        age_days = (datetime.utcnow() - last_used).days
        scores['recency'] = float(np.exp(-age_days / 30.0))
        
        # 3. Frequency (logarithmic scale)
        usage_count = item.get('usage_count', 0)
        scores['frequency'] = min(1.0, float(np.log1p(usage_count) / np.log1p(100)))
        
        # 4. Outcome success rate
        outcomes = item.get('outcomes', [])
        if outcomes:
            success_rate = sum(o.get('success_score', 0.5) for o in outcomes) / len(outcomes)
            scores['outcome'] = success_rate
        else:
            scores['outcome'] = 0.5
        
        # 5. User pin (explicit importance)
        scores['user_pin'] = 1.0 if item.get('pinned', False) else 0.0
        
        # Weighted sum
        crs = sum(scores[k] * self.weights[k] for k in scores)
        
        return float(np.clip(crs, 0.0, 1.0))
    
    def calculate_batch(
        self,
        items: List[Dict],
        query_embedding: Optional[np.ndarray] = None
    ) -> List[float]:
        """Calculate CRS for multiple items efficiently."""
        return [self.calculate(item, query_embedding) for item in items]
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
```

### Step 3.2: Embedding Generator

**File: `services/crs-engine/src/embeddings/generator.py`**

```python
"""Embedding generation using Ollama."""
import aiohttp
import numpy as np
from typing import List

class EmbeddingGenerator:
    """Generates embeddings using Ollama."""
    
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.model = "nomic-embed-text"
    
    async def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector (768-dim)
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.ollama_host}/api/embeddings",
                json={"model": self.model, "prompt": text}
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama error: {response.status}")
                
                data = await response.json()
                embedding = np.array(data["embedding"], dtype=np.float32)
                
                return embedding
    
    async def generate_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        # TODO: Optimize with batch API if available
        embeddings = []
        for text in texts:
            emb = await self.generate(text)
            embeddings.append(emb)
        return embeddings
```

### Step 3.3: gRPC Server

**File: `services/crs-engine/proto/crs.proto`**

```protobuf
syntax = "proto3";

package crs;

service CRSService {
  rpc CalculateCRS(CRSRequest) returns (CRSResponse);
  rpc GenerateEmbedding(EmbeddingRequest) returns (EmbeddingResponse);
}

message CRSRequest {
  repeated float embedding = 1;
  string last_used_at = 2;
  int32 usage_count = 3;
  repeated Outcome outcomes = 4;
  bool pinned = 5;
  repeated float query_embedding = 6;  // optional
}

message Outcome {
  float success_score = 1;
}

message CRSResponse {
  float crs = 1;
}

message EmbeddingRequest {
  string text = 1;
}

message EmbeddingResponse {
  repeated float embedding = 1;
}
```

**File: `services/crs-engine/src/api/server.py`**

```python
"""gRPC server for CRS engine."""
import asyncio
import grpc
from concurrent import futures
from ..crs.calculator import CRSCalculator
from ..embeddings.generator import EmbeddingGenerator
# Import generated protobuf code
# from proto import crs_pb2, crs_pb2_grpc

class CRSService:
    """CRS gRPC service implementation."""
    
    def __init__(self):
        self.calculator = CRSCalculator()
        self.embedder = EmbeddingGenerator()
    
    async def CalculateCRS(self, request, context):
        """Calculate CRS for a single item."""
        item = {
            'embedding': list(request.embedding),
            'last_used_at': request.last_used_at,
            'usage_count': request.usage_count,
            'outcomes': [{'success_score': o.success_score} for o in request.outcomes],
            'pinned': request.pinned
        }
        
        query_emb = None
        if request.query_embedding:
            query_emb = np.array(list(request.query_embedding))
        
        crs = self.calculator.calculate(item, query_emb)
        
        # return crs_pb2.CRSResponse(crs=crs)
        return {"crs": crs}  # Placeholder
    
    async def GenerateEmbedding(self, request, context):
        """Generate embedding for text."""
        embedding = await self.embedder.generate(request.text)
        
        # return crs_pb2.EmbeddingResponse(embedding=embedding.tolist())
        return {"embedding": embedding.tolist()}  # Placeholder

async def serve():
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    # crs_pb2_grpc.add_CRSServiceServicer_to_server(CRSService(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    print("CRS Engine listening on :50051")
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
```

### Step 3.4: Python Tests

**File: `services/crs-engine/tests/test_calculator.py`**

```python
"""Tests for CRS calculator."""
import pytest
import numpy as np
from datetime import datetime, timedelta
from src.crs.calculator import CRSCalculator

def test_calculate_crs_high_recency():
    """Recently used item should score high."""
    calculator = CRSCalculator()
    item = {
        'embedding': np.random.rand(768).tolist(),
        'last_used_at': datetime.utcnow(),
        'usage_count': 5,
        'outcomes': [],
        'pinned': False
    }
    
    crs = calculator.calculate(item)
    
    assert 0.0 <= crs <= 1.0
    assert crs > 0.4  # Should be relatively high

def test_calculate_crs_old_item():
    """Old item should score lower."""
    calculator = CRSCalculator()
    item = {
        'embedding': np.random.rand(768).tolist(),
        'last_used_at': datetime.utcnow() - timedelta(days=90),
        'usage_count': 1,
        'outcomes': [],
        'pinned': False
    }
    
    crs = calculator.calculate(item)
    
    assert 0.0 <= crs <= 1.0
    assert crs < 0.4  # Should be lower

def test_calculate_crs_pinned_item():
    """Pinned item should always score high."""
    calculator = CRSCalculator()
    item = {
        'embedding': np.random.rand(768).tolist(),
        'last_used_at': datetime.utcnow() - timedelta(days=365),
        'usage_count': 0,
        'outcomes': [],
        'pinned': True
    }
    
    crs = calculator.calculate(item)
    
    assert crs > 0.5  # Pin weight should boost score

def test_cosine_similarity():
    """Test cosine similarity calculation."""
    calculator = CRSCalculator()
    
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    
    sim = calculator._cosine_similarity(a, b)
    
    assert sim == pytest.approx(1.0)

def test_calculate_batch():
    """Test batch CRS calculation."""
    calculator = CRSCalculator()
    items = [
        {
            'embedding': np.random.rand(768).tolist(),
            'last_used_at': datetime.utcnow(),
            'usage_count': i,
            'outcomes': [],
            'pinned': False
        }
        for i in range(10)
    ]
    
    scores = calculator.calculate_batch(items)
    
    assert len(scores) == 10
    assert all(0.0 <= s <= 1.0 for s in scores)
```

---

## 🔄 PHASE 4: REHYDRATION ENGINE (Week 4)

**File: `internal/rehydration/engine.go`**

```go
package rehydration

import (
	"context"
	"fmt"
	"sort"
	"time"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/your-org/acms/pkg/models"
)

type Engine struct {
	db *pgxpool.Pool
	// TODO: Add CRS client
}

func NewEngine(db *pgxpool.Pool) *Engine {
	return &Engine{db: db}
}

type candidate struct {
	item       *models.MemoryItem
	similarity float64
	score      float64  // similarity * CRS
}

func (e *Engine) Rehydrate(ctx context.Context, userID uuid.UUID, req *models.RehydrationRequest) (*models.RehydrationResponse, error) {
	start := time.Now()
	
	// TODO: Step 1: Generate query embedding via CRS service
	// queryEmbedding := await crsClient.GenerateEmbedding(req.Query)
	
	// Step 2: Vector similarity search (top 50)
	candidates, err := e.vectorSearch(ctx, userID, nil, 50)  // TODO: Pass real embedding
	if err != nil {
		return nil, fmt.Errorf("vector search: %w", err)
	}
	
	// Step 3: Filter by CRS threshold
	filtered := e.filterByCRS(candidates, req.MinCRS)
	
	// Step 4: Rank by composite score (similarity * CRS)
	ranked := e.rankByScore(filtered)
	
	// Step 5: Build token-bounded bundle
	bundle, itemsUsed := e.buildBundle(ranked, req.MaxTokens)
	
	// Step 6: Update usage stats asynchronously
	go e.updateUsageStats(context.Background(), itemsUsed)
	
	latency := time.Since(start).Milliseconds()
	
	return &models.RehydrationResponse{
		ContextBundle: bundle,
		ItemsUsed:     itemsUsed,
		TokenCount:    e.countTokens(bundle),
		LatencyMs:     latency,
	}, nil
}

func (e *Engine) vectorSearch(ctx context.Context, userID uuid.UUID, embedding []float32, limit int) ([]*candidate, error) {
	// TODO: Use actual vector search with embedding
	// For now, return recent items
	query := `
		SELECT id, user_id, content, crs, tier, 
		       created_at, last_used_at, usage_count, pinned
		FROM memory_items
		WHERE user_id = $1
		ORDER BY last_used_at DESC
		LIMIT $2
	`
	
	rows, err := e.db.Query(ctx, query, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()
	
	var candidates []*candidate
	for rows.Next() {
		var item models.MemoryItem
		if err := rows.Scan(
			&item.ID, &item.UserID, &item.Content, &item.CRS,
			&item.Tier, &item.CreatedAt, &item.LastUsedAt,
			&item.UsageCount, &item.Pinned,
		); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		
		candidates = append(candidates, &candidate{
			item:       &item,
			similarity: 0.8,  // TODO: Calculate real similarity
			score:      0.8 * item.CRS,
		})
	}
	
	return candidates, nil
}

func (e *Engine) filterByCRS(candidates []*candidate, minCRS float64) []*candidate {
	var filtered []*candidate
	for _, c := range candidates {
		if c.item.CRS >= minCRS {
			filtered = append(filtered, c)
		}
	}
	return filtered
}

func (e *Engine) rankByScore(candidates []*candidate) []*candidate {
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].score > candidates[j].score
	})
	return candidates
}

func (e *Engine) buildBundle(candidates []*candidate, maxTokens int) (string, []uuid.UUID) {
	var bundle string
	var itemsUsed []uuid.UUID
	tokenCount := 0
	
	for _, c := range candidates {
		// Estimate tokens (rough: 1 token ≈ 4 chars)
		itemTokens := len(c.item.Content) / 4
		
		if tokenCount+itemTokens > maxTokens {
			break
		}
		
		bundle += c.item.Content + "\n\n"
		itemsUsed = append(itemsUsed, c.item.ID)
		tokenCount += itemTokens
	}
	
	return bundle, itemsUsed
}

func (e *Engine) countTokens(text string) int {
	// Rough estimate: 1 token ≈ 4 characters
	return len(text) / 4
}

func (e *Engine) updateUsageStats(ctx context.Context, itemIDs []uuid.UUID) {
	for _, id := range itemIDs {
		query := `
			UPDATE memory_items 
			SET usage_count = usage_count + 1,
			    last_used_at = NOW()
			WHERE id = $1
		`
		_ = e.db.Exec(ctx, query, id)
	}
}
```

---

## 🌐 PHASE 5: API GATEWAY (Week 5)

### Step 5.1: HTTP Server Setup

**File: `internal/api/server.go`**

```go
package api

import (
	"context"
	"fmt"
	"net/http"
	"time"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"go.uber.org/zap"
	"github.com/your-org/acms/internal/api/handlers"
	apimiddleware "github.com/your-org/acms/internal/api/middleware"
	"github.com/your-org/acms/pkg/config"
)

type Server struct {
	router *chi.Mux
	server *http.Server
	logger *zap.Logger
}

func NewServer(cfg *config.Config, logger *zap.Logger) *Server {
	r := chi.NewRouter()
	
	// Middleware
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))
	
	// CORS
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type"},
		AllowCredentials: true,
	}))
	
	// TODO: Initialize handlers with dependencies
	// authHandler := handlers.NewAuthHandler(...)
	// memoryHandler := handlers.NewMemoryHandler(...)
	
	// Routes
	r.Route("/api/v1", func(r chi.Router) {
		// Public routes
		r.Post("/auth/register", nil)  // TODO: authHandler.Register
		r.Post("/auth/login", nil)     // TODO: authHandler.Login
		
		// Protected routes
		r.Group(func(r chi.Router) {
			// r.Use(apimiddleware.Auth(jwtManager))
			
			r.Post("/memory/items", nil)          // TODO: memoryHandler.Create
			r.Get("/memory/items", nil)           // TODO: memoryHandler.List
			r.Get("/memory/items/{id}", nil)      // TODO: memoryHandler.Get
			r.Put("/memory/items/{id}", nil)      // TODO: memoryHandler.Update
			r.Delete("/memory/items/{id}", nil)   // TODO: memoryHandler.Delete
			
			r.Post("/rehydrate", nil)             // TODO: rehydrationHandler.Rehydrate
		})
		
		// Admin routes
		r.Get("/admin/health", handlers.HealthCheck)
	})
	
	server := &http.Server{
		Addr:         cfg.Server.Address,
		Handler:      r,
		ReadTimeout:  time.Duration(cfg.Server.ReadTimeout) * time.Second,
		WriteTimeout: time.Duration(cfg.Server.WriteTimeout) * time.Second,
	}
	
	return &Server{
		router: r,
		server: server,
		logger: logger,
	}
}

func (s *Server) Start() error {
	s.logger.Info("Starting HTTP server", zap.String("addr", s.server.Addr))
	return s.server.ListenAndServe()
}

func (s *Server) Shutdown(ctx context.Context) error {
	return s.server.Shutdown(ctx)
}
```

**File: `internal/api/handlers/health.go`**

```go
package handlers

import (
	"encoding/json"
	"net/http"
)

type HealthResponse struct {
	Status string `json:"status"`
}

func HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteStatus(http.StatusOK)
	json.NewEncoder(w).Encode(HealthResponse{Status: "ok"})
}
```

---

## 🐳 PHASE 6: DEPLOYMENT (Week 6)

### Docker Compose

**File: `docker-compose.yml`**

```yaml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: acms
      POSTGRES_USER: acms
      POSTGRES_PASSWORD: changeme
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U acms"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    command: serve

  crs-engine:
    build: ./services/crs-engine
    ports:
      - "50051:50051"
    depends_on:
      - ollama
    environment:
      - OLLAMA_HOST=http://ollama:11434

  api-gateway:
    build: .
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis
      - crs-engine
    environment:
      - DATABASE_HOST=postgres
      - REDIS_HOST=redis
      - CRS_GRPC_ADDRESS=crs-engine:50051

volumes:
  postgres_data:
  redis_data:
  ollama_data:
```

### Makefile

**File: `Makefile`**

```makefile
.PHONY: all build test run clean

all: build

build:
	@echo "Building API Gateway..."
	go build -o bin/api-gateway ./cmd/api-gateway

test:
	@echo "Running tests..."
	go test -v -race -cover ./...
	cd services/crs-engine && pytest tests/

run:
	@echo "Starting services..."
	docker-compose up -d
	sleep 5
	go run cmd/api-gateway/main.go

clean:
	@echo "Cleaning..."
	rm -rf bin/
	docker-compose down -v

migrate:
	@echo "Running migrations..."
	psql -h localhost -U acms -d acms -f migrations/001_init_schema.sql

setup:
	@echo "Setting up development environment..."
	./scripts/setup-dev.sh
```

---

## ✅ COMPLETION CHECKLIST

### Phase 1: Foundation
- [ ] Go module initialized
- [ ] Configuration system working
- [ ] Database schema created
- [ ] JWT authentication implemented
- [ ] Tests passing for auth

### Phase 2: Memory Service
- [ ] Memory CRUD operations
- [ ] Database queries working
- [ ] Tests passing for memory service

### Phase 3: CRS Engine
- [ ] CRS calculator implemented
- [ ] Embedding generator working
- [ ] gRPC server running
- [ ] Python tests passing

### Phase 4: Rehydration
- [ ] Vector search working
- [ ] CRS-based ranking implemented
- [ ] Token budgeting working
- [ ] Tests passing

### Phase 5: API Gateway
- [ ] HTTP server running
- [ ] All endpoints implemented
- [ ] Middleware working
- [ ] Integration tests passing

### Phase 6: Deployment
- [ ] Docker Compose working
- [ ] All services starting
- [ ] Health check passing
- [ ] E2E tests passing

---

## 🎯 SUCCESS CRITERIA

Your MVP is complete when:
- ✅ All tests pass (80%+ coverage)
- ✅ API responds < 200ms (p95)
- ✅ Rehydration works < 2s
- ✅ Can create/read/update/delete memories
- ✅ CRS scores are computed correctly
- ✅ Context is recalled relevantly
- ✅ Docker Compose brings everything up
- ✅ Documentation is complete

---

## 📞 NEXT STEPS

1. **Save this document**
2. **Run code scaffolding script** (from earlier artifact)
3. **Follow phases 1-6 sequentially**
4. **Write tests before implementation (TDD)**
5. **Ask for clarification on specific components as needed**

**You now have everything needed to build ACMS. Start with Phase 1!** 🚀
