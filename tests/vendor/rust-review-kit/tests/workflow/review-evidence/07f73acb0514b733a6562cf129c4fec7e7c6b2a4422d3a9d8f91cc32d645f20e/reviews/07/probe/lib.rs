#[cfg(feature = "model")]
use loom::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
#[cfg(not(feature = "model"))]
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

#[derive(Default)]
pub struct Published {
    value: AtomicUsize,
    ready: AtomicBool,
}
impl Published {
    /// The caller publishes at most once, from one writer.
    pub fn publish(&self, value: usize) {
        self.value.store(value, Ordering::Relaxed);
        self.ready.store(true, Ordering::Release);
    }
    pub fn snapshot(&self) -> Option<usize> {
        self.ready
            .load(Ordering::Acquire)
            .then(|| self.value.load(Ordering::Relaxed))
    }
}
