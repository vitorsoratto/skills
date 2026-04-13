# Performance & Troubleshooting

## Table of Contents
1. Diagnostic Framework
2. Explain Plans
3. Slow Query Analysis
4. Profiler
5. currentOp
6. Server Status Analysis
7. Common Performance Issues
8. Index Optimization

## 1. Diagnostic Framework

When investigating performance, follow this order:

1. **What is the symptom?** (slow reads, slow writes, timeouts, high CPU, high memory)
2. **What changed?** (deploy, traffic spike, data growth, schema change)
3. **Where is the bottleneck?** (CPU, disk I/O, memory, network, locks)
4. **What queries are involved?** (profiler, slow query log, currentOp)
5. **What does explain() show?** (COLLSCAN, rejected plans, high docsExamined)

### Quick Diagnostic Commands

```javascript
// Active operations (what's running right now)
db.currentOp({
  active: true,
  secs_running: { $gte: 5 }  // Operations running > 5 seconds
})

// Server status overview
db.serverStatus()

// Collection stats
db.collection.stats()

// Index stats (which indexes are used)
db.collection.aggregate([{ $indexStats: {} }])

// Top operations per collection
db.adminCommand({ top: 1 })
```

## 2. Explain Plans

### Running Explain

```javascript
// Query plan only (no execution)
db.collection.find({...}).explain("queryPlanner")

// Execute and show stats
db.collection.find({...}).explain("executionStats")

// All candidate plans with stats
db.collection.find({...}).explain("allPlansExecution")
```

### Reading Explain Output

Key fields in `executionStats`:

| Field | Good Value | Bad Value |
|-------|-----------|-----------|
| `winningPlan.stage` | IXSCAN, FETCH | COLLSCAN |
| `totalDocsExamined` | Close to `nReturned` | >> nReturned |
| `totalKeysExamined` | Close to `nReturned` | >> nReturned |
| `executionTimeMillis` | < 100ms | > 1000ms |

### Explain Stage Hierarchy

```
COLLSCAN        → Scanning every document (worst case)
IXSCAN          → Using an index (good)
FETCH           → Retrieving documents from index keys
SORT            → In-memory sort (bad if large dataset)
SORT_KEY_GENERATOR → Generating sort keys
PROJECTION      → Applying projection
LIMIT           → Applying limit
SKIP            → Applying skip
```

### Red Flags in Explain

Ask: Is `totalDocsExamined` much larger than `nReturned`?
- YES → Index is not selective enough or missing. The query reads many documents to return few.

Ask: Is there a `SORT` stage without `IXSCAN` providing order?
- YES → In-memory sort. For large result sets, this uses significant memory (100MB limit by default).

Ask: Is `executionTimeMillis` > 100ms for a frequent query?
- YES → This query needs optimization (index, schema, or query rewrite).

## 3. Slow Query Analysis

### Enabling Slow Query Logging

```javascript
// Log queries slower than 100ms
db.setProfilingLevel(0)  // Profiler off
db.adminCommand({ setParameter: 1, slowOpThresholdMs: 100 })
```

Slow queries appear in `mongod.log` with the `COMMAND` component.

### Parsing Slow Query Logs

Key fields in slow query log entries:
- `millis`: Execution time
- `planSummary`: Which index was used (or COLLSCAN)
- `keysExamined`: How many index keys were scanned
- `docsExamined`: How many documents were read
- `nreturned`: How many documents were returned
- `ns`: Namespace (database.collection)
- `command`: The actual query/command

### Identifying Patterns

Ask: Is the same query appearing repeatedly in slow logs?
- YES → This is a systematic issue. Fix the query or add an index.
- NO → May be a one-time issue (data spike, competing operation).

## 4. Profiler

### Profiler Levels

| Level | Behavior | Production Safe? |
|-------|----------|-----------------|
| 0 | Off | Yes |
| 1 | Log slow operations only | Yes (with appropriate `slowms`) |
| 2 | Log ALL operations | **NO** — significant overhead |

```javascript
// Enable profiler (slow ops only)
db.setProfilingLevel(1, { slowms: 100 })

// Query profiler data
db.system.profile.find({
  millis: { $gt: 100 },
  ns: "mydb.mycollection"
}).sort({ ts: -1 }).limit(10)

// Disable profiler
db.setProfilingLevel(0)
```

### Profiler Output Fields

