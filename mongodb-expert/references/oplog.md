# Oplog (Operation Log)

## Table of Contents
1. What is the Oplog
2. Oplog Size
3. Oplog Window
4. Monitoring
5. Oplog and Change Streams
6. Resizing
7. Common Problems

## 1. What is the Oplog

The oplog is a special **capped collection** (`local.oplog.rs`) that records all operations that modify data in a replica set.

Key properties:
- Lives on every replica set member
- Idempotent: applying the same oplog entry multiple times produces the same result
- Entries contain: timestamp, operation type (i/u/d/c/n), namespace, document
- Used by secondaries to replicate the primary's data

### Operation Types

| Type | Meaning |
|------|---------|
| `i` | Insert |
| `u` | Update |
| `d` | Delete |
| `c` | Command (createCollection, dropCollection, etc.) |
| `n` | No-op (used for elections, initial sync markers) |

### Oplog Entry Structure (simplified)

```javascript
{
  ts: Timestamp(1234567890, 1),  // Operation timestamp
  t: NumberLong(1),              // Election term
  h: NumberLong(0),              // Hash (deprecated in newer versions)
  v: 2,                          // Oplog version
  op: "i",                       // Operation type
  ns: "mydb.mycollection",       // Namespace
  o: { /* document */ }          // Operation details
}
```

## 2. Oplog Size

### Default Size (VERIFY for target version)

MongoDB 8.0 (verify):
- **Linux/Windows**: 5% of free disk space, capped between 990MB and 50GB
- **macOS** (development): 192MB

### Why Size Matters

The oplog is a capped collection — when it fills up, the oldest entries are overwritten. If a secondary falls behind by more than the oplog can hold, it must perform a full initial sync (expensive).

### Setting Custom Size

At startup:
```
mongod --oplogSize <megabytes>
```

In config file:
```yaml
replication:
  oplogSizeMB: 10240  # 10GB
```

At runtime (MongoDB 4.0+):
```javascript
db.adminCommand({replSetResizeOplog: 1, size: 10240})  // size in MB
```

## 3. Oplog Window

The **oplog window** is the time difference between the newest and oldest oplog entry. It determines how long a secondary can be offline and still catch up without a full resync.

### Calculating Oplog Window

```javascript
rs.printReplicationInfo()
```

Output:
```
configured oplog size:   10240MB
log length start to end: 172800secs (48hrs)
oplog first event time:  Mon Apr 11 2026 00:00:00
oplog last event time:   Wed Apr 13 2026 00:00:00
```

`log length start to end` = oplog window (48 hours in this example)

### Oplog Window Guidelines

Ask: What is the longest expected secondary downtime?
- Maintenance window? Add 2x buffer
- Cross-DC replication? Account for network delays
- Backup operations? Backups reading oplog hold entries

| Scenario | Minimum Recommended Window |
|----------|---------------------------|
| Standard production | 24-48 hours |
| Cross-datacenter | 48-72 hours |
| Compliance/audit | 72+ hours |

## 4. Monitoring

### Replication Lag

```javascript
// From primary
rs.printSecondaryReplicationInfo()
```

Output per secondary:
```
source: mongo2:27017
  syncedTo: Wed Apr 13 2026 12:00:00
  5 secs (0 hrs) behind the primary
```

### Oplog Consumption Rate

Ask: How fast is the oplog being consumed?
```javascript
// Check oplog stats
use local
db.oplog.rs.stats()
```

Key metrics:
- `size` / `maxSize`: Current vs. max oplog size
- `count`: Number of oplog entries

### Programmatic Lag Check

```javascript
// Get primary's latest optime
var primaryStatus = rs.status().members.find(m => m.stateStr === "PRIMARY")
var primaryOptime = primaryStatus.optimeDate

// Get secondary lag
rs.status().members.filter(m => m.stateStr === "SECONDARY").forEach(m => {
  var lag = (primaryOptime - m.optimeDate) / 1000
  print(m.name + ": " + lag + " seconds behind")
})
```

## 5. Oplog and Change Streams

Change streams are built on top of the oplog. They use oplog entries to notify applications of data changes in real-time.

### Important Relationship

- Change streams need oplog entries to exist to resume from a token
- If the oplog rolls over past a resume token, the change stream cannot resume
- For change streams, the oplog window must be larger than the longest expected downtime of the change stream consumer

### Resume Token Lifetime

The resume token is valid as long as the corresponding oplog entry exists. Once the oplog rolls past that entry, the token is invalid.

**Sizing for change streams**: Ensure oplog window > maximum consumer downtime + safety buffer.

## 6. Resizing

### Online Resize (MongoDB 4.0+)

```javascript
// Increase to 20GB
db.adminCommand({replSetResizeOplog: 1, size: 20480})

// Verify
use local
db.oplog.rs.stats().maxSize  // in bytes
```

### When to Resize

Ask: Is the current oplog window sufficient for:
1. Secondary maintenance downtime? (rolling restarts, patching)
2. Initial sync of a new member? (sync can take hours for large datasets)
3. Change stream consumer recovery?
4. Cross-datacenter replication lag spikes?

### Shrinking the Oplog

Shrinking is possible but:
1. It requires a `compact` operation on the oplog
2. `compact` blocks on the collection
3. Do it on secondaries first, then step down primary

```javascript
// Resize to smaller
db.adminCommand({replSetResizeOplog: 1, size: 5120})  // 5GB
// Then compact to reclaim space
db.adminCommand({compact: "oplog.rs"})
```

## 7. Common Problems

### Secondary Falls Too Far Behind
- **Symptom**: Secondary enters RECOVERING state, cannot catch up
- **Cause**: Oplog window was too small for the downtime duration
- **Fix**: Member must perform initial sync (full resync)
- **Prevention**: Size oplog to at least 2x your longest expected downtime

### Oplog Consuming Too Much Disk
- **Symptom**: Disk filling up, oplog larger than expected
- **Cause**: Heavy write workload creating large oplog entries
- **Investigate**: Check write patterns — large document updates generate full-document oplog entries
- **Mitigation**: Use targeted updates (`$set`, `$inc`) instead of full document replacement

### Replication Lag Spikes
- **Cause**: Large operations (bulk writes, index builds), slow secondary disk I/O, secondary serving heavy read traffic
- **Diagnose**: Check `db.currentOp()` on secondary, check disk I/O metrics
- **Fix**: Reduce secondary read load, improve disk performance, optimize write patterns

### Oplog Holes
- **What**: Gaps in oplog timestamps due to failed/aborted operations
- **Impact**: Can temporarily prevent secondaries from advancing
- **Usually resolves**: Automatically, but can cause brief lag spikes
