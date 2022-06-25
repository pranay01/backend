from flask import Flask, render_template, request, url_for
import flask_praetorian
import psycopg2
import os
from re import sub
from typing import Dict

from src.db.models import db, guard, User
from src.db.models import db, User, Payment


def fetch_user_payment_info(username: str,
                            ) -> Dict:
    """
    Query
    :param username:
    :return:
    """


def insert_feedback(description: str,
                    email: str = "",
                    ) -> str:
    """
    Insert feedback into Postgres database.

    :param description: Free text entry of feedback.
    :param email: Optional string of reply email.
    :return:
    # TODO: Why do we return the description?
    """
    text = ''
    if request.method == 'POST':
        """ These are the postgres environment variables to avoid storing sensitive info in the github repo """
        POSTGRESQL_HOST = os.environ.get('POSTGRESQL_HOST')
        POSTGRESQL_USER_NAME = os.environ.get('POSTGRESQL_USER_NAME')
        POSTGRESQL_PASSWORD = os.environ.get('POSTGRESQL_PASSWORD')
        POSTGRESQL_DB = os.environ.get('POSTGRESQL_DB')

        """ We use psycopg2 to create a database connection either locally or in AWS """
        conn = psycopg2.connect(
            host=POSTGRESQL_HOST,
            port=5432,
            database=POSTGRESQL_DB,
            user=POSTGRESQL_USER_NAME,
            password=POSTGRESQL_PASSWORD)

        conn.autocommit = True

        """ Create a cursor object """
        cur = conn.cursor()

        """ Insert new feedback """
        cur.execute("INSERT INTO public.feedbacks values(default,%(description)s,%(email)s);",
                    {'description': description,
                     'email': email})

    return description


def insert_user_payment_information(username: str,
                                    stripe_customer_id: str,
                                    stripe_subscription_id: str,
                                    stripe_price_id: str,
                                    ) -> None:
    user = User.query.filter_by(username=username).one_or_none()
    if user is None:
        raise ValueError('User does not exist')
    if user.username != username:
        raise ValueError(f"Mismatch between input username ({username})"
                         f"and retrieved User's username ({user.username})")

    db.session.add(
        Payment(
            username=username,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=stripe_price_id,
            roles="v00.00.00"))
    db.session.commit()
    return None


# @flask_praetorian.roles_accepted('admin', 'explorer', 'creator')
# def insert_new_customer(stripe_customer_id: str, stripe_product_id: str, stripe_price_id: str):
#     """
#     An endpoint to insert a new customer into the database
#     Takes in stripe_customer_id, stripe_product_id, and stripe_price_id
#     """

#     user = User.lookup(username=flask_praetorian.current_user)
#     user.modify(stripe_customer_id, subscription=stripe_product_id, price=stripe_price_id)
