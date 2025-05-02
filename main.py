import json

from flask import Flask, render_template, redirect, request, abort, session, url_for, flash
from flask_login import LoginManager, login_user, login_required, current_user

from data import db_session
from data.reviews import Reviews
from data.users import User
from data.jobs import Jobs

from routes.jobs_routes import jobs_blueprint
from routes.mythril_API import api_blueprint
from routes.responses_routes import responses_blueprint
from routes.my_routes import my_blueprint
from routes.auth_routes import auth_blueprint
from routes.reviews_routes import reviews_blueprint

import logging

from sqlalchemy import func

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'ENTER_YOUR_SECRETKEY_HERE'

# Подключение blueprints
app.register_blueprint(jobs_blueprint)
app.register_blueprint(responses_blueprint)
app.register_blueprint(my_blueprint)
app.register_blueprint(auth_blueprint)
app.register_blueprint(reviews_blueprint)
app.register_blueprint(api_blueprint)


def main():
    db_session.global_init("database/database.db")
    # session = db_session.create_session()

    app.run(port=8080)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    try:
        user = session.get(User, int(user_id))
        return user
    finally:
        session.close()


@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    session = db_session.create_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            abort(404, description="Пользователь не найден")

        completed_jobs = session.query(Jobs).filter(
            Jobs.executor_id == user.id,
            Jobs.status == "Завершён"
        ).order_by(Jobs.created_date.desc()).limit(2).all()

        received_reviews = (session.query(Reviews).
                            filter(Reviews.executor_id == user.id).
                            order_by(Reviews.created_date.desc()).all())

        avg_rating = session.query(func.avg(Reviews.rating)).filter(Reviews.executor_id == user.id).scalar()
        avg_rating = round(avg_rating, 2) if avg_rating else "N/A"

        return render_template('profile.html', user=user,
                               completed_jobs=completed_jobs, received_reviews=received_reviews, avg_rating=avg_rating)
    finally:
        session.close()


@app.route('/profile/<int:user_id>/set_role/<int:role>')
@login_required
def set_role(user_id, role):
    session = db_session.create_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            abort(404, description="Пользователь не найден")

        if role not in (1, 2, 3):
            abort(404, description="Роли не существует")

        if current_user.role < 3:
            flash("У вас недостаточно прав", "warning")
            return redirect(f"/profile/{user_id}")

        if current_user.id == user_id:
            flash("Вы не можете менять свою роль!", "warning")
            return redirect(f"/profile/{user_id}")

        user.role = role
        session.commit()

        return redirect(f"/profile/{user_id}")
    finally:
        session.close()

@app.route('/settings/theme/toggle')
def toggle_theme():
    # Переключаем тему в сессии
    if session.get('theme') == 'dark':
        session['theme'] = 'light'
    else:
        session['theme'] = 'dark'
    return redirect(request.referrer or url_for('index'))

@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    try:
        return session.query(User).get(int(user_id))
    finally:
        session.close()


if __name__ == '__main__':
    main()
