from flask import Blueprint, render_template, redirect, abort, flash
from flask_login import login_required, current_user

from data import db_session
from data.jobs import Jobs
from data.responses import Responses

responses_blueprint = Blueprint('responses', __name__)


@responses_blueprint.route('/jobs/responses/<int:job_id>')
@login_required
def view_responses(job_id):
    session = db_session.create_session()
    try:
        job = session.query(Jobs).get(job_id)
        if not job:
            abort(404)
        if job.author_id != current_user.id and current_user.role < 2:
            flash('Вы не можете просматривать отклики на эту работу.', 'danger')
            return redirect(f'/jobs/{job_id}')

        responses = session.query(Responses).filter(Responses.job_id == job_id).all()
        return render_template('view_responses.html', job=job, responses=responses)
    finally:
        session.close()


@responses_blueprint.route('/jobs/responses/select/<int:job_id>/<int:response_id>', methods=['POST'])
@login_required
def select_response(job_id, response_id):
    session = db_session.create_session()
    try:
        job = session.query(Jobs).get(job_id)
        response = session.query(Responses).get(response_id)

        if not job or not response:
            abort(404)
        if job.author_id != current_user.id:
            flash('Вы не можете выбрать исполнителя для этой работы.', 'danger')
            return redirect(f'/jobs/responses/{job_id}')
        if job.executor_id is not None:
            flash('Исполнитель уже выбран.', 'danger')
            return redirect(f'/jobs/responses/{job_id}')
        if job.status != "Открыт":
            flash('Работа уже в работе или завершена.', 'danger')
            return redirect(f'/jobs/responses/{job_id}')

        job.executor_id = response.user_id
        job.status = "В работе"
        session.commit()
        return redirect(f'/jobs/responses/{job_id}')
    finally:
        session.close()


@responses_blueprint.route('/jobs/responses/cancel/<int:job_id>/<int:response_id>', methods=['POST'])
@login_required
def cancel_response(job_id, response_id):
    session = db_session.create_session()
    try:
        job = session.query(Jobs).get(job_id)
        if job.status == "Завершён":
            flash("Работа уже завершена", 'danger')
            return redirect(f'/jobs/responses/{job_id}')
        response = session.query(Responses).get(response_id)

        if not job or not response:
            abort(404)
        if job.author_id != current_user.id:
            flash('Вы не можете выбрать исполнителя для этой работы.', 'danger')
            return redirect(f'/jobs/responses/{job_id}')
        if job.executor_id is None:
            flash('Исполнитель ещё не выбран.', 'danger')
            return redirect(f'/jobs/responses/{job_id}')

        job.executor_id = None
        job.status = "Открыт"
        session.commit()

        return redirect(f'/jobs/responses/{job_id}')
    finally:
        session.close()
