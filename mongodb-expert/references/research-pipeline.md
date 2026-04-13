# Research Pipeline — Deep Reference

## Table of Contents
1. Search Strategy
2. Source Hierarchy
3. Cross-Validation Protocol
4. Version Verification
5. Confidence Rating System
6. Common Research Patterns

## 1. Search Strategy

### Primary Searches (always execute)

```
# Official manual - most authoritative
site:mongodb.com/docs/manual/<topic>

# Version-specific
site:mongodb.com/docs/v8.0/<topic>

# Release notes for breaking changes
site:mongodb.com/docs/manual/release-notes/<version>
```

### Secondary Searches (when primary is insufficient)

```
# Jira for known bugs
site:jira.mongodb.org <topic> <version>

# Engineering blog for deep internals
site:mongodb.com/blog <topic>

# GitHub source for implementation details
site:github.com/mongodb/mongo <topic>
```

### Search Query Templates by Domain

| Domain | Query Template |
|--------|---------------|
| ReplicaSet | `mongodb replica set <specific_topic> docs` |
| WiredTiger | `mongodb wiredtiger <specific_topic> storage engine` |
| Oplog | `mongodb oplog <specific_topic> replication` |
| TimeSeries | `mongodb time series collection <specific_topic>` |
| Performance | `mongodb performance <specific_topic> explain` |
| Indexes | `mongodb index <type> <specific_topic>` |
| Aggregation | `mongodb aggregation pipeline <stage> <specific_topic>` |

## 2. Source Hierarchy

When sources conflict, follow this priority:

1. **Official Manual for exact version** — mongodb.com/docs/v{VERSION}/
2. **Release Notes for exact version** — changelog of what changed
3. **MongoDB Jira** — confirmed bugs and known issues
4. **Official Blog** — engineering context, BUT may reference older versions
5. **Community sources** — Stack Overflow, forums (LOWEST trust — always verify)

NEVER cite a community source as authoritative. If you can only find community sources, rate confidence as LOW.

## 3. Cross-Validation Protocol

For every critical fact:

1. Find it in the official manual
2. Check if release notes mention changes to it
3. Check if there are open Jira tickets affecting it
4. If the fact involves a parameter: verify the parameter exists using `db.adminCommand({getParameter: "*"})` or docs

### Red Flags During Research

- A blog post says one thing, docs say another → docs win
- A Stack Overflow answer uses deprecated syntax → ignore it
- Documentation page hasn't been updated for the target version → flag as MEDIUM confidence
- Feature is marked "beta" or "experimental" → flag explicitly

## 4. Version Verification

### How to Verify Version-Specific Behavior

1. Check the URL: `mongodb.com/docs/v8.0/...` vs `mongodb.com/docs/manual/...` (manual = latest)
2. Look for "New in version X.Y" badges in the docs
3. Look for "Changed in version X.Y" badges
4. Look for "Deprecated since version X.Y" badges
5. Check release notes: `mongodb.com/docs/manual/release-notes/{version}/`

### Version-Specific URL Patterns

```
# Specific version docs
https://www.mongodb.com/docs/v8.0/
https://www.mongodb.com/docs/v7.0/

# Latest (follows current release)
https://www.mongodb.com/docs/manual/

# Release notes
https://www.mongodb.com/docs/manual/release-notes/8.0/
```

## 5. Confidence Rating System

### HIGH Confidence
- Confirmed in official docs for exact target version
- Parameter/command verified to exist
- No conflicting information found
- No open Jira bugs affecting this

### MEDIUM Confidence
- Confirmed in official docs but for a DIFFERENT version
- No breaking changes found in release notes between versions
- OR: confirmed in docs but Jira shows an open bug

### LOW Confidence
- Only found in blog posts, community sources, or training data
- Could not verify in official docs
- OR: conflicting information between sources
- OR: feature marked as experimental/beta

### UNVERIFIED
- Could not find any authoritative source
- Must be disclosed to user: "I could not verify this against official documentation"
- NEVER present unverified information as fact

## 6. Common Research Patterns

### "What's the default value of X?"
1. Search: `site:mongodb.com/docs/v{VERSION} <parameter_name>`
2. Check the Configuration Options page: `/reference/configuration-options/`
3. Check if the default changed in release notes
4. Verify with: `db.adminCommand({getParameter: 1, <parameter>: 1})`

### "Is X safe to run in production?"
1. Search official docs for the command/operation
2. Check "Considerations" or "Behavior" sections
3. Search Jira for bugs: `<command> production issue`
4. Check if there's a "Production Notes" page covering it

### "How do I configure X?"
1. Search official docs for the configuration reference
2. Check version compatibility
3. Look for "Examples" section in the docs
4. Verify parameter names and types match the target version

### "Why is X slow?"
1. Start with `references/performance.md`
2. Check explain plan documentation for the target version
3. Search for known performance issues in Jira
4. Verify diagnostic commands exist in the target version
