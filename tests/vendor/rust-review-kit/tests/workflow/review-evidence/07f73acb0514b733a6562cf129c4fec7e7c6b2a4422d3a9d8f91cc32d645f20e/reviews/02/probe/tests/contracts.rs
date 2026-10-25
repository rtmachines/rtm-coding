use ledger_preview::*;
#[test] fn parse_boundaries(){ for (s,want) in [("0",Some(0)),("65535",Some(65535)),("65536",None),("-1",None),("abc",None),("",None)] {assert_eq!(parse_limit(s),want);} }
#[test] fn retained_contracts(){let a=Identity{tenant_id:1,user_id:7};assert!(!can_read(a,Identity{tenant_id:2,user_id:7})); assert!(!can_read(a,Identity{tenant_id:1,user_id:8})); assert_eq!(debit(0,1),None);assert_eq!(preview("é🦀x",2),"é🦀");assert!(!token_usable(100,100));assert_eq!(fee(u32::MAX,u32::MAX),1_844_674_406_511_961);}
