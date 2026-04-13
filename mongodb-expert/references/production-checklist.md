# Production Checklist

## Table of Contents
1. Security
2. ReplicaSet Configuration
3. Storage & WiredTiger
4. Networking
5. Monitoring
6. Backup & Recovery
7. Operating System
8. Application Configuration

## 1. Security

### Authentication & Authorization

- [ ] Authentication enabled (`security.authorization: enabled`)
- [ ] SCRAM-SHA-256 used (not legacy SCRAM-SHA-1 or MONGODB-CR)
- [ ] Admin user created with `userAdminAnyDatabase` role
- [ ] Application users have MINIMUM required roles (principle of least privilege)
- [ ] No user has `root` role in production
- [ ] `localhost` exception disabled after creating admin user

### Network Security

- [ ] `bindIp` set to specific interfaces (NOT `0.0.0.0` unless with firewall)
- [ ] TLS/SSL enabled for client connections (`net.tls.mode: requireTLS`)
- [ ] TLS/SSL enabled for replica set internal communication
- [ ] TLS certificates are valid and not expired
- [ ] Firewall restricts MongoDB port (27017) to known clients only
- [ ] No MongoDB port exposed to public internet

### Encryption

- [ ] Encryption at rest enabled (Enterprise or Atlas) or disk-level encryption
- [ ] TLS for data in transit (see above)
- [ ] Key rotation policy in place

### Audit (Enterprise)

- [ ] Audit log enabled for authentication events
- [ ] Audit log enabled for authorization failures
- [ ] Audit log shipped to centralized logging

## 2. ReplicaSet Configuration

- [ ] Minimum 3 data-bearing members (NOT 2 + arbiter for production)
- [ ] Members spread across failure domains (racks, AZs, DCs)
- [ ] Odd number of voting members
- [ ] Write concern set to `majority` (default since 5.0, VERIFY)
- [ ] Read concern appropriate for use case
- [ ] `electionTimeoutMillis` appropriate for network topology
- [ ] Member priorities set correctly (desired primary has highest)
- [ ] Hidden/delayed member configured for disaster recovery (recommended)
- [ ] All members reachable by hostname (not IP — for certificate validation)

## 3. Storage & WiredTiger

### Disk

- [ ] Dedicated disk/volume for `dbPath` (not shared with OS or other apps)
- [ ] XFS filesystem (recommended for WiredTiger on Linux)
- [ ] `noatime` mount option set
- [ ] Sufficient IOPS for workload (SSD recommended for production)
- [ ] Disk space monitoring with alerts at 70%, 85%, 95%
- [ ] Separate disk for journal (optional, for high-write workloads)

### WiredTiger

- [ ] Cache size appropriate for workload (load `references/wiredtiger.md` for details)
- [ ] Compression algorithm chosen based on workload profile
- [ ] Checkpoint interval appropriate (default 60s usually fine)
- [ ] Journal enabled (default, NEVER disable in production)

### Oplog

- [ ] Oplog sized for at least 2x longest expected maintenance window
- [ ] Oplog window monitored with alerts
- [ ] Oplog large enough for change stream consumers

## 4. Networking

