use memory_probe::{bytes::read_word, registration::Registration};
use std::cell::Cell;
thread_local! {static RETAINED: Cell<(*const u8,usize)> = const {Cell::new((std::ptr::null(),0))};}
unsafe extern "C" fn register(p: *const u8,n: usize){ RETAINED.set((p,n)); }
fn read_retained(){let(p,n)=RETAINED.get();assert_eq!(unsafe {std::slice::from_raw_parts(p,n)}, &[1,2,3,4]);}
unsafe extern "C" fn unregister(){read_retained();RETAINED.set((std::ptr::null(),0));}
#[test] fn retained_after_move_and_during_unregister(){
 let r=unsafe{Registration::new(vec![1,2,3,4].into_boxed_slice(),register,unregister)};
 let moved=Box::new(r);assert_eq!(moved.len(),4);read_retained();drop(moved);assert_eq!(RETAINED.get().1,0);
}
#[test] fn unaligned_and_short(){let b=[0,1,2,3,4,5];assert_eq!(read_word(&b[1..]),Some(u32::from_ne_bytes([1,2,3,4])));for n in 0..4{assert_eq!(read_word(&b[..n]),None);}}
