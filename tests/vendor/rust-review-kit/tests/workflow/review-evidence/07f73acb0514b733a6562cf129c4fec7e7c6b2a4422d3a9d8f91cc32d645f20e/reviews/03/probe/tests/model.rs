#[cfg(feature="model")]
#[test] fn publication(){loom::model(|| {let p=loom::sync::Arc::new(runtime_bridge::publication::Published::default());let w=p.clone();let writer=loom::thread::spawn(move||w.publish(42));if let Some(v)=p.snapshot(){assert_eq!(v,42);}writer.join().unwrap();});}
