mod bytes;mod registration;
#[cfg(test)]mod probes {
 use super::*;
 #[test] fn short_word(){let b=Box::new([1u8]);assert_eq!(bytes::read_word(&*b),None);}
 #[test] fn unaligned_word(){#[repr(align(4))]struct A([u8;8]);let b=A([1;8]);assert_eq!(bytes::read_word(&b.0[1..5]),Some(u32::from_ne_bytes([1;4])));}
 static mut RETAINED:*const u8=std::ptr::null();
 unsafe extern "C" fn register(p:*const u8,_:usize){unsafe{RETAINED=p;}}
 unsafe extern "C" fn unregister(){unsafe{assert_eq!(*RETAINED,7);RETAINED=std::ptr::null();}}
 #[test] fn retained_buffer(){let r=unsafe{registration::Registration::new(vec![7u8].into_boxed_slice(),register,unregister)};let moved=Box::new(r);unsafe{assert_eq!(*RETAINED,7);}drop(moved);}
 #[test] fn unregister_retained_buffer(){let r=unsafe{registration::Registration::new(vec![7u8].into_boxed_slice(),register,unregister)};drop(Box::new(r));}
}
