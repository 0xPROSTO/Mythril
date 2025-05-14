from flask import Blueprint, render_template, redirect, flash
from flask_login import login_required, current_user

from data import db_session
from data.reviews import Reviews
from data.jobs import Jobs
from forms.jobs_form import ReviewsForm

reviews_blueprint = Blueprint('reviews', __name__)


@reviews_blueprint.route('/reviews/add/<int:job_id>', methods=['GET', 'POST'])
@login_required
def add_reviews(job_id):
    """Позволяет автору работы оставить отзыв о завершенной работе."""
    session = db_session.create_session()
    try:
        job = session.query(Jobs).get(job_id)
        if not job:
            flash('Работа не найдена.', 'danger')
            return redirect('/')
        if job.status != "Завершён":
            flash('Отзыв можно оставить только на завершённую работу.', 'danger')
            return redirect('/')
        if job.author_id != current_user.id:
            flash('Только автор работы может оставить отзыв.', 'danger')
            return redirect('/')
        if session.query(Reviews).filter_by(job_id=job_id).first():
            flash('Отзыв на эту работу уже существует.', 'danger')
            return redirect('/')

        form = ReviewsForm()
        if form.validate_on_submit():
            reviews = Reviews()
            job = session.query(Jobs).filter(Jobs.id == job_id).first()
            reviews.author_id = current_user.id
            reviews.executor_id = job.executor_id
            reviews.job_id = job.id
            reviews.rating = form.rating.data
            reviews.comment = form.comment.data
            session.add(reviews)
            session.commit()
            session.close()
            return redirect('/')
        return render_template('reviews.html', title='Оставить отзыв', form=form)
    finally:
        session.close()
