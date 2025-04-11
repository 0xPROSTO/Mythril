from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, BooleanField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Length


class RegisterForm(FlaskForm):
    name = StringField('Имя пользователя',
                       validators=[DataRequired(),
                                   Length(1, 32, message="Имя должно быть от 1 до 32 символов")])
    email = EmailField('Почта', validators=[DataRequired(), Length(max=255, message="Почта слишком длинная")])
    password = PasswordField('Пароль', validators=[DataRequired(),
                                                   Length(min=6, max=128,
                                                          message="Пароль должен быть от 6 до 128 символов")])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired(), Length(max=255, message="Почта слишком длинная")])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(max=128, message="Пароль слишком длинный")])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')
