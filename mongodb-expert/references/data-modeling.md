# Data Modeling

## Table of Contents
1. Core Principles
2. Embedding vs. Referencing
3. Schema Design Patterns
4. Index Strategy
5. Schema Validation
6. Anti-Patterns

## 1. Core Principles

MongoDB data modeling is driven by **how the application accesses data**, not by how data relates logically.

Three questions that drive every schema decision:

1. **What queries does this application run?** — Model for the read pattern.
2. **What is the read/write ratio?** — Heavy reads → denormalize. Heavy writes → normalize.
3. **How does this data grow?** — Unbounded arrays are dangerous. Growing documents degrade performance.

## 2. Embedding vs. Referencing

### When to Embed (Denormalize)

| Signal | Example |
|--------|---------|
| 1:1 relationship | User ↔ Profile |
| 1:few relationship | Blog post ↔ Comments (if bounded) |
| Data always accessed together | Order ↔ Line items |
| Data owned by parent | Address inside User |

Embedding advantages:
- Single read operation (no `$lookup`)
- Atomic writes (single document = single transaction)
- Better read performance (data locality)

### When to Reference (Normalize)

| Signal | Example |
|--------|---------|
| 1:many (unbounded) | Author ↔ Blog posts |
| Many:many | Students ↔ Courses |
| Data accessed independently | User ↔ Audit log |
| Frequent updates to child | Product ↔ Inventory |
| Document size approaching 16MB | Any with large nested arrays |

Referencing advantages:
- Smaller documents (better cache utilization)
- No unbounded growth risk
- Independent updates without rewriting parent

### Decision Framework

Ask: Will this embedded array grow without bound?
- YES → Reference. Unbounded arrays are the #1 MongoDB anti-pattern.
- NO, bounded to < ~100 items → Embedding is likely fine.
- NO, bounded to < ~1000 items → Consider embedding with array size monitoring.

Ask: Is the embedded data frequently updated independently of the parent?
- YES → Reference (avoids rewriting the entire parent document on every update).
- NO → Embedding is fine.

