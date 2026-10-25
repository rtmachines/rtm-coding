/// Decode a native-endian word; short inputs return None, unaligned input is allowed.
pub fn read_word(bytes: &[u8]) -> Option<u32> {
    let raw: [u8; 4] = bytes.get(..4)?.try_into().ok()?;
    Some(u32::from_ne_bytes(raw))
}
