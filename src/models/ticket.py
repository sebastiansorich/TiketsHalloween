from datetime import datetime
from .. import db

class Ticket(db.Model):
    __tablename__ = 'tickets'

    id_ticket = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(255), unique=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    date_of_issue = db.Column(db.DateTime, nullable=False)

    def __init__(self, token, is_used=False, date_of_issue=None):
        self.token = token
        self.is_used = is_used
        self.date_of_issue = date_of_issue or datetime.utcnow()
