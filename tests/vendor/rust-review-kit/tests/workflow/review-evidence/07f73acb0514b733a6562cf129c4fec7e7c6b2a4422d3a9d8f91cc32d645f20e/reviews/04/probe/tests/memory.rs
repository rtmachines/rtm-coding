use runtime_bridge::{registration::Registration,bytes::read_word};
use std::cell::Cell;
thread_local! {static SLOT: Cell<(*const u8,usize)>=const{Cell::new((std::ptr::null(),0))};}
unsafe extern "C" fn register(p:*const u8,n:usize){SLOT.with(|s|s.set((p,n)));}
fn read(){SLOT.with(|s|{let(p,n)=s.get();assert_eq!(unsafe{std::slice::from_raw_parts(p,n)},[7,8,9]);});}
unsafe extern "C" fn unregister(){read();SLOT.with(|s|s.set((std::ptr::null(),0)));}
#[test] fn retained_reads_after_move_and_during_unregister(){let r=unsafe{Registration::new(vec![7,8,9].into_boxed_slice(),register,unregister)};let moved=Box::new(r);assert_eq!(moved.len(),3);read();drop(moved);SLOT.with(|s|assert!(s.get().0.is_null()));}
#[test] fn arbitrary_alignment_and_short(){let b=[0,1,2,3,4,5,6,7]; for n in 0..4{assert_eq!(read_word(&b[..n]),None);} for offset in 0..4{assert_eq!(read_word(&b[offset..]),Some(u32::from_ne_bytes(b[offset..offset+4].try_into().unwrap())));}}
