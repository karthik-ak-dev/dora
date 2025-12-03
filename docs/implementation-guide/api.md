# REST API Design

## Overview

This document defines the complete REST API for the Content Intelligence MVP. The API is built using **FastAPI** (Python) and follows RESTful conventions with JWT-based authentication.

**Base URL**: `https://api.yourapp.com/v1`

**Technology Stack**:
- **Framework**: FastAPI (Python 3.11+)
- **Auth**: JWT (JSON Web Tokens)
- **Validation**: Pydantic v2
- **Database**: PostgreSQL (via SQLAlchemy)
- **Queue**: AWS SQS (for async processing)

---

## API Catalog

| Category | Endpoint | Method | Purpose |
|----------|----------|--------|---------|
| **Authentication** | `/auth/register` | POST | Create new user account |
| | `/auth/login` | POST | Authenticate and get JWT token |
| **Content** | `/items` | POST | Save new content (URL) |
| | `/items` | GET | List user's saved content |
| | `/items/grouped` | GET | Get content grouped by category |
| | `/items/{item_id}` | GET | Get single item details |
| **Clusters** | `/clusters` | GET | List user's clusters |
| | `/clusters/{cluster_id}` | GET | Get cluster details with items |

---

## Authentication

All endpoints except `/auth/register` and `/auth/login` require authentication via JWT token.

### Header Format

```http
Authorization: Bearer <jwt_token>
```

### Token Structure

```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890
}
```

**Token Expiry**: 7 days (configurable)

---

## 1. Authentication Endpoints

### 1.1 POST /auth/register

**Purpose**: Create a new user account.

#### Request

**Headers**:
```http
Content-Type: application/json
```

**Body** (Pydantic Schema):
```python
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="User's email address")
    password: str = Field(min_length=8, description="Password (min 8 characters)")
```

**Example**:
```json
{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

#### Response

**Success - 201 Created**:
```python
class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiry
```

**Example**:
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "alice@example.com",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

**Error - 400 Bad Request** (Email already exists):
```json
{
  "detail": "Email already registered"
}
```

**Error - 422 Unprocessable Entity** (Validation failed):
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 8 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

#### Implementation Notes

- Password is hashed using bcrypt before storing
- JWT token is generated immediately after registration
- User can start using the app without email verification (for MVP)

---

### 1.2 POST /auth/login

**Purpose**: Authenticate existing user and receive JWT token.

#### Request

**Body**:
```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

**Example**:
```json
{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

#### Response

**Success - 200 OK**:
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "alice@example.com",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

**Error - 401 Unauthorized** (Invalid credentials):
```json
{
  "detail": "Invalid email or password"
}
```

#### Implementation Notes

- Use constant-time comparison for password verification
- Rate limit: Max 5 failed attempts per 15 minutes per email
- Return generic error message (don't reveal if email exists)

---

## 2. Content Endpoints

### 2.1 POST /items

**Purpose**: Save a new piece of content (Instagram reel, YouTube video, etc.)

#### Request

**Headers**:
```http
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**:
```python
class SaveContentRequest(BaseModel):
    url: str = Field(description="URL to save")
    raw_share_text: Optional[str] = Field(None, description="User's personal note")
```

**Example**:
```json
{
  "url": "https://www.instagram.com/reel/abc123xyz/",
  "raw_share_text": "Must visit this cafe this weekend!"
}
```

#### Response

**Success - 201 Created**:
```python
class SaveContentResponse(BaseModel):
    save: UserContentSaveResponse
    content: SharedContentResponse
    message: str
```

**Example (New content)**:
```json
{
  "save": {
    "id": "save-uuid-1",
    "user_id": "user-uuid",
    "shared_content_id": "content-uuid-1",
    "raw_share_text": "Must visit this cafe this weekend!",
    "created_at": "2024-01-15T14:30:00Z"
  },
  "content": {
    "id": "content-uuid-1",
    "url": "https://www.instagram.com/reel/abc123xyz/",
    "source_platform": "instagram",
    "status": "PENDING",
    "title": null,
    "thumbnail_url": null,
    "save_count": 1
  },
  "message": "Content saved successfully. Processing has been queued."
}
```

**Example (Content already processed)**:
```json
{
  "save": {
    "id": "save-uuid-2",
    "user_id": "user-uuid",
    "shared_content_id": "content-uuid-1",
    "raw_share_text": "Must visit this cafe this weekend!",
    "created_at": "2024-01-15T14:30:00Z"
  },
  "content": {
    "id": "content-uuid-1",
    "url": "https://www.instagram.com/reel/abc123xyz/",
    "source_platform": "instagram",
    "status": "READY",
    "title": "Best Cafe in Indiranagar",
    "thumbnail_url": "https://cdn.example.com/thumb.jpg",
    "category_high": "Food & Drink",
    "topic_main": "Trendy cafe in Indiranagar",
    "save_count": 2
  },
  "message": "Content already processed and ready to view!"
}
```

**Error - 400 Bad Request** (Already saved by this user):
```json
{
  "detail": "You have already saved this content",
  "existing_save_id": "save-uuid-1"
}
```

**Error - 422 Unprocessable Entity** (Invalid URL):
```json
{
  "detail": "Invalid URL format or unsupported platform"
}
```

#### Processing Flow

