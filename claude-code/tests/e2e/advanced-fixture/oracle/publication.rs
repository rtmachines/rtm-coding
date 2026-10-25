#[cfg(feature = "model")]
#[test]
fn publication_is_coherent() {
    loom::model(|| {
        let published = loom::sync::Arc::new(runtime_bridge::publication::Published::default());
        let writer = published.clone();
        let task = loom::thread::spawn(move || writer.publish(42));
        if let Some(value) = published.snapshot() { assert_eq!(value, 42); }
        task.join().unwrap();
    });
}
