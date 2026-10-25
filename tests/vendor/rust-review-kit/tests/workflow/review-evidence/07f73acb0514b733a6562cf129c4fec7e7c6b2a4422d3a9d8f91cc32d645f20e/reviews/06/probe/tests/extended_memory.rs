use runtime_bridge::{bytes::read_word,registration::Registration};
use std::cell::Cell;
thread_local! {static RETAINED: Cell<(*const u8,usize)> = const {Cell::new((std::ptr::null(),0))};}
unsafe extern "C" fn register(p:*const u8,n:usize){RETAINED.with(|s|s.set((p,n)));}
unsafe extern "C" fn unregister(){RETAINED.with(|s|{let(p,n)=s.get();if n>0 {assert_eq!(unsafe{*p},42);assert_eq!(unsafe{*p.add(n-1)},43);}s.set((std::ptr::null(),0));});}
#[test] fn retained_reads_through_unregister_after_move(){
 let r=unsafe{Registration::new(vec![42,43].into_boxed_slice(),register,unregister)};
 let r=Some(r);assert_eq!(r.as_ref().unwrap().len(),2);
 RETAINED.with(|s|assert_eq!(unsafe{*s.get().0},42));drop(r);
 assert!(RETAINED.with(|s|s.get().0.is_null()));
}
#[test] fn empty_registration(){let r=unsafe{Registration::new(Vec::new().into_boxed_slice(),register,unregister)};assert!(r.is_empty());drop(r);}
#[test] fn every_offset_and_short_length(){let bytes=[1,2,3,4,5,6,7,8];for offset in 0..4 {assert_eq!(read_word(&bytes[offset..]),Some(u32::from_ne_bytes(bytes[offset..offset+4].try_into().unwrap())));}for n in 0..4 {assert_eq!(read_word(&bytes[..n]),None);}}
