create table users(
    id serial primary key,
    username varchar (1000) unique not null,
    password varchar(1000) not null
);

create table subscriptions(
     subscription_id serial primary key,
     name varchar(1000) not null,
     cost real not null,
     frequency int not null,
     start_date date not null,
     user_id int not null, 
     is_deleted boolean default false,
     foreign key (user_id) references users (id) on delete cascade
);

create table audits (
    audit_id serial primary key,
    user_id int not null,
    subscription_id int, 
    action varchar(1000) not null,
    action_date timestamp default current_timestamp,
    subscription_name varchar(1000) not null,
    foreign key (user_id) references users (id) on delete cascade,
    foreign key (subscription_id) references subscriptions(subscription_id) on delete cascade
);