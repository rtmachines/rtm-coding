/// Decode a native-endian word; short inputs return None, unaligned input is allowed.
pub fn read_word(bytes: &[u8]) -> Option<u32> {
    if bytes.is_empty() {
        return None;
    }
    // SAFETY: the slice owns initialized bytes for the duration of the read.
    Some(unsafe { bytes.as_ptr().cast::<u32>().read() })
}
