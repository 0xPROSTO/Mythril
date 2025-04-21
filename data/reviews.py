import datetime
import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Reviews(SqlAlchemyBase):
    __tablename__ = 'reviews'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=True)
    executor_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=True)
    job_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('jobs.id'), nullable=True)
    rating = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    comment = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    # Связь
    author = orm.relationship("User", back_populates="reviews_given", foreign_keys=[author_id])
    executor = orm.relationship("User", back_populates="reviews_received", foreign_keys=[executor_id])
    job = orm.relationship("Jobs", back_populates="reviews")