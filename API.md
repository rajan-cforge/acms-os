openapi: 3.0.3
info:
  title: ACMS API
  description: |
    Adaptive Context Memory System REST API
    
    **Version 2.0** - Production-Ready (15-Pass Refined)
    
    ## Overview
    ACMS provides intelligent, privacy-first memory for AI assistants.
    All data is stored locally with user-owned encryption keys.
    
    ## Authentication
    All endpoints require Bearer token authentication:
    ```
    Authorization: Bearer <jwt_token>
    ```
    
    ## Rate Limiting
    - Standard: 100 requests/minute per user
    - Admin: 1000 requests/minute per user
    - Headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
    
    ## Error Handling
    All errors follow the standard format:
    ```json
    {
      "success": false,
      "error": {
        "code": "error_code",
        "message": "Human-readable message",
        "details": {}
      }
    }
    ```
    
    ## Pagination
    List endpoints support pagination via `limit` and `offset` parameters.
    
  version: 2.0.0
  contact:
    name: ACMS Engineering
    email: engineering@acms.example.com
    url: https://docs.acms.example.com
  license:
    name: Proprietary
    url: https://acms.example.com/license

servers:
  - url: https://api.acms.example.com/v1
    description: Production
  - url: https://staging-api.acms.example.com/v1
    description: Staging
  - url: http://localhost:8000/v1
    description: Local Development

tags:
  - name: Query
    description: Execute queries with memory context
  - name: Memory
    description: Manage memory items
  - name: Outcomes
    description: Submit feedback and outcomes
  - name: Export
    description: Data export and compliance
  - name: Admin
    description: Administrative operations

security:
  - BearerAuth: []

