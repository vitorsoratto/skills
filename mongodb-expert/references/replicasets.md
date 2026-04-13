# ReplicaSets

## Table of Contents
1. Architecture Fundamentals
2. Member Types & Roles
3. Elections
4. Read/Write Concerns
5. Read Preferences
6. Configuration
7. Reconfiguration Safety
8. Monitoring
9. Common Problems
10. Maintenance Operations

## 1. Architecture Fundamentals

A replica set = group of mongod instances maintaining the same dataset.

Minimum production topology:
- **3 members** (or more, always odd number for elections)
- 1 Primary + 2 Secondaries (recommended)
- 1 Primary + 1 Secondary + 1 Arbiter (minimal — NOT recommended for production)

### Why Odd Numbers?

Elections require a **majority** of voting members. With even numbers, a network partition can result in no side having majority → no primary elected → cluster is read-only.

| Members | Majority Needed | Can Tolerate Failures |
|---------|----------------|----------------------|
| 3 | 2 | 1 |
| 5 | 3 | 2 |
| 7 | 4 | 3 |

### Maximum Members

- Maximum **50 members** in a replica set
- Maximum **7 voting members** (members beyond 7 must have `votes: 0`)

## 2. Member Types & Roles

### Primary
- Receives all write operations
- Only member that accepts writes by default
- Records operations in the **oplog**

### Secondary
- Replicates the primary's oplog and applies operations
- Can serve reads (with appropriate read preference)
- Becomes primary candidate in elections

### Arbiter
- Votes in elections but holds NO data
- Uses minimal resources
- **Caution**: An arbiter cannot become a data-bearing member. If you lose a data member, you're down to fewer copies of your data.

### Hidden Members
- `hidden: true` + `priority: 0`
- Invisible to client applications
- Good for: dedicated reporting, backup, analytics
- Still participates in elections (votes)

### Delayed Members
- `secondaryDelaySecs: N` (was `slaveDelay` in older versions — DEPRECATED)
- Maintains a copy that lags behind by N seconds
- Useful for: point-in-time recovery from human error
- Must be `hidden: true` and `priority: 0`

## 3. Elections

### When Elections Happen
- Primary steps down (manual or automatic)
- Primary becomes unreachable (heartbeat timeout: 10 seconds default)
- `rs.stepDown()` called
- Replica set reconfig changes priorities

### Election Protocol

MongoDB uses **Raft-based protocol** (protocol version 1, pv1) since MongoDB 4.0.

Key factors in who wins:
1. **Priority**: Higher priority = more likely to win (0 = never primary)
2. **Optime**: Must be most up-to-date or within `catchUpTimeoutMillis`
3. **Votes**: Must receive majority of votes
4. **Network**: Must be reachable by majority

### Election Timing

- `electionTimeoutMillis`: Default 10000ms (10s)
  - Time a secondary waits after losing contact with primary before calling election
- Shorter timeout = faster failover but more false elections on network blips
- `catchUpTimeoutMillis`: Default -1 (unlimited, but VERIFY for target version)

## 4. Read/Write Concerns

### Write Concern

Controls acknowledgment for write operations.

| Value | Meaning | Trade-off |
|-------|---------|-----------|
| `w: 1` | Acknowledged by primary only | Fast but data could be lost if primary fails before replication |
| `w: "majority"` | Acknowledged by majority of members | **Default since MongoDB 5.0**. Safe. Slightly higher latency |
| `w: N` | Acknowledged by N members | Custom durability requirement |
| `j: true` | Written to journal before ack | Crash-safe on primary |

**CRITICAL**: MongoDB 5.0+ changed the default write concern to `{w: "majority"}`. For MongoDB 4.x, default was `{w: 1}`.

### Read Concern

Controls the recency/consistency of data returned.

| Level | Guarantee |
|-------|-----------|
| `local` | Returns most recent data available on the queried member. Default for reads against primary. May return data that will be rolled back. |
| `available` | Like local but for sharded clusters, may return orphaned documents. |
| `majority` | Returns data acknowledged by majority. Won't be rolled back. |
| `linearizable` | Strongest. Reads reflect all successful majority-acknowledged writes before the read. Only against primary. Can be slow. |
| `snapshot` | For multi-document transactions. Point-in-time snapshot. |

## 5. Read Preferences

Controls which member serves reads.

| Mode | Behavior |
|------|----------|
| `primary` | All reads to primary. Default. |
| `primaryPreferred` | Primary if available, else secondary. |
| `secondary` | Only secondaries. |
| `secondaryPreferred` | Secondary if available, else primary. |
| `nearest` | Lowest network latency member. |

