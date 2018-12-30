create table bitflyer_executions (
    id int not null primary key,
    side varchar(8),
    price int,
    size decimal(13, 8),
    exec_date datetime,
    buy_child_order_acceptance_id varchar(32),
    sell_child_order_acceptance_id varchar(32),
    symbol varchar(16),
    index(exec_date)
);
