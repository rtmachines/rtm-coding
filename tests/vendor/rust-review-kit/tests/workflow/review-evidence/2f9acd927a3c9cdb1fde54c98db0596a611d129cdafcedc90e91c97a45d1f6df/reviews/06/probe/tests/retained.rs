use memory_probe::{registration::Registration,bytes::read_word};
use std::cell::Cell;
thread_local! {static PTR: Cell<*const u8> = const {Cell::new(std::ptr::null())}; static READ: Cell<u8> = const {Cell::new(0)};}
unsafe extern "C" fn retain(p:*const u8,_:usize) {PTR.with(|x|x.set(p));}
unsafe extern "C" fn release() {let v=PTR.with(|x|unsafe{x.get().read()});READ.with(|x|x.set(v));PTR.with(|x|x.set(std::ptr::null()));}
#[test] fn retained_read_during_unregister_after_move() {
let r=unsafe{Registration::new(vec![42].into_boxed_slice(),retain,release)};
let moved=std::hint::black_box(r);assert_eq!(moved.len(),1);
assert_eq!(PTR.with(|x|unsafe{x.get().read()}),42);drop(moved);
assert_eq!(READ.with(|x|x.get()),42);assert!(PTR.with(|x|x.get().is_null()));
}
#[test] fn arbitrary_alignment_and_short_inputs() {
let data=[0,1,2,3,4,5,6,7];for start in 0..4 {assert_eq!(read_word(&data[start..]),Some(u32::from_ne_bytes(data[start..start+4].try_into().unwrap())));}
for n in 0..4 {assert_eq!(read_word(&data[..n]),None);}
}