### Tag Sets

Route reads to specific members by tag:
```javascript
{readPreference: "secondary", readPreferenceTags: [{dc: "east"}]}
```

### Hedged Reads (MongoDB 4.4+)

Send read to multiple members, return first response. Reduces tail latency.
```javascript
{readPreference: "nearest", hedge: {enabled: true}}
```
**Note**: Only with `nearest` mode. VERIFY availability in target version.

## 6. Configuration

### rs.initiate() — Initial Setup

```javascript
rs.initiate({
  _id: "myReplicaSet",
  members: [
    { _id: 0, host: "mongo1:27017" },
    { _id: 1, host: "mongo2:27017" },
    { _id: 2, host: "mongo3:27017" }
  ]
})
```

### Key Configuration Fields

```javascript
{
  _id: "replicaSetName",
  version: <auto-incremented>,
  term: <raft term>,
  members: [
    {
      _id: <integer>,
      host: "hostname:port",
      arbiterOnly: false,
      buildIndexes: true,
      hidden: false,
      priority: 1,        // 0 to 1000. 0 = never primary
      tags: {},
      secondaryDelaySecs: 0,
      votes: 1             // 0 or 1
    }
  ],
  settings: {
    chainingAllowed: true,
    heartbeatIntervalMillis: 2000,
    heartbeatTimeoutSecs: 10,
    electionTimeoutMillis: 10000,
    catchUpTimeoutMillis: -1,
    getLastErrorModes: {},
    getLastErrorDefaults: { w: 1, wtimeout: 0 }
  }
}
```

## 7. Reconfiguration Safety

### BEFORE Any rs.reconfig()

Ask these questions:
1. Is the majority of voting members reachable? (If NO → reconfig will fail or require `force: true`)
2. Am I changing the number of voting members? (Affects majority calculation)
3. Am I changing priorities? (May trigger an election)
4. Am I removing a member that holds the only copy of recent writes?

### rs.reconfig() vs. rs.reconfig({force: true})

- **Normal reconfig**: Safe. Requires current primary and majority.
- **Force reconfig**: DANGEROUS. Only use when majority is lost and you need to rebuild. Can cause data rollback.

### Adding/Removing Members

- Add one member at a time and wait for it to sync
- Removing a member: ensure remaining members still form a majority
- If removing the member would break majority → reconfig will fail (expected safety behavior)

## 8. Monitoring

### Key Commands

```javascript
rs.status()              // Replica set status
rs.conf()                // Current configuration
rs.printReplicationInfo() // Oplog info from primary
rs.printSecondaryReplicationInfo() // Lag info per secondary
db.serverStatus().repl   // Replication metrics
```

### What to Monitor

| Metric | Warning Threshold | Source |
|--------|------------------|--------|
| Replication lag | > 10 seconds | `rs.status().members[N].optimeDate` |
| Member state | Any not PRIMARY/SECONDARY | `rs.status().members[N].stateStr` |
| Election count | Unexpected elections | `db.serverStatus().electionMetrics` |
| Oplog window | < 24 hours | `rs.printReplicationInfo()` |

## 9. Common Problems

### Split Brain
- **Cause**: Network partition where both sides think they're primary
- **Prevention**: Odd number of voting members, proper network topology
- **MongoDB's protection**: Write concern `majority` ensures data safety

### Replication Lag
- **Cause**: Secondary can't keep up (slow disk, missing indexes, large operations)
- **Diagnose**: `rs.printSecondaryReplicationInfo()`
- **Fix**: Check secondary disk I/O, check if secondary is being used for heavy reads, check for large operations in oplog

### Rollback
- **Cause**: Primary accepted writes that weren't replicated to majority before failover
- **Prevention**: Use `w: "majority"` write concern
- **Recovery**: Rollback files are saved to `dbPath/rollback/` for manual recovery

## 10. Maintenance Operations

### Stepping Down Primary

```javascript
rs.stepDown(60)  // Step down for 60 seconds
```
- Triggers election for a new primary
- Use during maintenance windows

### Rolling Restart Pattern

1. Restart secondaries one at a time
2. Wait for each to catch up and become SECONDARY
3. Step down primary: `rs.stepDown()`
4. Restart the old primary (now secondary)
5. Optionally step up preferred primary: `rs.stepDown()` on current + set priority

### Initial Sync

When a new member joins or a member is too far behind:
- Member performs a full copy from a sync source
- Then applies oplog entries from the point the sync started
- Can be resource-intensive on the sync source
