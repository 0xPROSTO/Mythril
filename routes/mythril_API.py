from flask import Blueprint, session as flask_session
from flask_restful import reqparse, abort, Api, Resource
from data import db_session
from data.jobs import Jobs
from data.responses import Responses
from data.reviews import Reviews
from data.users import User
from sqlalchemy import func
import datetime
import json


def load_categories(file_path='./data/categories.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        categories = json.load(f)
    return [(category['value'], category['label']) for category in categories]


def validate_price(value, name):
    if value is None:
        raise ValueError(f"{name} is required")
    try:
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
        if value > 1_000_000_000_000:
            raise ValueError(f"{name} cannot exceed 1 trillion")
        value_str = f"{float(value):.10f}".rstrip('0')
        decimal_part = value_str[value_str.find('.') + 1:] if '.' in value_str else ''
        if len(decimal_part) > 2:
            raise ValueError(f"{name} must have no more than 2 decimal places")
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a valid number with no more than 2 decimal places")


def validate_length(max_length):
    def validate(value, name):
        if value is None:
            raise ValueError(f"{name} is required")
        if len(value) > max_length:
            raise ValueError(f"{name} must not exceed {max_length} characters")
        return value

    return validate


CATEGORIES = load_categories()
CATEGORY_VALUES = [value for value, label in CATEGORIES]
CATEGORY_HELP_MESSAGE = f"Category must be one of: {', '.join([f'{value}' for value, _ in CATEGORIES])}"

api_blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(api_blueprint)

login_parser = reqparse.RequestParser()
login_parser.add_argument('email', type=validate_length(255), required=True, help='Email is required')
login_parser.add_argument('password', type=validate_length(128), required=True, help='Password is required')

job_parser = reqparse.RequestParser()
job_parser.add_argument('title', type=validate_length(128), required=True, help='Title is required')
job_parser.add_argument('description', type=validate_length(2048), required=True, help='Description is required')
job_parser.add_argument('category', type=str, choices=CATEGORY_VALUES, required=True, help=CATEGORY_HELP_MESSAGE)
job_parser.add_argument('price', type=validate_price, required=True,
                        help='Price must be a valid number with no more than 2 decimal places')
job_parser.add_argument('contact', type=validate_length(256), required=True, help='Contact is required')
job_parser.add_argument('status', type=str, choices=('Открыт', 'В работе', 'Завершён'), default='Открыт')

response_parser = reqparse.RequestParser()
response_parser.add_argument('comment', type=validate_length(512), required=True, help='Comment is required')
response_parser.add_argument('price', type=validate_price, required=True,
                             help='Price must be a valid number with no more than 2 decimal places')


def login_required(method):
    """Декоратор для проверки авторизации пользователя в API."""

    def wrapper(*args, **kwargs):
        if 'user_id' not in flask_session:
            return {'error': 'Unauthorized'}, 401
        return method(*args, **kwargs)

    return wrapper


def abort_if_job_not_found(job_id):
    session = db_session.create_session()
    try:
        job = session.query(Jobs).get(job_id)
        if not job:
            abort(404, message=f"Job {job_id} not found")
        return job
    finally:
        session.close()


def abort_if_user_not_found(user_id):
    session = db_session.create_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            abort(404, message=f"User {user_id} not found")
        return user
    finally:
        session.close()


class LoginResource(Resource):
    def post(self):
        """Обрабатывает вход пользователя через API."""
        args = login_parser.parse_args()
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == args['email']).first()
            if user and user.check_password(args['password']):
                flask_session['user_id'] = user.id
                flask_session['role'] = user.role
                return {'success': 'Logged in', 'user_id': user.id}, 200
            return {'error': 'Invalid credentials'}, 401
        finally:
            db_sess.close()


class LogoutResource(Resource):
    def post(self):
        """Обрабатывает выход пользователя из системы через API."""
        flask_session.pop('user_id', None)
        flask_session.pop('role', None)
        return {'success': 'Logged out'}, 200


class JobsListResource(Resource):
    def get(self):
        """Возвращает список всех работ."""
        session = db_session.create_session()
        try:
            jobs = session.query(Jobs).all()
            return {
                'jobs': [
                    job.to_dict(
                        only=('id', 'title', 'description', 'category', 'price', 'status', 'author_id', 'created_date'))
                    for job in jobs
                ]
            }
        finally:
            session.close()

    @login_required
    def post(self):
        """Создает новую работу через API."""
        args = job_parser.parse_args()
        session = db_session.create_session()
        try:
            job = Jobs(
                title=args['title'],
                description=args['description'],
                category=args['category'],
                price=args['price'],
                status=args['status'],
                contact=args['contact'],
                author_id=flask_session['user_id'],
                created_date=datetime.datetime.now()
            )
            session.add(job)
            session.commit()
            return {'success': 'Job created', 'job_id': job.id}, 201
        finally:
            session.close()


