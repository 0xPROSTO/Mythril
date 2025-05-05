from flask import Blueprint, render_template, redirect, abort, request
from flask_login import login_required, current_user

from data import db_session
from data.jobs import Jobs
from data.responses import Responses
from data.users import User

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from routes.jobs_routes import load_categories

from get_rates import get_currencies

my_blueprint = Blueprint('my', __name__)


@my_blueprint.route('/my/jobs')
@login_required
def my_jobs():
    session = db_session.create_session()
    try:
        category = request.args.get('category')
        status = request.args.get('status')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        currency = request.args.get('currency', 'RUB')
        search = request.args.get('search')

        query = session.query(Jobs).filter(Jobs.author_id == current_user.id)

        # Получить курсы
        currency_data = get_currencies()
        rates = currency_data["rates"]

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
                    Jobs.description.ilike(search_term)
                )
            )
        jobs = query.all()

        # Подсчёт откликов
        response_counts = dict(
            session.query(Responses.job_id, func.count(Responses.id).
                          label('response_count')).group_by(Responses.job_id).all())
        for job in jobs:
            job.response_count = response_counts.get(job.id, 0)

        # Сортировка
        jobs = sorted(
            jobs,
            key=lambda job: (1 if job.status == "Завершён" else 0, -job.response_count, job.created_date)
        )

        for job in jobs:
            job.display_price = round(job.price * rates.get(currency, 1.0), 2)
            job.currency = currency

        title = "Мои работы"
        search_text = "Название или описание"
        categories = load_categories()

        return render_template("index.html", jobs=jobs, title=title,
                               categories=categories, category=category, status=status,
                               min_price=min_price, max_price=max_price, currency=currency,
                               search=search, search_text=search_text)
    finally:
        session.close()


@my_blueprint.route('/my/responses')
@login_required
def my_responses():
    session = db_session.create_session()
    try:
        responses = (session.query(Responses).filter(
            Responses.user_id == current_user.id,
            Responses.job.has(Jobs.status != "Завершён")
        ).order_by(Responses.created_date.desc())).all()

        responses_history = session.query(Responses).outerjoin(Jobs, Responses.job_id == Jobs.id).filter(
            Responses.user_id == current_user.id,
            or_(
                Jobs.status == "Завершён",
                Jobs.id.is_(None)
            )
        ).order_by(Responses.created_date.desc()).all()
        return render_template("my_responses.html", responses=responses,
                               responses_history=responses_history)
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
