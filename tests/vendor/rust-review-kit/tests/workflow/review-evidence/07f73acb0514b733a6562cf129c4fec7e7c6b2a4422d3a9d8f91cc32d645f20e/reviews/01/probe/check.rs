#[path="lib.rs"] mod subject;
use subject::*;
#[test] fn tenant_isolation(){assert!(!can_read(Identity{tenant_id:1,user_id:7},Identity{tenant_id:2,user_id:7}));}
#[test] fn overdraft(){assert_eq!(debit(1,2),None);}
#[test] fn unicode(){assert_eq!(preview("éx",1),"é");}
#[test] fn exact_expiry(){assert!(!token_usable(100,100));}
#[test] fn fractional_fee(){assert_eq!(fee(1999,250),49);}
#[test] fn malformed_limit(){assert_eq!(parse_limit("x"),None);}
#[test] fn negative_limit(){assert_eq!(parse_limit("-1"),None);}
#[test] fn oversized_limit(){assert_eq!(parse_limit("65536"),None);}
