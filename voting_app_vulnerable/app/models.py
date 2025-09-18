from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    votes = db.Column(db.Integer, default=0)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(100))
    voted_for = db.Column(db.Integer, db.ForeignKey('candidate.id'))
    vote_timestamp = db.Column(db.DateTime) 

class VoteLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'))
    action = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)