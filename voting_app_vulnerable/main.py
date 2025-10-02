from app import create_app, db
from app.models import Candidate, User, VoteLog
from app.database import init_db
from flask import render_template, request, redirect, url_for, session
from datetime import datetime
import os

app = create_app()

# Проверим пути
print("Current directory:", os.getcwd())
print("Templates exists:", os.path.exists('templates'))
print("Templates files:", os.listdir('templates') if os.path.exists('templates') else "NO TEMPLATES")

# Инициализация БД
with app.app_context():
    init_db()

# Вспомогательная функция для проверки админа
def is_admin():
    if 'user_id' not in session:
        return False
    user = User.query.get(session['user_id'])
    return user and user.is_admin

# Проверка победы "Огурца от Копатыча"
def check_winner():
    cucumber = Candidate.query.filter_by(name="Огурец от Копатыча").first()
    if cucumber and cucumber.votes >= 10:
        cucumber.email = f"cucumber@kopatych.com - ФЛАГ: SiBears{{0h_th1s_us3r_h4s_w0n_4g41n}}"
        db.session.commit()

# Главная страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    candidates = Candidate.query.all()
    
    cucumber = Candidate.query.filter_by(name="Огурец от Копатыча").first()
    if cucumber and cucumber.votes >= 10:
        return redirect(url_for('candidate_profile', candidate_id=cucumber.id))
    
    return render_template('index.html', 
                         user=user, 
                         candidates=candidates,
                         is_admin=is_admin())

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

# Остальные маршруты остаются без изменений...
@app.route('/user/<int:user_id>')
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    target_user = User.query.get_or_404(user_id)
    candidates = Candidate.query.all()
    
    return render_template('user_profile.html', 
                         user=target_user, 
                         current_user_id=session['user_id'],
                         candidates=candidates,
                         is_admin=is_admin())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if not is_admin():
        return "Доступ запрещен. Только администратор может создавать пользователей.", 403
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        if User.query.filter_by(username=username).first():
            return "Пользователь с таким логином уже существует", 400
        
        new_user = User(username=username, password=password, email=email)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('users_list'))
    
    return render_template('register.html')

@app.route('/create_candidate', methods=['GET', 'POST'])
def create_candidate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if not is_admin():
        return "Доступ запрещен. Только администратор может создавать кандидатов.", 403
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        if Candidate.query.filter_by(name=name).first():
            return "Кандидат с таким именем уже существует", 400
        
        new_candidate = Candidate(name=name, email=email)
        db.session.add(new_candidate)
        db.session.commit()
        
        return redirect(url_for('index'))
    
    return render_template('create_candidate.html')

@app.route('/candidate/<int:candidate_id>')
def candidate_profile(candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    candidate = Candidate.query.get_or_404(candidate_id)
    candidates = Candidate.query.all()
    
    return render_template('candidate_profile.html', 
                         candidate=candidate,
                         candidates=candidates,
                         current_user_id=session['user_id'],
                         is_admin=is_admin())

@app.route('/users')
def users_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if not is_admin():
        return "Доступ запрещен. Только администратор может просматривать список пользователей.", 403
    
    all_users = User.query.order_by(User.id).all()
    return render_template('users_list.html', users=all_users, is_admin=is_admin())

@app.route('/vote/<int:candidate_id>', methods=['POST'])
def vote(candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    candidate = Candidate.query.get_or_404(candidate_id)
    user = User.query.get(session['user_id'])
    
    if user.voted_for:
        old_candidate = Candidate.query.get(user.voted_for)
        if old_candidate:
            old_candidate.votes -= 1
    
    candidate.votes += 1
    user.voted_for = candidate_id
    user.vote_timestamp = datetime.utcnow()
    
    vote_log = VoteLog(user_id=user.id, candidate_id=candidate_id, action='vote')
    db.session.add(vote_log)
    
    db.session.commit()
    
    check_winner()
    return redirect(url_for('index'))

@app.route('/cancel_vote/<int:user_id>', methods=['POST'])
def cancel_vote(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    target_user = User.query.get_or_404(user_id)
    
    if not current_user.is_admin and current_user.id != user_id:
        return "Доступ запрещен. Вы можете отменять только свой голос.", 403
    
    if target_user.voted_for:
        candidate = Candidate.query.get(target_user.voted_for)
        if candidate:
            candidate.votes -= 1
        
        vote_log = VoteLog(user_id=target_user.id, candidate_id=target_user.voted_for, action='cancel')
        db.session.add(vote_log)
        
        target_user.voted_for = None
        target_user.vote_timestamp = None
        db.session.commit()
    
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/transfer_vote/<int:user_id>/<int:candidate_id>', methods=['POST'])
def transfer_vote(user_id, candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    target_user = User.query.get_or_404(user_id)
    candidate = Candidate.query.get_or_404(candidate_id)
    
    if not current_user.is_admin and current_user.id != user_id:
        return "Доступ запрещен. Вы можете передавать только свой голос.", 403
    
    if target_user.voted_for:
        old_candidate = Candidate.query.get(target_user.voted_for)
        if old_candidate:
            old_candidate.votes -= 1
    
    candidate.votes += 1
    target_user.voted_for = candidate.id
    target_user.vote_timestamp = datetime.utcnow()
    
    vote_log = VoteLog(user_id=target_user.id, candidate_id=candidate.id, action='vote')
    db.session.add(vote_log)
    
    db.session.commit()
    
    check_winner()
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)