Ask: Is the embedded data > 50% of the document size and rarely accessed?
- YES → Reference (don't load unnecessary data on every read).
- NO → Embedding is fine.

## 3. Schema Design Patterns

### Attribute Pattern

Use when: Documents have many similar fields with similar access patterns.

```javascript
// Instead of:
{ height: 10, width: 20, depth: 5, weight: 100, color: "red" }

// Use:
{ attributes: [
  { k: "height", v: 10, u: "cm" },
  { k: "width",  v: 20, u: "cm" },
  { k: "depth",  v: 5,  u: "cm" },
  { k: "weight", v: 100, u: "kg" }
]}
// Advantage: single index on attributes.k + attributes.v covers all attribute queries
```

### Bucket Pattern

Use when: High-volume time-series-like data (if not using native TimeSeries collections).

```javascript
{
  sensorId: "A1",
  date: ISODate("2026-04-13"),
  measurements: [
    { ts: ISODate("2026-04-13T00:01:00"), value: 42 },
    { ts: ISODate("2026-04-13T00:02:00"), value: 43 },
    // ... bounded by time window
  ],
  count: 2
}
```

**Note**: For MongoDB 5.0+, prefer native TimeSeries collections. See `references/timeseries.md`.

### Computed Pattern

Use when: Expensive computations that don't need real-time accuracy.

```javascript
{
  productId: "P1",
  totalReviews: 1542,       // Pre-computed
  avgRating: 4.3,           // Pre-computed
  lastComputed: ISODate()   // Track staleness
}
// Updated periodically or on write using $inc
```

### Extended Reference Pattern

Use when: You need some fields from a referenced document without a `$lookup`.

```javascript
// Order document with extended reference to customer
{
  orderId: "O1",
  customer: {
    _id: ObjectId("..."),  // Reference for full lookup
    name: "João",          // Cached for display
    email: "j@email.com"   // Cached for notifications
  },
  items: [...]
}
// Trade-off: duplicated data needs eventual consistency strategy
```

### Subset Pattern

Use when: Documents are large but queries typically need only a subset.

```javascript
// Full review in "reviews" collection
{ _id: 1, productId: "P1", text: "Great product...", rating: 5, ... }

// Product document with only the top 10 reviews embedded
{ 
  productId: "P1",
  topReviews: [ /* only top 10 */ ],
  totalReviews: 1542
}
```

### Outlier Pattern

Use when: Most documents are small but a few are huge (e.g., a post with 10K comments).

```javascript
// Normal document
{ postId: 1, comments: [...], hasOverflow: false }

// Outlier — overflow to separate collection
{ postId: 2, comments: [/* first 100 */], hasOverflow: true }
// Overflow in: post_comments_overflow collection
```

## 4. Index Strategy

### Index Types

| Type | Use Case | Example |
|------|----------|---------|
| Single field | Filter/sort on one field | `{email: 1}` |
| Compound | Filter/sort on multiple fields | `{status: 1, createdAt: -1}` |
| Multikey | Array fields | `{tags: 1}` (auto-detected) |
| Text | Full-text search | `{description: "text"}` |
| 2dsphere | Geospatial | `{location: "2dsphere"}` |
| Hashed | Hash-based sharding | `{userId: "hashed"}` |
| Wildcard | Dynamic/unknown field paths | `{"attributes.$**": 1}` |

### ESR Rule (Equality, Sort, Range)

For compound indexes, order fields as:
1. **Equality** fields first (`status: "active"`)
2. **Sort** fields second (`createdAt: -1`)
3. **Range** fields last (`age: { $gte: 18 }`)

```javascript
// Query: find active users, sorted by creation date, age > 18
// Index: { status: 1, createdAt: -1, age: 1 }
//         Equality    Sort           Range
```

### Covered Queries

A query is "covered" when ALL fields in the query AND projection are in the index. The query never touches the document — only the index.

```javascript
// Index: { email: 1, name: 1 }
// Covered query (no document fetch):
db.users.find({ email: "x@y.com" }, { name: 1, _id: 0 })
```

### Index Analysis

```javascript
// Check if query uses index
db.collection.find({...}).explain("executionStats")

// Key fields in explain:
// - winningPlan.stage: "IXSCAN" (good) vs "COLLSCAN" (bad)
// - executionStats.totalDocsExamined vs totalKeysExamined
// - executionStats.executionTimeMillis
```

## 5. Schema Validation

```javascript
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "email", "status"],
      properties: {
        name: { bsonType: "string", description: "must be a string" },
        email: { bsonType: "string", pattern: "^.+@.+$" },
        status: { enum: ["active", "inactive", "banned"] },
        age: { bsonType: "int", minimum: 0, maximum: 200 }
      }
    }
  },
  validationLevel: "strict",    // "strict" (all docs) or "moderate" (only inserts and updates to valid docs)
  validationAction: "error"     // "error" (reject) or "warn" (log only)
})
```

### Changing Validation After Creation

```javascript
db.runCommand({
  collMod: "users",
  validator: { /* new schema */ },
  validationLevel: "moderate"   // Use moderate during migration
})
```

## 6. Anti-Patterns

### Unbounded Arrays
- **Problem**: Array grows without limit → document exceeds 16MB, performance degrades
- **Fix**: Use referencing or bucket pattern with bounded size

### Massive Documents
- **Problem**: Documents approaching 16MB → high memory usage, slow reads
- **Fix**: Subset pattern, referencing, or split into multiple collections

### Over-Indexing
- **Problem**: Too many indexes → slow writes, high memory usage
- **Fix**: Each index adds overhead on every write. Only index fields used in queries.
- **Check**: `db.collection.getIndexes()` — remove unused indexes

### COLLSCAN in Production
- **Problem**: Query scanning entire collection without index
- **Fix**: Create appropriate index. Check with `explain()`.

### Using $lookup as a Join Substitute
- **Problem**: Treating MongoDB like a relational DB with frequent `$lookup`s
- **Fix**: If you need `$lookup` frequently, the schema should embed the data instead

### Storing Large Binary in Documents
- **Problem**: Large files (images, videos) as BSON binary inside documents
- **Fix**: Use GridFS for files > 256KB, or external object storage with reference
