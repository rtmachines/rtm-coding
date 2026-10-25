use runtime_bridge::Published;
#[test] fn initial_none_and_one_shot_values(){for value in [0,42,usize::MAX] {let p=Published::default();assert_eq!(p.snapshot(),None);p.publish(value);assert_eq!(p.snapshot(),Some(value));}}
#[test] fn thread_publication(){let p=std::sync::Arc::new(Published::default());let writer=p.clone();let t=std::thread::spawn(move||writer.publish(42));if let Some(v)=p.snapshot(){assert_eq!(v,42);}t.join().unwrap();assert_eq!(p.snapshot(),Some(42));}
