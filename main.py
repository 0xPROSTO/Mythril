import json

from flask import Flask, render_template, redirect, request, abort, flash, session, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from data import db_session
from data.users import User
from data.jobs import Jobs
from data.responses import Responses
from data.reviews import Reviews
from forms.user_form import RegisterForm, LoginForm
from forms.jobs_form import JobsForm, ResponseForm

from routes.jobs_routes import jobs_blueprint
from routes.responses_routes import responses_blueprint
from routes.my_routes import my_blueprint
from routes.auth_routes import auth_blueprint

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

        reviews = []

        return render_template('profile.html', user=user, completed_jobs=completed_jobs, reviews=reviews)
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


if __name__ == '__main__':
    main()
