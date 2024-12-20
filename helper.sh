#!/bin/bash

DB_HOST="127.0.0.1"
DB_NAME="rgr"
DB_USER="sajfulina_alina"

create_database() {
    psql -h $DB_HOST -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;"

    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(1000) UNIQUE NOT NULL,
        password VARCHAR(1000) NOT NULL
    );
    "

    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    CREATE TABLE IF NOT EXISTS subscriptions (
        subscription_id SERIAL PRIMARY KEY,
        name VARCHAR(1000) NOT NULL,
        cost REAL NOT NULL,
        frequency INT NOT NULL,
        start_date DATE NOT NULL,
        user_id INT NOT NULL,
        is_deleted BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    "

    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
    CREATE TABLE IF NOT EXISTS audits (
        audit_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        subscription_id INT,
        action VARCHAR(1000) NOT NULL,
        action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        subscription_name VARCHAR(1000) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id)
    );
    "

    echo "Готово"
}

install_dependencies() {
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    echo "Готово"
}

start_app() {
    source venv/bin/activate
    export FLASK_APP=app.py
    flask run

    echo "Готово"
}

stop_app() {
    pkill -f "flask run"

    echo "Готово"
}

case "$1" in
    create_database)
        create_database
        ;;
    install_dependencies)
        install_dependencies
        ;;
    start_app)
        start_app
        ;;
    stop_app)
        stop_app
        ;;
    *)
        echo "Неверная команда"
        exit 1
        ;;
esac
