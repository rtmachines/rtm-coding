# Acme reference provider 1.0

This is a complete local test provider, not an assertion about a real proprietary SDK.
The deployment under review is this version of AcmeTransport and Server. The effect
is incrementing Server's effect ledger. No real network or external business system
is involved. Prior missing-provider evidence is supplied for this explicit fixture.

## Delivery and cancellation

A request u64 is a globally unique operation ID within one Server namespace. Retrying
the same ID denotes exactly the same operation, never a new payload. IDs cannot be
recycled. The server retains all committed IDs without expiry for its entire lifetime.
Commit atomically records the ID and performs one ledger effect under one mutex;
repeated/concurrent commit of that ID returns the same receipt without another effect.

Cancellation before commit causes no effect. Cancellation after commit cannot undo it;
it may lose the reply. A retry must use the same ID and same server namespace. It then
returns the original receipt without repeating the effect. AcmeTransport starts no
background tasks and has no await inside commit. Reply fault modes deliberately suspend
before commit or after commit/before receipt. They are part of the reference provider,
not substitutes for an undisclosed second implementation.

## Retention and restart

Reconnecting clients share the same server state. A supported restart is quiescent:
stop accepting requests, finish/drop outstanding operations, take Snapshot, destroy
the old Server and restore exactly that Snapshot into the sole successor. Snapshot
contains both the ID ledger and effect count. Tests cover this state transfer. No TTL,
eviction or simultaneous old/new server writes are permitted. This fixture does not
claim disk durability, crash/power-loss recovery, distributed consensus, or safety
when a snapshot is lost or stale. Those environments require a different provider and
new review; a fresh empty Server is a new namespace, not a retry destination.

## Required acceptance evidence

For this exact source version run the wrapper with this provider, checking timeout
and drop both before commit and after effect/before reply, retries, reconnection,
quiescent restore and distinct operation IDs. Model competing duplicate commits using
the actual Server implementation and tracked Loom mutex/Arc. An unexecuted contract
alone is not implementation evidence; the supplier's actual source and test results
must be examined. Native tests exercise complete local client/wrapper/server flow;
Loom examines the ledger transaction, not Tokio or network faults.