1. **URL Normalization**: Remove tracking params, standardize format
2. **Generate url_hash**: SHA256 of normalized URL
3. **Check SharedContent**: Does this URL already exist?
   - **Yes**: Reuse existing, create UserContentSave (instant if READY)
   - **No**: Create SharedContent, create UserContentSave, enqueue processing
4. **Check Duplicate Save**: Has this user already saved this?
   - **Yes**: Return error
   - **No**: Create UserContentSave
5. **Increment save_count**: If new save created
6. **Return Response**: Include save + content data

#### URL Support

**Supported Platforms**:
- Instagram: `instagram.com/reel/*`, `instagram.com/p/*`
- YouTube: `youtube.com/watch?v=*`, `youtu.be/*`

**Normalization Rules**:
- Convert to HTTPS
- Remove `www.` subdomain
- Remove tracking parameters (`utm_*`, `ref`, `fbclid`, etc.)
- Remove trailing slashes
- Remove URL fragments (`#section`)

---

### 2.2 GET /items

**Purpose**: List user's saved content with filtering, sorting, and pagination.

#### Request

**Headers**:
```http
Authorization: Bearer <token>
```

**Query Parameters**:
```python
class ListItemsParams(BaseModel):
    status: Optional[ItemStatus] = Field(None, description="Filter by status")
    category: Optional[CategoryHighLevel] = Field(None, description="Filter by category")
    search: Optional[str] = Field(None, description="Search in title, topic, notes")
    is_favorited: Optional[bool] = Field(None, description="Show only favorites")
    is_archived: Optional[bool] = Field(False, description="Include archived items")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", description="asc or desc")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    offset: int = Field(0, ge=0, description="Pagination offset")
```

**Example Request**:
```http
GET /items?status=READY&category=Food+%26+Drink&limit=10&offset=0
```

#### Response

**Success - 200 OK**:
```python
class ListItemsResponse(BaseModel):
    items: List[ContentItemResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
```

**Example**:
```json
{
  "items": [
    {
      "save": {
        "id": "save-uuid-1",
        "raw_share_text": "Must visit this weekend!",
        "is_favorited": false,
        "is_archived": false,
        "created_at": "2024-01-15T14:30:00Z"
      },
      "content": {
        "id": "content-uuid-1",
        "url": "https://instagram.com/reel/abc123",
        "source_platform": "instagram",
        "status": "READY",
        "title": "Best Cafe in Indiranagar",
        "caption": "Here are my top 5 favorite brunch spots...",
        "thumbnail_url": "https://cdn.example.com/thumb1.jpg",
        "duration_seconds": 45,
        "category_high": "Food & Drink",
        "topic_main": "Trendy cafe in Indiranagar",
        "subcategories": ["Cafes", "Brunch", "Bangalore"],
        "locations": ["Indiranagar", "Bangalore"],
        "intent": "visit",
        "save_count": 5
      }
    },
    {
      "save": {
        "id": "save-uuid-2",
        "raw_share_text": "Looks cozy",
        "is_favorited": true,
        "is_archived": false,
        "created_at": "2024-01-15T15:00:00Z"
      },
      "content": {
        "id": "content-uuid-2",
        "url": "https://instagram.com/reel/def456",
        "source_platform": "instagram",
        "status": "READY",
        "title": "Hidden Cafe Gem",
        "thumbnail_url": "https://cdn.example.com/thumb2.jpg",
        "category_high": "Food & Drink",
        "topic_main": "Cozy cafe in Indiranagar",
        "save_count": 1
      }
    }
  ],
  "total": 47,
  "limit": 10,
  "offset": 0,
  "has_more": true
}
```

#### Implementation Notes

**Default Behavior**:
- Shows only READY items (unless `status` param specified)
- Excludes archived items (unless `is_archived=true`)
- Sorts by `created_at` descending (newest first)
- Max 100 items per page

**Search Implementation**:
- Searches in: `shared_content.title`, `shared_content.topic_main`, `user_content_saves.raw_share_text`
- Case-insensitive
- Uses PostgreSQL `ILIKE` or full-text search

**SQL Query**:
```sql
SELECT 
    ucs.id as save_id,
    ucs.raw_share_text,
    ucs.is_favorited,
    ucs.created_at as saved_at,
    sc.*
FROM user_content_saves ucs
JOIN shared_content sc ON ucs.shared_content_id = sc.id
WHERE ucs.user_id = $1
  AND sc.status = $2  -- if status filter
  AND sc.category_high = $3  -- if category filter
  AND ucs.is_archived = $4
ORDER BY ucs.created_at DESC
LIMIT $5 OFFSET $6;
```

---

### 2.3 GET /items/grouped

**Purpose**: Get user's content grouped by high-level category.

#### Request

**Headers**:
```http
Authorization: Bearer <token>
```

**Query Parameters**:
```python
class GroupedItemsParams(BaseModel):
    status: Optional[ItemStatus] = Field("READY", description="Filter by status")
    limit_per_category: int = Field(10, ge=1, le=50, description="Items per category")
```

**Example**:
```http
GET /items/grouped?limit_per_category=5
```

#### Response

**Success - 200 OK**:
```python
class GroupedItemsResponse(BaseModel):
    groups: Dict[str, CategoryGroup]
    total_items: int
```

