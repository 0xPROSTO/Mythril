import json

from flask import Blueprint, render_template, redirect, request, abort, flash
from flask_login import login_required, current_user

from data import db_session
from data.jobs import Jobs
from data.users import User
from data.responses import Responses
from forms.jobs_form import JobsForm, ResponseForm

from sqlalchemy import func, case, or_
from sqlalchemy.orm import joinedload

from get_rates import get_currencies

jobs_blueprint = Blueprint('jobs', __name__)


def load_categories(file_path='data/categories.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        categories = json.load(f)
    return {category['value']: category['label'] for category in categories}


@jobs_blueprint.route("/")
def index():
    session = db_session.create_session()
    try:
        status_order = case(
            {
                "Открыт": 1,
                "В работе": 2,
                "Завершён": 3
            },
            value=Jobs.status
        )

        category = request.args.get('category')
        status = request.args.get('status')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        currency = request.args.get('currency', 'RUB')
        search = request.args.get('search')

        # Получить курсы
        currency_data = get_currencies()
        rates = currency_data["rates"]

        query = session.query(Jobs).join(User, Jobs.author_id == User.id)
        if category:
            query = query.filter(Jobs.category == category)
        if status:
            query = query.filter(Jobs.status == status)
        if min_price:
            try:
                min_price = float(min_price)
                min_price_rub = min_price / rates.get(currency, 1.0)
                query = query.filter(Jobs.price >= float(min_price_rub))
            except ValueError:
                pass
        if max_price:
            try:
                max_price = float(max_price)
                max_price_rub = max_price / rates.get(currency, 1.0)
                query = query.filter(Jobs.price <= float(max_price_rub))
            except ValueError:
                pass

        # Поиск
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Jobs.title.ilike(search_term),
                    Jobs.description.ilike(search_term),
                    User.username.ilike(search_term)
                )
            )

        jobs = query.options(joinedload(Jobs.author)).order_by(status_order, Jobs.created_date).all()

        # Подсчёт откликов
        response_counts = dict(
            session.query(Responses.job_id, func.count(Responses.id).
                          label('response_count')).group_by(Responses.job_id).all())

        for job in jobs:
            job.response_count = response_counts.get(job.id, 0)
            job.display_price = round(job.price * rates.get(currency, 1.0), 2)
            job.currency = currency

        title = "Доступные работы"
        search_text = "Название, описание или автор"
        categories = load_categories()

        return render_template("index.html", jobs=jobs, title=title,
                               categories=categories, category=category, status=status,
                               min_price=min_price, max_price=max_price, currency=currency,
                               search=search, search_text=search_text)
    finally:
        session.close()


@jobs_blueprint.route('/jobs/add', methods=['GET', 'POST'])
@login_required
def add_jobs():
    form = JobsForm()
    can_edit_status = True if current_user.role > 1 else False
    if form.validate_on_submit():
        session = db_session.create_session()
        try:
            jobs = Jobs()
            jobs.title = form.title.data
            jobs.description = form.description.data
            jobs.category = form.category.data
            jobs.price = form.price.data
            jobs.contact = form.contact.data
            jobs.author_id = current_user.id
            jobs.status = form.status.data
            session.add(jobs)
            session.commit()
            return redirect('/')
        finally:
            session.close()
    return render_template('jobs.html', title='Добавление работы', form=form, can_edit_status=can_edit_status)


@jobs_blueprint.route('/jobs/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def jobs_delete(id):
    session = db_session.create_session()
    try:
        jobs = session.query(Jobs).filter(Jobs.id == id).first()
        if not jobs:
            abort(404)
        if jobs.author_id != current_user.id and current_user.role < 2:
            flash('У вас нет прав для редактирования этого задания.', 'danger')
            return redirect('/')
        if jobs.status == "Завершён" and current_user.role < 3:
            flash('Задание уже завершено.', 'danger')
            return redirect('/')
        else:
            session.delete(jobs)
            session.commit()
        return redirect('/')
    finally:
        session.close()


@jobs_blueprint.route('/jobs/complete/<int:job_id>', methods=['GET', 'POST'])
@login_required
def jobs_complete(job_id):
    session = db_session.create_session()
    try:
        job = session.query(Jobs).filter(Jobs.id == job_id).first()
        job.status = 'Завершён'
        session.commit()
        return redirect('/')
    finally:
        session.close()


@jobs_blueprint.route('/jobs/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_jobs(id):
    form = JobsForm()
    can_edit_status = True if current_user.role >= 3 else False
    session = db_session.create_session()
    try:
        jobs = session.query(Jobs).filter(Jobs.id == id).first()
        if not jobs:
            abort(404)
        if jobs.author_id != current_user.id and current_user.role < 2:
            flash('У вас нет прав для редактирования этого задания.', 'danger')
            return redirect('/')

        if request.method == "GET":
            form.title.data = jobs.title
            form.description.data = jobs.description
            form.category.data = jobs.category
            form.price.data = jobs.price
            form.contact.data = jobs.contact
            form.status.data = jobs.status
        if form.validate_on_submit():
            jobs.title = form.title.data
            jobs.description = form.description.data
            jobs.category = form.category.data
            jobs.price = form.price.data
            jobs.contact = form.contact.data
            if can_edit_status:
                jobs.status = form.status.data
            session.commit()
            session.close()
            return redirect('/')
        return render_template('jobs.html', title='Редактирование работы', form=form, can_edit_status=can_edit_status)
    finally:
        session.close()


@jobs_blueprint.route('/jobs/<int:id>', methods=['GET', 'POST'])
@login_required
def jobs_view(id):
    session = db_session.create_session()
    try:
        item = session.query(Jobs).filter(Jobs.id == id).first()
        if not item:
            abort(404)

        currency_data = get_currencies()
        rates = currency_data["rates"]
        other_prices = (f"{round(item.price * rates.get('USD', 1.0), 2)} $ | "
                        f"{round(item.price * rates.get('EUR', 1.0), 2)} €")

        categories = load_categories()
        return render_template('view_jobs.html', title=f'Просмотр работы',
                               item=item, categories=categories, other_prices=other_prices)
    finally:
        session.close()


@jobs_blueprint.route('/jobs/answer/<int:job_id>', methods=['GET', 'POST'])
@login_required
def answer_jobs(job_id):
    session = db_session.create_session()
    try:
        job = session.query(Jobs).get(job_id)
        if not job:
            abort(404)
        if job.author_id == current_user.id:
            flash('Вы не можете откликнуться на свою работу.', 'danger')
            return redirect(f'/jobs/{job_id}')
        if job.status != "Открыт":
            flash('На эту работу нельзя откликнуться, она уже в работе или завершена.', 'danger')
            return redirect(f'/jobs/{job_id}')
        if session.query(Responses).filter_by(job_id=job_id, user_id=current_user.id).first():
            flash('Вы уже откликнулись на это объявление.', 'danger')
            return redirect(f'/my/responses')

        form = ResponseForm(price=job.price)
        categories = load_categories()
        title='Отклик на работу'

        if form.validate_on_submit():
            response = Responses(
                job_id=job_id,
                user_id=current_user.id,
                comment=form.comment.data,
                price=form.price.data
            )
            session.add(response)
            session.commit()

            flash('Ваш отклик успешно отправлен!', 'success')
            return redirect(f'/jobs/{job_id}')

        return render_template('answer_jobs.html', job=job, form=form,
                               categories=categories, title=title)
    finally:
        session.close()
