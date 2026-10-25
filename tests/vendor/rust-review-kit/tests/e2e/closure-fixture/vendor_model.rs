#![cfg(feature = "model")]
use runtime_bridge::acme::Server;
#[test]
fn competing_retries_commit_once() {
    let mut builder = loom::model::Builder::new();
    builder.max_threads = 3;
    builder.max_branches = 1000;
    builder.max_permutations = None;
    builder.max_duration = None;
    builder.preemption_bound = None;
    builder.check(|| {
        let server = loom::sync::Arc::new(Server::default());
        let other = server.clone();
        let writer = loom::thread::spawn(move || other.commit(7));
        assert_eq!(server.commit(7), 7);
        assert_eq!(writer.join().unwrap(), 7);
        assert_eq!(server.effect_count(), 1);
        assert_eq!(server.commit(8), 8);
        assert_eq!(server.effect_count(), 2);
    });
}
