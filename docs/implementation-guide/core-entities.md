# Core Domain Entities

## Overview

This document defines the **core domain entities** for the Content Intelligence MVP with a **normalized architecture** that separates content-level data from user-level data.

**Key Architectural Decisions**:

1. **Content Deduplication**: Instead of duplicating content processing for each user who saves the same URL, we split the data model into:
   - **SharedContent** - Universal content metadata (processed once, shared across all users)
   - **UserContentSave** - User's personal relationship to that content

2. **Strong Classification**: Content is classified into a `content_category` during AI processing:
   - Classification is **strong and tight** (exactly one of the defined categories)
   - Classification is **user-independent** (based purely on content)
   - Classification is **immutable** after processing completes

3. **Per-Category Clustering**: Clusters group items **within** a content_category:
   - All items in a cluster share the same `content_category`
   - Cluster labels are AI-generated for the specific grouping
   - Example: Food items → "Cafe Hopping in Indiranagar" cluster

**Technology**: Python 3.11+ with SQLAlchemy 2.0 and PostgreSQL 14+

---

## Entity Catalog

| Entity | Level | Purpose |
|--------|-------|---------|
| `User` | User | Registered application user |
| `SharedContent` | Content | Universal content metadata + **authoritative content_category** |
| `UserContentSave` | User-Content | User's personal save of a SharedContent item |
| `Cluster` | User-Category | AI-generated group of similar items **within a content_category** |
| `ClusterMembership` | User-Content | Links UserContentSaves to Clusters |
| `ProcessingJob` | Content | Background job tracking for SharedContent processing |

---

## Classification vs Clustering

| Aspect | Classification (content_category) | Clustering (Cluster) |
|--------|----------------------------------|---------------------|
| **Stored In** | `SharedContent.content_category` | `Cluster` entity |
| **When Set** | During AI processing | After classification, per-user |
| **Scope** | Global (per content) | User-specific |
| **Values** | Enum: Travel, Food, Learning, etc. | AI-generated labels |
| **Mutability** | Immutable after READY | Re-computed on demand |
| **Example** | "Food" | "Cafe Hopping in Indiranagar" |

---

```
User A saves instagram.com/reel/abc123
  → Check if SharedContent exists for url_hash
  → Not found → Create SharedContent, enqueue processing
  → Create UserContentSave (links User A to SharedContent)
  → Cost: $0.005

User B saves instagram.com/reel/abc123 (SAME URL)
  → Check if SharedContent exists for url_hash
  → Found! (already processed)
  → Create UserContentSave (links User B to SharedContent)
  → Cost: $0 (instant READY state)
```

---

## 1. User Entity

### Purpose
Represents a registered user of the application. Users own personal saves and have their own clusters. This is the root entity for all user-specific data.

### ORM Model

```python
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid as uuid_pkg

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid_pkg.uuid4
    )
    
    # Authentication
    email = Column(
        String(255), 
        unique=True, 
        nullable=False
    )
    password_hash = Column(
        Text, 
        nullable=False
    )
    
    # Audit Fields
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    saved_content = relationship(
        "UserContentSave", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    clusters = relationship(
        "Cluster", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
```

### Attributes

#### `id` - UUID (Primary Key)
- **Type**: UUID v4
- **Purpose**: Unique identifier for each user
- **Why UUID?**
  - Better security than auto-incrementing integers (non-enumerable)
  - Better distribution for database sharding/partitioning
  - Can be generated client-side if needed
  - No collision risk when merging data from different sources

#### `email` - String(255)
- **Type**: VARCHAR(255), UNIQUE, NOT NULL
- **Purpose**: User's email address, used for authentication and identification
- **Constraints**:
  - Must be unique across all users
  - Cannot be null
  - Validated at application level using Pydantic's `EmailStr`
- **Indexed**: Automatic unique index for fast lookups during login

#### `password_hash` - Text
- **Type**: TEXT, NOT NULL
- **Purpose**: Stores hashed password (never plaintext)
- **Implementation**: Use bcrypt or argon2 for hashing
- **Security Note**: Original password is never stored; only the hash is persisted

#### `created_at` - Timestamp with Timezone
- **Type**: TIMESTAMPTZ, NOT NULL
- **Purpose**: Records when the user account was created
- **Default**: Automatically set to current timestamp on insert
- **Timezone**: Always stored in UTC, converted to user timezone in application

#### `updated_at` - Timestamp with Timezone
- **Type**: TIMESTAMPTZ, NOT NULL
- **Purpose**: Tracks last modification to user record
- **Behavior**: Automatically updated on any row modification via database trigger
- **Use Case**: Audit trail, cache invalidation

### Relationships

#### `saved_content` → UserContentSave (One-to-Many)
- **Type**: One User has many UserContentSaves
- **Cascade**: `all, delete-orphan`
  - When a user is deleted, all their saves are automatically deleted
  - SharedContent remains (other users may have saved it)
- **Access Pattern**: `user.saved_content` returns list of all saves
- **Reverse**: `save.user` returns the owning user

#### `clusters` → Cluster (One-to-Many)
- **Type**: One User has many Clusters
- **Cascade**: `all, delete-orphan`
  - User deletion cascades to all their clusters
  - Clusters cannot exist without a user
- **Access Pattern**: `user.clusters` returns all user's clusters
- **Reverse**: `cluster.user` returns the owning user

---

## 2. SharedContent Entity

### Purpose
Represents the **universal, platform-level metadata** for a piece of content (Instagram Reel, YouTube video). This entity is **user-independent** and contains all data that is the same regardless of who saves it:
- Platform metadata (title, caption, thumbnail)
- AI-generated insights (topic, category, entities)
- Embeddings for similarity search

**Key Principle**: Process once, share across all users who save the same URL.

### Supporting Enums

```python
from enum import Enum

class SourcePlatform(str, Enum):
    """Platform where content originated"""
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    UNKNOWN = "unknown"

class ItemStatus(str, Enum):
    """Processing lifecycle state"""
    PENDING = "PENDING"        # Just created, awaiting processing
    PROCESSING = "PROCESSING"  # Worker currently processing
    READY = "READY"            # Successfully processed and enriched
    FAILED = "FAILED"          # Processing failed (can be retried)

class ContentCategory(str, Enum):
    """
    AUTHORITATIVE content categorization.
    
    This is the single source of truth for content classification.
    Assigned during AI processing, immutable after READY status.
    Used by both SharedContent and Cluster entities.
    """
    TRAVEL = "Travel"
    FOOD = "Food"
    LEARNING = "Learning"
    CAREER = "Career"
    FITNESS = "Fitness"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    TECH = "Tech"
    LIFESTYLE = "Lifestyle"
    MISC = "Misc"

class IntentType(str, Enum):
    """Likely intent behind content"""
    LEARN = "learn"    # Educational content
    VISIT = "visit"    # Places to visit
    BUY = "buy"        # Products to purchase
    TRY = "try"        # Activities/experiences to try
    WATCH = "watch"    # Entertainment to consume later
    MISC = "misc"      # Unclear or mixed intent
```

### ORM Model

```python
from sqlalchemy import Column, String, Text, Integer, Enum as SQLEnum, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB

class SharedContent(Base):
    """
    Universal content metadata (processed once, shared across users).
    
    CLASSIFICATION ARCHITECTURE:
    - `content_category`: The AUTHORITATIVE classification assigned during AI processing.
      This is a strong, tight classification into one of the defined categories.
      NOT dependent on user context or clustering.
    
    - Content is classified ONCE during processing and this classification is immutable.
    - Clusters are then created WITHIN each category for finer user-level groupings.
    """
    __tablename__ = "shared_content"
    
    # === IDENTITY ===
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid_pkg.uuid4
    )
    
    # === SOURCE INFORMATION ===
    source_platform = Column(
        SQLEnum(SourcePlatform), 
        nullable=False
    )
    url = Column(
        Text, 
        nullable=False
    )
    url_hash = Column(
        Text, 
        unique=True,  # GLOBALLY UNIQUE
        nullable=False,
        index=True
    )
    
    # === PROCESSING STATUS ===
    status = Column(
        SQLEnum(ItemStatus), 
        nullable=False, 
        default=ItemStatus.PENDING,
        index=True
    )
    
    # === PRIMARY CLASSIFICATION ===
    # This is the authoritative category - assigned during AI processing
    content_category = Column(
        SQLEnum(ContentCategory),
        nullable=True,  # Null until processed
        index=True,
        comment="Primary content category. Assigned during AI processing. Immutable after READY status."
    )
    
    # === BASIC METADATA (from platform) ===
    title = Column(Text)
    caption = Column(Text)
    description = Column(Text)
    thumbnail_url = Column(Text)
    duration_seconds = Column(Integer)
    
    # === AI UNDERSTANDING - TEXT ANALYSIS ===
    content_text = Column(Text)
    topic_main = Column(Text)
    subcategories = Column(JSONB, comment="Fine-grained tags within the content_category")
    locations = Column(JSONB)
    entities = Column(JSONB)
    intent = Column(SQLEnum(IntentType))
    
    # === AI UNDERSTANDING - VISUAL ANALYSIS ===
    visual_description = Column(Text)
    visual_tags = Column(JSONB)
    
    # === VECTOR DATABASE REFERENCE ===
    embedding_id = Column(Text)
    
    # === STATISTICS ===
    save_count = Column(
        Integer, 
        default=0,
        comment="Number of users who saved this content"
    )
    
    # === AUDIT ===
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # === RELATIONSHIPS ===
    user_saves = relationship(
        "UserContentSave", 
        back_populates="shared_content",
        cascade="all, delete-orphan"
    )
    processing_jobs = relationship(
        "ProcessingJob", 
        back_populates="shared_content", 
        cascade="all, delete-orphan"
    )
```

