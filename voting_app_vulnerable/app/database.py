from models import db, Candidate, User

def init_db(app):
    with app.app_context():
        db.create_all()
        
        # Добавляем кандидатов
        if Candidate.query.count() == 0:
            candidates = [
                Candidate(name="Иван Петров", email="ivan@company.com", votes=0),
                Candidate(name="Мария Сидорова", email="maria@company.com", votes=0), 
                Candidate(name="Петр Иванов", email="petr@company.com", votes=0)
            ]
            db.session.add_all(candidates)
            db.session.commit()
        
        # Добавляем 9 предсозданных пользователей
        if User.query.count() == 0:
            users = [
                User(username="user1", password="pass1", email="user1@mail.com", voted_for=2),  # Голосовал за Марию
                User(username="user2", password="pass2", email="user2@mail.com", voted_for=2),  # Голосовал за Марию
                User(username="user3", password="pass3", email="user3@mail.com", voted_for=2),  # Голосовал за Марию
                User(username="user4", password="pass4", email="user4@mail.com", voted_for=2),  # Голосовал за Марию
                User(username="user5", password="pass5", email="user5@mail.com", voted_for=2),  # Голосовал за Марию
                User(username="user6", password="pass6", email="user6@mail.com", voted_for=3),  # Голосовал за Петра
                User(username="user7", password="pass7", email="user7@mail.com", voted_for=3),  # Голосовал за Петра
                User(username="user8", password="pass8", email="user8@mail.com", voted_for=3),  # Голосовал за Петра
                User(username="user9", password="pass9", email="user9@mail.com", voted_for=3),  # Голосовал за Петра
                User(username="user10", password="pass10", email="user10@mail.com", voted_for=3)  # Голосовал за Петра
            ]
            db.session.add_all(users)
            db.session.commit()
            
            # Обновляем счетчики голосов кандидатов
            maria = Candidate.query.get(2)
            petr = Candidate.query.get(3)
            maria.votes = 5
            petr.votes = 5
            db.session.commit()