- [ ] Connection pooling configured in application (don't open/close per operation)
- [ ] Connection pool size appropriate for workload
- [ ] `maxIncomingConnections` set on mongod (default: 65536, usually fine)
- [ ] TCP keepalive enabled (OS-level)
- [ ] DNS resolution working for all replica set hostnames
- [ ] Application uses replica set connection string (not direct connections)

### Connection String Best Practices

```
mongodb://user:pass@host1:27017,host2:27017,host3:27017/mydb?replicaSet=myRS&w=majority&readPreference=primaryPreferred&retryWrites=true&retryReads=true&connectTimeoutMS=10000&serverSelectionTimeoutMS=15000
```

Key parameters:
- `replicaSet`: Required for replica set awareness
- `w=majority`: Durable writes
- `retryWrites=true`: Auto-retry on transient failures (default true since 4.2)
- `retryReads=true`: Auto-retry reads
- `connectTimeoutMS`: How long to wait for initial connection
- `serverSelectionTimeoutMS`: How long to wait for suitable server

## 5. Monitoring

### Key Metrics to Monitor

| Category | Metric | Alert Threshold |
|----------|--------|----------------|
| Replication | Replication lag | > 10s warning, > 60s critical |
| Replication | Oplog window | < 24h warning |
| Replication | Member state | Any not PRIMARY/SECONDARY |
| Storage | Disk usage | > 80% warning, > 90% critical |
| Storage | WiredTiger cache usage | > 80% warning |
| Performance | Slow queries (>100ms) | Trending upward |
| Performance | Ticket availability | < 10 available |
| Connections | Current connections | > 80% of max |
| Connections | Connection pool utilization | > 90% |

### Monitoring Tools

- `db.serverStatus()` — comprehensive server metrics
- `db.currentOp()` — active operations
- `mongotop` — time spent per collection
- `mongostat` — quick overview of operations
- MongoDB Atlas monitoring (if using Atlas)
- Prometheus + MongoDB exporter (self-hosted)
- Datadog, Grafana integrations

### Profiler

```javascript
// Enable profiler for slow queries (>100ms)
db.setProfilingLevel(1, { slowms: 100 })

// Check slow queries
db.system.profile.find().sort({ts: -1}).limit(10)
```

⚠️ Profiler adds overhead. Use `level: 1` (slow only) in production, NEVER `level: 2` (all operations) in production.

## 6. Backup & Recovery

### Options

| Method | Type | Impact | Best For |
|--------|------|--------|----------|
| `mongodump`/`mongorestore` | Logical | Medium (locks/reads) | Small datasets, selective restore |
| Filesystem snapshot | Physical | Low (with journal) | Large datasets, full restore |
| Oplog backup | Incremental | Low | Point-in-time recovery |
| Atlas Backup | Managed | None | Atlas deployments |

### Backup Checklist

- [ ] Automated backup schedule in place
- [ ] Backups taken from a secondary (not primary)
- [ ] Backup includes oplog for point-in-time recovery
- [ ] Backup stored off-site (different region/DC)
- [ ] Restore process tested regularly (at least quarterly)
- [ ] Backup retention policy defined and enforced
- [ ] Backup monitoring with alerts on failure

### Testing Backups

Ask: When was the last time a backup was restored to verify integrity?
- If "never" or "more than 3 months ago" → this is a critical gap

## 7. Operating System

### Linux Settings (Production)

- [ ] Transparent Huge Pages (THP) disabled
- [ ] `ulimit -n` (open files) set to at least 64000
- [ ] `ulimit -u` (processes) set to at least 64000
- [ ] Swappiness set to 1 (or 0 with care)
- [ ] NUMA disabled or `numactl --interleave=all` used
- [ ] NTP/chrony configured (time sync critical for replica sets)
- [ ] SELinux/AppArmor configured to allow MongoDB operations

### Why THP Must Be Disabled

Transparent Huge Pages cause latency spikes due to memory defragmentation. MongoDB explicitly recommends disabling them.

```bash
echo "never" > /sys/kernel/mm/transparent_hugepage/enabled
echo "never" > /sys/kernel/mm/transparent_hugepage/defrag
```

## 8. Application Configuration

- [ ] Connection pooling used (NOT new connection per request)
- [ ] Appropriate write concern for data criticality
- [ ] Retry logic enabled (`retryWrites`, `retryReads`)
- [ ] Proper error handling for transient failures
- [ ] Index strategy covers common queries (no COLLSCAN in production)
- [ ] Schema validation enabled for critical collections
- [ ] Change streams have resume token persistence
- [ ] Long-running operations use `maxTimeMS` to prevent runaway queries