### Attributes

#### Identity Section

##### `id` - UUID (Primary Key)
- **Purpose**: Unique identifier for this content
- **Generation**: UUID v4 auto-generated

#### Source Information Section

##### `source_platform` - Enum
- **Purpose**: Identifies where the content came from
- **Values**: `instagram`, `youtube`, `unknown`
- **Why Track This?**
  - Different platforms require different metadata fetching strategies
  - Platform-specific UI elements (Instagram icon vs YouTube icon)

##### `url` - Text
- **Purpose**: Canonical URL for the content
- **Format**: Normalized version (lowercase, no tracking params, HTTPS, no trailing slash)
- **Example**: `https://instagram.com/reel/abc123`
- **Not Unique**: Could theoretically have duplicates if normalization fails, but `url_hash` prevents this

##### `url_hash` - Text (Unique Index)
- **Purpose**: SHA256 hash of normalized URL for fast deduplication
- **Uniqueness**: **GLOBALLY UNIQUE** (not per-user like before)
- **Generation**: `SHA256(normalize_url(url))`
- **Normalization Rules**:
  - Convert to lowercase
  - Remove tracking parameters (`utm_*`, `ref`, etc.)
  - Standardize protocol (HTTPS)
  - Remove trailing slashes and fragments
- **Critical**: This is the **deduplication key**
  - Before creating SharedContent, check if `url_hash` exists
  - If exists → reuse existing record
  - If not → create new record
- **Index**: Unique index for fast lookups during save flow

#### Processing Status Section

##### `status` - Enum
- **Purpose**: Tracks where the content is in the processing pipeline
- **State Machine**:
  ```
  PENDING → PROCESSING → READY
                ↓
              FAILED
  ```
- **States**:
  - **PENDING**: Just created, not yet picked up by worker
  - **PROCESSING**: Worker currently fetching metadata and running AI
  - **READY**: Successfully processed, all data available
  - **FAILED**: Processing failed (can be retried)
- **Impact on Users**: All users who saved this content see the same status

#### Basic Metadata Section

##### `title` - Text (Optional)
- **Source**: Platform API or HTML parsing
- **Example**: "Best Brunch Cafes in Indiranagar"

##### `caption` - Text (Optional)
- **Source**: Platform API
- **Example**: "Here are my top 5 favorite brunch spots in Bangalore! 🥞☕"

##### `description` - Text (Optional)
- **Source**: YouTube video description
- **Example**: "In this video, I'll take you through the best cafes..."

##### `thumbnail_url` - Text (Optional)
- **Source**: Platform API or Open Graph image
- **Use**: Display in UI, input for visual AI

##### `duration_seconds` - Integer (Optional)
- **Source**: Platform API
- **Nullable**: Yes (null for static images/posts)

#### AI Understanding - Text Analysis Section

##### `content_text` - Text (Optional)
- **Purpose**: Unified text input for AI analysis
- **Composition**: Concatenation of:
  - `title`
  - `caption`
  - `description`
  - Transcript (if video)
  - OCR text (if applicable)
  - `visual_description`
