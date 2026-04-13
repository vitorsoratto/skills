# TimeSeries Collections

## Table of Contents
1. Overview
2. Creating TimeSeries Collections
3. Fields & Configuration
4. Granularity
5. Bucketing Internals
6. Indexes
7. Querying
8. Limitations
9. Best Practices
10. Migration Patterns

## 1. Overview

TimeSeries collections are optimized for storing time-stamped data with efficient compression and query patterns. Available since MongoDB 5.0.

Key advantages:
- Automatic bucketing: Groups measurements by time and metadata for efficient storage
- Better compression: Similar data points stored together
- Optimized queries: Time-range queries benefit from bucket structure
- Reduced storage: Typically 5-10x less disk usage than regular collections

### When to Use

Ask: Does the data have these characteristics?
1. Each document has a timestamp
2. Documents have metadata that identifies the source (sensor ID, user ID, etc.)
3. Data is mostly append-only (inserts, rarely updates/deletes)
4. Queries are typically time-range based

If YES to all → TimeSeries collection is appropriate.

## 2. Creating TimeSeries Collections

```javascript
db.createCollection("measurements", {
  timeseries: {
    timeField: "timestamp",        // REQUIRED: field containing the date
    metaField: "metadata",         // OPTIONAL: field identifying the data source
    granularity: "seconds"         // OPTIONAL: "seconds" | "minutes" | "hours"
  },
  expireAfterSeconds: 2592000      // OPTIONAL: TTL in seconds (30 days here)
})
```

### CRITICAL: Fields Must Be Set at Creation

- `timeField` and `metaField` CANNOT be changed after creation
- `granularity` CAN be changed (increased only, not decreased)
- Choose these carefully before creating the collection

## 3. Fields & Configuration

### timeField (REQUIRED)

- Must contain a BSON `Date` type
- Cannot be an array
- Every inserted document MUST have this field
- Documents without the timeField will be rejected

### metaField (OPTIONAL but STRONGLY recommended)

- Identifies the "source" of the measurement (sensor, device, user, etc.)
- Can be a sub-document (e.g., `{sensorId: "A1", location: "warehouse"}`)
- Used by MongoDB to group documents into buckets
- Documents with the same metaField values go into the same bucket

**CRITICAL**: If you don't set metaField, ALL documents go into buckets based ONLY on time proximity. This severely reduces bucketing efficiency for multi-source data.

### granularity

Controls how MongoDB groups data points into buckets.

| Value | Time span per bucket | Best for |
|-------|---------------------|----------|
| `"seconds"` | ~1 hour | High-frequency data (multiple per second/minute) |
| `"minutes"` | ~24 hours | Data arriving every few minutes |
| `"hours"` | ~30 days | Data arriving every few hours |

**MongoDB 6.3+ alternative**: `bucketMaxSpanSeconds` and `bucketRoundingSeconds` for custom control (VERIFY for target version).

### expireAfterSeconds (TTL)

- Automatically deletes documents older than the specified age
- Age is calculated from the `timeField` value
- Deletion happens in background, not instantaneous
- Can be changed after creation with `collMod`

## 4. Granularity Deep Dive

### How Granularity Affects Buckets

Each bucket has a time range. Documents falling within that range AND sharing the same metaField go into one bucket.

```
granularity: "seconds" → buckets span ~1 hour
granularity: "minutes" → buckets span ~24 hours  
granularity: "hours"   → buckets span ~30 days
```

### Choosing the Right Granularity

Ask: What is the typical interval between consecutive measurements from the SAME source?

| Interval | Recommended Granularity |
|----------|------------------------|
| Sub-second to few seconds | `"seconds"` |
| 1-30 minutes | `"minutes"` |
| 1+ hours | `"hours"` |

### Changing Granularity

Can only INCREASE (seconds → minutes → hours), never decrease:

```javascript
db.runCommand({
  collMod: "measurements",
  timeseries: { granularity: "minutes" }
})
```

## 5. Bucketing Internals

### How Buckets Work

MongoDB internally creates a `system.buckets.<collection_name>` collection. Each bucket document contains:

