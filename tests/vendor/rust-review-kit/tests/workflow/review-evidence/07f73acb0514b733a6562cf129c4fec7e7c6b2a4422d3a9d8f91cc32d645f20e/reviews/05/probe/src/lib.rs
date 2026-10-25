mod vendor;
#[cfg(test)] mod tests {
use super::vendor::*;
use std::{cell::Cell,ffi::c_void};
thread_local! { static RETAINED: Cell<*mut u64> = const {Cell::new(std::ptr::null_mut())}; }
unsafe extern "C" fn register(p:*mut c_void) { RETAINED.with(|s|s.set(p.cast())); }
unsafe extern "C" fn unregister(_: *mut c_void) { RETAINED.with(|s|s.set(std::ptr::null_mut())); }
#[test] fn retained_read_after_return_and_move() {
 let s=unsafe {Session::attach(Api{register,unregister})};
 let moved=Some(s);
 RETAINED.with(|s| assert_eq!(unsafe {*s.get()},17));
 drop(moved);
 RETAINED.with(|s|assert!(s.get().is_null()));
}
}
