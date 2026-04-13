# Aggregation Pipeline Patterns

## Table of Contents
1. Pipeline Fundamentals
2. Optimization Rules
3. Common Patterns
4. Performance Considerations
5. Anti-Patterns

## 1. Pipeline Fundamentals

The aggregation pipeline processes documents through stages. Each stage transforms the document stream.

### Stage Execution Order Matters

```javascript
// BAD: $sort before $match processes ALL documents
[
  { $sort: { createdAt: -1 } },    // Sorts entire collection
  { $match: { status: "active" } }  // Then filters
]

// GOOD: $match first reduces the working set
[
  { $match: { status: "active" } },  // Filters first
  { $sort: { createdAt: -1 } }       // Sorts only matching docs
]
```

### Most-Used Stages

| Stage | Purpose | Tip |
|-------|---------|-----|
| `$match` | Filter documents | Put as early as possible. Uses indexes when first. |
| `$project` / `$addFields` | Shape documents | Remove unneeded fields early to reduce memory |
| `$group` | Aggregate by key | Accumulator operators: `$sum`, `$avg`, `$max`, `$min`, `$push`, `$first` |
| `$sort` | Order results | Uses index if matches an index. 100MB memory limit without `allowDiskUse`. |
| `$lookup` | Left outer join | Expensive on large collections. Consider embedding instead. |
| `$unwind` | Flatten arrays | Increases document count. Use `preserveNullAndEmptyArrays` when needed. |
| `$limit` / `$skip` | Pagination | Put after `$sort`. `$skip` for large offsets is slow — use range-based pagination instead. |
| `$facet` | Multiple pipelines in parallel | Each sub-pipeline gets the same input. Memory limit applies to total. |
| `$merge` / `$out` | Write results | `$merge` (upsert behavior), `$out` (replace collection). Must be last stage. |

## 2. Optimization Rules

### MongoDB's Automatic Optimizations (VERIFY for target version)

MongoDB automatically:
1. **`$match` + `$match` coalescence**: Adjacent `$match` stages merged with `$and`
2. **`$sort` + `$limit` coalescence**: Combined into a top-N sort (memory-efficient)
3. **`$match` before `$project`**: If `$match` only uses fields not modified by `$project`, MongoDB moves `$match` first
4. **`$match` after `$lookup`**: MongoDB may move part of a `$match` before `$lookup`

### Manual Optimization Principles

1. **Filter early**: `$match` as first stage to use indexes and reduce pipeline input
2. **Project early**: Remove unneeded fields to reduce memory per document
3. **Limit early**: If you only need N results, `$limit` after `$sort` (auto-optimized)
4. **Avoid `$unwind` on large arrays**: Each array element becomes a separate document
5. **Use `$group` with accumulators instead of `$unwind` + `$group`** when possible

## 3. Common Patterns

### Time-Based Aggregation

```javascript
// Hourly aggregation
db.events.aggregate([
  { $match: { 
    timestamp: { $gte: ISODate("2026-04-01"), $lt: ISODate("2026-04-13") }
  }},
  { $group: {
    _id: { $dateTrunc: { date: "$timestamp", unit: "hour" } },
    count: { $sum: 1 },
    avgValue: { $avg: "$value" }
  }},
  { $sort: { _id: 1 } }
])
```

### Top-N per Group

```javascript
// Top 3 products per category by sales
db.products.aggregate([
  { $sort: { sales: -1 } },
  { $group: {
    _id: "$category",
    topProducts: { $push: { name: "$name", sales: "$sales" } }
  }},
  { $project: {
    topProducts: { $slice: ["$topProducts", 3] }
  }}
])

// MongoDB 5.2+: More efficient with $topN accumulator (VERIFY)
db.products.aggregate([
  { $group: {
    _id: "$category",
    topProducts: { 
      $topN: { n: 3, sortBy: { sales: -1 }, output: { name: "$name", sales: "$sales" } }
    }
  }}
])
```

### Lookup with Pipeline (Correlated Subquery)

