use runtime_bridge::{bytes::read_word,registration::Registration};
#[test] fn short_word(){let b=Box::new([1u8]);assert_eq!(read_word(&*b),None);}
#[test] fn unaligned_word(){#[repr(align(4))]struct Aligned([u8;8]);let b=Aligned([1;8]);assert_eq!(read_word(&b.0[1..5]),Some(u32::from_ne_bytes([1;4])));}
static mut PTR:*const u8=std::ptr::null();
unsafe extern "C" fn register(p:*const u8,_n:usize){unsafe{PTR=p;}}
unsafe extern "C" fn unregister(){unsafe{let _=std::ptr::read_volatile(PTR);PTR=std::ptr::null();}}
#[test] fn registration_retained(){let r=unsafe{Registration::new(vec![7].into_boxed_slice(),register,unregister)};let moved=Box::new(r);unsafe{assert_eq!(*PTR,7);}drop(moved);}