**Example**:
```json
{
  "groups": {
    "Food & Drink": {
      "category": "Food & Drink",
      "count": 12,
      "items": [
        {
          "save": {
            "id": "save-uuid-1",
            "raw_share_text": "Must visit!",
            "created_at": "2024-01-15T14:30:00Z"
          },
          "content": {
            "id": "content-uuid-1",
            "title": "Best Cafe in Indiranagar",
            "thumbnail_url": "https://cdn.example.com/thumb1.jpg",
            "topic_main": "Trendy cafe in Indiranagar",
            "save_count": 5
          }
        }
        // ... 4 more items
      ]
    },
    "Travel": {
      "category": "Travel",
      "count": 8,
      "items": [
        // ... up to 5 items
      ]
    },
    "Learning": {
      "category": "Learning",
      "count": 3,
      "items": [
        // ... up to 3 items
      ]
    }
  },
  "total_items": 47
}
```

#### Implementation Notes

**SQL Query**:
```sql
WITH user_items AS (
    SELECT 
        ucs.*,
        sc.*,
        ROW_NUMBER() OVER (
            PARTITION BY sc.category_high 
            ORDER BY ucs.created_at DESC
        ) as rn
    FROM user_content_saves ucs
    JOIN shared_content sc ON ucs.shared_content_id = sc.id
    WHERE ucs.user_id = $1 
      AND sc.status = 'READY'
      AND ucs.is_archived = false
)
SELECT 
    category_high,
    COUNT(*) as category_count,
    json_agg(
        CASE WHEN rn <= $2 THEN 
            json_build_object(
                'save', json_build_object(...),
                'content', json_build_object(...)
            )
        END
    ) FILTER (WHERE rn <= $2) as items
FROM user_items
GROUP BY category_high
ORDER BY category_count DESC;
```

---

### 2.4 GET /items/{item_id}

**Purpose**: Get detailed information about a specific saved item, optionally with similar items.

#### Request

**Headers**:
```http
Authorization: Bearer <token>
```

**Path Parameters**:
- `item_id` (UUID): The UserContentSave ID

**Query Parameters**:
```python
class ItemDetailParams(BaseModel):
    include_similar: bool = Field(False, description="Include similar items")
    similar_limit: int = Field(10, ge=1, le=20, description="Max similar items")
```

**Example**:
```http
GET /items/save-uuid-1?include_similar=true&similar_limit=5
```

#### Response

**Success - 200 OK**:
```python
class ItemDetailResponse(BaseModel):
    save: UserContentSaveDetail
    content: SharedContentDetail
    cluster: Optional[ClusterSummary]  # Which cluster this belongs to
    similar_items: Optional[List[SimilarItemResponse]]
```

**Example**:
```json
{
  "save": {
    "id": "save-uuid-1",
    "user_id": "user-uuid",
    "raw_share_text": "Must visit this weekend!",
    "is_favorited": false,
    "is_archived": false,
    "last_viewed_at": "2024-01-15T18:00:00Z",
    "created_at": "2024-01-15T14:30:00Z",
    "updated_at": "2024-01-15T18:00:00Z"
  },
  "content": {
    "id": "content-uuid-1",
    "url": "https://instagram.com/reel/abc123",
    "source_platform": "instagram",
    "status": "READY",
    "title": "Best Cafe in Indiranagar",
    "caption": "Here are my top 5 favorite brunch spots in Bangalore! Check out these amazing cafes...",
    "description": null,
    "thumbnail_url": "https://cdn.example.com/thumb1.jpg",
    "duration_seconds": 45,
    "content_text": "Best Cafe in Indiranagar\nHere are my top 5 favorite brunch spots...",
    "topic_main": "Trendy cafe in Indiranagar",
    "category_high": "Food & Drink",
    "subcategories": ["Cafes", "Brunch", "Bangalore", "Food"],
    "locations": ["Indiranagar", "Bangalore", "Karnataka", "India"],
    "entities": ["Cafe A", "Cafe B", "Third Wave Coffee"],
    "intent": "visit",
    "visual_description": "A cozy cafe interior with wooden tables and coffee cups...",
    "visual_tags": ["cafe", "coffee", "indoor", "modern"],
    "save_count": 5,
    "created_at": "2024-01-15T14:30:00Z",
    "updated_at": "2024-01-15T14:35:00Z"
  },
  "cluster": {
    "id": "cluster-uuid-1",
    "label": "Indiranagar Cafe Hopping",
    "cluster_type": "Food",
    "short_description": "Saved content about trendy cafes and brunch spots in Bangalore."
  },
  "similar_items": [
    {
      "save_id": "save-uuid-7",
      "content": {
        "id": "content-uuid-7",
        "title": "Hidden Brunch Spots in Bangalore",
        "thumbnail_url": "https://cdn.example.com/thumb7.jpg",
        "topic_main": "Brunch cafes in Bangalore",
        "category_high": "Food & Drink"
      },
      "similarity_score": 0.92,
      "already_saved": true
    },
    {
      "save_id": null,
      "content": {
        "id": "content-uuid-15",
        "title": "Koramangala Cafe Guide",
        "thumbnail_url": "https://cdn.example.com/thumb15.jpg",
        "topic_main": "Best cafes in Koramangala",
        "category_high": "Food & Drink"
      },
      "similarity_score": 0.87,
      "already_saved": false
    }
  ]
}
```

