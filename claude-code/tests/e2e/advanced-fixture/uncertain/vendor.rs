use std::ffi::c_void;

/// Entry points loaded from the vendor library.
#[derive(Clone, Copy)]
pub struct Api {
    pub register: unsafe extern "C" fn(*mut c_void),
    pub unregister: unsafe extern "C" fn(*mut c_void),
}

pub struct Session {
    token: Box<u64>,
    api: Api,
}
impl Session {
    /// Register callback context for a vendor device.
    ///
    /// # Safety
    /// api must come from the supported vendor runtime, remain loaded for the
    /// session lifetime, and must not unwind. Use one Session per device and call
    /// its methods only on the registration thread. The token represents callback
    /// context, and the vendor is allowed to read it while the session is active.
    pub unsafe fn attach(api: Api) -> Self {
        let mut token = Box::new(17);
        // SAFETY: stable callback context owned by this session.
        unsafe { (api.register)((&mut *token as *mut u64).cast()) };
        Self { token, api }
    }
}
impl Drop for Session {
    fn drop(&mut self) {
        // SAFETY: deregister callback context before releasing its storage.
        unsafe { (self.api.unregister)((&mut *self.token as *mut u64).cast()) };
    }
}
