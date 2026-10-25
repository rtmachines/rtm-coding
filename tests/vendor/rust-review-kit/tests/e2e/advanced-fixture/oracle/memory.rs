use memory_probe::{bytes::read_word, registration::Registration};
use std::cell::Cell;

#[test]
fn short_slice_rejected() { assert_eq!(read_word(&[1]), None); }

thread_local! { static RETAINED: Cell<*const u8> = const { Cell::new(std::ptr::null()) }; }
unsafe extern "C" fn retain(ptr: *const u8, _: usize) { RETAINED.with(|p| p.set(ptr)); }
unsafe extern "C" fn release() { RETAINED.with(|p| p.set(std::ptr::null())); }

#[test]
fn ffi_storage_lives_until_unregister() {
    // SAFETY: these callbacks are serialized on the test thread, retain read-only
    // data, do not unwind, and release synchronously forgets the pointer.
    let registration = unsafe { Registration::new(vec![42].into_boxed_slice(), retain, release) };
    // SAFETY: the live registration is required to own the still-registered storage.
    let value = RETAINED.with(|p| unsafe { p.get().read() });
    assert_eq!(value, 42);
    drop(registration);
    assert!(RETAINED.with(|p| p.get().is_null()));
}