**Error - 404 Not Found**:
```json
{
  "detail": "Save not found or does not belong to you"
}
```

#### Implementation Notes

**Similar Items Algorithm**:
1. Get embedding for current item from vector DB
2. Query vector DB for similar embeddings (cosine similarity)
3. Filter to user's content preference (can include global recommendations)
4. Check which items user has already saved
5. Return top N similar items with similarity scores

**Updating last_viewed_at**:
```python
# Update asynchronously (non-blocking)
background_tasks.add_task(
    update_last_viewed,
    save_id=item_id,
    timestamp=datetime.utcnow()
)
```

---

## 3. Cluster Endpoints

### 3.1 GET /clusters

**Purpose**: List all clusters for the authenticated user.

#### Request

**Headers**:
```http
Authorization: Bearer <token>
```

**Query Parameters**:
```python
class ListClustersParams(BaseModel):
    cluster_type: Optional[ClusterType] = Field(None, description="Filter by type")
    min_items: int = Field(1, ge=1, description="Min items in cluster")
    sort_by: str = Field("updated_at", description="Sort field")
    sort_order: str = Field("desc", description="asc or desc")
```

**Example**:
```http
GET /clusters?cluster_type=Food&min_items=3
```

#### Response

**Success - 200 OK**:
```python
class ListClustersResponse(BaseModel):
    clusters: List[ClusterSummary]
    total: int
```

**Example**:
```json
{
  "clusters": [
    {
      "id": "cluster-uuid-1",
      "label": "Indiranagar Cafe Hopping",
      "cluster_type": "Food",
      "short_description": "Saved content about trendy cafes and brunch spots in Bangalore.",
      "item_count": 5,
      "sample_items": [
        {
          "id": "content-uuid-1",
          "title": "Best Cafe in Indiranagar",
          "thumbnail_url": "https://cdn.example.com/thumb1.jpg"
        },
        {
          "id": "content-uuid-2",
          "title": "Hidden Cafe Gem",
          "thumbnail_url": "https://cdn.example.com/thumb2.jpg"
        },
        {
          "id": "content-uuid-3",
          "title": "Bangalore Brunch Guide",
          "thumbnail_url": "https://cdn.example.com/thumb3.jpg"
        }
      ],
      "created_at": "2024-01-16T02:00:00Z",
      "updated_at": "2024-01-16T02:00:00Z"
    },
    {
      "id": "cluster-uuid-2",
      "label": "Goa Vacation Planning",
      "cluster_type": "Travel",
      "short_description": "Beach destinations and adventure activities in Goa.",
      "item_count": 3,
      "sample_items": [
        // ... up to 3 thumbnails
      ],
      "created_at": "2024-01-16T02:00:00Z",
      "updated_at": "2024-01-16T02:00:00Z"
    }
  ],
  "total": 7
}
```

#### Implementation Notes

**SQL Query**:
```sql
SELECT 
    c.*,
    COUNT(cm.user_save_id) as item_count,
    json_agg(
        json_build_object(
            'id', sc.id,
            'title', sc.title,
            'thumbnail_url', sc.thumbnail_url
        ) 
        ORDER BY ucs.created_at DESC
        LIMIT 3
    ) as sample_items
FROM clusters c
LEFT JOIN cluster_memberships cm ON c.id = cm.cluster_id
LEFT JOIN user_content_saves ucs ON cm.user_save_id = ucs.id
LEFT JOIN shared_content sc ON ucs.shared_content_id = sc.id
WHERE c.user_id = $1
GROUP BY c.id
HAVING COUNT(cm.user_save_id) >= $2  -- min_items filter
ORDER BY c.updated_at DESC;
```

---

### 3.2 GET /clusters/{cluster_id}

**Purpose**: Get detailed information about a specific cluster including all its items.

#### Request

**Headers**:
```http
Authorization: Bearer <token>
```

**Path Parameters**:
- `cluster_id` (UUID): The Cluster ID

**Query Parameters**:
```python
class ClusterDetailParams(BaseModel):
    limit: int = Field(50, ge=1, le=100, description="Items per page")
    offset: int = Field(0, ge=0, description="Pagination offset")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("asc", description="asc or desc")
```

**Example**:
```http
GET /clusters/cluster-uuid-1?limit=20&offset=0
```

#### Response

**Success - 200 OK**:
```python
class ClusterDetailResponse(BaseModel):
    cluster: ClusterDetail
    items: List[ClusterItemResponse]
    total_items: int
    has_more: bool
```