paths:
  /query:
    post:
      tags: [Query]
      summary: Execute query with memory rehydration
      description: |
        Process a user query with intelligent context retrieval.
        
        Flow:
        1. Classify query intent
        2. Retrieve relevant memory items
        3. Assemble context bundle
        4. Generate LLM response
        5. Log outcome for learning
        
        Performance: p95 < 3 seconds end-to-end
      operationId: executeQuery
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QueryRequest'
            examples:
              basic:
                summary: Basic query
                value:
                  query: "What were the key findings from our last security audit?"
                  topic_id: "work"
              advanced:
                summary: Advanced query with options
                value:
                  query: "Analyze the phishing campaign from last week"
                  topic_id: "security"
                  intent: "threat_hunt"
                  model: "llama3.1:8b"
                  max_tokens: 2000
                  token_budget: 1200
                  compliance_mode: true
                  stream: false
      responses:
        '200':
          description: Successful query execution
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryResponse'
              example:
                success: true
                data:
                  query_id: "550e8400-e29b-41d4-a716-446655440000"
                  response:
                    text: "Based on your previous security audits..."
                    model: "llama3.1:8b"
                    tokens_used: 1847
                    generation_time_ms: 1543
                  context_bundle:
                    items_used:
                      - id: "660e8400-e29b-41d4-a716-446655440001"
                        tier: "MID"
                        crs: 0.82
                        excerpt: "Security audit Q3 2024..."
                    total_items: 8
                    token_count: 923
                  metadata:
                    intent_detected: "threat_hunt"
                    rehydration_time_ms: 347
                    cache_hit: false
        '400':
          $ref: '#/components/responses/ValidationError'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimitExceeded'
        '500':
          $ref: '#/components/responses/InternalError'

  /memory/ingest:
    post:
      tags: [Memory]
      summary: Ingest new memory item
      description: |
        Store a new memory item with automatic embedding generation.
        
        The system will:
        1. Generate embedding for the text
        2. Detect PII (if present)
        3. Compute initial CRS
        4. Assign to SHORT tier
        5. Encrypt and store
        
        Performance: p95 < 100ms
      operationId: ingestMemory
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MemoryIngestRequest'
            examples:
              meeting_notes:
                summary: Meeting notes
                value:
                  text: "Team standup: Focus on ACMS security review this week"
                  topic_id: "work"
                  metadata:
                    source: "meeting_notes"
                    participants: ["alice", "bob"]
              incident:
                summary: Security incident
                value:
                  text: "Detected suspicious login from IP 10.0.0.5"
                  topic_id: "security"
                  metadata:
                    severity: "high"
                    source_system: "SIEM"
      responses:
        '201':
          description: Memory item created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MemoryIngestResponse'
              example:
                success: true
                data:
                  item_id: "770e8400-e29b-41d4-a716-446655440002"
                  tier: "SHORT"
                  crs: 0.45
                  pii_detected: false
                  created_at: "2024-10-11T10:30:00Z"
        '400':
          $ref: '#/components/responses/ValidationError'
        '401':
          $ref: '#/components/responses/Unauthorized'

  /memory/items:
    get:
      tags: [Memory]
      summary: List memory items
      description: |
        Retrieve memory items with filtering and pagination.
        
        Supports filtering by:
        - Topic ID
        - Tier (SHORT, MID, LONG)
        - Date range
        - CRS range
        - Text search
      operationId: listMemoryItems
      parameters:
        - name: topic_id
          in: query
          description: Filter by topic
          schema:
            type: string
          example: "work"
        - name: tier
          in: query
          description: Filter by tier
          schema:
            $ref: '#/components/schemas/Tier'
        - name: crs_min
          in: query
          description: Minimum CRS
          schema:
            type: number
            format: float
            minimum: 0.0
            maximum: 1.0
          example: 0.6
        - name: crs_max
          in: query
          description: Maximum CRS
          schema:
            type: number
            format: float
            minimum: 0.0
            maximum: 1.0
          example: 1.0
        - name: search
          in: query
          description: Text search query
          schema:
            type: string
          example: "security audit"
        - name: limit
          in: query
          description: Page size
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: offset
          in: query
          description: Offset for pagination
          schema:
            type: integer
            minimum: 0
            default: 0
      responses:
        '200':
          description: List of memory items
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MemoryListResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'

  /memory/items/{item_id}:
    get:
      tags: [Memory]
      summary: Get memory item by ID
      operationId: getMemoryItem
      parameters:
        - $ref: '#/components/parameters/ItemId'
      responses:
        '200':
          description: Memory item details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MemoryItemResponse'
        '404':
          $ref: '#/components/responses/NotFound'
    
    delete:
      tags: [Memory]
      summary: Delete memory item (forget)
      description: |
        Permanently delete a memory item.
        
        This operation:
        - Removes the item from storage
        - Deletes all encryption keys
        - Logs the deletion in audit trail
        - Cannot be undone
        
        Completes within 1 second.
      operationId: deleteMemoryItem
      parameters:
        - $ref: '#/components/parameters/ItemId'
      responses:
        '204':
          description: Item deleted successfully
        '404':
          $ref: '#/components/responses/NotFound'

  /memory/items/{item_id}/pin:
    put:
      tags: [Memory]
      summary: Pin or unpin memory item
      description: |
        Pin an item to prevent automatic demotion or consolidation.
        Pinned items maintain their tier regardless of CRS.
      operationId: pinMemoryItem
      parameters:
        - $ref: '#/components/parameters/ItemId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [pinned]
              properties:
                pinned:
                  type: boolean
                  description: True to pin, false to unpin
            example:
              pinned: true
      responses:
        '200':
          description: Pin status updated
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
                    properties:
                      item_id:
                        type: string
                        format: uuid
                      pinned:
                        type: boolean
                      crs_adjusted:
                        type: number
                        format: float
        '404':
          $ref: '#/components/responses/NotFound'

  /outcomes/feedback:
    post:
      tags: [Outcomes]
      summary: Submit user feedback on query response
      description: |
        Submit feedback to improve memory selection.
        
        Feedback is used to:
        - Update CRS for memory items used
        - Train intent classifier (future)
        - Tune hybrid retrieval weights
      operationId: submitFeedback
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FeedbackRequest'
            examples:
              thumbs_up:
                summary: Positive feedback
                value:
                  query_id: "550e8400-e29b-41d4-a716-446655440000"
                  feedback_type: "thumbs_up"
              rating:
                summary: Star rating with comment
                value:
                  query_id: "550e8400-e29b-41d4-a716-446655440000"
                  feedback_type: "star_rating"
                  rating: 5
                  comment: "Very helpful context!"
      responses:
        '201':
          description: Feedback recorded
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
                    properties:
                      outcome_id:
                        type: integer
                        format: int64
                      recorded_at:
                        type: string
                        format: date-time
        '400':
          $ref: '#/components/responses/ValidationError'
        '404':
          description: Query ID not found

  /memory/export:
    get:
      tags: [Export]
      summary: Export user memory (GDPR Article 20)
      description: |
        Export all memory data in machine-readable format.
        
        The export includes:
        - All memory items (text, metadata)
        - CRS scores and history
        - Tier information
        - Outcome logs
        - Audit trail
        
        Export is encrypted with user's public key.
        Link expires in 24 hours.
      operationId: exportMemory
      parameters:
        - name: topic_id
          in: query
          description: Optional: export specific topic only
          schema:
            type: string
        - name: format
          in: query
          description: Export format
          schema:
            type: string
            enum: [json, csv]
            default: json
      responses:
        '200':
          description: Export initiated
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
                    properties:
                      export_id:
                        type: string
                        format: uuid
                      status:
                        type: string
                        enum: [pending, ready, expired]
                      download_url:
                        type: string
                        format: uri
                        description: URL to download export (null if pending)
                      created_at:
                        type: string
                        format: date-time
                      expires_at:
                        type: string
                        format: date-time
              example:
                success: true
                data:
                  export_id: "880e8400-e29b-41d4-a716-446655440003"
                  status: "ready"
                  download_url: "https://exports.acms.example.com/880e8400.json.enc"
                  created_at: "2024-10-11T10:40:00Z"
                  expires_at: "2024-10-12T10:40:00Z"

  /memory:
    delete:
      tags: [Export]
      summary: Delete all user data (GDPR Right to Erasure)
      description: |
        Permanently delete all memory data for a user.
        
        This operation:
        - Deletes all memory items
        - Removes all encryption keys
        - Deletes audit logs (after retention period)
        - Cannot be undone
        
        Completion: < 24 hours
      operationId: deleteAllMemory
      parameters:
        - name: topic_id
          in: query
          description: Optional: delete specific topic only
          schema:
            type: string
      responses:
        '202':
          description: Deletion initiated
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
                    properties:
                      deletion_id:
                        type: string
                        format: uuid
                      status:
                        type: string
                        enum: [pending, in_progress, completed]
                      estimated_completion:
                        type: string
                        format: date-time
              example:
                success: true
                data:
                  deletion_id: "990e8400-e29b-41d4-a716-446655440004"
                  status: "pending"
                  estimated_completion: "2024-10-11T11:00:00Z"

  /admin/users/{user_id}/stats:
    get:
      tags: [Admin]
      summary: Get user statistics
      description: Admin-only endpoint for user analytics
      security:
        - BearerAuth: []
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: User statistics
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserStatsResponse'
        '403':
          description: Forbidden (requires admin role)

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT token obtained from authentication endpoint.
        
        Token payload includes:
        - sub: user_id (UUID)
        - email: user email
        - roles: array of roles
        - topics: accessible topic IDs
        - exp: expiration timestamp

  parameters:
    ItemId:
      name: item_id
      in: path
      required: true
      description: Memory item UUID
      schema:
        type: string
        format: uuid

  schemas:
    # Request Schemas
    
    QueryRequest:
      type: object
      required: [query, topic_id]
      properties:
        query:
          type: string
          minLength: 1
          maxLength: 10000
          description: User query text
          example: "What were the key findings from our last security audit?"
        topic_id:
          type: string
          pattern: '^[a-zA-Z0-9_-]+$'
          description: Topic identifier
          example: "work"
        intent:
          $ref: '#/components/schemas/Intent'
        model:
          type: string
          default: "llama3.1:8b"
          description: LLM model to use
          enum:
            - "llama3.1:8b"
            - "mistral:7b"
            - "gpt-4o-mini"
        max_tokens:
          type: integer
          minimum: 100
          maximum: 10000
          default: 2000
          description: Maximum tokens for LLM response
        token_budget:
          type: integer
          minimum: 100
          maximum: 5000
          default: 1000
          description: Token budget for context bundle
        compliance_mode:
          type: boolean
          description: Enable compliance mode (restrict cross-topic retrieval)
        stream:
          type: boolean
          default: false
          description: Enable streaming response (SSE)
    
    MemoryIngestRequest:
      type: object
      required: [text, topic_id]
      properties:
        text:
          type: string
          minLength: 1
          maxLength: 50000
          description: Memory item content
        topic_id:
          type: string
          pattern: '^[a-zA-Z0-9_-]+$'
        metadata:
          type: object
          additionalProperties: true
          description: Optional metadata
    
    FeedbackRequest:
      type: object
      required: [query_id, feedback_type]
      properties:
        query_id:
          type: string
          format: uuid
          description: Query ID from QueryResponse
        feedback_type:
          type: string
          enum: [thumbs_up, thumbs_down, star_rating, comment]
        rating:
          type: integer
          minimum: 1
          maximum: 5
          description: Star rating (required if feedback_type is star_rating)
        comment:
          type: string
          maxLength: 1000
          description: Optional comment
    
    # Response Schemas
    
    QueryResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
          properties:
            query_id:
              type: string
              format: uuid
            response:
              $ref: '#/components/schemas/LLMResponse'
            context_bundle:
              $ref: '#/components/schemas/ContextBundle'
            metadata:
              $ref: '#/components/schemas/QueryMetadata'
    
    MemoryIngestResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
          properties:
            item_id:
              type: string
              format: uuid
            tier:
              $ref: '#/components/schemas/Tier'
            crs:
              type: number
              format: float
            pii_detected:
              type: boolean
            created_at:
              type: string
              format: date-time
    
    MemoryListResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
          properties:
            items:
              type: array
              items:
                $ref: '#/components/schemas/MemoryItem'
            total:
              type: integer
              description: Total count (before pagination)
            limit:
              type: integer
            offset:
              type: integer
    
    MemoryItemResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          $ref: '#/components/schemas/MemoryItem'
    
    UserStatsResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
          properties:
            user_id:
              type: string
              format: uuid
            total_items:
              type: integer
            items_by_tier:
              type: object
              properties:
                SHORT:
                  type: integer
                MID:
                  type: integer
                LONG:
                  type: integer
            avg_crs:
              type: number
              format: float
            total_queries:
              type: integer
            avg_tokens_saved_percent:
              type: number
              format: float
            last_activity:
              type: string
              format: date-time
    
    # Domain Models
    
    LLMResponse:
      type: object
      properties:
        text:
          type: string
          description: Generated response text
        model:
          type: string
        tokens_used:
          type: integer
        generation_time_ms:
          type: integer
    
    ContextBundle:
      type: object
      properties:
        items_used:
          type: array
          items:
            $ref: '#/components/schemas/ContextItem'
        total_items:
          type: integer
        token_count:
          type: integer
    
    ContextItem:
      type: object
      properties:
        id:
          type: string
          format: uuid
        tier:
          $ref: '#/components/schemas/Tier'
        crs:
          type: number
          format: float
        excerpt:
          type: string
          description: First 100 characters
        relevance_score:
          type: number
          format: float
    
    QueryMetadata:
      type: object
      properties:
        intent_detected:
          $ref: '#/components/schemas/Intent'
        rehydration_time_ms:
          type: integer
        cache_hit:
          type: boolean
    
    MemoryItem:
      type: object
      properties:
        id:
          type: string
          format: uuid
        text:
          type: string
        topic_id:
          type: string
        tier:
          $ref: '#/components/schemas/Tier'
        crs:
          type: number
          format: float
        created_at:
          type: string
          format: date-time
        last_used_at:
          type: string
          format: date-time
        access_count:
          type: integer
        pii_flags:
          type: object
          additionalProperties:
            type: object
        outcome_success_rate:
          type: number
          format: float
        pinned:
          type: boolean
    
    # Enums
    
    Tier:
      type: string
      enum: [SHORT, MID, LONG]
      description: |
        Memory tier:
        - SHORT: Minutes-hours retention
        - MID: Days-weeks retention
        - LONG: Months-years retention
    
    Intent:
      type: string
      enum:
        - code_assist
        - research
        - meeting_prep
        - writing
        - analysis
        - threat_hunt
        - triage
        - general
      description: Query intent classification
    
    # Error Schema
    
    Error:
      type: object
      required: [success, error]
      properties:
        success:
          type: boolean
          enum: [false]
        error:
          type: object
          required: [code, message]
          properties:
            code:
              type: string
              description: Machine-readable error code
              example: "rate_limit_exceeded"
            message:
              type: string
              description: Human-readable error message
              example: "Rate limit exceeded. Try again in 42 seconds."
            details:
              type: object
              additionalProperties: true
              description: Additional error context

  responses:
    ValidationError:
      description: Request validation failed
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            success: false
            error:
              code: "validation_error"
              message: "Invalid request parameters"
              details:
                field: "query"
                issue: "Query cannot be empty"
    
    Unauthorized:
      description: Authentication failed or missing
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            success: false
            error:
              code: "authentication_failed"
              message: "Missing or invalid Authorization header"
    
    RateLimitExceeded:
      description: Rate limit exceeded
      headers:
        Retry-After:
          schema:
            type: integer
          description: Seconds until rate limit resets
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            success: false
            error:
              code: "rate_limit_exceeded"
              message: "Rate limit exceeded. Try again later."
              details:
                retry_after: 42
    
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            success: false
            error:
              code: "not_found"
              message: "Memory item not found"
    
    InternalError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            success: false
            error:
              code: "internal_error"
              message: "An internal error occurred"
