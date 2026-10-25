#[cfg(feature = "model")]
use loom::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
#[cfg(not(feature = "model"))]
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

/// One-shot publication. The owner calls publish exactly once.
/// A reader observing Some must see the value passed to publish.
pub struct Published {
    value: AtomicUsize,
    ready: AtomicBool,
}
impl Default for Published {
    fn default() -> Self { Self { value: AtomicUsize::new(0), ready: AtomicBool::new(false) } }
}
impl Published {
    pub fn publish(&self, value: usize) {
        self.value.store(value, Ordering::Relaxed);
        self.ready.store(true, Ordering::Release);
    }
    pub fn snapshot(&self) -> Option<usize> {
        self.ready.load(Ordering::Acquire).then(|| self.value.load(Ordering::Relaxed))
    }
}
