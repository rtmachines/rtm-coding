use runtime_bridge::vendor::{Api, Session};
use std::{cell::Cell,ffi::c_void};
thread_local! {static SAVED: Cell<*const u64> = const {Cell::new(std::ptr::null())};}
unsafe extern "C" fn register(p:*mut c_void) { SAVED.with(|x|x.set(p.cast())); }
unsafe extern "C" fn unregister(_: *mut c_void) {SAVED.with(|x| {assert_eq!(unsafe{x.get().read()},17);x.set(std::ptr::null());});}
#[test]
fn retained_context_after_move_and_during_unregister() {
 // Assumed synchronous, same-thread read-only vendor contract; actual vendor is unavailable.
 let session=unsafe{Session::attach(Api{register,unregister})};
 let moved=Box::new(session);
 assert_eq!(SAVED.with(|x|unsafe{x.get().read()}),17);
 drop(moved);
 assert!(SAVED.with(|x|x.get().is_null()));
}