**Example**:
```json
{
  "cluster": {
    "id": "cluster-uuid-1",
    "user_id": "user-uuid",
    "label": "Indiranagar Cafe Hopping",
    "cluster_type": "Food",
    "short_description": "Saved content about trendy cafes and brunch spots in Bangalore.",
    "created_at": "2024-01-16T02:00:00Z",
    "updated_at": "2024-01-16T02:00:00Z"
  },
  "items": [
    {
      "save": {
        "id": "save-uuid-1",
        "raw_share_text": "Must visit this weekend!",
        "is_favorited": false,
        "created_at": "2024-01-15T14:30:00Z"
      },
      "content": {
        "id": "content-uuid-1",
        "url": "https://instagram.com/reel/abc123",
        "title": "Best Cafe in Indiranagar",
        "thumbnail_url": "https://cdn.example.com/thumb1.jpg",
        "topic_main": "Trendy cafe in Indiranagar",
        "category_high": "Food & Drink",
        "locations": ["Indiranagar", "Bangalore"],
        "save_count": 5
      }
    },
    {
      "save": {
        "id": "save-uuid-2",
        "raw_share_text": "Looks cozy",
        "is_favorited": true,
        "created_at": "2024-01-15T15:00:00Z"
      },
      "content": {
        "id": "content-uuid-2",
        "url": "https://instagram.com/reel/def456",
        "title": "Hidden Cafe Gem",
        "thumbnail_url": "https://cdn.example.com/thumb2.jpg",
        "topic_main": "Cozy cafe in Indiranagar",
        "category_high": "Food & Drink",
        "save_count": 1
      }
    },
    {
      "save": {
        "id": "save-uuid-3",
        "raw_share_text": "Good recommendations",
        "is_favorited": false,
        "created_at": "2024-01-15T16:00:00Z"
      },
      "content": {
        "id": "content-uuid-3",
        "url": "https://youtube.com/watch?v=xyz789",
        "title": "Bangalore Brunch Guide",
        "thumbnail_url": "https://cdn.example.com/thumb3.jpg",
        "topic_main": "Best brunch spots in Bangalore",
        "category_high": "Food & Drink",
        "save_count": 12
      }
    }
  ],
  "total_items": 5,
  "has_more": false
}
```

**Error - 404 Not Found**:
```json
{
  "detail": "Cluster not found or does not belong to you"
}
```

#### Implementation Notes

**SQL Query**:
```sql
SELECT 
    ucs.id as save_id,
    ucs.raw_share_text,
    ucs.is_favorited,
    ucs.created_at as saved_at,
    sc.*
FROM cluster_memberships cm
JOIN user_content_saves ucs ON cm.user_save_id = ucs.id
JOIN shared_content sc ON ucs.shared_content_id = sc.id
JOIN clusters c ON cm.cluster_id = c.id
WHERE cm.cluster_id = $1
  AND c.user_id = $2  -- Security: ensure cluster belongs to user
ORDER BY ucs.created_at ASC
LIMIT $3 OFFSET $4;
```

---

## 4. Pydantic Response Models

### 4.1 User Models

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### 4.2 Content Models

```python
from typing import Optional, List
from enum import Enum

class SourcePlatform(str, Enum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    UNKNOWN = "unknown"

class ItemStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"

class CategoryHighLevel(str, Enum):
    TRAVEL = "Travel"
    FOOD_DRINK = "Food & Drink"
    LEARNING = "Learning"
    CAREER = "Career"
    FITNESS = "Fitness"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    TECH = "Tech"
    MISC = "Misc"

class IntentType(str, Enum):
    LEARN = "learn"
    VISIT = "visit"
    BUY = "buy"
    TRY = "try"
    WATCH = "watch"
    MISC = "misc"

class SharedContentResponse(BaseModel):
    id: UUID
    url: str
    source_platform: SourcePlatform
    status: ItemStatus
    title: Optional[str]
    caption: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: Optional[int]
    category_high: Optional[CategoryHighLevel]
    topic_main: Optional[str]
    subcategories: Optional[List[str]]
    locations: Optional[List[str]]
    save_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SharedContentDetail(SharedContentResponse):
    """Extended version with all fields"""
    description: Optional[str]
    content_text: Optional[str]
    entities: Optional[List[str]]
    intent: Optional[IntentType]
    visual_description: Optional[str]
    visual_tags: Optional[List[str]]
    updated_at: datetime

class UserContentSaveResponse(BaseModel):
    id: UUID
    user_id: UUID
    shared_content_id: UUID
    raw_share_text: Optional[str]
    is_favorited: bool = False
    is_archived: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserContentSaveDetail(UserContentSaveResponse):
    """Extended version with all fields"""
    last_viewed_at: Optional[datetime]
    updated_at: datetime

class ContentItemResponse(BaseModel):
    """Combined save + content for list views"""
    save: UserContentSaveResponse
    content: SharedContentResponse
```

### 4.3 Cluster Models

```python
class ClusterType(str, Enum):
    TRAVEL = "Travel"
    FOOD = "Food"
    LEARNING = "Learning"
    FITNESS = "Fitness"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    TECH = "Tech"
    MISC = "Misc"

class ClusterSummary(BaseModel):
    id: UUID
    label: str
    cluster_type: Optional[ClusterType]
    short_description: Optional[str]
    item_count: int
    sample_items: List[dict]  # Simplified item preview
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ClusterDetail(BaseModel):
    id: UUID
    user_id: UUID
    label: str
    cluster_type: Optional[ClusterType]
    short_description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

---

## 5. Error Handling

### Standard Error Response

```python
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    field_errors: Optional[List[Dict]] = None
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET request |
| 201 | Created | Successful POST (resource created) |
| 400 | Bad Request | Invalid input, duplicate resource |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation failed (Pydantic) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |

### Common Error Examples

**401 Unauthorized**:
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden**:
```json
{
  "detail": "You do not have permission to access this cluster"
}
```

**429 Too Many Requests**:
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

