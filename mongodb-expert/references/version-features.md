# MongoDB Version Features & Breaking Changes

## Table of Contents
1. MongoDB 8.0
2. MongoDB 7.0
3. MongoDB 6.0
4. MongoDB 5.0
5. Deprecated Features Across Versions
6. Migration Notes

**IMPORTANT**: This file provides a starting point. ALWAYS verify against official release notes for the specific minor version (e.g., 8.0.1 vs 8.0.4) as behavior may differ.

## 1. MongoDB 8.0

**Release**: ~2024 (VERIFY exact date)

### Key Features (VERIFY each against official docs)

- **Queryable Encryption improvements**: Enhanced range queries on encrypted fields
- **Improved sharding**: Auto-sharding improvements, balancer enhancements
- **Performance improvements**: Various query optimizer improvements
- **Bulk write command**: New `bulkWrite` command at database level (not just collection)

### Breaking Changes (VERIFY)

- Check release notes: `mongodb.com/docs/manual/release-notes/8.0/`
- **Removed features**: Verify which features were removed from 7.0 → 8.0
- **Default changes**: Check if any server defaults changed
- **Driver compatibility**: Verify minimum driver versions required

### Configuration Changes to Watch

Always verify these parameters exist and have the expected defaults in 8.0:
- `wiredTigerCacheSizeGB` — formula may have changed
- `oplogSizeMB` — default may have changed
- Write concern defaults
- Security defaults

## 2. MongoDB 7.0

**Release**: ~2023

### Key Features

- **Queryable Encryption** (GA): Client-side field-level encryption with server-side query support
- **Compound Wildcard Indexes**: Combine wildcard with specific fields
- **Improved $lookup**: Better performance and expanded support
- **Slot-Based Query Execution Engine (SBE)**: Expanded to more query types
- **Automatic Merge for sharded clusters**: Improvements

### Notable Changes

- **Read/Write tickets**: Default changed (VERIFY exact values for 7.0)
- **Sampling-based query planning**: For some query shapes
- **Deprecated**: Several legacy shell commands

## 3. MongoDB 6.0

**Release**: ~2022

### Key Features

- **Queryable Encryption** (Preview): First introduction
- **Cluster-to-Cluster Sync**: New tool for migration/sync
- **Time Series improvements**: 
  - Custom bucketing parameters (`bucketMaxSpanSeconds`, `bucketRoundingSeconds`)
  - Better secondary indexes on TimeSeries
  - Update and delete support improvements
- **Aggregation improvements**: `$densify`, `$fill`, `$shardedDataDistribution`
- **Change Stream improvements**: Pre/post images of documents

### Breaking Changes

- **Removed**: `--serviceExecutor adaptive` option
- **Changed**: Some aggregation stage behaviors
- Check: `mongodb.com/docs/manual/release-notes/6.0/`

## 4. MongoDB 5.0

**Release**: ~2021

### Key Features

- **Native Time Series Collections**: First introduction of `timeseries` collection type
- **Live Resharding**: Reshard collections without downtime
- **Window Functions**: `$setWindowFields` in aggregation
- **Versioned API**: Stable API for forward compatibility
- **Default Write Concern**: Changed to `{w: "majority"}` — MAJOR CHANGE
- **Long-running snapshot reads**: For secondary reads

### Breaking Changes (Critical)

- **Write Concern Default**: Changed from `{w: 1}` to `{w: "majority"}`
  - Impact: Higher write latency (must wait for majority acknowledgment)
  - Impact: Different error behavior (writes fail if majority unavailable)
  - Migration note: Applications relying on `{w: 1}` behavior need explicit configuration
- **Removed**: `--oplogSize` parameter on mongos (was never valid but now errors)
- **Removed**: Legacy `mongo` shell replaced by `mongosh`

## 5. Deprecated Features Across Versions

### Currently Deprecated (as of latest known)

| Feature | Deprecated Since | Replacement |
|---------|-----------------|-------------|
| `db.collection.ensureIndex()` | 3.0 | `db.collection.createIndex()` |
| `db.collection.save()` | 4.2 | `insertOne()` / `replaceOne()` |
| `count()` without query | 4.0 | `countDocuments()` or `estimatedDocumentCount()` |
| `copydb` / `clone` commands | 4.0 | `mongodump`/`mongorestore` |
| `group` command | 3.4 | `$group` in aggregation |
| `eval` command | 3.0 | None (removed in 4.2) |
| `geoNear` command | 4.0 | `$geoNear` aggregation stage |
| MMAPv1 storage engine | 4.0 | WiredTiger (removed in 4.2) |
| `slaveDelay` | 5.0 | `secondaryDelaySecs` |
| `slaveOk` | 5.0 | `secondaryOk` |
| Legacy `mongo` shell | 5.0 | `mongosh` |

### NEVER Recommend

- MMAPv1 anything (removed since 4.2)
- `--master` / `--slave` replication (removed since 4.0)
- `db.eval()` (removed since 4.2)
- Legacy shell (`mongo`) for new deployments
- `ensureIndex()` — use `createIndex()`

## 6. Migration Notes

### Upgrading Between Major Versions

General procedure:
1. Read release notes for EVERY version between current and target
2. Check compatibility: `db.adminCommand({getParameter: 1, featureCompatibilityVersion: 1})`
3. Upgrade one version at a time (e.g., 6.0 → 7.0 → 8.0, NOT 6.0 → 8.0)
4. Set `featureCompatibilityVersion` AFTER successful upgrade
5. Test thoroughly before setting FCV (FCV unlock is harder to reverse)

### Feature Compatibility Version (FCV)

```javascript
// Check current FCV
db.adminCommand({ getParameter: 1, featureCompatibilityVersion: 1 })

// Set FCV after upgrade (enables new features, may change behavior)
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })
```

**CRITICAL**: Setting FCV is NOT easily reversible for all features. Some changes (new index types, new collection types) cannot be reverted by lowering FCV. ALWAYS research before setting.

### Driver Compatibility

When upgrading MongoDB server:
1. Check driver compatibility matrix: `mongodb.com/docs/drivers/`
2. Upgrade driver BEFORE upgrading server (drivers are forward-compatible)
3. Test driver + new server version in staging first
