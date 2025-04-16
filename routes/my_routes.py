from flask import Blueprint, render_template, redirect, abort
from flask_login import login_required, current_user

from data import db_session
from data.jobs import Jobs
from data.responses import Responses

from sqlalchemy import func

my_blueprint = Blueprint('my', __name__)


@my_blueprint.route('/my/jobs')
@login_required
def my_jobs():
    session = db_session.create_session()
    try:
        jobs = session.query(Jobs).filter(Jobs.author_id == current_user.id).all()

        response_counts = dict(
            session.query(Responses.job_id, func.count(Responses.id).label('response_count')).group_by(
                Responses.job_id).all())
        for job in jobs:
            job.response_count = response_counts.get(job.id, 0)

        title = "Мои работы"
        return render_template("index.html", jobs=jobs, title=title)
    finally:
        session.close()


@my_blueprint.route('/my/responses')
@login_required
def my_responses():
    session = db_session.create_session()
    try:
        responses = session.query(Responses).filter_by(user_id=current_user.id)
        return render_template("my_responses.html", responses=responses)
    finally:
        session.close()


@my_blueprint.route('/my/responses/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def responses_delete(id):
    session = db_session.create_session()
    try:
        response = session.query(Responses).filter(Responses.id == id, Responses.user_id == current_user.id).first()
        if response:
            if response.job:
                if response.job.executor_id == current_user.id:
                    response.job.status = "Открыт"
                    response.job.executor_id = None
                session.delete(response)
                session.commit()
            else:
                session.delete(response)
                session.commit()
        else:
            abort(404)
        return redirect('/my/responses')
    finally:
        session.close()