---

## 6. Rate Limiting

### Limits (Per User)

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /auth/login` | 5 requests | 15 minutes |
| `POST /auth/register` | 3 requests | 1 hour |
| `POST /items` | 50 requests | 1 hour |
| `GET /items*` | 100 requests | 1 minute |
| `GET /clusters*` | 100 requests | 1 minute |

### Headers

```http
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1234567890
```

---

## 7. Pagination

### Standard Pagination Parameters

All list endpoints support:
- `limit`: Items per page (default: 20, max: 100)
- `offset`: Number of items to skip (default: 0)

### Response Format

```json
{
  "items": [...],
  "total": 156,
  "limit": 20,
  "offset": 40,
  "has_more": true
}
```

### Calculating Pages

```python
page_number = (offset // limit) + 1
total_pages = ceil(total / limit)
has_more = (offset + limit) < total
```

---

## 8. FastAPI Implementation Examples

### 8.1 Authentication Dependency

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user
```

### 8.2 POST /items Endpoint

```python
from fastapi import APIRouter, Depends, BackgroundTasks, status
from pydantic import BaseModel

router = APIRouter(prefix="/items", tags=["Content"])

@router.post("", response_model=SaveContentResponse, status_code=status.HTTP_201_CREATED)
async def save_content(
    request: SaveContentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Normalize URL
    normalized_url = normalize_url(request.url)
    url_hash = generate_url_hash(normalized_url)
    
    # 2. Check if SharedContent exists
    shared_content = db.query(SharedContent).filter(
        SharedContent.url_hash == url_hash
    ).first()
    
    if not shared_content:
        # Create new SharedContent
        shared_content = SharedContent(
            url=normalized_url,
            url_hash=url_hash,
            source_platform=detect_platform(normalized_url),
            status=ItemStatus.PENDING,
            save_count=0
        )
        db.add(shared_content)
        db.flush()  # Get ID without committing
        
        # Enqueue processing job
        background_tasks.add_task(
            enqueue_processing_job,
            shared_content_id=shared_content.id
        )
        message = "Content saved successfully. Processing has been queued."
    else:
        message = "Content already processed and ready to view!" if shared_content.status == ItemStatus.READY else "Content is being processed."
    
    # 3. Check if user already saved this
    existing_save = db.query(UserContentSave).filter(
        UserContentSave.user_id == current_user.id,
        UserContentSave.shared_content_id == shared_content.id
    ).first()
    
    if existing_save:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already saved this content"
        )
    
    # 4. Create UserContentSave
    user_save = UserContentSave(
        user_id=current_user.id,
        shared_content_id=shared_content.id,
        raw_share_text=request.raw_share_text
    )
    db.add(user_save)
    
    # 5. Increment save_count
    shared_content.save_count += 1
    
    db.commit()
    db.refresh(user_save)
    db.refresh(shared_content)
    
    return SaveContentResponse(
        save=UserContentSaveResponse.from_orm(user_save),
        content=SharedContentResponse.from_orm(shared_content),
        message=message
    )
```

### 8.3 GET /clusters/{cluster_id} Endpoint

```python
@router.get("/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster_detail(
    cluster_id: UUID,
    params: ClusterDetailParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify cluster exists and belongs to user
    cluster = db.query(Cluster).filter(
        Cluster.id == cluster_id,
        Cluster.user_id == current_user.id
    ).first()
    
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found or does not belong to you"
        )
    
    # 2. Get items in cluster with pagination
    items_query = (
        db.query(UserContentSave, SharedContent)
        .join(ClusterMembership, ClusterMembership.user_save_id == UserContentSave.id)
        .join(SharedContent, UserContentSave.shared_content_id == SharedContent.id)
        .filter(ClusterMembership.cluster_id == cluster_id)
    )
    
    # Sort
    if params.sort_by == "created_at":
        order_column = UserContentSave.created_at
    else:
        order_column = getattr(UserContentSave, params.sort_by)
    
    if params.sort_order == "desc":
        items_query = items_query.order_by(order_column.desc())
    else:
        items_query = items_query.order_by(order_column.asc())
    
    # Count total
    total_items = items_query.count()
    
    # Paginate
    items = items_query.limit(params.limit).offset(params.offset).all()
    
    # 3. Format response
    return ClusterDetailResponse(
        cluster=ClusterDetail.from_orm(cluster),
        items=[
            ClusterItemResponse(
                save=UserContentSaveResponse.from_orm(save),
                content=SharedContentResponse.from_orm(content)
            )
            for save, content in items
        ],
        total_items=total_items,
        has_more=(params.offset + params.limit) < total_items
    )
```

---

## 9. API Testing Examples

### cURL Examples

**Register**:
```bash
curl -X POST https://api.yourapp.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "SecurePass123!"
  }'
```

**Save Content**:
```bash
curl -X POST https://api.yourapp.com/v1/items \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/abc123/",
    "raw_share_text": "Must try this weekend!"
  }'
```

**List Clusters**:
```bash
curl -X GET "https://api.yourapp.com/v1/clusters?cluster_type=Food" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Summary

This API provides:

✅ **JWT Authentication** - Secure token-based auth  
✅ **Content Deduplication** - Save processing costs via SharedContent  
✅ **Smart Clustering** - AI-generated groups  
✅ **Flexible Filtering** - Category, status, search support  
✅ **Pagination** - Efficient data loading  
✅ **Type Safety** - Pydantic validation  
✅ **Error Handling** - Consistent error responses  
✅ **Rate Limiting** - Prevent abuse  

**Next Documents**:
- `03-ai-pipelines.md` - AI/ML components and workflows
- `04-worker-architecture.md` - Background job processing
- `05-deployment.md` - AWS infrastructure setup

---

## 10. Production Requirements

### 10.1 Health Check & Monitoring

####GET /health

**Purpose**: Service health check for load balancers and monitoring.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "sqs": "healthy",
    "vector_db": "healthy"
  }
}
```

**Implementation**:
```python
@app.get("/health")
async def health_check():
    # Quick database ping
    db_healthy = await check_db_connection()
    redis_healthy = await check_redis_connection()
    sqs_healthy = await check_sqs_connection()
    vector_db_healthy = await check_vector_db()
    
    all_healthy = all([db_healthy, redis_healthy, sqs_healthy, vector_db_healthy])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": API_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "sqs": "healthy" if sqs_healthy else "unhealthy",
            "vector_db": "healthy" if vector_db_healthy else "unhealthy"
        }
    }
```

#### GET /metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

### 10.2 Security Headers & CORS

**Required Headers**:
```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourapp.com", "https://app.yourapp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"]
)

# Trusted Host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.yourapp.com", "*.yourapp.com"]
)

# Security Headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

**Request ID Tracking**:
```python
import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

---

### 10.3 Idempotency for POST Operations

**Header**: `Idempotency-Key: <unique-key>`

**POST /items with Idempotency**:
```python
from fastapi import Header

@router.post("/items")
async def save_content(
    request: SaveContentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cache: Redis = Depends(get_redis)
):
    # Check idempotency cache (24 hour TTL)
    if idempotency_key:
        cache_key = f"idempotency:{current_user.id}:{idempotency_key}"
        cached_response = await cache.get(cache_key)
        if cached_response:
            return json.loads(cached_response)
    
    # Process request normally
    response = await process_save_content(...)
    
    # Cache response if idempotency key provided
    if idempotency_key:
        await cache.setex(
            cache_key,
            86400,  # 24 hours
            json.dumps(response)
        )
    
    return response
```

---

### 10.4 Webhook/Callback for Processing Status

**POST /webhooks/register**:
```python
class WebhookRegister(BaseModel):
    url: HttpUrl
    events: List[str]  # ["content.ready", "content.failed"]
    secret: str  # For HMAC signature

@router.post("/webhooks/register")
async def register_webhook(
    webhook: WebhookRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Store webhook configuration
    wh = Webhook(
        user_id=current_user.id,
        url=webhook.url,
        events=webhook.events,
        secret=webhook.secret
    )
    db.add(wh)
    db.commit()
    
    return {"id": wh.id, "url": wh.url}
```

**Webhook Payload** (when content processing completes):
```json
{
  "event": "content.ready",
  "timestamp": "2024-01-15T14:35:00Z",
  "data": {
    "save_id": "save-uuid-1",
    "content_id": "content-uuid-1",
    "status": "READY",
    "title": "Best Cafe in Indiranagar"
  },
  "signature": "sha256=abc123..." 
}
```

---

### 10.5 Caching Strategy

**Redis Caching**:
```python
from functools import wraps
import json

def cache_response(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name + args
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Check cache
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await redis.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Usage
@cache_response(ttl=60)
async def get_user_clusters(user_id: str):
    return db.query(Cluster).filter(Cluster.user_id == user_id).all()
```

**Cache Invalidation**:
```python
# When new item saved
await redis.delete(f"user_items:{user_id}")
await redis.delete(f"grouped_items:{user_id}")

# When clustering completes
await redis.delete(f"user_clusters:{user_id}")
```

---

### 10.6 Database Transaction Handling

**ACID Transactions for POST /items**:
```python
from sqlalchemy.exc import IntegrityError
from contextlib import contextmanager

@contextmanager
def db_transaction(db: Session):
    try:
        yield db
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate entry")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/items")
async def save_content(...):
    with db_transaction(db):
        # Check existing content
        shared_content = db.query(SharedContent).filter(...).with_for_update().first()
        
        # Create save
        user_save = UserContentSave(...)
        db.add(user_save)
        
        # Increment counter
        if shared_content:
            shared_content.save_count += 1
        
        # All-or-nothing commit
```

**Optimistic Locking**:
```python
class SharedContent(Base):
    # ... other fields
    version = Column(Integer, default=0, nullable=False)

# When updating
content = db.query(SharedContent).filter(
    SharedContent.id == content_id,
    SharedContent.version == expected_version
).first()

if not content:
    raise HTTPException(409, "Content has been modified by another request")

content.save_count += 1
content.version += 1
db.commit()
```

---

### 10.7 Input Validation & Sanitization

**URL Validation**:
```python
import re
from urllib.parse import urlparse

ALLOWED_DOMAINS = ["instagram.com", "youtube.com", "youtu.be"]

def validate_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return False
        
        domain = parsed.netloc.replace("www.", "")
        return any(domain.endswith(allowed) for allowed in ALLOWED_DOMAINS)
    except:
        return False

class SaveContentRequest(BaseModel):
    url: str
    raw_share_text: Optional[str] = Field(None, max_length=500)
    
    @field_validator("url")
    def validate_url_field(cls, v):
        if not validate_url(v):
            raise ValueError("Invalid or unsupported URL")
        return v
    
    @field_validator("raw_share_text")
    def sanitize_share_text(cls, v):
        if v:
            # Remove potential XSS vectors
            v = re.sub(r'<[^>]+>', '', v)  # Strip HTML tags
            v = v.strip()
        return v
```

**SQL Injection Prevention**:
- Use SQLAlchemy ORM (parameterized queries)
- Never use string concatenation for SQL
- Always use bind parameters

---

### 10.8 Retry Logic & Circuit Breaker

**Exponential Backoff for External APIs**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_instagram_metadata(url: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

**Circuit Breaker**:
```python
from pybreaker import CircuitBreaker

youtube_breaker = CircuitBreaker(
    fail_max=5,  # Open after 5 failures
    timeout_duration=60  # Try again after 60 seconds
)

@youtube_breaker
async def fetch_youtube_metadata(url: str):
    # Call YouTube API
    pass
```

---

### 10.9 Rate Limiting (Production Implementation)

**Redis-based Rate Limiting**:
```python
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/items")
@limiter.limit("50/hour")
async def save_content(request: Request, ...):
    pass

@router.post("/auth/login")
@limiter.limit("5/15minutes")
async def login(request: Request, ...):
    pass
```

**Custom Rate Limiter**:
```python
async def check_rate_limit(user_id: str, endpoint: str, limit: int, window: int):
    key = f"ratelimit:{user_id}:{endpoint}"
    count = await redis.incr(key)
    
    if count == 1:
        await redis.expire(key, window)
    
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {window} seconds.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + window)
            }
        )
```

---

### 10.10 Logging & Audit Trail

**Structured Logging**:
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            "endpoint": getattr(record, "endpoint", None),
        }
        return json.dumps(log_obj)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# Usage
logger.info("Content saved", extra={
    "request_id": request.state.request_id,
    "user_id": current_user.id,
    "content_id": content.id
})
```

**Audit Table**:
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"))
    action = Column(String)  # "save_content", "create_cluster", etc.
    resource_type = Column(String)  # "content_item", "cluster", etc.
    resource_id = Column(UUID)
    details = Column(JSONB)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
```

---

### 10.11 Background Job Status Tracking

**GET /jobs/{job_id}**:
```python
class JobStatus(BaseModel):
    id: UUID
    status: ItemStatus
    progress: int  # 0-100
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(ProcessingJob).filter(
        ProcessingJob.id == job_id,
        ProcessingJob.user_id == current_user.id  # Security check
    ).first()
    
    if not job:
        raise HTTPException(404, "Job not found")
    
    return JobStatus.from_orm(job)
```

---

### 10.12 Error Handling & Exceptions

**Global Exception Handler**:
```python
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "request_id": request.state.request_id,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "request_id": request.state.request_id
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request.state.request_id
        },
        headers=exc.headers
    )
```

---

### 10.13 Database Connection Pooling

**SQLAlchemy Pool Configuration**:
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Maintain 20 connections
    max_overflow=10,  # Allow up to 30 total connections
    pool_timeout=30,  # Wait 30s for connection
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging in dev
)
```

---

### 10.14 API Documentation (OpenAPI /Swagger)

FastAPI automatically generates:
- **OpenAPI Schema**: `GET /openapi.json`
- **Swagger UI**: `GET /docs`
- **ReDoc**: `GET /redoc`

**Customize**:
```python
app = FastAPI(
    title="Content Intelligence API",
    description="AI-powered content organization platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)
```

---

### 10.15 Deployment Checklist

**Environment Variables**:
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://host:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_DAYS=7

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/...

# AI Services
OPENAI_API_KEY=sk-...
VECTOR_DB_URL=https://qdrant-instance.com

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourapp.com,https://app.yourapp.com
RATE_LIMIT_ENABLED=true
```

**Production Settings**:
```python
class Settings(BaseSettings):
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database
    database_url: str
    database_pool_size: int = 20
    
    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 7
    cors_origins: List[str]
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## ✅ Production MVP Readiness Summary

### Core API (Already Documented)
- ✅ Authentication (JWT)
- ✅ Content endpoints (POST, GET, filter, search)
- ✅ Cluster endpoints
- ✅ Pydantic validation
- ✅ Error handling
- ✅ Pagination

### Production Requirements (Added Above)
- ✅ Health checks & monitoring
- ✅ Security headers (CORS, CSP, etc.)
- ✅ Request ID tracking
- ✅ Idempotency for POST operations
- ✅ Webhook/callback support
- ✅ Caching strategy (Redis)
- ✅ Database transactions & pooling
- ✅ Input validation & sanitization
- ✅ Retry logic & circuit breakers
- ✅ Rate limiting (production-grade)
- ✅ Structured logging & audit trail
- ✅ Background job status tracking
- ✅ Global exception handling
- ✅ OpenAPI/Swagger documentation
- ✅ Deployment configuration

**The API is now PRODUCTION-READY for MVP!** 🎯

All critical production requirements are documented and can be implemented. The next step is the actual implementation and deployment.
