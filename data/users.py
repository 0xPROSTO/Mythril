import datetime
import sqlalchemy
from flask_login import UserMixin
import sqlalchemy.orm as orm
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=False)
    password_hash = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    role = sqlalchemy.Column(sqlalchemy.Integer, default=1, nullable=False)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    # Связь
    jobs_authored = orm.relationship("Jobs", back_populates="author", foreign_keys="Jobs.author_id")
    jobs_executed = orm.relationship("Jobs", back_populates="executor", foreign_keys="Jobs.executor_id")
    responses = orm.relationship("Responses", back_populates="user")
    reviews_given = orm.relationship("Reviews", back_populates="author", foreign_keys="Reviews.author_id")
    reviews_received = orm.relationship("Reviews", back_populates="executor", foreign_keys="Reviews.executor_id")

    def __repr__(self):
        return f'<User> {self.id} {self.username} {self.email}'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