```javascript
{
  _id: ObjectId,
  control: {
    version: 1,
    min: { timestamp: ISODate("..."), value: 10 },  // Min values in bucket
    max: { timestamp: ISODate("..."), value: 95 }   // Max values in bucket
  },
  meta: { sensorId: "A1" },    // From metaField
  data: {
    timestamp: { "0": ISODate, "1": ISODate, ... },
    value: { "0": 42, "1": 55, ... }
  }
}
```

### Bucket Limits

- Max documents per bucket: ~1000 (VERIFY for target version)
- Max bucket size: ~125KB (compressed, VERIFY)
- When a bucket is full (by count or size), a new one is created

### Why This Matters for Performance

- Queries on `timeField` ranges can skip entire buckets using `control.min`/`control.max`
- Queries filtering by `metaField` are efficient because buckets are grouped by meta
- Columnar compression within buckets reduces storage significantly

## 6. Indexes

### Default Indexes

TimeSeries collections automatically create:
- Compound index on `{metaField: 1, timeField: 1}` (if metaField is set)
- Index on `{timeField: 1}` (if no metaField)

### Custom Indexes (MongoDB 6.0+)

```javascript
// Secondary index on a measurement field
db.measurements.createIndex({"metadata.sensorId": 1, "timestamp": 1})

// Partial index
db.measurements.createIndex(
  {"value": 1},
  {partialFilterExpression: {"value": {$gt: 100}}}
)
```

### Index Limitations (VERIFY for target version)

- Some index types may not be supported on TimeSeries (e.g., text indexes, 2dsphere — check docs)
- Compound indexes have specific field ordering requirements
- `unique` indexes are NOT supported on TimeSeries

## 7. Querying

### Efficient Query Patterns

```javascript
// Time range query (uses bucket min/max for pruning)
db.measurements.find({
  timestamp: {
    $gte: ISODate("2026-04-01"),
    $lt: ISODate("2026-04-13")
  }
})

// Meta + time range (most efficient)
db.measurements.find({
  "metadata.sensorId": "A1",
  timestamp: { $gte: ISODate("2026-04-01") }
})

// Aggregation with $group by time window
db.measurements.aggregate([
  { $match: { timestamp: { $gte: ISODate("2026-04-01") } } },
  { $group: {
    _id: {
      $dateTrunc: { date: "$timestamp", unit: "hour" }
    },
    avgValue: { $avg: "$value" },
    maxValue: { $max: "$value" }
  }},
  { $sort: { _id: 1 } }
])
```

### Query Optimization

Ask: Does the query filter on metaField first, then timeField?
- YES → Optimal pattern, uses bucket structure efficiently
- NO → May scan more buckets than necessary

## 8. Limitations

### Cannot Do (VERIFY for target version)

- Update with arbitrary filters (limited update support)
- Delete individual documents (can delete by time range or metaField)
- Unique indexes
- Capped collection behavior
- Schema validation on measurement fields (only on metaField)
- `$out` to a TimeSeries collection (VERIFY)
- Transactions involving TimeSeries (VERIFY)

### Partial Support

- Updates: Limited to `metaField` updates in some versions (VERIFY)
- Deletes: Supported with certain filters since MongoDB 5.1+ (VERIFY specifics)

## 9. Best Practices

1. **Always set metaField**: Without it, bucketing is time-only and far less efficient
2. **metaField should be low-cardinality per time window**: If every document has a unique meta value, you get one document per bucket (defeats the purpose)
3. **Match granularity to data frequency**: Wrong granularity = wasted space or suboptimal bucketing
4. **Use TTL for data lifecycle**: Set `expireAfterSeconds` rather than manual cleanup
5. **Include metaField in queries**: Helps MongoDB prune buckets efficiently
6. **Pre-aggregate when possible**: For dashboards showing hourly/daily aggregates, consider a pre-aggregation pattern with change streams
7. **Monitor bucket stats**: Check `db.system.buckets.<name>.stats()` to verify bucketing efficiency

## 10. Migration Patterns

### Regular Collection → TimeSeries

1. Create the TimeSeries collection with proper configuration
2. Use aggregation pipeline with `$out` or `$merge` to copy data
3. OR use `mongodump`/`mongorestore` with schema conversion
4. Verify data integrity after migration
5. Update application code to use new collection

### Changing metaField (requires recreation)

Since metaField can't be changed:
1. Create new TimeSeries collection with correct metaField
2. Migrate data using aggregation pipeline
3. Drop old collection
4. Rename new collection (if needed)
