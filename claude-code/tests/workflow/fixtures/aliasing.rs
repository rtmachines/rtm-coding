mod registration;
mod bytes;
#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;
    thread_local! { static POINTER: Cell<(*const u8, usize)> = const { Cell::new((std::ptr::null(), 0)) }; }
    unsafe extern "C" fn register(p: *const u8, n: usize) { POINTER.set((p,n)); }
    fn read_retained() {
        let (p,n) = POINTER.get();
        if n != 0 { assert_eq!(unsafe { std::slice::from_raw_parts(p,n) }, &[1,2,3,4]); }
    }
    unsafe extern "C" fn unregister() { read_retained(); POINTER.set((std::ptr::null(),0)); }
    #[inline(never)]
    fn moved(r: registration::Registration) -> registration::Registration { r }
    #[test]
    fn retained_after_constructor_and_owner_move() {
        let r = unsafe { registration::Registration::new(vec![1,2,3,4].into_boxed_slice(),register,unregister) };
        read_retained();
        let r = moved(r);
        assert_eq!(r.len(),4); assert!(!r.is_empty());
        read_retained();
        drop(r);
        assert!(POINTER.get().0.is_null());
    }
    #[test]
    fn unregister_reads_before_quiescence() {
        let r = unsafe { registration::Registration::new(vec![1,2,3,4].into_boxed_slice(),register,unregister) };
        drop(r);
        assert!(POINTER.get().0.is_null());
    }
    #[test]
    fn empty_registration() {
        let r = unsafe { registration::Registration::new(Vec::new().into_boxed_slice(),register,unregister) };
        assert!(r.is_empty()); drop(r);
    }
    #[test]
    fn arbitrary_alignment_and_short_input() {
        #[repr(align(4))] struct Aligned([u8;8]);
        let b = Aligned([0,1,2,3,4,5,6,7]);
        for offset in 0..4 { assert_eq!(bytes::read_word(&b.0[offset..]),Some(u32::from_ne_bytes(b.0[offset..offset+4].try_into().unwrap()))); }
        for len in 0..4 { assert_eq!(bytes::read_word(&b.0[..len]),None); }
    }
}
