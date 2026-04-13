# WiredTiger Storage Engine

## Table of Contents
1. Architecture Overview
2. Cache Management
3. Compression
4. Journaling & Checkpoints
5. Concurrency (Tickets)
6. Eviction
7. Diagnostic Commands
8. Tuning Guidelines
9. Common Problems

## 1. Architecture Overview

WiredTiger is MongoDB's default (and only supported) storage engine since MongoDB 4.2+.

Key components:
- **Cache**: In-memory working set. NOT the same as the OS page cache.
- **Journal**: Write-ahead log (WAL) for crash recovery.
- **Checkpoints**: Periodic flush of in-memory data to disk. Default: every 60 seconds.
- **B-tree**: Default data structure for collections and indexes.
- **Block Manager**: Handles I/O to/from disk.

### Data Flow
```
Write → Journal (WAL) → Cache (dirty pages) → Checkpoint → Disk
Read → Cache hit? → Return | Cache miss → Disk → Cache → Return
```

## 2. Cache Management

### Cache Size Formula

**CRITICAL**: Always verify the formula for the target version.

MongoDB 8.0 default:
```
wiredTigerCacheSizeGB = max(256MB, (RAM - 1GB) * 0.5)
```

Example: 16GB RAM → (16 - 1) * 0.5 = 7.5GB cache

### Key Cache Metrics

```javascript
db.serverStatus().wiredTiger.cache
```

Important fields:
- `bytes currently in the cache` — current cache usage
- `maximum bytes configured` — configured cache limit
- `tracked dirty bytes in the cache` — dirty pages needing write
- `pages evicted` — pages removed from cache
- `pages read into cache` / `pages written from cache`

### Cache Pressure Indicators

Ask: Is `bytes currently in the cache` consistently > 80% of `maximum bytes configured`?
- YES → cache pressure exists, investigate eviction metrics
- NO → cache is not the bottleneck

Ask: Are `tracked dirty bytes in the cache` > 5% of cache size?
- YES → checkpoints or eviction may be falling behind
- High dirty ratio can indicate write-heavy workload exceeding checkpoint capacity

## 3. Compression

### Collection Compression (data on disk)

| Algorithm | Ratio | CPU | Use Case |
|-----------|-------|-----|----------|
| snappy | Good (~2-4x) | Low | Default. Good balance for most workloads |
| zlib | Better (~4-7x) | Medium | Archive data, read-heavy, storage-constrained |
| zstd | Best (~4-8x) | Medium | Available since 4.2. Best ratio with reasonable CPU |
| none | 1x | None | Ultra-low-latency reads, CPU-constrained |

### Index Compression

Indexes use **prefix compression** by default. This is separate from collection compression.

### Journal Compression

Journal uses **snappy** by default. Configurable via `storage.wiredTiger.engineConfig.journalCompressor`.

### Verify Compression

```javascript
db.collection.stats().wiredTiger.creationString
// Look for: block_compressor=snappy
```

## 4. Journaling & Checkpoints

### Journal (WAL)

- Write-ahead log for crash recovery
- Synced to disk every 100ms by default (configurable via `storage.journal.commitIntervalMs`)
- Minimum: 1ms, Maximum: 500ms
- Stored in the `journal/` subdirectory of dbPath

### Checkpoints

- Full flush of dirty pages to data files
- Default interval: 60 seconds (`storage.wiredTiger.engineConfig.checkpointIntervalSecs` — MongoDB 8.0+ name, VERIFY for your version)
- During checkpoint: increased I/O activity (expected)
- Long checkpoints indicate: large dirty data volume or slow storage

### Recovery Process

1. On unclean shutdown, WiredTiger replays journal entries from the last checkpoint
2. Recovery time depends on: journal size since last checkpoint
3. More frequent checkpoints = faster recovery but more I/O

## 5. Concurrency (Tickets)

### Read/Write Tickets

WiredTiger uses a ticketing system to control concurrent access:
- **Read tickets**: Default 128 (MongoDB 7.0+, VERIFY for target version)
- **Write tickets**: Default 128

```javascript
db.serverStatus().wiredTiger.concurrentTransactions
// readAvailable, writeAvailable, readOut, writeOut
```

### Ticket Exhaustion

Ask: Are `readAvailable` or `writeAvailable` approaching 0?
- YES → operations are queueing. Investigate what's holding tickets (long-running queries, transactions)
- This is often a symptom, not the root cause — look for slow queries, missing indexes, long transactions

## 6. Eviction

WiredTiger evicts pages from cache when:
- Cache usage exceeds thresholds
- Dirty data ratio is too high

### Eviction Thresholds (VERIFY for target version)

| Threshold | Default | Meaning |
|-----------|---------|---------|
| `eviction_target` | 80% | Start background eviction |
| `eviction_trigger` | 95% | Start aggressive eviction |
| `eviction_dirty_target` | 5% | Start evicting dirty pages |
| `eviction_dirty_trigger` | 20% | Aggressive dirty page eviction |

### Eviction Metrics

```javascript
db.serverStatus().wiredTiger.cache["pages evicted"]
db.serverStatus().wiredTiger.cache["application threads page eviction"]
```

**CRITICAL**: If `application threads page eviction` > 0, application threads are doing eviction work — this directly impacts latency.

## 7. Diagnostic Commands

```javascript
// Full WiredTiger stats
db.serverStatus().wiredTiger

// Cache stats
db.serverStatus().wiredTiger.cache

// Concurrency stats
db.serverStatus().wiredTiger.concurrentTransactions

// Connection stats
db.serverStatus().wiredTiger.connection

// Collection-level stats
db.collection.stats().wiredTiger

// Index-level stats (per index)
db.collection.stats({indexDetails: true})
```

## 8. Tuning Guidelines

### Cache Size

Rule of thumb (VERIFY with official docs):
- Never set > 80% of available RAM (leave room for OS, connections, aggregation)
- If running alongside other services, account for their memory needs
- Monitor: if `bytes currently in the cache` is consistently near max AND eviction is happening, consider increasing

### When NOT to Increase Cache

Ask: Is the working set larger than available RAM?
- If YES → adding cache won't help. Consider: sharding, archiving old data, adding RAM
- More cache only helps if the working set fits

## 9. Common Problems

### Checkpoint Stalls
- **Symptom**: Periodic latency spikes every ~60 seconds
- **Cause**: Large amount of dirty data being flushed
- **Investigate**: `db.serverStatus().wiredTiger.transaction["transaction checkpoint currently running"]`

### Cache Pressure
- **Symptom**: Increasing read/write latency, application thread eviction
- **Cause**: Working set larger than cache, or large transactions holding dirty pages
- **Investigate**: Cache metrics (section 2) and eviction metrics (section 6)

### Ticket Exhaustion
- **Symptom**: Operations queueing, timeouts
- **Cause**: Long-running operations holding tickets
- **Investigate**: `db.currentOp()` for long-running ops + ticket availability
