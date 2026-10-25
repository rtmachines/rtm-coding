
use ledger_preview::*;
#[test] fn parse_boundaries() {
 for raw in ["", "abc", "-1", "65536", "999999999999999999999999", "1.5"] { assert_eq!(parse_limit(raw),None); }
 for (raw,value) in [("0",0),("1",1),("65535",65535)] { assert_eq!(parse_limit(raw),Some(value)); }
}
#[test] fn preserved_contracts() {
 let a=Identity{tenant_id:1,user_id:2};
 assert!(!can_read(a,Identity{tenant_id:9,user_id:2}));
 assert!(!can_read(a,Identity{tenant_id:1,user_id:9}));
 assert_eq!(debit(1,2),None);assert_eq!(debit(1,1),Some(0));
 assert_eq!(preview("é🦀x",2),"é🦀");assert_eq!(preview("é",0),"");
 assert!(!token_usable(5,5));
 assert_eq!(fee(u32::MAX,u32::MAX),(u32::MAX as u128*u32::MAX as u128/10000) as u64);
 assert_eq!(fee(1999,250),49);
}
