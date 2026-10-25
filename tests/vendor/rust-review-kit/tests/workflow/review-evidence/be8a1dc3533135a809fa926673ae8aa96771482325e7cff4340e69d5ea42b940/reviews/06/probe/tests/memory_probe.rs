use runtime_bridge::{bytes::read_word,registration::Registration};
use std::cell::Cell;
thread_local!{static SAVED:Cell<(*const u8,usize)>=const{Cell::new((std::ptr::null(),0))};}
unsafe extern "C" fn register(p:*const u8,n:usize){SAVED.with(|x|x.set((p,n)));}
unsafe extern "C" fn unregister(){SAVED.with(|x|{let(p,n)=x.get();if n>0 {assert_eq!(unsafe{p.read()},42);}x.set((std::ptr::null(),0));});}
#[test]
fn reads_after_owner_move_and_during_unregister(){
 let owner=unsafe{Registration::new(vec![42,8].into_boxed_slice(),register,unregister)};
 let moved=Box::new(owner);assert_eq!(moved.len(),2);assert!(!moved.is_empty());
 assert_eq!(SAVED.with(|x|unsafe{x.get().0.read()}),42);
 drop(moved);assert!(SAVED.with(|x|x.get().0.is_null()));
}
#[test]
fn empty_registration(){let r=unsafe{Registration::new(Vec::new().into_boxed_slice(),register,unregister)};assert!(r.is_empty());drop(r);}
#[test]
fn byte_alignment_and_bounds(){let bytes=[1u8,2,3,4,5,6,7,8];for offset in 0..4{assert_eq!(read_word(&bytes[offset..]),Some(u32::from_ne_bytes(bytes[offset..offset+4].try_into().unwrap())));}for len in 0..4{assert_eq!(read_word(&bytes[..len]),None);}}
