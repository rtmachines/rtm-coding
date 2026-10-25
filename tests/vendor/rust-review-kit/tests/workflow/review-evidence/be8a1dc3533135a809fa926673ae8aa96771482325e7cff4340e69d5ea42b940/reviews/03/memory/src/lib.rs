
pub mod bytes;pub mod registration;
#[cfg(test)] mod tests {
 use super::*;
 #[repr(align(4))] struct Aligned([u8;8]);
 #[test] fn unaligned_word() {let b=Aligned([1;8]);assert_eq!(bytes::read_word(&b.0[1..5]),Some(u32::from_ne_bytes([1;4])));}
 #[test] fn short_word() {let b=Box::new([1u8]);assert_eq!(bytes::read_word(&b[..]),None);}
 static mut RETAINED:*const u8=std::ptr::null();
 unsafe extern "C" fn register(p:*const u8,_:usize){unsafe{RETAINED=p;}}
 unsafe extern "C" fn unregister(){unsafe{assert_eq!(*RETAINED,7);RETAINED=std::ptr::null();}}
 #[test] fn retained_until_unregister(){
 let registration=unsafe{registration::Registration::new(vec![7].into_boxed_slice(),register,unregister)};
 let moved=Box::new(registration);
 unsafe{assert_eq!(*RETAINED,7);}
 drop(moved);
 }
}
