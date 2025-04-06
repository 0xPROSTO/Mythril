import datetime
import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Responses(SqlAlchemyBase):
    __tablename__ = 'responses'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    job_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('jobs.id'), nullable=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=True)
    comment = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    price = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    # Связь
    job = orm.relationship("Jobs", back_populates="responses")
    user = orm.relationship("User", back_populates="responses")
