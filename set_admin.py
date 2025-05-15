from data import db_session
from data.users import User
from sqlalchemy.exc import SQLAlchemyError


def grant_admin_by_email(email):
    db_session.global_init("database/database.db")
    session = db_session.create_session()
    try:
        user = session.query(User).filter(User.email == email).first()

        if not user:
            print(f"Ошибка: Пользователь с email {email} не найден")
            return

        if user.role == 3:
            print(f"Ошибка: Пользователь с email {email} уже администратор")
            return

        user.role = 3
        session.commit()
        print(f"Пользователь {user.username} ({user.email}) теперь администратор")

    except SQLAlchemyError as e:
        print(f"Ошибка базы данных: {str(e)}")
        session.rollback()

    except Exception as e:
        print(f"Непредвиденная ошибка: {str(e)}")
        session.rollback()

    finally:
        session.close()


if __name__ == "__main__":
    try:
        email = input("Введите email пользователя для назначения администратором: ")
        if not email:
            print("Ошибка: email не может быть пустым")
        else:
            grant_admin_by_email(email)
    except KeyboardInterrupt:
        print("\nОперация прервана пользователем")