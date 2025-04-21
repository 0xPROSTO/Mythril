from flask import Blueprint, render_template, redirect
from flask_login import login_user, login_required, logout_user

from data import db_session
from data.users import User

from forms.user_form import RegisterForm, LoginForm

auth_blueprint = Blueprint('auth', __name__)


@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@auth_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        try:
            if session.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация', form=form,
                                       message="Такой пользователь уже есть")
            user = User(
                username=form.name.data,
                email=form.email.data,
            )
            user.set_password(form.password.data)
            session.add(user)
            session.commit()
            return redirect('/login')
        finally:
            session.close()
    return render_template('register.html', title='Регистрация', form=form)


@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        try:
            user = session.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template('login.html', message="Неправильный логин или пароль", form=form)
        finally:
            session.close()
    return render_template('login.html', title='Авторизация', form=form)