class JobResource(Resource):
    def get(self, job_id):
        """Возвращает информацию о конкретной работе."""
        abort_if_job_not_found(job_id)
        session = db_session.create_session()
        try:
            job = session.query(Jobs).get(job_id)
            return {
                'job': job.to_dict(
                    only=('id', 'title', 'description', 'category', 'price', 'status', 'author_id', 'created_date'))
            }
        finally:
            session.close()

    @login_required
    def put(self, job_id):
        """Обновляет информацию о работе через API."""
        abort_if_job_not_found(job_id)
        db_sess = db_session.create_session()
        try:
            job = db_sess.query(Jobs).get(job_id)
            if job.author_id != flask_session['user_id'] and flask_session.get('role', 0) < 2:
                return {'error': 'Permission denied'}, 403
            args = job_parser.parse_args()
            if args['status'] == 'Завершён' and (job.status != 'В работе' or not job.executor_id):
                return {
                    'error': 'Job cannot be marked as completed unless it is in progress with an assigned executor'}, 400
            job.title = args['title']
            job.description = args['description']
            job.category = args['category']
            job.contact = args['contact']
            job.price = args['price']
            job.status = args['status']
            db_sess.commit()
            return {'success': 'Job updated'}, 200
        finally:
            db_sess.close()

    @login_required
    def delete(self, job_id):
        """Удаляет работу через API."""
        abort_if_job_not_found(job_id)
        db_sess = db_session.create_session()
        try:
            job = db_sess.query(Jobs).get(job_id)
            if job.author_id != flask_session['user_id'] and flask_session.get('role', 0) < 2:
                return {'error': 'Permission denied'}, 403
            db_sess.delete(job)
            db_sess.commit()
            return {'success': 'Job deleted'}, 200
        finally:
            db_sess.close()


class JobResponsesResource(Resource):
    @login_required
    def get(self, job_id):
        """Возвращает список откликов на работу."""
        abort_if_job_not_found(job_id)
        db_sess = db_session.create_session()
        try:
            job = db_sess.query(Jobs).get(job_id)
            if job.author_id != flask_session['user_id'] and flask_session.get('role', 0) < 2:
                return {'error': 'Permission denied'}, 403
            responses = db_sess.query(Responses).filter(Responses.job_id == job_id).all()
            return {
                'responses': [
                    response.to_dict(only=('id', 'comment', 'price', 'user_id', 'created_date'))
                    for response in responses
                ]
            }
        finally:
            db_sess.close()

    @login_required
    def post(self, job_id):
        """Создает новый отклик на работу через API."""
        abort_if_job_not_found(job_id)
        db_sess = db_session.create_session()
        try:
            job = db_sess.query(Jobs).get(job_id)
            if job.author_id == flask_session['user_id']:
                return {'error': 'Cannot respond to own job'}, 403
            existing_response = db_sess.query(Responses).filter(
                Responses.job_id == job_id,
                Responses.user_id == flask_session['user_id']
            ).first()
            if existing_response:
                return {'error': 'You have already responded to this job'}, 400
            if job.executor_id:
                return {'error': 'The job already has an executor'}, 400
            args = response_parser.parse_args()
            response = Responses(
                user_id=flask_session['user_id'],
                job_id=job_id,
                comment=args['comment'],
                price=args.get('price'),
                created_date=datetime.datetime.now()
            )
            db_sess.add(response)
            db_sess.commit()
            return {'success': 'Response created', 'response_id': response.id}, 201
        finally:
            db_sess.close()

    @login_required
    def patch(self, job_id, response_id):
        """Выбирает исполнителя для работы на основе отклика."""
        abort_if_job_not_found(job_id)
        db_sess = db_session.create_session()
        try:
            job = db_sess.query(Jobs).get(job_id)
            if job.author_id != flask_session['user_id']:
                return {'error': 'Only the job author can select an executor'}, 403
            if job.executor_id:
                return {'error': 'The job already has an executor'}, 400
            response = db_sess.query(Responses).filter(
                Responses.id == response_id,
                Responses.job_id == job_id
            ).first()
            if not response:
                return {'error': 'Response not found or does not belong to this job'}, 404
            job.executor_id = response.user_id
            job.status = 'В работе'
            db_sess.commit()
            return {'success': 'Executor selected', 'executor_id': response.user_id}, 200
        finally:
            db_sess.close()


class UserResource(Resource):
    """Возвращает информацию о пользователе, его работах и отзывах."""

    @login_required
    def get(self, user_id):
        abort_if_user_not_found(user_id)
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).get(user_id)
            completed_jobs = db_sess.query(Jobs).filter(
                Jobs.executor_id == user.id,
                Jobs.status == "Завершён"
            ).order_by(Jobs.created_date.desc()).limit(2).all()
            received_reviews = db_sess.query(Reviews).filter(
                Reviews.executor_id == user.id
            ).order_by(Reviews.created_date.desc()).all()
            avg_rating = db_sess.query(func.avg(Reviews.rating)).filter(
                Reviews.executor_id == user.id
            ).scalar()
            avg_rating = round(avg_rating, 2) if avg_rating else "N/A"
            return {
                'user': user.to_dict(only=('id', 'username', 'role')),
                'avg_rating': avg_rating,
                'completed_jobs': [
                    job.to_dict(only=('id', 'title', 'description', 'category', 'price', 'author_id', 'created_date'))
                    for job in completed_jobs
                ],
                'received_reviews': [
                    review.to_dict(only=('rating', 'comment', 'job_id', 'author_id', 'created_date'))
                    for review in received_reviews
                ]
            }
        finally:
            db_sess.close()


api.add_resource(LoginResource, '/login')
api.add_resource(LogoutResource, '/logout')
api.add_resource(JobsListResource, '/jobs')
api.add_resource(JobResource, '/jobs/<int:job_id>')
api.add_resource(JobResponsesResource, '/jobs/<int:job_id>/responses',
                 '/jobs/<int:job_id>/responses/<int:response_id>')
api.add_resource(UserResource, '/profile/<int:user_id>')
