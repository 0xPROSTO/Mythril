import json
import datetime

from flask import Flask, render_template, redirect, request, abort, flash, session, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from data import db_session
from data.users import User
from data.jobs import Jobs
from data.responses import Responses
from data.reviews import Reviews
from forms.user_form import RegisterForm, LoginForm
from forms.jobs_form import JobsForm, ResponseForm

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'ENTER_YOUR_SECRETKEY_HERE'


def main():
    db_session.global_init("database/database.db")
    session = db_session.create_session()

    app.run(port=8080)


def load_categories(file_path='data/categories.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        categories = json.load(f)
    return {category['value']: category['label'] for category in categories}


@app.route("/")
def index():
    session = db_session.create_session()
    jobs = session.query(Jobs).all()

    for job in jobs:
        job.response_count = session.query(Responses).filter(Responses.job_id == job.id).count()

    title="Доступные работы"
    return render_template("index.html", jobs=jobs, title=title)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    try:
        user = session.get(User, int(user_id))
        return user
    finally:
        session.close()
    # return session.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
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
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/add-jobs', methods=['GET', 'POST'])
@login_required
def add_jobs():
    form = JobsForm()
    if form.validate_on_submit():
        session = db_session.create_session()
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
        session.close()
        return redirect('/')
    return render_template('jobs.html', title='Добавление работы', form=form)


@app.route('/delete-jobs/<int:id>', methods=['GET', 'POST'])
@login_required
def jobs_delete(id):
    db_sess = db_session.create_session()
    jobs = db_sess.query(Jobs).filter(Jobs.id == id).first()
    if not jobs:
        abort(404)
    if jobs.author_id != current_user.id and current_user.role < 2:
        flash('У вас нет прав для редактирования этого задания.', 'danger')
        return redirect('/')
    else:
        db_sess.delete(jobs)
        db_sess.commit()
    return redirect('/')


@app.route('/edit-jobs/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_jobs(id):
    form = JobsForm()
    db_sess = db_session.create_session()
    jobs = db_sess.query(Jobs).filter(Jobs.id == id).first()
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
        jobs.status = form.status.data
        db_sess.commit()
        return redirect('/')
    return render_template('jobs.html', title='Редактирование работы', form=form)


@app.route('/jobs/<int:id>', methods=['GET', 'POST'])
@login_required
def jobs_view(id):
    db_sess = db_session.create_session()
    item = db_sess.query(Jobs).filter(Jobs.id == id).first()
    if not item:
        abort(404)
    categories = load_categories()

    return render_template('view_jobs.html', title='Просмотр работы',
                           item=item, categories=categories)


@app.route('/answer-jobs/<int:job_id>', methods=['GET', 'POST'])
@login_required
def answer_jobs(job_id):
    session = db_session.create_session()
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
        return redirect(f'/my-responses')


    form = ResponseForm(price=job.price)
    categories = load_categories()

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

    return render_template('answer_jobs.html', job=job, form=form, categories=categories)

@app.route('/view-responses/<int:job_id>')
@login_required
def view_responses(job_id):
    session = db_session.create_session()
    job = session.query(Jobs).get(job_id)
    if not job:
        abort(404)
    if job.author_id != current_user.id and current_user.role < 2:
        flash('Вы не можете просматривать отклики на эту работу.', 'danger')
        return redirect(f'/jobs/{job_id}')

    responses = session.query(Responses).filter(Responses.job_id == job_id).all()
    return render_template('view_responses.html', job=job, responses=responses)

@app.route('/select-response/<int:job_id>/<int:response_id>', methods=['POST'])
@login_required
def select_response(job_id, response_id):
    session = db_session.create_session()
    job = session.query(Jobs).get(job_id)
    response = session.query(Responses).get(response_id)

    if not job or not response:
        abort(404)
    if job.author_id != current_user.id:
        flash('Вы не можете выбрать исполнителя для этой работы.', 'danger')
        return redirect(f'/view-responses/{job_id}')
    if job.executor_id is not None:
        flash('Исполнитель уже выбран.', 'danger')
        return redirect(f'/view-responses/{job_id}')
    if job.status != "Открыт":
        flash('Работа уже в работе или завершена.', 'danger')
        return redirect(f'/view-responses/{job_id}')

    job.executor_id = response.user_id
    job.status = "В работе"
    session.commit()

    return redirect(f'/view-responses/{job_id}')

@app.route('/my-jobs')
@login_required
def my_jobs():
    session = db_session.create_session()
    jobs = session.query(Jobs).filter_by(author_id=current_user.id)
    title = "Мои работы"
    return render_template("index.html", jobs=jobs, title=title)

@app.route('/my-responses')
@login_required
def my_responses():
    session = db_session.create_session()
    responses = session.query(Responses).filter_by(user_id=current_user.id)
    return render_template("my_responses.html", responses=responses)

@app.route('/delete-responses/<int:id>', methods=['GET', 'POST'])
@login_required
def responses_delete(id):
    session = db_session.create_session()
    response = session.query(Responses).filter(Responses.id == id, Responses.user == current_user).first()
    if response:
        if response.job.executor_id == current_user.id:
            response.job.status = "Открыт"
            response.job.executor_id = None
        session.delete(response)
        session.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/profile/<int:user_id>')
def profile(user_id):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404, description="Пользователь не найден")

    completed_jobs = session.query(Jobs).filter(
        Jobs.executor_id == user.id,
        Jobs.status == "Завершён"
    ).order_by(Jobs.created_date.desc()).limit(2).all()

    reviews = []

    return render_template('profile.html', user=user, completed_jobs=completed_jobs, reviews=reviews)


@app.route('/toggle-theme')
def toggle_theme():
    # Переключаем тему в сессии
    if session.get('theme') == 'dark':
        session['theme'] = 'light'
    else:
        session['theme'] = 'dark'
    # Возвращаемся на предыдущую страницу
    return redirect(request.referrer or url_for('index'))


if __name__ == '__main__':
    main()