- **Note**: Does NOT include user-specific `raw_share_text` (that's in UserContentSave)

##### `topic_main` - Text (Optional)
- **Purpose**: AI's interpretation of the main topic
- **Example**: "Best brunch cafes in Indiranagar, Bangalore"

##### `category_high` - Enum (Optional)
- **Purpose**: High-level categorization
- **Values**: Travel, Food & Drink, Learning, Career, Fitness, Entertainment, Shopping, Tech, Misc

##### `subcategories` - JSONB Array (Optional)
- **Type**: Array of strings
- **Example**: `["Cafes", "Brunch", "Bangalore"]`

##### `locations` - JSONB Array (Optional)
- **Type**: Array of place names
- **Example**: `["Indiranagar", "Bangalore", "Karnataka", "India"]`

##### `entities` - JSONB Array (Optional)
- **Type**: Array of proper nouns
- **Example**: `["Cafe A", "Cafe B", "Chef John"]`

##### `intent` - Enum (Optional)
- **Purpose**: Likely intent behind the content
- **Values**: `learn`, `visit`, `buy`, `try`, `watch`, `misc`
- **Note**: This is content-level intent, not user-specific

#### AI Understanding - Visual Analysis Section

##### `visual_description` - Text (Optional)
- **Source**: Vision model analysis
- **Example**: "A cozy cafe interior with wooden tables, coffee cups, and pastries."

##### `visual_tags` - JSONB Array (Optional)
- **Example**: `["cafe", "coffee", "indoor", "wooden furniture"]`

#### Vector Database Reference Section

##### `embedding_id` - Text (Optional)
- **Purpose**: Links to vector representation in vector database
- **Format**: `shared:{shared_content_id}` (e.g., `"shared:123e4567-..."`)
- **Why "shared:" prefix?** Distinguishes from old user-level embeddings
- **Use Case**: Similarity search across all content (not just one user's)

#### Statistics Section

##### `save_count` - Integer
- **Purpose**: Track how many users have saved this content
- **Default**: 0
- **Updated**: Incremented when UserContentSave created, decremented when deleted
- **Use Cases**:
  - "Trending" content detection (high save_count in short time)
  - "You and 1,247 others saved this"
  - Content recommendation ("popular in your network")
  - Analytics on viral content

#### Audit Section

##### `created_at` - Timestamp
- **Purpose**: When content was first discovered/saved by any user

##### `updated_at` - Timestamp
- **Purpose**: Last metadata or AI update
- **Use**: Cache invalidation, re-processing detection

### Relationships

#### `user_saves` → UserContentSave (One-to-Many)
- **Type**: One SharedContent has many UserContentSaves
- **Cascade**: `all, delete-orphan`
- **Meaning**: Many users can save the same content
- **Access**: `shared_content.user_saves` returns all user saves

#### `processing_jobs` → ProcessingJob (One-to-Many)
- **Type**: One SharedContent has many ProcessingJobs
- **Cascade**: `all, delete-orphan`
- **Access**: `shared_content.processing_jobs` shows processing history

### Design Decisions

**Why Global url_hash?**
- Prevents duplicate processing across all users
- Enables instant saves if content already exists
- Foundation for viral/trending analytics

**Why save_count?**
- Track popularity without expensive COUNT queries
- Enable social features ("1,247 users saved this")
- Identify trending content

**Why no user_id?**
- SharedContent is user-independent
- Multiple users link via UserContentSave
- Cleaner separation of concerns

---

## 3. UserContentSave Entity

### Purpose
Represents a **user's personal save** of a SharedContent item. This captures the user-specific aspects:
- When they saved it
- Their personal note/context
- User-specific metadata (last viewed, favorited, etc.)
- Link to clusters (via ClusterMembership)

**Key Principle**: Lightweight, user-specific wrapper around SharedContent.

### ORM Model

```python
from sqlalchemy import Column, ForeignKey, Text, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID

class UserContentSave(Base):
    __tablename__ = "user_content_saves"
    
    # === IDENTITY ===
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid_pkg.uuid4
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    shared_content_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("shared_content.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # === USER-SPECIFIC DATA ===
    raw_share_text = Column(
        Text,
        comment="User's personal note when saving"
    )
    
    # === USER ACTIONS (Optional MVP+) ===
    is_favorited = Column(
        Boolean, 
        default=False,
        comment="User marked as favorite"
    )
    is_archived = Column(
        Boolean, 
        default=False,
        comment="User archived this save"
    )
    last_viewed_at = Column(
        TIMESTAMP(timezone=True),
        comment="When user last viewed this"
    )
    
    # === AUDIT ===
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="When user saved this"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # === RELATIONSHIPS ===
    user = relationship("User", back_populates="saved_content")
    shared_content = relationship("SharedContent", back_populates="user_saves")
    cluster_memberships = relationship(
        "ClusterMembership", 
        back_populates="user_save", 
        cascade="all, delete-orphan"
    )
```

### Attributes

#### Identity Section

##### `id` - UUID (Primary Key)
- **Purpose**: Unique identifier for this save
- **Generation**: UUID v4

##### `user_id` - UUID (Foreign Key)
- **Purpose**: Links to the user who saved
- **References**: `users.id`
- **On Delete**: CASCADE (if user deleted, save deleted)
- **Indexed**: Yes (for "show all saves for user")

##### `shared_content_id` - UUID (Foreign Key)
- **Purpose**: Links to the shared content
- **References**: `shared_content.id`
- **On Delete**: CASCADE (if content deleted, save deleted)
- **Indexed**: Yes (for "show all users who saved this content")

**Composite Unique Constraint**: `UNIQUE(user_id, shared_content_id)`
- Prevents duplicate saves (user can't save same content twice)
- Enforced at database level

#### User-Specific Data Section

##### `raw_share_text` - Text (Optional)
- **Purpose**: User's personal note/context when saving
- **Example**: "This cafe looks amazing!" or "Need to try this recipe"
- **User-Specific**: Different users can have different notes for same content
- **Use Cases**:
  - Display as personal note in UI
  - Additional context for user-level intent detection
  - Search through user's own notes

#### User Actions Section (Optional MVP+)

##### `is_favorited` - Boolean
- **Purpose**: User marked this save as favorite
- **Default**: False
- **Use**: Filter view to show only favorites

##### `is_archived` - Boolean
- **Purpose**: User archived this save (hide from main view)
- **Default**: False
- **Use**: Clean up feed without deleting

##### `last_viewed_at` - Timestamp (Optional)
- **Purpose**: Track when user last viewed this content
- **Use**: "Recently viewed", engagement analytics

#### Audit Section

##### `created_at` - Timestamp
- **Purpose**: When user saved this content
- **Importance**: This is the "save timestamp" for sorting user's feed
- **Different from SharedContent.created_at** (which is when content first discovered)

##### `updated_at` - Timestamp
- **Purpose**: Last modification (favorited, archived, note edited)

### Relationships

#### `user` → User (Many-to-One)
- **Foreign Key**: `user_id → users.id`
- **Access**: `save.user` returns User object

#### `shared_content` → SharedContent (Many-to-One)
- **Foreign Key**: `shared_content_id → shared_content.id`
- **Access**: `save.shared_content` returns SharedContent object
- **Critical**: This is how user accesses all content metadata

#### `cluster_memberships` → ClusterMembership (One-to-Many)
- **Purpose**: Links this save to cluster(s) it belongs to
- **Cascade**: `all, delete-orphan`
- **Access**: `save.cluster_memberships[0].cluster` to get cluster

### Design Decisions

**Why separate table instead of just many-to-many?**
- Enables user-specific fields (`raw_share_text`, `is_favorited`, timestamps)
- Cleaner than storing user-specific data in junction table
- Easier to extend with user actions (views, shares, etc.)

**Why created_at on UserContentSave?**
- Each user has their own "when I saved this" timestamp
- Critical for sorting user's feed chronologically
- Different from when content was first discovered globally

---

## 4. Cluster Entity

### Purpose
Represents an AI-generated group of semantically similar content saves for a specific user **within a specific content_category**. 

**Key Architectural Point**: Clusters are created WITHIN a content_category, not across categories.
- All items in a cluster MUST have the same `SharedContent.content_category`
- The `content_category` field on Cluster matches the category of its items

### ORM Model

```python
class Cluster(Base):
    """
    AI-generated cluster of semantically similar content saves.
    
    CLUSTERING ARCHITECTURE:
    - Clusters are created WITHIN a content_category (e.g., all Food items grouped together).
    - The `content_category` field indicates which category this cluster belongs to.
    - All items in a cluster MUST have the same SharedContent.content_category.
    
    Example:
    - User has 5 Food saves, 3 Travel saves
    - Clustering groups the 5 Food items into "Cafe Hopping in Indiranagar" cluster
    - Clustering groups the 3 Travel items into "Goa Beach Vacation" cluster
    - Each cluster has a content_category matching its items (Food, Travel)
    """
    __tablename__ = "clusters"
    
    # === IDENTITY ===
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid_pkg.uuid4
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # === CLUSTER METADATA ===
    content_category = Column(
        SQLEnum(ContentCategory),
        nullable=False,
        index=True,
        comment="The category this cluster belongs to. All items in cluster share this category."
    )
    label = Column(
        Text, 
        nullable=False,
        comment="AI-generated human-readable cluster name (e.g., 'Cafe Hopping in Indiranagar')"
    )
    short_description = Column(
        Text,
        comment="AI-generated one-sentence description of the cluster"
    )
    
    # === AUDIT ===
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # === RELATIONSHIPS ===
    user = relationship("User", back_populates="clusters")
    cluster_memberships = relationship(
        "ClusterMembership", 
        back_populates="cluster", 
        cascade="all, delete-orphan"
    )
```

### Attributes

#### Identity Section

##### `id` - UUID (Primary Key)
- **Purpose**: Unique identifier for the cluster

##### `user_id` - UUID (Foreign Key)
- **Purpose**: Links cluster to owning user
- **References**: `users.id`
- **On Delete**: CASCADE
- **Scoping**: Clusters are user-specific
- **Note**: Clustering happens per-user (user A's clusters ≠ user B's clusters)

#### Cluster Metadata Section

##### `content_category` - Enum (Required)
- **Purpose**: The category this cluster belongs to
- **Values**: Travel, Food, Learning, Career, Fitness, Entertainment, Shopping, Tech, Lifestyle, Misc
- **Constraint**: All items in the cluster MUST have this same content_category
- **Example**: A "Cafe Hopping in Indiranagar" cluster has `content_category = Food`

##### `label` - Text (Required)
- **Purpose**: Human-readable name for the cluster
- **Generated By**: LLM based on cluster contents
- **Example**: "Cafe Hopping in Indiranagar", "Goa Beach Vacation", "Python Tutorials"
- **Note**: This is the fine-grained grouping within a category

##### `short_description` - Text (Optional)
- **Purpose**: One-sentence summary
- **Example**: "Saved reels about trendy cafes and brunch spots in Indiranagar."

### Relationships

#### `user` → User (Many-to-One)
- **Foreign Key**: `user_id → users.id`

#### `cluster_memberships` → ClusterMembership (One-to-Many)
- **Purpose**: Links cluster to its member saves
- **Cascade**: `all, delete-orphan`

### Classification vs Cluster Label

| Aspect | content_category | label |
|--------|-----------------|-------|
| **Source** | From SharedContent | AI-generated for cluster |
| **Scope** | Category-level | Cluster-specific |
| **Values** | Fixed enum | Free-form text |
| **Example** | "Food" | "Cafe Hopping in Indiranagar" |
| **Granularity** | Broad | Fine-grained |

---

## 5. ClusterMembership Entity

### Purpose
Junction table linking UserContentSaves to Clusters. Represents "this user's save belongs to this cluster."

**Important**: Links **UserContentSave** (not SharedContent) because clustering is user-specific.

### ORM Model

```python
class ClusterMembership(Base):
    __tablename__ = "cluster_memberships"
    
    # === COMPOSITE PRIMARY KEY ===
    cluster_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("clusters.id", ondelete="CASCADE"), 
        primary_key=True
    )
    user_save_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("user_content_saves.id", ondelete="CASCADE"), 
        primary_key=True
    )
    
    # === RELATIONSHIPS ===
    cluster = relationship("Cluster", back_populates="cluster_memberships")
    user_save = relationship("UserContentSave", back_populates="cluster_memberships")
```

### Attributes

##### `cluster_id` - UUID (Foreign Key, Primary Key)
- **References**: `clusters.id`
- **On Delete**: CASCADE

##### `user_save_id` - UUID (Foreign Key, Primary Key)
- **References**: `user_content_saves.id`
- **On Delete**: CASCADE
- **Note**: Links to UserContentSave, not SharedContent

### Design Decisions

**Why link to UserContentSave instead of SharedContent?**
- Clustering is per-user
- User A and User B might save the same content but cluster it differently
- User A: "Weekend Cafe Plans"
- User B: "Recipe Inspiration"
- Different users, same SharedContent, different clusters

---

## 6. ProcessingJob Entity

### Purpose
Tracks background job execution for SharedContent processing.

### Supporting Enum

```python
class JobType(str, Enum):
    """Types of background jobs"""
    INGEST = "INGEST"        # Fetch metadata from platform
    ANALYZE = "ANALYZE"      # AI analysis
    CLUSTERING = "CLUSTERING" # User-level clustering
```

### ORM Model

```python
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    # === IDENTITY ===
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid_pkg.uuid4
    )
    
    # === JOB METADATA ===
    job_type = Column(
        SQLEnum(JobType), 
        nullable=False
    )
    shared_content_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("shared_content.id", ondelete="CASCADE"),
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        comment="For CLUSTERING jobs (user-level)"
    )
    
    # === JOB STATUS ===
    status = Column(
        SQLEnum(ItemStatus), 
        nullable=False, 
        default=ItemStatus.PENDING
    )
    error_message = Column(Text)
    
    # === AUDIT ===
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # === RELATIONSHIPS ===
    shared_content = relationship("SharedContent", back_populates="processing_jobs")
```

### Attributes

##### `shared_content_id` - UUID (Foreign Key, Optional)
- **References**: `shared_content.id` (changed from content_items)
- **Nullable**: Yes (CLUSTERING jobs are user-level)

##### `user_id` - UUID (Foreign Key, Optional)
- **Purpose**: For user-level jobs (CLUSTERING)

---

## 7. Relationships Summary

### Relationship Diagram

```
        User (1)
        │
        ├────────────────────────────────────┐
        │                                    │
        ▼ (1:N)                              ▼ (1:N)
    UserContentSave                      Cluster
        │                                    │
        ├──────────────┐                     │
        │              │                     │
        ▼ (N:1)        └──────┐    ┌─────────┘
    SharedContent            │    │
        │                    ▼    ▼ (N:M)
        │              ClusterMembership
        ▼ (1:N)
    ProcessingJob
```

### Cascade Behavior

**Delete User →**
- ✓ All UserContentSaves deleted (CASCADE)
- ✓ All Clusters deleted (CASCADE)
- ✓ All ClusterMemberships deleted (via UserContentSaves and Clusters)
- ✗ SharedContent remains (other users may have saved it)
- ✗ ProcessingJobs remain (content-level, not user-level)

**Delete SharedContent →**
- ✓ All UserContentSaves deleted (CASCADE)
- ✓ All ClusterMemberships deleted (via UserContentSaves)
- ✓ All ProcessingJobs deleted (CASCADE)
- ✗ Users remain
- ✗ Clusters remain (just lose members)

**Delete UserContentSave →**
- ✓ ClusterMemberships deleted (CASCADE)
- ✗ User remains
- ✗ SharedContent remains
- ✗ Cluster remains

---

## 8. Workflows with Normalized Design

### Content Save Flow (New)

```
User saves URL from mobile app
  ↓
1. Normalize URL → generate url_hash
  ↓
2. Check: SELECT id, status FROM shared_content WHERE url_hash = $1
  ↓
3a. If EXISTS:
      ├─ Check duplicate: SELECT id FROM user_content_saves 
      │                    WHERE user_id=$1 AND shared_content_id=$2
      ├─ If duplicate → return existing save
      └─ Else → CREATE UserContentSave, INCREMENT shared_content.save_count
  ↓
3b. If NOT EXISTS:
      ├─ CREATE SharedContent (status=PENDING)
      ├─ CREATE UserContentSave
      ├─ Enqueue processing job: process_shared_content(shared_content_id)
      └─ Return save (content status=PENDING)
  ↓
4. Worker processes SharedContent (once for all users)
  ↓
5. All users who saved it automatically see READY status
```

**Key Insight**: User B saves the same URL after User A → instant READY if processing complete!

### Background Processing Flow (Updated)

```
Worker picks up job from SQS
  ↓
1. UPDATE shared_content SET status='PROCESSING' WHERE id=$1
  ↓
2. Fetch metadata from platform
  ↓
3. Build content_text (no user-specific data)
  ↓
4. AI analysis → topic, category, entities, locations, intent
  ↓
5. Generate embedding (format: "shared:{id}")
  ↓
6. Store embedding in vector DB
  ↓
7. UPDATE shared_content SET status='READY', title=$1, ... WHERE id=$2
  ↓
8. Trigger user-level clustering for all users who have saved this
   (or queue for next periodic run)
```

### Clustering Flow (User-Level)

```
Periodic job (nightly or after user saves 20+ items)
  ↓
1. Get all user's saves:
     SELECT ucs.id, sc.embedding_id
     FROM user_content_saves ucs
     JOIN shared_content sc ON ucs.shared_content_id = sc.id
     WHERE ucs.user_id = $1 AND sc.status = 'READY'
  ↓
2. Fetch embeddings from vector DB
  ↓
3. Run clustering (KMeans/HDBSCAN) on user's saves
  ↓
4. For each cluster:
     ├─ Create/update Cluster record
     ├─ Generate label & description (LLM)
     └─ Create ClusterMemberships (link user_save_id to cluster_id)
```

### Query Patterns

**Get user's feed (with content)**:
```sql
SELECT 
    ucs.id as save_id,
    ucs.created_at as saved_at,
    ucs.raw_share_text,
    ucs.is_favorited,
    sc.id as content_id,
    sc.title,
    sc.thumbnail_url,
    sc.category_high,
    sc.status,
    sc.save_count
FROM user_content_saves ucs
JOIN shared_content sc ON ucs.shared_content_id = sc.id
WHERE ucs.user_id = $1 
  AND sc.status = 'READY'
  AND ucs.is_archived = false
ORDER BY ucs.created_at DESC
LIMIT 20 OFFSET 0;
```

**Find similar content (global similarity)**:
```python
# 1. Get embedding for a SharedContent
embedding = vector_db.get_embedding(f"shared:{shared_content_id}")

# 2. Find similar content globally (not just user's saves)
similar = vector_db.query(
    vector=embedding,
    top_k=20,
    filter={}  # No user filter - global search
)

# 3. Check which user has already saved
similar_content_ids = [parse_embedding_id(r["id"]) for r in similar]
already_saved = db.query(UserContentSave).filter(
    UserContentSave.user_id == user_id,
    UserContentSave.shared_content_id.in_(similar_content_ids)
).all()
```

**Trending content (global)**:
```sql
-- Most saved content in last 7 days
SELECT 
    sc.id,
    sc.title,
    sc.thumbnail_url,
    sc.save_count,
    COUNT(ucs.id) as recent_saves
FROM shared_content sc
JOIN user_content_saves ucs ON sc.id = ucs.shared_content_id
WHERE ucs.created_at >= NOW() - INTERVAL '7 days'
GROUP BY sc.id
ORDER BY recent_saves DESC
LIMIT 10;
```

---

## 9. Migration from Old Design

If you have an existing `content_items` table:

```sql
-- 1. Create new tables
CREATE TABLE shared_content (...);
CREATE TABLE user_content_saves (...);

-- 2. Migrate data (deduplicate by url_hash)
INSERT INTO shared_content (url_hash, url, source_platform, ...)
SELECT DISTINCT ON (url_hash)
    url_hash, url, source_platform, ...
FROM content_items
ORDER BY url_hash, created_at ASC;  -- Keep oldest

-- 3. Create user saves
INSERT INTO user_content_saves (user_id, shared_content_id, raw_share_text, created_at)
SELECT 
    ci.user_id,
    sc.id,
    ci.raw_share_text,
    ci.created_at
FROM content_items ci
JOIN shared_content sc ON ci.url_hash = sc.url_hash;

-- 4. Update save counts
UPDATE shared_content sc
SET save_count = (
    SELECT COUNT(*) FROM user_content_saves ucs
    WHERE ucs.shared_content_id = sc.id
);

-- 5. Update cluster_memberships to point to user_save_id
-- (More complex, depends on existing data)
```

---

## 10. Summary

### New Architecture Benefits

✅ **50-90% reduction in AI costs** (process once, share across users)  
✅ **Faster save experience** (instant if content already processed)  
✅ **Viral content insights** ("1,247 users saved this")  
✅ **Global similarity search** (discover content beyond your saves)  
✅ **Trending/popular feeds** (aggregate user behavior)  
✅ **Better data quality** (consolidated metadata)  

### Core Entities (Normalized)

1. **User** - Authentication and ownership
2. **SharedContent** - Universal content metadata (processed once)
3. **UserContentSave** - User's personal save (lightweight wrapper)
4. **Cluster** - User-specific AI groupings
5. **ClusterMembership** - Links saves to clusters
6. **ProcessingJob** - Background job tracking

### Key Design Principles

- ✅ **Separation of concerns**: Content-level vs. user-level data
- ✅ **Deduplication**: Global `url_hash` prevents duplicate processing
- ✅ **Efficiency**: Process once, benefit all users
- ✅ **Scalability**: Supports viral content with millions of saves
- ✅ **User privacy**: User-specific data isolated in UserContentSave
- ✅ **Flexibility**: Easy to add user actions (favorite, archive, share)

**Next Documents**: 
- `02-api-design.md` - REST API endpoints
- `03-ai-pipelines.md` -  AI/ML components
- `04-worker-architecture.md` - SQS + Lambda workers

---

## 11. Comprehensive Example: Two Users, Multiple Saves, Clustering

This section demonstrates the complete flow with concrete data showing how SharedContent, UserContentSave, Cluster, and ClusterMembership tables interact.

### Scenario Setup

**Two Users**:
- **Alice** (id: `alice-uuid`) - Food blogger in Bangalore
- **Bob** (id: `bob-uuid`) - Tech enthusiast and fitness buff

**Timeline**: Both users save various Instagram reels and YouTube videos over a week.

---

### Step 1: Users Save Content

#### Alice's Saves (Day 1-3)

| # | URL | Platform | Alice's Note | Category |
|---|-----|----------|--------------|----------|
| 1 | `instagram.com/reel/cafe-indiranagar-1` | Instagram | "Must visit this weekend!" | Food & Drink |
| 2 | `instagram.com/reel/cafe-indiranagar-2` | Instagram | "Looks cozy" | Food & Drink |
| 3 | `youtube.com/watch/bangalo re-brunch-guide` | YouTube | "Good recommendations" | Food & Drink |
| 4 | `instagram.com/reel/goa-beaches` | Instagram | "Next vacation spot" | Travel |
| 5 | `instagram.com/reel/goa-activities` | Instagram | "Water sports!" | Travel |
| 6 | `youtube.com/watch/python-tutorial` | YouTube | "Learn decorators" | Learning |

#### Bob's Saves (Day 2-4)

| # | URL | Platform | Bob's Note | Category |
|---|-----|----------|--------------|----------|
| 1 | `instagram.com/reel/cafe-indiranagar-1` | Instagram | "Coffee looks great" | Food & Drink |
| 2 | `youtube.com/watch/hiit-workout` | YouTube | "Try this tomorrow" | Fitness |
| 3 | `youtube.com/watch/python-tutorial` | YouTube | "For work project" | Learning |
| 4 | `instagram.com/reel/reactjs-tips` | Instagram | "Bookmark" | Tech |
| 5 | `youtube.com/watch/aws-lambda-guide` | YouTube | "Deployment reference" | Tech |

**Key Observations**:
- Alice and Bob both saved `instagram.com/reel/cafe-indiranagar-1` (same content, different notes)
- Alice and Bob both saved `youtube.com/watch/python-tutorial` (same content, different purposes)
- Alice focuses on Food & Travel
- Bob focuses on Tech & Fitness

---

### Step 2: Database State After Saves

#### Table: `shared_content`

| id | url | url_hash | status | title | category_high | topic_main | save_count |
|----|-----|----------|--------|-------|---------------|------------|------------|
| `sc-1` | `instagram.com/reel/cafe-indiranagar-1` | `hash-cafe-1` | READY | "Best Cafe in Indiranagar" | Food & Drink | "Trendy cafe in Indiranagar" | **2** |
| `sc-2` | `instagram.com/reel/cafe-indiranagar-2` | `hash-cafe-2` | READY | "Hidden Cafe Gem" | Food & Drink | "Cozy cafe in Indiranagar" | 1 |
| `sc-3` | `youtube.com/watch/bangalore-brunch-guide` | `hash-brunch` | READY | "Bangalore Brunch Guide" | Food & Drink | "Best brunch spots in Bangalore" | 1 |
| `sc-4` | `instagram.com/reel/goa-beaches` | `hash-goa-beach` | READY | "Top Goa Beaches" | Travel | "Beautiful beaches in Goa" | 1 |
| `sc-5` | `instagram.com/reel/goa-activities` | `hash-goa-act` | READY | "Goa Adventure Activities" | Travel | "Water sports and activities in Goa" | 1 |
| `sc-6` | `youtube.com/watch/python-tutorial` | `hash-python` | READY | "Python Decorators Tutorial" | Learning | "Learn Python decorators" | **2** |
| `sc-7` | `youtube.com/watch/hiit-workout` | `hash-hiit` | READY | "30-Min HIIT Workout" | Fitness | "High intensity interval training" | 1 |
| `sc-8` | `instagram.com/reel/reactjs-tips` | `hash-react` | READY | "ReactJS Best Practices" | Tech | "React hooks and performance tips" | 1 |
| `sc-9` | `youtube.com/watch/aws-lambda-guide` | `hash-lambda` | READY | "AWS Lambda Tutorial" | Tech | "Deploying serverless functions" | 1 |

**Note**: `sc-1` and `sc-6` have `save_count = 2` because both Alice and Bob saved them.

#### Table: `user_content_saves`

**Alice's Saves**:

| id | user_id | shared_content_id | raw_share_text | created_at |
|----|---------|-------------------|----------------|------------|
| `save-a1` | `alice-uuid` | `sc-1` | "Must visit this weekend!" | Day 1 10:00 |
| `save-a2` | `alice-uuid` | `sc-2` | "Looks cozy" | Day 1 11:00 |
| `save-a3` | `alice-uuid` | `sc-3` | "Good recommendations" | Day 2 09:00 |
| `save-a4` | `alice-uuid` | `sc-4` | "Next vacation spot" | Day 2 14:00 |
| `save-a5` | `alice-uuid` | `sc-5` | "Water sports!" | Day 3 10:00 |
| `save-a6` | `alice-uuid` | `sc-6` | "Learn decorators" | Day 3 16:00 |

**Bob's Saves**:

| id | user_id | shared_content_id | raw_share_text | created_at |
|----|---------|-------------------|----------------|------------|
| `save-b1` | `bob-uuid` | `sc-1` | "Coffee looks great" | Day 2 12:00 |
| `save-b2` | `bob-uuid` | `sc-7` | "Try this tomorrow" | Day 2 18:00 |
| `save-b3` | `bob-uuid` | `sc-6` | "For work project" | Day 3 09:00 |
| `save-b4` | `bob-uuid` | `sc-8` | "Bookmark" | Day 3 15:00 |
| `save-b5` | `bob-uuid` | `sc-9` | "Deployment reference" | Day 4 10:00 |

**Key Insight**: Same `shared_content_id` appears in both users' saves (sc-1 and sc-6), but with different `raw_share_text` and `created_at` timestamps.

---

### Step 3: Clustering Algorithm Runs

**Trigger**: Nightly job runs on Day 4 for both users.

#### Alice's Clustering Job

**Input**:
- Fetch all Alice's saves: `save-a1` through `save-a6`
- Get embeddings for: `sc-1, sc-2, sc-3, sc-4, sc-5, sc-6`
- Total: 6 items

**Clustering Algorithm** (e.g., KMeans with k=3):

```python
# Fetch embeddings from vector DB
alice_embeddings = [
    vector_db.get("shared:sc-1"),  # Cafe 1
    vector_db.get("shared:sc-2"),  # Cafe 2
    vector_db.get("shared:sc-3"),  # Brunch guide
    vector_db.get("shared:sc-4"),  # Goa beaches
    vector_db.get("shared:sc-5"),  # Goa activities
    vector_db.get("shared:sc-6"),  # Python tutorial
]

# Run clustering
kmeans = KMeans(n_clusters=3)
labels = kmeans.fit_predict(alice_embeddings)
# Result: [0, 0, 0, 1, 1, 2]
#   Cluster 0: save-a1, save-a2, save-a3 (all food-related)
#   Cluster 1: save-a4, save-a5 (both Goa travel)
#   Cluster 2: save-a6 (learning)
```

#### 🔍 CLARIFICATION: Where Does `topic` Come From?

**Important**: The `topic` field in the clustering prompt comes from `shared_content.topic_main`, which was **already populated** when the SharedContent was first processed.

**Complete Data Flow**:

```
1. User saves URL → SharedContent created (status=PENDING)
   ↓
2. Worker processes SharedContent:
   ├─ Fetch metadata (title, caption, thumbnail)
   ├─ Build content_text (title + caption + transcript)
   ├─ AI Analysis → Extract:
   │   ├─ topic_main: "Trendy cafe in Indiranagar" ✅ STORED IN DATABASE
   │   ├─ category_high: "Food & Drink"
   │   ├─ locations: ["Indiranagar", "Bangalore"]
   │   ├─ entities: ["Cafe A", "Cafe B"]
   │   └─ intent: "visit"
   ├─ Generate embedding
   └─ UPDATE shared_content SET status='READY', topic_main=$1, ...
   ↓
3. Later: Clustering job runs for user
   ├─ Fetch user's saves (with SharedContent metadata via JOIN)
   ├─ For each cluster group:
   │   └─ Read topic_main, category_high, locations from shared_content table
   └─ Pass these attributes to LLM for cluster labeling
```

**So the flow is**:
1. **SharedContent processing** (happens once per unique URL) → AI extracts `topic_main` from content
2. **Clustering job** (happens per user) → Reads already-extracted `topic_main` from database
3. **Cluster label generation** (per cluster) → Uses `topic_main` + other fields to create label

**Example SQL During Clustering**:
```sql
-- Fetch data for items in Cluster 0
SELECT 
    sc.topic_main,
    sc.category_high,
    sc.locations,
    sc.entities
FROM user_content_saves ucs
JOIN shared_content sc ON ucs.shared_content_id = sc.id
WHERE ucs.id IN ('save-a1', 'save-a2', 'save-a3');

-- Returns:
-- topic_main: "Trendy cafe in Indiranagar"  (from sc-1)
-- topic_main: "Cozy cafe in Indiranagar"     (from sc-2)
-- topic_main: "Best brunch spots in Bangalore" (from sc-3)
```

This data is then formatted and sent to LLM for labeling.

---

**AI Label Generation**:

For each cluster, pass sample items to LLM:

**Cluster 0 Input to LLM** (using data from `shared_content` table):
```json
[
  {
    "topic": "Trendy cafe in Indiranagar",        // from shared_content.topic_main (sc-1)
    "category": "Food & Drink",                     // from shared_content.category_high (sc-1)
    "locations": ["Indiranagar"]                   // from shared_content.locations (sc-1)
  },
  {
    "topic": "Cozy cafe in Indiranagar",           // from shared_content.topic_main (sc-2)
    "category": "Food & Drink",
    "locations": ["Indiranagar"]
  },
  {
    "topic": "Best brunch spots in Bangalore",     // from shared_content.topic_main (sc-3)
    "category": "Food & Drink",
    "locations": ["Bangalore"]
  }
]
```

**LLM Prompt**:
```
You are labeling a group of user-saved content. Here are the topics and attributes 
of items in this cluster. Generate:
1. A short, descriptive label (max 5 words)
2. A cluster_type (Food, Travel, Learning, etc.)
3. A one-sentence description

Items: [JSON above]
```

**LLM Output**:
```json
{
  "label": "Indiranagar Cafe Hopping",
  "cluster_type": "Food",
  "description": "Saved content about trendy cafes and brunch spots in Bangalore."
}
```

This output is stored in the `clusters` table for Alice.

Similarly for Cluster 1 and 2...

#### Bob's Clustering Job

**Input**:
- Fetch all Bob's saves: `save-b1` through `save-b5`
- Get embeddings for: `sc-1, sc-7, sc-6, sc-8, sc-9`
- Total: 5 items

**Clustering Result**:
```
Cluster 0: save-b4, save-b5 (Tech: React, AWS)
Cluster 1: save-b2 (Fitness: HIIT)
Cluster 2: save-b1, save-b3 (Misc: Cafe + Python - doesn't cluster clearly)
```

**Note**: Bob saved `sc-1` (cafe) and `sc-6` (Python), but his clustering produces different results than Alice because:
- He has only 1 food item (not enough for a food cluster)
- His context is different (Tech + Fitness dominant)

---

### Step 4: Final Database State

#### Table: `clusters`

**Alice's Clusters**:

| id | user_id | label | cluster_type | short_description |
|----|---------|-------|--------------|-------------------|
| `cluster-a1` | `alice-uuid` | "Indiranagar Cafe Hopping" | Food | "Saved content about trendy cafes and brunch spots in Bangalore." |
| `cluster-a2` | `alice-uuid` | "Goa Vacation Planning" | Travel | "Beach destinations and adventure activities in Goa." |
| `cluster-a3` | `alice-uuid` | "Python Learning" | Learning | "Tutorials and guides for learning Python programming." |

**Bob's Clusters**:

| id | user_id | label | cluster_type | short_description |
|----|---------|-------|--------------|-------------------|
| `cluster-b1` | `bob-uuid` | "Web Development Stack" | Tech | "React development tips and AWS deployment guides." |
| `cluster-b2` | `bob-uuid` | "Fitness Routines" | Fitness | "High-intensity workout videos for daily exercise." |
| `cluster-b3` | `bob-uuid` | "Miscellaneous Saves" | Misc | "Various saved content including cafes and tutorials." |

#### Table: `cluster_memberships`

**Alice's Cluster Memberships**:

| cluster_id | user_save_id | → Which Cluster | → Which Save |
|------------|--------------|-----------------|--------------|
| `cluster-a1` | `save-a1` | "Indiranagar Cafe Hopping" | Cafe 1 |
| `cluster-a1` | `save-a2` | "Indiranagar Cafe Hopping" | Cafe 2 |
| `cluster-a1` | `save-a3` | "Indiranagar Cafe Hopping" | Brunch guide |
| `cluster-a2` | `save-a4` | "Goa Vacation Planning" | Goa beaches |
| `cluster-a2` | `save-a5` | "Goa Vacation Planning" | Goa activities |
| `cluster-a3` | `save-a6` | "Python Learning" | Python tutorial |

**Bob's Cluster Memberships**:

| cluster_id | user_save_id | → Which Cluster | → Which Save |
|------------|--------------|-----------------|--------------|
| `cluster-b1` | `save-b4` | "Web Development Stack" | ReactJS tips |
| `cluster-b1` | `save-b5` | "Web Development Stack" | AWS Lambda guide |
| `cluster-b2` | `save-b2` | "Fitness Routines" | HIIT workout |
| `cluster-b3` | `save-b1` | "Miscellaneous Saves" | Cafe 1 |
| `cluster-b3` | `save-b3` | "Miscellaneous Saves" | Python tutorial |

---

### 🔍 DEEP DIVE: How ClusterMembership Actually Works

**ClusterMembership is a junction table** that creates the many-to-many relationship between Clusters and UserContentSaves. Let's break this down step-by-step.

#### The Problem It Solves

**Without ClusterMembership**:
- How do we know which saves belong to which cluster?
- How do we query "show all items in this cluster"?
- How do we allow a save to potentially belong to multiple clusters in the future?

**Solution**: A junction table that stores pairs of `(cluster_id, user_save_id)`.

---

#### Step-by-Step: Creating ClusterMemberships

Let's trace through Alice's first cluster: "Indiranagar Cafe Hopping"

**1. Clustering Algorithm Determines Groups**
```python
# KMeans result for Alice
labels = [0, 0, 0, 1, 1, 2]
# save-a1, save-a2, save-a3 → label 0  (Food group)
# save-a4, save-a5 → label 1            (Travel group)
# save-a6 → label 2                     (Learning group)
```

**2. Create Cluster Record**
```sql
INSERT INTO clusters (id, user_id, label, cluster_type, short_description)
VALUES (
    'cluster-a1',  -- UUID generated
    'alice-uuid',
    'Indiranagar Cafe Hopping',
    'Food',
    'Saved content about trendy cafes and brunch spots in Bangalore.'
);
```

**3. Create ClusterMembership Records**

Now we need to **link** the three saves (`save-a1`, `save-a2`, `save-a3`) to this new cluster:

```sql
-- For save-a1 (Cafe 1)
INSERT INTO cluster_memberships (cluster_id, user_save_id)
VALUES ('cluster-a1', 'save-a1');

-- For save-a2 (Cafe 2)
INSERT INTO cluster_memberships (cluster_id, user_save_id)
VALUES ('cluster-a1', 'save-a2');

-- For save-a3 (Brunch guide)
INSERT INTO cluster_memberships (cluster_id, user_save_id)
VALUES ('cluster-a1', 'save-a3');
```

**Result**: 3 rows in `cluster_memberships` table linking `cluster-a1` to three UserContentSaves.

---

#### What Each ClusterMembership Row Represents

Let's look at one specific row:

```
cluster_id: cluster-a1
user_save_id: save-a1
```

**This row says**:
- The cluster `cluster-a1` ("Indiranagar Cafe Hopping")...
- Contains the save `save-a1` (Alice's save of the cafe reel)

**Trace the complete relationship chain**:
```
cluster_memberships row
  ├─ cluster_id: cluster-a1
  │   └─→ clusters table
  │       ├─ user_id: alice-uuid
  │       ├─ label: "Indiranagar Cafe Hopping"
  │       └─ cluster_type: Food
  │
  └─ user_save_id: save-a1
      └─→ user_content_saves table
          ├─ user_id: alice-uuid
          ├─ shared_content_id: sc-1
          ├─ raw_share_text: "Must visit this weekend!"
          └─→ shared_content table
              ├─ title: "Best Cafe in Indiranagar"
              ├─ topic_main: "Trendy cafe in Indiranagar"
              └─ category_high: "Food & Drink"
```

**So when you query cluster-a1's items, you**:
1. Find rows in `cluster_memberships` where `cluster_id = 'cluster-a1'`
2. Get the `user_save_id` values → `['save-a1', 'save-a2', 'save-a3']`
3. JOIN to `user_content_saves` to get user-specific data (notes, timestamps)
4. JOIN to `shared_content` to get content metadata (title, thumbnail, topic)

---

#### Why Link to UserContentSave Instead of SharedContent?

**Critical Design Decision**: ClusterMembership has `user_save_id`, NOT `shared_content_id`.

**Why?**

Let's see what would happen if we linked directly to SharedContent:

**❌ BAD: If we linked to SharedContent**:
```
cluster_memberships:
  cluster_id: cluster-a1
  shared_content_id: sc-1  ← Links directly to content
```

**Problem**: `sc-1` is saved by both Alice AND Bob!
- Alice's cluster-a1: "Indiranagar Cafe Hopping"
- Bob's cluster-b3: "Miscellaneous Saves"

If ClusterMembership linked to `sc-1`, which cluster does it belong to?
- **Can't distinguish** between Alice's save and Bob's save
- **Can't have different clusters** for different users
- **Can't track when each user saved it**
- **Loses user context** (personal notes, timestamps)

**✅ GOOD: Linking to UserContentSave**:
```
cluster_memberships:
  cluster_id: cluster-a1
  user_save_id: save-a1  ← Links to Alice's specific save
```

Now:
- Alice's `save-a1` → `cluster-a1` ("Indiranagar Cafe Hopping")
- Bob's `save-b1` → `cluster-b3` ("Miscellaneous Saves")
- **Same content (`sc-1`), different user saves, different clusters!**

---

#### Visual Diagram: The Complete Linkage

```
Alice saves cafe reel:

  User                  UserContentSave           SharedContent
┌──────────┐          ┌───────────────┐         ┌─────────────┐
│ alice-   │ ←──┐     │ save-a1       │ ───────→│ sc-1        │
│ uuid     │    │     │               │         │ (Cafe reel) │
└──────────┘    │     │ user_id:      │    ┌───→│             │
                │     │  alice-uuid   │    │    │ title: "Best│
                │     │               │    │    │  Cafe..."   │
                │     │ shared_       │    │    │ topic_main: │
                │     │ content_id:───┼────┘    │  "Trendy    │
                │     │  sc-1         │         │   cafe..."  │
                │     │               │         └─────────────┘
                │     │ raw_share_    │
                │     │ text: "Must   │
                │     │  visit!"      │
                │     └───────┬───────┘
                │             │
                │             ↑ Links here (NOT to sc-1)
                │             │
  Cluster       │    ClusterMembership
┌──────────┐    │    ┌───────────────┐
│ cluster- │    │    │ cluster_id: ──┼───┐
│ a1       │←───┼────┼─ cluster-a1   │   │
│          │    │    │               │   │
│ user_id: │    │    │ user_save_id: │   │
│  alice-  │────┘    │  save-a1 ─────┼───┘
│  uuid    │         └───────────────┘
│          │
│ label:   │
│  "Indi-  │
│  ranagar │
│  Cafe    │
│  Hopping"│
└──────────┘


Key: ClusterMembership creates the link between:
  - cluster-a1 (the thematic group)
  - save-a1 (Alice's specific save)
```

---

#### Practical SQL Queries Using ClusterMembership

**Query 1: Get all clusters for Alice**
```sql
SELECT 
    c.id,
    c.label,
    c.cluster_type,
    COUNT(cm.user_save_id) as item_count
FROM clusters c
LEFT JOIN cluster_memberships cm ON c.id = cm.cluster_id
WHERE c.user_id = 'alice-uuid'
GROUP BY c.id;
```

**How it works**:
- Finds Alice's clusters in `clusters` table
- JOINs to `cluster_memberships` to count how many saves in each
- Returns cluster metadata + count

---

**Query 2: Get all items in "Indiranagar Cafe Hopping" cluster**
```sql
SELECT 
    sc.title,
    sc.thumbnail_url,
    ucs.raw_share_text,
    ucs.created_at as saved_at
FROM cluster_memberships cm
JOIN user_content_saves ucs ON cm.user_save_id = ucs.id
JOIN shared_content sc ON ucs.shared_content_id = sc.id
WHERE cm.cluster_id = 'cluster-a1'
ORDER BY ucs.created_at ASC;
```

**Step-by-step**:
1. Start with `cluster_memberships` rows where `cluster_id = 'cluster-a1'`
   - Finds 3 rows: `(cluster-a1, save-a1)`, `(cluster-a1, save-a2)`, `(cluster-a1, save-a3)`
2. JOIN to `user_content_saves` using `user_save_id`
   - Gets Alice's notes, timestamps for each save
3. JOIN to `shared_content` using `shared_content_id`
   - Gets title, thumbnail, topic, etc. for each piece of content
4. Returns combined data for all 3 items in cluster

---

**Query 3: Check if a specific save is in a cluster**
```sql
SELECT 
    c.label,
    c.cluster_type
FROM cluster_memberships cm
JOIN clusters c ON cm.cluster_id = c.id
WHERE cm.user_save_id = 'save-a1';
```

**Result**: 
```
label: "Indiranagar Cafe Hopping"
cluster_type: "Food"
```

---

#### Database Operations During Clustering

**Full pseudo-code for creating clusters + memberships**:

```python
def create_clusters_for_user(user_id, clustering_results):
    """
    clustering_results = {
        0: ['save-a1', 'save-a2', 'save-a3'],  # Food cluster
        1: ['save-a4', 'save-a5'],             # Travel cluster
        2: ['save-a6']                         # Learning cluster
    }
    """
    
    for label_id, save_ids in clustering_results.items():
        # 1. Fetch metadata for items in this cluster
        items_metadata = db.query("""
            SELECT 
                sc.topic_main,
                sc.category_high,
                sc.locations,
                sc.entities
            FROM user_content_saves ucs
            JOIN shared_content sc ON ucs.shared_content_id = sc.id
            WHERE ucs.id = ANY($1)
        """, [save_ids])
        
        # 2. Generate cluster label using LLM
        cluster_label = generate_cluster_label(items_metadata)
        # Returns: {
        #   "label": "Indiranagar Cafe Hopping",
        #   "cluster_type": "Food",
        #   "description": "Saved content about..."
        # }
        
        # 3. Insert cluster record
        cluster_id = db.execute("""
            INSERT INTO clusters (user_id, label, cluster_type, short_description)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, [
            user_id,
            cluster_label['label'],
            cluster_label['cluster_type'],
            cluster_label['description']
        ])
        
        # 4. Insert cluster memberships (the junction rows)
        for save_id in save_ids:
            db.execute("""
                INSERT INTO cluster_memberships (cluster_id, user_save_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING  -- Prevents duplicate inserts
            """, [cluster_id, save_id])
    
    return "Clustering complete"
```

---

#### MVP Constraint vs. Schema Flexibility

**MVP**: Each save belongs to **at most 1 cluster**
- Enforced at application level (not database level)
- When creating new cluster memberships, delete old ones first:
  ```sql
  -- Remove old membership
  DELETE FROM cluster_memberships 
  WHERE user_save_id = 'save-a1';
  
  -- Create new membership
  INSERT INTO cluster_memberships (cluster_id, user_save_id)
  VALUES ('cluster-a1', 'save-a1');
  ```

**Future**: Schema already supports **multi-cluster memberships**
- Same save could belong to multiple clusters
- Just insert multiple rows:
  ```sql
  INSERT INTO cluster_memberships VALUES ('cluster-food-1', 'save-a1');
  INSERT INTO cluster_memberships VALUES ('cluster-bangalore-1', 'save-a1');
  ```
- Composite primary key `(cluster_id, user_save_id)` prevents duplicates

---

### Summary: ClusterMembership Explained

**What it is**: A junction table linking Clusters to UserContentSaves

**Why it exists**: Enables many-to-many relationships between clusters and saves

**Key fields**:
- `cluster_id` (foreign key to clusters) - Which cluster
- `user_save_id` (foreign key to user_content_saves) - Which save
- Composite primary key prevents duplicates

**Why link to UserContentSave**: 
- ✅ User-specific clustering (same content, different clusters for different users)
- ✅ Preserves user context (notes, timestamps)
- ✅ Allows personalization

**Why NOT link to SharedContent**:
- ❌ Would lose user context
- ❌ Can't have different clusters for different users
- ❌ Global content doesn't know about individual user perspectives

**Operations**:
- INSERT: Create membership when clustering assigns save to cluster
- DELETE: Remove membership when save deleted or re-clustered
- SELECT: Query to find all items in cluster or which cluster a save belongs to

---

### Step 5: Key Insights from This Example

#### 1. **Same SharedContent, Different Clusters**

`sc-1` (Cafe in Indiranagar):
- **Alice**: `save-a1` → `cluster-a1` ("Indiranagar Cafe Hopping")
- **Bob**: `save-b1` → `cluster-b3` ("Miscellaneous Saves")

**Why Different?**
- Alice has 3 food items → strong "Food" cluster
- Bob has only 1 food item → goes to "Misc" cluster
- **Clustering is context-dependent per user**

#### 2. **Same SharedContent, Different User Intent**

`sc-6` (Python Tutorial):
- **Alice's Note**: "Learn decorators" → Personal learning
- **Bob's Note**: "For work project" → Professional need
- Both notes stored in `user_content_saves.raw_share_text`
- Same content, different personal context

#### 3. **ClusterMembership Links UserContentSave, NOT SharedContent**

This is critical:
- `cluster_memberships` has `user_save_id` (not `shared_content_id`)
- Ensures clustering is **user-specific**
- Same content can be in completely different clusters for different users

#### 4. **Cluster Types Are High-Level Labels**

`cluster_type` enum values:
- Food, Travel, Learning, Fitness, Entertainment, Shopping, Tech, Misc

**Question**: Could there be more subcategories?

**Answer**: 
- `cluster_type` is intentionally **broad** (8-9 values only)
- **Fine-grained categorization** happens via:
  - `cluster.label` (AI-generated, unlimited possibilities)
  - `shared_content.subcategories` (JSONB array, flexible)
  - `cluster.short_description` (detailed text)

**Example**:
- `cluster_type` = "Food" (broad)
- `label` = "Indiranagar Cafe Hopping" (specific)
- `short_description` = "Trendy cafes and brunch spots in Bangalore" (detailed)

So **NO**, you don't add more values to the `cluster_type` enum. The granularity comes from the AI-generated fields.

---

### Step 6: Querying Clusters (API Usage)

#### Alice Requests: "Show My Clusters"

**Query**:
```sql
SELECT 
    c.id,
    c.label,
    c.cluster_type,
    c.short_description,
    COUNT(cm.user_save_id) as item_count
FROM clusters c
LEFT JOIN cluster_memberships cm ON c.id = cm.cluster_id
WHERE c.user_id = 'alice-uuid'
GROUP BY c.id
ORDER BY c.created_at DESC;
```

**Result**:
```json
[
  {
    "id": "cluster-a1",
    "label": "Indiranagar Cafe Hopping",
    "cluster_type": "Food",
    "short_description": "Saved content about trendy cafes and brunch spots in Bangalore.",
    "item_count": 3
  },
  {
    "id": "cluster-a2",
    "label": "Goa Vacation Planning",
    "cluster_type": "Travel",
    "short_description": "Beach destinations and adventure activities in Goa.",
    "item_count": 2
  },
  {
    "id": "cluster-a3",
    "label": "Python Learning",
    "cluster_type": "Learning",
    "short_description": "Tutorials and guides for learning Python programming.",
    "item_count": 1
  }
]
```

#### Alice Requests: "Show Items in 'Indiranagar Cafe Hopping' Cluster"

**Query**:
```sql
SELECT 
    ucs.id as save_id,
    ucs.raw_share_text,
    ucs.created_at as saved_at,
    sc.title,
    sc.thumbnail_url,
    sc.url,
    sc.category_high,
    sc.topic_main
FROM cluster_memberships cm
JOIN user_content_saves ucs ON cm.user_save_id = ucs.id
JOIN shared_content sc ON ucs.shared_content_id = sc.id
WHERE cm.cluster_id = 'cluster-a1'
ORDER BY ucs.created_at ASC;
```

**Result**:
```json
[
  {
    "save_id": "save-a1",
    "raw_share_text": "Must visit this weekend!",
    "saved_at": "Day 1 10:00",
    "title": "Best Cafe in Indiranagar",
    "url": "instagram.com/reel/cafe-indiranagar-1",
    "category_high": "Food & Drink",
    "topic_main": "Trendy cafe in Indiranagar"
  },
  {
    "save_id": "save-a2",
    "raw_share_text": "Looks cozy",
    "saved_at": "Day 1 11:00",
    "title": "Hidden Cafe Gem",
    "url": "instagram.com/reel/cafe-indiranagar-2",
    "category_high": "Food & Drink",
    "topic_main": "Cozy cafe in Indiranagar"
  },
  {
    "save_id": "save-a3",
    "raw_share_text": "Good recommendations",
    "saved_at": "Day 2 09:00",
    "title": "Bangalore Brunch Guide",
    "url": "youtube.com/watch/bangalore-brunch-guide",
    "category_high": "Food & Drink",
    "topic_main": "Best brunch spots in Bangalore"
  }
]
```

**Notice**:
- Alice's personal notes (`raw_share_text`) shown
- Items sorted by when **Alice saved them** (`ucs.created_at`)
- All metadata from SharedContent available

---

### Step 7: Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Alice saves "instagram.com/reel/cafe-indiranagar-1"   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Check url_hash in    │
              │ shared_content       │
              └──────────┬───────────┘
                         │
                ┌────────┴────────┐
                │                 │
         Not Found           Found (by Bob earlier)
                │                 │
                ▼                 ▼
     ┌──────────────────┐   ┌──────────────────┐
     │ CREATE           │   │ REUSE existing   │
     │ shared_content   │   │ shared_content   │
     │ sc-1             │   │ sc-1             │
     │ save_count = 1   │   │ save_count = 2   │
     └────────┬─────────┘   └────────┬─────────┘
              │                      │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ CREATE               │
              │ user_content_save    │
              │ save-a1              │
              │ - user_id: alice     │
              │ - shared_content: sc-1│
              │ - note: "Must visit!"│
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Later: Clustering    │
              │ job runs             │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ CREATE               │
              │ cluster_membership   │
              │ - cluster: a1        │
              │ - user_save: save-a1 │
              └──────────────────────┘
```

---

### Step 8: Advanced Scenario - Cluster Re-computation

**Day 7**: Alice saves 10 more food-related items in different areas of Bangalore.

**Clustering Job Runs Again**:

**New Clustering Result**:
```
Old Cluster: "Indiranagar Cafe Hopping" (3 items)
  ↓
Split into Two Clusters:
  - "Indiranagar Cafes" (3 items - Indiranagar specific)
  - "Bangalore Brunch Spots" (7 items - other areas)
```

**What Happens**:

1. **Old cluster `cluster-a1` updated**:
   - Label changed to "Indiranagar Cafes"
   - Description updated
   - Memberships reduced (only Indiranagar items)

2. **New cluster created**:
   - `cluster-a4`: "Bangalore Brunch Spots"
   - Contains items from other areas

3. **cluster_memberships updated**:
   ```sql
   -- Remove old memberships for items moving to new cluster
   DELETE FROM cluster_memberships 
   WHERE user_save_id IN (save-a3, save-a7, save-a8, ...)
   AND cluster_id = 'cluster-a1';
   
   -- Create new memberships in new cluster
   INSERT INTO cluster_memberships (cluster_id, user_save_id)
   VALUES ('cluster-a4', 'save-a3'),
          ('cluster-a4', 'save-a7'),
          ...;
   ```

**Result**: Clusters **evolve** as user saves more content. AI continuously refines groupings.

---

### Step 9: Cross-User Insights (Bonus)

**Question**: "What other users saved the same content as Alice?"

**Query**:
```sql
-- Find users who saved same content as Alice
SELECT 
    u.email,
    sc.title,
    ucs.raw_share_text,
    ucs.created_at
FROM user_content_saves ucs_alice
JOIN shared_content sc ON ucs_alice.shared_content_id = sc.id
JOIN user_content_saves ucs ON sc.id = ucs.shared_content_id
JOIN users u ON ucs.user_id = u.id
WHERE ucs_alice.user_id = 'alice-uuid'
  AND ucs.user_id != 'alice-uuid'  -- exclude Alice herself
ORDER BY sc.save_count DESC, ucs.created_at DESC
LIMIT 20;
```

**Result**:
```
Bob saved "Best Cafe in Indiranagar" on Day 2 with note "Coffee looks great"
Bob saved "Python Decorators Tutorial" on Day 3  with note "For work project"
```

**Use Case**: "You and Bob both saved this" social feature!

---

## Summary of Cluster & ClusterMembership Workings

### Cluster Entity
- **One cluster = one thematic group** (e.g., "Indiranagar Cafes")
- **User-specific**: Alice and Bob have completely different clusters
- **AI-generated**: Label and description created by LLM
- **cluster_type**: High-level category (Food, Travel, Tech, etc.) - **limited to 8-9 values**
- **Granularity**: Comes from `label` and `description`, NOT more enum values

### ClusterMembership Entity
- **Links UserContentSave (not SharedContent)** → User-specific clustering
- **Composite primary key**: (cluster_id, user_save_id) → prevents duplicates
- **Flexible**: MVP enforces 1 cluster per save, schema supports many-to-many
- **Cascading deletes**: Delete save → membership deleted automatically

### Key Takeaway
**Same SharedContent can belong to different clusters for different users** because ClusterMembership links to UserContentSave (user-specific), not SharedContent (global). This enables personalized, context-aware groupings for each user!
