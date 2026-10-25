/// C-ABI registration retains a read-only buffer until unregister returns.
pub struct Registration {
    bytes: *mut [u8],
    len: usize,
    unregister: unsafe extern "C" fn(),
}
impl Registration {
    /// Register a stable buffer with a foreign consumer.
    ///
    /// # Safety
    /// Callbacks must form one valid registration pair. register may retain and read
    /// the provided range but cannot write or free it. unregister must synchronously
    /// stop all reads before returning and must not unwind. Calls must be serialized
    /// by the owner; no other registration may replace the active one.
    pub unsafe fn new(bytes: Box<[u8]>, register: unsafe extern "C" fn(*const u8, usize), unregister: unsafe extern "C" fn()) -> Self {
        let len = bytes.len();
        let bytes = Box::into_raw(bytes);
        // SAFETY: allocation ownership stays with this raw-pointer owner. No Box
        // or reference is recreated until all foreign reads have stopped.
        unsafe { register(bytes.cast::<u8>(), len) };
        Self { bytes, len, unregister }
    }
    pub fn len(&self) -> usize { self.len }
    pub fn is_empty(&self) -> bool { self.len == 0 }
}
impl Drop for Registration {
    fn drop(&mut self) {
        // SAFETY: constructor contract guarantees synchronous quiescence.
        unsafe { (self.unregister)() };
        // SAFETY: this owns the original Box allocation; unregister stopped all
        // reads and no other owner frees it. Reconstruct exactly once.
        unsafe { drop(Box::from_raw(self.bytes)) };
    }
}
