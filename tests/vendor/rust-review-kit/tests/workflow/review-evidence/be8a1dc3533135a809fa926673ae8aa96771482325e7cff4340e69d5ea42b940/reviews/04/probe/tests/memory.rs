use runtime_bridge::registration::Registration;
use std::cell::Cell;
thread_local! { static SAVED: Cell<(*const u8,usize)> = const {Cell::new((std::ptr::null(),0))}; }
unsafe extern "C" fn register(p:*const u8,n:usize){SAVED.set((p,n));}
fn read_saved(){let(p,n)=SAVED.get();assert_eq!(unsafe{std::slice::from_raw_parts(p,n)},&[3,5,7]);}
unsafe extern "C" fn unregister(){read_saved();SAVED.set((std::ptr::null(),0));}
#[test]
fn retained_read_after_return_move_and_unregister(){
 let r=unsafe{Registration::new(vec![3,5,7].into_boxed_slice(),register,unregister)};
 read_saved();let moved=Box::new(r);read_saved();assert_eq!(moved.len(),3);read_saved();drop(moved);assert!(SAVED.get().0.is_null());
}
