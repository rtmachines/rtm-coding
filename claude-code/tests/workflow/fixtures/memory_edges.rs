#![cfg(miri)]
use runtime_bridge::{bytes::read_word,registration::Registration};
use std::cell::Cell;
#[repr(align(4))] struct Aligned([u8;8]);
#[test]fn empty(){assert_eq!(read_word(&[]),None);}
#[test]fn aligned_word(){let a=Aligned([1,2,3,4,5,6,7,8]);assert_eq!(read_word(&a.0),Some(u32::from_ne_bytes([1,2,3,4])));}
#[test]fn short_one(){let a=vec![1].into_boxed_slice();assert_eq!(read_word(&a),None);}
#[test]fn short_two(){let a=vec![1,2].into_boxed_slice();assert_eq!(read_word(&a),None);}
#[test]fn short_three(){let a=vec![1,2,3].into_boxed_slice();assert_eq!(read_word(&a),None);}
#[test]fn unaligned_word(){let a=Aligned([1,2,3,4,5,6,7,8]);assert_eq!(read_word(&a.0[1..5]),Some(u32::from_ne_bytes([2,3,4,5])));}
thread_local!{static PTR:Cell<*const u8>=const{Cell::new(std::ptr::null())};}
unsafe extern "C" fn register(p:*const u8,n:usize){assert_eq!(n,3);assert_eq!(unsafe{*p},7);PTR.with(|v|v.set(p));}
unsafe extern "C" fn unregister(){PTR.with(|v|{assert_eq!(unsafe{*v.get()},7);v.set(std::ptr::null());});}
#[test]fn registration_read_after_move(){let r=unsafe{Registration::new(vec![7,8,9].into_boxed_slice(),register,unregister)};let moved=Box::new(r);assert_eq!(moved.len(),3);PTR.with(|v|assert_eq!(unsafe{*v.get()},7));drop(moved);}
#[test]fn registration_read_during_unregister(){let r=unsafe{Registration::new(vec![7,8,9].into_boxed_slice(),register,unregister)};drop(r);}
