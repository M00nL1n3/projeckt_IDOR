from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from models import db, Candidate, User, VoteLog
from database import init_db
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key_123'

db.init_app(app)

# Инициализация БД
init_db(app)

# Главная страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    candidates = Candidate.query.all()
    
    # Проверяем победу Ивана Петрова
    ivan = Candidate.query.filter_by(name="Иван Петров").first()
    if ivan and ivan.votes >= 10:
        return redirect(url_for('candidate_profile', candidate_id=ivan.id))
    
    return render_template('index.html', 
                         user=user, 
                         candidates=candidates)

# Страница регистрации (ТОЛЬКО ДЛЯ СОЗДАНИЯ ОДНОГО ПОЛЬЗОВАТЕЛЯ)
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Если уже есть зарегистрированные пользователи, запрещаем регистрацию
    if User.query.count() >= 10:
        return "Регистрация закрыта. Доступно только 10 пользователей.", 403
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        new_user = User(username=username, password=password, email=email)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, password=password).first()
        
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Неверные логин или пароль", 401
    
    return render_template('login.html')

# УЯЗВИМОСТЬ IDOR: Просмотр профиля пользователя
@app.route('/user/<int:user_id>')
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # УЯЗВИМОСТЬ: Можно смотреть любой профиль по ID
    target_user = User.query.get_or_404(user_id)
    return render_template('user_profile.html', 
                         user=target_user, 
                         current_user_id=session['user_id'])

# УЯЗВИМОСТЬ IDOR: Просмотр профиля кандидата
@app.route('/candidate/<int:candidate_id>')
def candidate_profile(candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    candidate = Candidate.query.get_or_404(candidate_id)
    voters = User.query.filter_by(voted_for=candidate_id).all()
    
    return render_template('candidate_profile.html', 
                         candidate=candidate, 
                         voters=voters,
                         current_user_id=session['user_id'])

# Функция для навигации по пользователям
@app.route('/users')
def users_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_users = User.query.order_by(User.id).all()
    return render_template('users_list.html', users=all_users)

# Голосование за кандидата (только для текущего пользователя)
@app.route('/vote/<int:candidate_id>', methods=['POST'])
def vote(candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    candidate = Candidate.query.get_or_404(candidate_id)
    user = User.query.get(session['user_id'])
    
    # Если пользователь уже голосовал, отменяем предыдущий голос
    if user.voted_for:
        old_candidate = Candidate.query.get(user.voted_for)
        if old_candidate:
            old_candidate.votes -= 1
    
    # Добавляем новый голос
    candidate.votes += 1
    user.voted_for = candidate_id
    user.vote_timestamp = datetime.utcnow()
    
    # Логируем действие
    vote_log = VoteLog(user_id=user.id, candidate_id=candidate_id, action='vote')
    db.session.add(vote_log)
    
    db.session.commit()
    
    check_winner()
    return redirect(url_for('index'))

# УЯЗВИМОСТЬ IDOR: Отмена голоса (доступно из любого профиля!)
@app.route('/cancel_vote/<int:user_id>', methods=['POST'])
def cancel_vote(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # УЯЗВИМОСТЬ: Нет проверки прав! Любой user_id можно отменить
    target_user = User.query.get_or_404(user_id)
    
    if target_user.voted_for:
        candidate = Candidate.query.get(target_user.voted_for)
        if candidate:
            candidate.votes -= 1
        
        # Логируем отмену
        vote_log = VoteLog(user_id=target_user.id, candidate_id=target_user.voted_for, action='cancel')
        db.session.add(vote_log)
        
        target_user.voted_for = None
        target_user.vote_timestamp = None
        db.session.commit()
    
    return redirect(url_for('user_profile', user_id=user_id))

# УЯЗВИМОСТЬ IDOR: Передать голос Ивану Петрову (доступно из любого профиля!)
@app.route('/transfer_vote/<int:user_id>', methods=['POST'])
def transfer_vote(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # УЯЗВИМОСТЬ: Нет проверки прав! Любой user_id можно изменить
    target_user = User.query.get_or_404(user_id)
    ivan = Candidate.query.filter_by(name="Иван Петров").first()
    
    if not ivan:
        return jsonify({'error': 'Кандидат не найден'}), 404
    
    # Отменяем текущий голос если есть
    if target_user.voted_for:
        old_candidate = Candidate.query.get(target_user.voted_for)
        if old_candidate:
            old_candidate.votes -= 1
    
    # Голосуем за Ивана
    ivan.votes += 1
    target_user.voted_for = ivan.id
    target_user.vote_timestamp = datetime.utcnow()
    
    # Логируем
    vote_log = VoteLog(user_id=target_user.id, candidate_id=ivan.id, action='vote')
    db.session.add(vote_log)
    
    db.session.commit()
    
    check_winner()
    return redirect(url_for('user_profile', user_id=user_id))

# Проверка победы
def check_winner():
    ivan = Candidate.query.filter_by(name="Иван Петров").first()
    if ivan and ivan.votes >= 10:
        # Генерируем флаг для Ивана
        ivan.email = f"ivan@company.com - ФЛАГ: CTF{{ID0R_VULN_{ivan.votes}_{ivan.id}}}"
        db.session.commit()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)