```javascript
db.orders.aggregate([
  { $lookup: {
    from: "inventory",
    let: { productId: "$productId", minQty: "$minQuantity" },
    pipeline: [
      { $match: { 
        $expr: { 
          $and: [
            { $eq: ["$productId", "$$productId"] },
            { $gte: ["$quantity", "$$minQty"] }
          ]
        }
      }},
      { $project: { quantity: 1, warehouse: 1 } }
    ],
    as: "stockInfo"
  }}
])
```

### Running Totals / Window Functions (MongoDB 5.0+)

```javascript
db.sales.aggregate([
  { $setWindowFields: {
    partitionBy: "$region",
    sortBy: { date: 1 },
    output: {
      runningTotal: {
        $sum: "$amount",
        window: { documents: ["unbounded", "current"] }
      },
      movingAvg: {
        $avg: "$amount",
        window: { documents: [-6, 0] }  // 7-day moving average
      }
    }
  }}
])
```

### Pagination (Range-Based, NOT skip-based)

```javascript
// First page
db.collection.find({ status: "active" })
  .sort({ _id: 1 })
  .limit(20)

// Next page (use last _id from previous page)
db.collection.find({ status: "active", _id: { $gt: lastId } })
  .sort({ _id: 1 })
  .limit(20)

// In aggregation:
{ $match: { status: "active", _id: { $gt: lastId } } },
{ $sort: { _id: 1 } },
{ $limit: 20 }
```

### Faceted Search

```javascript
db.products.aggregate([
  { $match: { $text: { $search: "laptop" } } },
  { $facet: {
    results: [
      { $sort: { score: { $meta: "textScore" } } },
      { $skip: 0 },
      { $limit: 10 }
    ],
    totalCount: [
      { $count: "count" }
    ],
    byCategory: [
      { $group: { _id: "$category", count: { $sum: 1 } } }
    ],
    priceRange: [
      { $group: {
        _id: null,
        min: { $min: "$price" },
        max: { $max: "$price" },
        avg: { $avg: "$price" }
      }}
    ]
  }}
])
```

## 4. Performance Considerations

### Memory Limits

- Default: 100MB per pipeline stage
- `allowDiskUse: true`: Spills to disk when exceeded (slower)
- `$group`, `$sort`, `$bucket` are the main memory consumers

### Index Usage

Only the FIRST `$match` stage can use indexes. Subsequent `$match` stages filter in-memory.

```javascript
// Index used ✓
[{ $match: { status: "active" } }, { $group: ... }]

// No index for second $match ✗
[{ $group: ... }, { $match: { total: { $gt: 100 } } }]
```

### $lookup Performance

Ask: How large is the `from` collection?
- Large (>1M docs) with no index on the join field → VERY slow
- Always ensure an index exists on the `from` collection's join field

```javascript
// Ensure index on inventory.productId before this lookup
db.orders.aggregate([
  { $lookup: { from: "inventory", localField: "productId", foreignField: "productId", as: "stock" } }
])
```

### Explain for Aggregation

```javascript
db.collection.explain("executionStats").aggregate([...])
```

## 5. Anti-Patterns

### $unwind + $group to Count Array Elements
```javascript
// BAD: Unwinds entire array just to count
[{ $unwind: "$tags" }, { $group: { _id: "$_id", tagCount: { $sum: 1 } } }]

// GOOD: Use $size
[{ $project: { tagCount: { $size: "$tags" } } }]
```

### Using $skip for Deep Pagination
```javascript
// BAD: $skip(10000) still reads 10000 documents
[{ $sort: { createdAt: -1 } }, { $skip: 10000 }, { $limit: 20 }]

// GOOD: Range-based pagination (see pattern above)
```

### Multiple $lookup on Same Collection
```javascript
// BAD: Two lookups on same collection
[{ $lookup: { from: "users", ... } }, { $lookup: { from: "users", ... } }]

// GOOD: Single lookup with pipeline that returns all needed data
```

### Not Using $project to Reduce Pipeline Data
```javascript
// BAD: Carries all fields through entire pipeline
[{ $match: ... }, { $group: ... }, { $sort: ... }]

// GOOD: Drop unnecessary fields early
[{ $match: ... }, { $project: { field1: 1, field2: 1 } }, { $group: ... }]
```
