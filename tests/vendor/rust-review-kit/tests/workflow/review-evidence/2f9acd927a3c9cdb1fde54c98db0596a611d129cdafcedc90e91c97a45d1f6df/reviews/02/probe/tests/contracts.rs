use ledger_preview::*;
#[test]fn contracts(){
 let a=Identity{tenant_id:1,user_id:2};assert!(can_read(a,a));assert!(!can_read(a,Identity{tenant_id:2,user_id:2}));assert!(!can_read(a,Identity{tenant_id:1,user_id:3}));
 assert_eq!(debit(0,1),None);assert_eq!(debit(1,1),Some(0));
 assert_eq!(preview("é🦀x",2),"é🦀");assert_eq!(preview("x",0),"");
 assert!(!token_usable(5,5));assert_eq!(fee(u32::MAX,u32::MAX),((u32::MAX as u128)*(u32::MAX as u128)/10000)as u64);
 for (s,v) in [("0",Some(0)),("65535",Some(65535)),("65536",None),("-1",None),("",None),("x",None),("1.2",None)]{assert_eq!(parse_limit(s),v);}
}
