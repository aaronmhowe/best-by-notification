from datetime import datetime
from db_setup import db

class ForgotPassword(db.Model):
    """
    Upon request, sends a reset code to the user via email address to perform a password reset.
    """
    __tablename__ = 'forgot_password'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(datetime.timezone.utc))
    expiration_window = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('password_reset', lazy=True))

    def valid_code(self):
        """
        Validates the reset code provided by the user.
        - Return: True if the provided code matches the code sent by the server and has been
        entered within the allotted time-window.
        """
        pass