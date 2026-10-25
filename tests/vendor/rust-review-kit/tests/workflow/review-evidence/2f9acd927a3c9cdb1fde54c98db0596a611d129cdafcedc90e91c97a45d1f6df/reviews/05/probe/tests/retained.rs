use memory_probe::{Session,Api};
use std::{cell::Cell,ffi::c_void};
thread_local! {static PTR: Cell<*const u64> = const {Cell::new(std::ptr::null())};}
unsafe extern "C" fn retain(p:*mut c_void) {PTR.with(|x| x.set(p.cast()));}
unsafe extern "C" fn release(_: *mut c_void) {PTR.with(|x| x.set(std::ptr::null()));}
#[test] fn retained_read_after_move() {
// Conditional shim: implements read-only retention, same-thread non-unwinding callbacks.
// Not claimed to be the supported vendor runtime or proof of its contract.
let s=unsafe {Session::attach(Api{register:retain,unregister:release})};
let moved=std::hint::black_box(s);
assert_eq!(PTR.with(|x| unsafe{x.get().read()}),17);
drop(moved);
assert!(PTR.with(|x|x.get().is_null()));
}
