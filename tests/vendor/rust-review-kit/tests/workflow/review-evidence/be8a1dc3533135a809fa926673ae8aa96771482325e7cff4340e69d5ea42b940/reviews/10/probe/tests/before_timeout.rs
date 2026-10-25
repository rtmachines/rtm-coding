use runtime_bridge::{Outcome,acme::{AcmeTransport,Reply,Server},deliver};
use std::{sync::Arc,time::Duration};
#[tokio::test]
async fn timeout_before_commit_then_retry(){let s=Arc::new(Server::default());let stalled=AcmeTransport::new(s.clone(),Reply::StallBeforeCommit);assert_eq!(deliver(&stalled,17,Duration::ZERO).await,Outcome::Retry(17));assert_eq!(s.effect_count(),0);let retry=AcmeTransport::new(s.clone(),Reply::Normal);assert_eq!(deliver(&retry,17,Duration::from_secs(1)).await,Outcome::Delivered(17));assert_eq!(s.effect_count(),1);}
