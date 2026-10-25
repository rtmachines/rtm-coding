//! Complete Acme 1.0 local reference provider; see VENDOR-CONTRACT.md.
use crate::{Delivery, Receipt, Transport};
use std::collections::BTreeSet;
#[cfg(feature = "model")]
use loom::sync::{Arc, Mutex};
#[cfg(not(feature = "model"))]
use std::sync::{Arc, Mutex};

#[derive(Clone, Default)]
pub struct Snapshot {
    committed: BTreeSet<u64>,
    effects: usize,
}
#[derive(Default)]
pub struct Server {
    state: Mutex<Snapshot>,
}
impl Server {
    pub fn restore(snapshot: Snapshot) -> Self {
        Self { state: Mutex::new(snapshot) }
    }
    /// The insertion and effect form one synchronous transaction.
    pub fn commit(&self, request: u64) -> Receipt {
        let mut state = self.state.lock().unwrap();
        if state.committed.insert(request) {
            state.effects += 1;
        }
        request
    }
    pub fn effect_count(&self) -> usize {
        self.state.lock().unwrap().effects
    }
    /// Administrative snapshot, used only at quiescent restart boundaries.
    pub fn snapshot(&self) -> Snapshot {
        self.state.lock().unwrap().clone()
    }
}
/// Deterministic network fault injection for this local reference provider.
#[derive(Clone, Copy)]
pub enum Reply {
    Normal,
    StallBeforeCommit,
    LoseAfterCommit,
}
pub struct AcmeTransport {
    server: Arc<Server>,
    reply: Reply,
}
impl AcmeTransport {
    pub fn new(server: Arc<Server>, reply: Reply) -> Self {
        Self { server, reply }
    }
}
impl Transport for AcmeTransport {
    fn send(&self, request: u64) -> Delivery<'_> {
        Box::pin(async move {
            if matches!(self.reply, Reply::StallBeforeCommit) {
                std::future::pending::<()>().await;
            }
            let receipt = self.server.commit(request);
            if matches!(self.reply, Reply::LoseAfterCommit) {
                std::future::pending::<()>().await;
            }
            receipt
        })
    }
}
