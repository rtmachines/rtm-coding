use ledger_preview::*;
#[test]fn tenant_isolation(){assert!(!can_read(Identity{tenant_id:1,user_id:7},Identity{tenant_id:2,user_id:7}));}
#[test]fn overdraft(){assert_eq!(debit(1,2),None);}
#[test]fn unicode_preview(){assert_eq!(preview("éx",1),"é");}
#[test]fn expiry(){assert!(!token_usable(100,100));}
#[test]fn fractional_fee(){assert_eq!(fee(1999,250),49);}
#[test]fn invalid_limit(){for s in ["abc","-1","65536"]{assert_eq!(parse_limit(s),None);}}
