import os  
from flask import Blueprint, flash, render_template,request, redirect, session, Flask, abort, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash 
import psycopg2
from flask_login import LoginManager
from models import User, Subscription, Audit

from dotenv import load_dotenv  

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://{user}:@{host}/{database}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')  

    app.register_blueprint(rgr)

    return app

rgr = Blueprint('rgr', __name__)

login_manager = LoginManager()

@login_manager.user_loader
def load_users(user_id):
    return User.query.get(int(user_id))

def dbConnect():
    conn = psycopg2.connect(
        host="127.0.0.1",
        database='rgr',
        user='sajfulina_alina'
    )
    return conn;
 
def dbClose(cursor, connection):
    cursor.close()
    connection.close()


@rgr.route('/')
def user():
    if not session.get('id'):
        return redirect('/login')
    
    username = session.get('username', 'Anon')
    userID = session.get('id')
    subscriptions = []   
    
    conn = dbConnect()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT subscription_id, name, cost, frequency, start_date 
        FROM subscriptions
        WHERE is_deleted = FALSE
    """)
    subscriptions = cur.fetchall()

    dbClose(cur, conn)
    
    return render_template('index.html', username=username, subscriptions=subscriptions)

  

@rgr.route('/registration', methods=['GET', 'POST'])
def registerPage():
    if request.method == 'GET':
        return render_template('registration.html')

    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Заполните все поля"}), 400  

    username = data['username']
    password = data['password']

    if not username or not password:
        return jsonify({"error": "Заполните все поля"}), 400  # Ошибка 400

    hashPassword = generate_password_hash(password)

    conn = dbConnect()
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE username = %s;", (username,))
    if cur.fetchone() is not None:
        conn.close()
        cur.close()
        return jsonify({"error": "Пользователь с данным именем уже существует"}), 400  

    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s);", (username, hashPassword))
    conn.commit()

    conn.close()
    cur.close()

    return jsonify({"message": "Регистрация прошла успешно!"}), 200  


@rgr.route('/login', methods=['GET', 'POST'])
def loginPage():
    errors = []
    
    if request.method == 'GET':
        return render_template('login.html', errors=errors)

    username = request.form.get('login')  
    password = request.form.get('password')

    if not (username and password):
        errors.append('Заполните все поля')
        return render_template('login.html', errors=errors)
    
    conn = dbConnect()
    cur = conn.cursor()

    cur.execute("SELECT id, password FROM users WHERE username = %s;", (username,))
    result = cur.fetchone()

    if result is None:
        errors.append('Неправильный логин')
        dbClose(cur, conn)
        return render_template('login.html', errors=errors)
    
    userID, hashPassword = result

    if check_password_hash(hashPassword, password):
        session['id'] = userID
        session['username'] = username
        dbClose(cur, conn)
        return redirect('/')  
    else:
        errors.append('Неправильный логин или пароль')
        dbClose(cur, conn)
        return render_template('login.html', errors=errors)
    

@rgr.route('/save_subscription', methods=['POST'])
def save_subscription():
    name = request.form['name']
    cost = request.form['cost']
    frequency = request.form['frequency']
    start_date = request.form['start_date']

    conn = dbConnect()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO subscriptions (name, cost, frequency, start_date)
    VALUES (%s, %s, %s, %s)
    RETURNING subscription_id, name
    """, (name, cost, frequency, start_date))
    
    subscription_id, subscription_name = cur.fetchone()  
    conn.commit()

    user_id = session.get('id')
    cur.execute("""
    INSERT INTO audits (user_id, subscription_id, action, action_date, subscription_name)
    VALUES (%s, %s, %s, NOW(), %s)
    """, (user_id, subscription_id, 'Added new subscription', subscription_name))
    conn.commit()

    cur.close()
    conn.close()

    return redirect('/')


@rgr.route('/audits')
def audit():
    user_id = session.get('id')

    if user_id is not None:
        conn = dbConnect()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.audit_id, a.user_id, a.subscription_id, a.action, a.action_date, s.name 
            FROM audits a
            JOIN subscriptions s ON a.subscription_id = s.subscription_id
            WHERE a.user_id = %s
        """, (user_id,))

        audits = cur.fetchall()

        dbClose(cur, conn)
        return render_template('audit.html', audits=audits)

    abort(404)



@rgr.route('/add_subscription', methods=['GET', 'POST'])
def add_subscription():
    if 'id' not in session:
        return redirect('/login')  

    if request.method == 'GET':
        return render_template('adding.html')

    # Логика добавления подписки
    name = request.form['name']
    cost = request.form['cost']
    frequency = request.form['frequency']
    start_date = request.form['start_date']

    with dbConnect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO subscriptions (name, cost, frequency, start_date)
            VALUES (%s, %s, %s, %s)
            """, (name, cost, frequency, start_date))
            conn.commit()

    return redirect(url_for('rgr.subscriptions'))


@rgr.route('/edit_subscription/<int:subscription_id>', methods=['GET'])
def edit_subscription(subscription_id):
    conn = dbConnect()
    cur = conn.cursor()
    cur.execute("SELECT subscription_id, name, cost, frequency, start_date FROM subscriptions WHERE subscription_id = %s", (subscription_id,))
    subscription = cur.fetchone()
    dbClose(cur, conn)
    if subscription:
        return render_template('edit.html', subscription=subscription)
    else:
        return "Подписка не найдена", 404
    

@rgr.route('/update_subscription/<int:subscription_id>', methods=['POST'])
def update_subscription(subscription_id):
    name = request.form['name']
    cost = request.form['cost']
    frequency = request.form['frequency']
    start_date = request.form['start_date']

    conn = dbConnect()
    cur = conn.cursor()
    cur.execute("""
    UPDATE subscriptions
    SET name = %s, cost = %s, frequency = %s, start_date = %s
    WHERE subscription_id = %s
    """, (name, cost, frequency, start_date, subscription_id))
    conn.commit()

    cur.execute("SELECT name FROM subscriptions WHERE subscription_id = %s", (subscription_id,))
    updated_name = cur.fetchone()[0]

    user_id = session.get('id')
    cur.execute("""
    INSERT INTO audits (user_id, subscription_id, action, action_date, subscription_name)
    VALUES (%s, %s, %s, NOW(), %s)
    """, (user_id, subscription_id, 'Updated subscription', updated_name))
    conn.commit()

    cur.close()
    conn.close()

    return redirect('/')


@rgr.route('/delete_subscription/<int:subscription_id>')
def delete_subscription(subscription_id):
    conn = dbConnect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET is_deleted = TRUE
        WHERE subscription_id = %s
        RETURNING subscription_id, name
    """, (subscription_id,))
    
    result = cur.fetchone()
    
    if result:
        subscription_id, subscription_name = result
        
        user_id = session.get('id') 
        cur.execute("""
            INSERT INTO audits (user_id, subscription_id, action, action_date, subscription_name)
            VALUES (%s, %s, %s, NOW(), %s)
        """, (user_id, subscription_id, 'deleted', subscription_name))
        
        conn.commit()

    cur.close()
    conn.close()

    return redirect('/')
  

@rgr.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app = create_app()
    app.run(debug=os.getenv('FLASK_DEBUG', 'false') == 'true')