```javascript
{
  op: "query",
  ns: "mydb.users",
  command: { find: "users", filter: { status: "active" } },
  keysExamined: 0,
  docsExamined: 100000,
  nreturned: 50,
  millis: 1500,
  planSummary: "COLLSCAN",
  ts: ISODate("...")
}
```

## 5. currentOp

### Finding Problematic Operations

```javascript
// Long-running operations (> 60 seconds)
db.currentOp({
  active: true,
  secs_running: { $gte: 60 }
})

// Operations waiting for locks
db.currentOp({
  waitingForLock: true
})

// Operations on a specific collection
db.currentOp({
  ns: "mydb.mycollection"
})

// Kill a problematic operation
db.killOp(<opid>)
```

### Key currentOp Fields

| Field | Meaning |
|-------|---------|
| `opid` | Operation ID (for killOp) |
| `secs_running` | How long it's been running |
| `op` | Operation type (query, insert, update, command) |
| `ns` | Namespace |
| `waitingForLock` | Is it blocked waiting for a lock? |
| `msg` | Progress message (for long operations like index builds) |
| `planSummary` | Index or COLLSCAN |

## 6. Server Status Analysis

### Key Sections

```javascript
var status = db.serverStatus()

// Connection info
status.connections  // current, available, totalCreated

// Operation counters
status.opcounters   // insert, query, update, delete, getmore, command

// Lock info
status.globalLock   // currentQueue (readers, writers), activeClients

// WiredTiger (see references/wiredtiger.md for details)
status.wiredTiger.cache
status.wiredTiger.concurrentTransactions

// Network
status.network      // bytesIn, bytesOut, numRequests

// Memory
status.mem          // resident, virtual, mapped
```

### Health Check Queries

```javascript
// Are operations queueing?
var gl = db.serverStatus().globalLock
print("Read queue: " + gl.currentQueue.readers)
print("Write queue: " + gl.currentQueue.writers)
// Both should be 0 or near 0

// Are connections exhausted?
var conn = db.serverStatus().connections
print("Current: " + conn.current + " / Available: " + conn.available)
// current should be << available

// WiredTiger ticket availability
var wt = db.serverStatus().wiredTiger.concurrentTransactions
print("Read tickets: " + wt.read.available + " / Write tickets: " + wt.write.available)
// Should NOT approach 0
```

## 7. Common Performance Issues

### COLLSCAN on Large Collection
- **Symptom**: Slow queries, high CPU
- **Cause**: Missing index
- **Fix**: Create appropriate index based on query pattern
- **Verify**: `explain("executionStats")` shows IXSCAN after

### In-Memory Sort Exceeding Limit
- **Symptom**: Error "Sort exceeded memory limit of 104857600 bytes"
- **Cause**: Sorting large result set without index support
- **Fix**: Create compound index that includes sort field (ESR rule)
- **Alternative**: `allowDiskUse: true` (slower but works)

### Write Contention
- **Symptom**: Slow writes, high write queue
- **Cause**: Hot document (counter), too many indexes, slow disk
- **Fix**: Depends on cause — reduce index count, shard, use distributed counter pattern

### Connection Pool Exhaustion
- **Symptom**: "connection refused" or timeout errors
- **Cause**: Pool too small, connections not returned (leaked), too many clients
- **Fix**: Increase pool size, fix connection leaks, add connection lifetime limits

### Large Documents
- **Symptom**: High memory usage, slow reads
- **Cause**: Unbounded arrays, embedded large data
- **Fix**: Subset pattern, referencing. See `references/data-modeling.md`

## 8. Index Optimization

### Finding Unused Indexes

```javascript
// Get index usage statistics
db.collection.aggregate([{ $indexStats: {} }])
// Look for indexes with accesses.ops = 0 over a significant time period
```

### Finding Missing Indexes

```javascript
// Check profiler for COLLSCAN
db.system.profile.find({ planSummary: "COLLSCAN" }).sort({ ts: -1 })

// Or enable slow query logging and grep for COLLSCAN
```

### Index Memory Usage

```javascript
// Total index size for a collection
db.collection.stats().totalIndexSize

// Per-index sizes
db.collection.stats().indexSizes
```

Ask: Do all indexes fit in RAM (WiredTiger cache)?
- YES → Optimal performance
- NO → Most-used indexes should fit. Less-used indexes will page from disk (slower but acceptable).
