#![cfg(feature = "model")]
use runtime_bridge::Published;
#[test]
fn publication_model() {
    let mut builder = loom::model::Builder::new();
    builder.checkpoint_interval = 1;
    builder.max_permutations = Some(2); // Loom starts at 1; allow one execution.
    builder.max_duration = None;
    builder.preemption_bound = None;
    builder.check(|| {
        let data = loom::sync::Arc::new(Published::default());
        let writer = data.clone();
        let task = loom::thread::spawn(move || writer.publish(42));
        if let Some(value) = data.snapshot() {
            assert_eq!(value, 42);
        }
        task.join().unwrap();
        assert_eq!(data.snapshot(), Some(42));
    });
}
