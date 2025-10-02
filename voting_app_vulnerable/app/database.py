from app import db
from app.models import Candidate, User

def init_db():
    db.create_all()
    
    # Добавляем кандидатов (БЕЗ ОГУРЦА - его создаст админ)
    if Candidate.query.count() == 0:
        candidates = [
            Candidate(name="Иван Петров", email="ivan@company.com", votes=0),
            Candidate(name="Мария Сидорова", email="maria@company.com", votes=0), 
            Candidate(name="Петр Иванов", email="petr@company.com", votes=0)
        ]
        db.session.add_all(candidates)
        db.session.commit()
    
    # Добавляем пользователей - админ (ID=1) + 15 обычных
    if User.query.count() == 0:
        # Админ (ID=1)
        admin = User(username="admin", password="admin123", email="admin@company.com", is_admin=True)
        db.session.add(admin)
        
        # Обычные пользователи (ID=2-16)
        for i in range(1, 16):
            voted_for = 2 if i % 2 == 0 else 3  # чередуем голоса
            user = User(
                username=f"user{i}", 
                password=f"pass{i}", 
                email=f"user{i}@mail.com",
                voted_for=voted_for
            )
            db.session.add(user)
        
        db.session.commit()
        
        # Обновляем счетчики голосов
        maria = Candidate.query.get(2)
        petr = Candidate.query.get(3)
        maria.votes = 7  # голоса за Марию
        petr.votes = 8   # голоса за Петра
        db.session.commit()