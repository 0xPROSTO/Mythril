import json
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Length


def validate_price_format(form, field):
    value = str(field.data)
    if len(value[value.find('.') + 1:]) > 2:
        raise ValidationError("После точки допускается только 2 цифры")


def load_categories(file_path='./data/categories.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        categories = json.load(f)
    return [(category['value'], category['label']) for category in categories]


class JobsForm(FlaskForm):
    title = StringField('Название работы', validators=[DataRequired(),
                                                       Length(max=100,
                                                              message="Название не должно превышать 100 символов")])
    description = TextAreaField("Описание работы", validators=[DataRequired(),
                                                               Length(max=2000,
                                                                      message="Описание не должно превышать 2000 символов")])
    categories = load_categories()
    category = SelectField(
        'Категория',
        choices=categories, validators=[DataRequired()])
    price = FloatField(
        'Рекомендуемая цена (руб.)',
        validators=[
            DataRequired(),
            NumberRange(min=0.0, message="Цена не может быть отрицательной, или она слишком большая",
                        max=1_000_000_000_000),
            validate_price_format
        ],
        render_kw={
            'step': '0.01',
            'inputmode': 'decimal',
            'placeholder': '0.00'
        }
    )
    contact = StringField("Как с вами связаться",
                          validators=[DataRequired(), Length(max=255, message="Контактная информация слишком длинная")])
    status = SelectField(
        label="Статус",
        choices=[
            ('Открыт', 'Открыт'),
            ('В работе', 'В работе'),
            ('Завершён', 'Завершён')
        ],
        validators=[DataRequired()],
        default='Открыт'
    )
    submit = SubmitField('Применить')


class ResponseForm(FlaskForm):
    comment = TextAreaField(
        'Комментарий',
        validators=[DataRequired(), Length(max=512, message="Комментарий не должен превышать 512 символов")],
        render_kw={'rows': 5}
    )
    price = FloatField(
        'Рекомендуемая цена (руб.)',
        validators=[
            DataRequired(),
            NumberRange(min=0.0, message="Цена не может быть отрицательной, или она слишком большая",
                        max=1_000_000_000_000),
            validate_price_format
        ],
        render_kw={
            'step': '0.01',
            'inputmode': 'decimal',
            'placeholder': '0.00'
        }
    )
    submit = SubmitField('Отправить отклик')


class ReviewsForm(FlaskForm):
    comment = TextAreaField("Комментарий", validators=[
        DataRequired(message="Комментарий обязателен"),
        Length(max=512, message="Описание не должно превышать 512 символов")
    ], render_kw={'rows': 5, 'placeholder': 'Ваш отзыв...'})

    rating = IntegerField(
        'Рейтинг',
        validators=[DataRequired(message="Укажите рейтинг"),
                    NumberRange(min=1, max=10, message='Рейтинг должен быть от 1 до 10')
                    ], render_kw={'min': 1, 'max': 10, 'placeholder': '1-10'}
    )

    submit = SubmitField('Отправить')
