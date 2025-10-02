from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from models import db, Candidate, User, VoteLog
from database import init_db
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key_123'

db.init_app(app)
init_db(app)

# Вспомогательная функция для проверки админа
def is_admin():
    if 'user_id' not in session:
        return False
    user = User.query.get(session['user_id'])
    return user and user.is_admin

# Главная страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    candidates = Candidate.query.all()
    
    # Проверяем победу кандидата "Огурец от Копатыча"
    cucumber = Candidate.query.filter_by(name="Огурец от Копатыча").first()
    if cucumber and cucumber.votes >= 10:
        return redirect(url_for('candidate_profile', candidate_id=cucumber.id))
    
    return render_template('index.html', 
                         user=user, 
                         candidates=candidates,
                         is_admin=is_admin())

# Страница регистрации (ТОЛЬКО ДЛЯ АДМИНА)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Только админ может создавать пользователей
    if not is_admin():
        return "Доступ запрещен. Только администратор может создавать пользователей.", 403
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        new_user = User(username=username, password=password, email=email, created_by=session['user_id'])
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('users_list'))
    
    return render_template('register.html')

# Страница создания кандидата (ТОЛЬКО ДЛЯ АДМИНА)
@app.route('/create_candidate', methods=['GET', 'POST'])
def create_candidate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Только админ может создавать кандидатов
    if not is_admin():
        return "Доступ запрещен. Только администратор может создавать кандидатов.", 403
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        new_candidate = Candidate(name=name, email=email, created_by=session['user_id'])
        db.session.add(new_candidate)
        db.session.commit()
        
        return redirect(url_for('index'))
    
    return render_template('create_candidate.html')

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

# Просмотр профиля пользователя
@app.route('/user/<int:user_id>')
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    target_user = User.query.get_or_404(user_id)
    
    return render_template('user_profile.html', 
                         user=target_user, 
                         current_user_id=session['user_id'],
                         is_admin=is_admin())

# Просмотр профиля кандидата
@app.route('/candidate/<int:candidate_id>')
def candidate_profile(candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    candidate = Candidate.query.get_or_404(candidate_id)
    voters = User.query.filter_by(voted_for=candidate_id).all()
    
    return render_template('candidate_profile.html', 
                         candidate=candidate, 
                         voters=voters,
                         current_user_id=session['user_id'],
                         is_admin=is_admin())

# Список всех пользователей (ТОЛЬКО ДЛЯ АДМИНА)
@app.route('/users')
def users_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if not is_admin():
        return "Доступ запрещен. Только администратор может просматривать список пользователей.", 403
    
    all_users = User.query.order_by(User.id).all()
    return render_template('users_list.html', users=all_users, is_admin=is_admin())

# Голосование за кандидата (только за себя)
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

# Отмена голоса (ТОЛЬКО АДМИН МОЖЕТ ОТМЕНЯТЬ ЧУЖИЕ ГОЛОСА)
@app.route('/cancel_vote/<int:user_id>', methods=['POST'])
def cancel_vote(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    target_user = User.query.get_or_404(user_id)
    
    # Админ может отменять любые голоса, обычные пользователи - только свои
    if not current_user.is_admin and current_user.id != user_id:
        return "Доступ запрещен. Вы можете отменять только свой голос.", 403
    
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

# Передача голоса (ТОЛЬКО АДМИН МОЖЕТ ПЕРЕДАВАТЬ ЧУЖИЕ ГОЛОСА)
@app.route('/transfer_vote/<int:user_id>/<int:candidate_id>', methods=['POST'])
def transfer_vote(user_id, candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    target_user = User.query.get_or_404(user_id)
    candidate = Candidate.query.get_or_404(candidate_id)
    
    # Админ может передавать любые голоса, обычные пользователи - только свои
    if not current_user.is_admin and current_user.id != user_id:
        return "Доступ запрещен. Вы можете передавать только свой голос.", 403
    
    # Отменяем текущий голос если есть
    if target_user.voted_for:
        old_candidate = Candidate.query.get(target_user.voted_for)
        if old_candidate:
            old_candidate.votes -= 1
    
    # Голосуем за указанного кандидата
    candidate.votes += 1
    target_user.voted_for = candidate.id
    target_user.vote_timestamp = datetime.utcnow()
    
    # Логируем
    vote_log = VoteLog(user_id=target_user.id, candidate_id=candidate.id, action='vote')
    db.session.add(vote_log)
    
    db.session.commit()
    
    check_winner()
    return redirect(url_for('user_profile', user_id=user_id))

# Проверка победы "Огурца от Копатыча"
def check_winner():
    cucumber = Candidate.query.filter_by(name="Огурец от Копатыча").first()
    if cucumber and cucumber.votes >= 10:
        # Генерируем флаг для Огурца
        cucumber.email = f"cucumber@kopatych.com - ФЛАГ: CTF{{IDOR_ADMIN_ACCESS_{cucumber.votes}}}"
        db.session.commit()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
