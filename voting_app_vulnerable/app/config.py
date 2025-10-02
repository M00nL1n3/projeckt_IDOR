import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///voting.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'super_secret_key_12345_never_share_this'