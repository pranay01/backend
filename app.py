from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
import flask_bcrypt
import flask_cors
import flask_praetorian
from joblib import dump, load
import json
import os
import psycopg2
import stripe
import sys
import pdb
import stripe

from src.db.models import db, guard, User
from src.db.utils import insert_feedback, insert_user_payment_information
from src.utils import is_prompt_permissible, create_generator


ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

# This is your test secret API key.
# stripe.api_key = ""
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
YOUR_DOMAIN = 'http://localhost:8080'


print(os.environ, flush=True)

app = Flask(__name__)
app.debug = True
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["JWT_ACCESS_LIFESPAN"] = {"hours": 24}
app.config["JWT_REFRESH_LIFESPAN"] = {"days": 30}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['POSTGRESQL_HOST'] = os.environ.get('POSTGRESQL_HOST')
app.config['POSTGRESQL_USER_NAME'] = os.environ.get('POSTGRESQL_USER_NAME')
app.config['POSTGRESQL_PASSWORD'] = os.environ.get('POSTGRESQL_PASSWORD')
app.config['POSTGRESQL_DB'] = os.environ.get('POSTGRESQL_DB')
user = app.config['POSTGRESQL_USER_NAME']
password = app.config['POSTGRESQL_PASSWORD']
host = app.config['POSTGRESQL_HOST']
database = app.config['POSTGRESQL_DB']
port = "5432"
app.config["SQLALCHEMY_DATABASE_URI"] = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}'
app.secret_key = os.environ.get("SECRET_KEY")


# Initialize the flask-praetorian instance for the app.
guard.init_app(app, User)

# Initialize the database.
db.init_app(app)

# Create flask-login manager.
# login_manager = flask_login.LoginManager()
# login_manager.init_app(app=app)

# Create encryption for passwords.
bcrypt = flask_bcrypt.Bcrypt(app=app)

# Create CORS.
cors = flask_cors.CORS(
    # TODO: Are we supposed to allow any origin?
    resources={
        r'/create-checkout-session/*': {'origins': '*'},
        r'/create-portal-session/*': {'origins': '*'},
        r'/generate/*': {'origins': '*'},
        r'/feedback/*': {'origins': '*'},
        r'/payments/*': {'origins': '*'},
        r'/refresh/*': {'origins': '*'},
        r'/signup/*': {'origins': '*'},
        r'/signin/*': {'origins': '*'},
        r'/webhook/*': {'origins': '*'},
    },
)
cors.init_app(app=app)


# Add users for the example
with app.app_context():
    print(app.config["SQLALCHEMY_DATABASE_URI"], flush=True)
    db.create_all()
    try:
        num_rows_deleted = User.query.delete()
        print(num_rows_deleted, flush=True)
        db.session.commit()
    except:
        db.session.rollback()
    db.session.commit()


@app.route('/complete-checkout-session', methods=['POST'])
def complete_checkout_session():
    print(request.get_json(force=True))
    print(request.form)

    insert_user_payment_information(
        username=username,
        stripe_customer_id=checkout_session['customer'],
        stripe_subscription_id=checkout_session['id'],
        stripe_price_id=price_id)


# See https://stackoverflow.com/a/26395623/4570472 for cross_origin()
@app.route('/create-checkout-session', methods=['POST'])
@flask_cors.cross_origin()
@flask_praetorian.auth_required
def create_checkout_session():
    """
    Looks up Stripe prices and redirects the user to Stripe's secure website.
    We require authorization because only users should be billable.
    """
    try:
        req = request.get_json(force=True)
        # print('Req: ', req, flush=True)
        price_id = req.get("price_id")
        username = flask_praetorian.current_user().username
        success_url = YOUR_DOMAIN + '/complete-checkout-session?success=true&session_id={CHECKOUT_SESSION_ID}'
        cancel_url = YOUR_DOMAIN + '/complete-checkout-session?canceled=true'
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # 'price': price.data[0].id,
                    'price': price_id,
                },
            ],
            # Other payment types: https://stripe.com/docs/api/payment_methods/object#payment_method_object-type
            payment_method_types=["card"],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
        )
        print(checkout_session, flush=True)
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        print(e, flush=True)
        ret = {"status": "Error recording user payment"}
        return jsonify(ret), 500


@app.route("/get-user-subscription-id")
@flask_praetorian.roles_accepted("operator", "admin", "creator")
def get_user_subscription_id():
    """
    A protected endpoint that accepts any of the listed roles. The
    roles_accepted decorator will require that the supplied JWT includes at
    least one of the accepted roles. Send the bearer token and the
    subscription ID is returned. If there is none from the database
    None is returned.
    .. example::
       $ curl http://localhost:8080/get-user-subscription-id -X GET \
         -H "Authorization: Bearer <your_token>"
    """
    #print("getting current user", flush=True)
    username = flask_praetorian.current_user().username
    #print("user is " + str(username), flush=True)
    user = User.lookup(username=username)
    #print("we have looked up the user", flush=True)
    return str(user.stripe_subscription_id)


# TODO: Extend this function to be able to create new subscriptions for different customers
# This is a test function I used to create our first "live" subscription for a customer
@app.route('/create-subscription', methods=['GET'])
@flask_praetorian.roles_accepted("operator", "admin", "creator")
def create_subscription():
    """
    A protected endpoint that accepts any of the listed roles. The
    roles_accepted decorator will require that the supplied JWT includes at
    least one of the accepted roles. Send the bearer token and the
    subscription ID is returned. If there is no customer one is created
    if there is no subscription one is created. Returns a subscription id.
    .. example::
       $ curl http://localhost:8080/create-subscription -X GET \
         -H "Authorization: Bearer <your_token>"
    """

    username = str(flask_praetorian.current_user().username)

    user = User.lookup(username=username)

    stripe_customer_id = user.stripe_customer_id

    if stripe_customer_id is None:
        print("No stripe customer in stripe: creating one now", flush=True)

        customer = stripe.Customer.create(
            description=username,
        )

        # update stripe_customer_id in database for user with username of username
        stripe_customer_id = str(customer.id)
        user.stripe_customer_id = stripe_customer_id
    else:
        print("Stripe customer ID already exists in database: No new stripe customer was created in the database", flush=True)

    print('customer ID: ' + stripe_customer_id, flush=True)

    stripe_subscription_id = user.stripe_subscription_id

    if stripe_subscription_id is None:
        print("No stripe subscription in the database: checking for one in stripe now", flush=True)
        # TODO: check stripe for subscription IDs for this customer
        subs = stripe.Subscription.list(limit=1000000)
        for sub in subs:
            print(sub, flush=True)
            if sub.customer == stripe_customer_id:
                stripe_subscription_id = sub.id
        if stripe_subscription_id is None:
            print("No stripe subscription on stripe: creating one now", flush=True)

            subscription = stripe.Subscription.create(
                customer=stripe_customer_id,
                items=[
                    {"price": "price_1LAHFfANX7SRTyI1CAVCDmNl"},
                ],
            )

            # update stripe_subscription_id in database for user with username of username
            stripe_subscription_id = str(subscription.id)
            user.stripe_subscription_id = stripe_subscription_id
        else:
            print("Stripe subscription already exists in Stripe but not in the database: creating one in the database now")
            user.stripe_subscription_id = stripe_subscription_id
    else:
        print("Stripe subscription already exists in database: No stripe subscription was made", flush=True)

    db.session.commit()

    print('subscription ID: ' + stripe_subscription_id, flush=True)

    return stripe_subscription_id


# # TODO: Extend this function to be able to create new customers and send valid descriptions
# # This is a test function I used to create our first "live" customer in stripe
# @app.route('/create-customer', methods=['GET'])
# def create_customer():

#     customer = stripe.Customer.create(
#         description="Chase Brignac",
#     )

#     return customer.id


@app.route('/create-portal-session', methods=['POST'])
@flask_praetorian.auth_required
def customer_portal():
    # For demonstration purposes, we're using the Checkout session to retrieve the customer ID.
    # Typically this is stored alongside the authenticated user in your database.
    checkout_session_id = request.form.get('session_id')
    checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)

    # This is the URL to which the customer will be redirected after they are
    # done managing their billing with the portal.
    return_url = YOUR_DOMAIN

    portalSession = stripe.billing_portal.Session.create(
        customer=checkout_session.customer,
        return_url=return_url,
    )
    return redirect(portalSession.url, code=303)


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        # print('This is error output' + str(request.json), file=sys.stderr, flush=True)
        print('This is standard output' + str(request.json), file=sys.stdout, flush=True)
        description = str(request.json['description'])
        email = str(request.json['email'])
        return insert_feedback(description=description, email=email)
    else:
        print('This is error output', file=sys.stderr, flush=True)
        print('This is standard output', file=sys.stdout, flush=True)
        result = {'Message': "Submit feedback by sending a POST with JSON "
                             "payload with a description (and an optional"
                             "screenshot and an optional email)"}
        return result, 400


@app.route('/generate-images', methods=['GET', 'POST'])
def generate_images():
    prompt = request.args.get('prompt')
    prompt_counter = request.args.get('counter')

    # TODO: figure out what these two lines do; are they necessary?
    # app.set_cookie('cross-site-cookie', 'bar', samesite='None', secure=True)
    # app.headers.add('Set-Cookie', 'cross-site-cookie=bar; SameSite=None; Secure')

    def return_message_generator():
        prompt_is_permissible = is_prompt_permissible(prompt=prompt)
        if prompt_is_permissible:
            gen = create_generator(prompt=prompt)
            for uri in gen:
                # https://www.html5rocks.com/en/tutorials/eventsource/basics/
                result_str = 'data: {\n'
                result_str += f'data: "uri": "{uri}",\n'
                result_str += f'data: "counter": {prompt_counter}\n'
                result_str += 'data: }\n\n'
                yield result_str

        # following https://stackoverflow.com/a/64204046
        final_result_str = 'event: close\n'
        final_result_str += 'data: {\n'
        final_result_str += f'data: "counter": {prompt_counter}\n'
        final_result_str += 'data: }\n\n'
        yield final_result_str

    return app.response_class(return_message_generator(), mimetype='text/event-stream')


@app.route('/refresh', methods=['POST'])
def refresh():
    """
    Refreshes an existing JWT by creating a new one that is a copy of the old
    except that it has a refrehsed access expiration.
    .. example::
       $ curl http://localhost:3000/api/refresh -X GET \
         -H "Authorization: Bearer <your_token>"
    """
    old_token = request.get_data()
    new_token = guard.refresh_jwt_token(old_token)
    ret = {'access_token': new_token}
    return jsonify(ret), 200


@app.route("/signin", methods=["POST"])
def signin():
    """
    Logs a user in by parsing a POST request containing user credentials and
    issuing a JWT token.
    .. example::
       $ curl http://localhost:3000/login -X POST \
         -d '{"username":"Walter","password":"calmerthanyouare"}'
    """

    req = request.get_json(force=True)
    username = req.get("username", None)
    password = req.get("password", None)
    user = guard.authenticate(username, password)
    ret = {"access_token": guard.encode_jwt_token(user)}
    print(ret)
    return jsonify(ret), 200


@app.route("/signup", methods=["POST"])
def signup():
    """
    Logs a user in by parsing a POST request containing user credentials and
    issuing a JWT token.
    .. example::
       $ curl http://localhost:3000/login -X POST \
         -d '{"username":"walter","password":"calmerthanyouare"}'
    """

    req = request.get_json(force=True)
    username = req.get("username")
    password = req.get("password", None)
    email = req.get("email", None)

    if username is None or password is None or email is None:
        ret = {"Message": "All of username, password, email must be provided"}
        return jsonify(ret), 400
    else:
        username = username.lower()

    username_exists = User.lookup(username=username) is not None
    if username_exists:
        ret = {"Message": "Please choose a different user name"}
        return jsonify(ret), 409

    db.session.add(
        User(
            username=username,
            hashed_password=guard.hash_password(password),
            email=email,
            roles="explorer",
        )
    )
    db.session.commit()
    user = guard.authenticate(username, password)
    ret = {"access_token": guard.encode_jwt_token(user)}
    return jsonify(ret), 200


@app.route("/signout")
def signout():
    raise NotImplementedError


@app.route('/webhook', methods=['POST'])
def webhook_received():
    # Replace this endpoint secret with your endpoint's unique secret
    # If you are testing with the CLI, find the secret by running 'stripe listen'
    # If you are using an endpoint defined with the API or dashboard, look in your webhook settings
    # at https://dashboard.stripe.com/webhooks
    # webhook_secret = 'whsec_12345'
    webhook_secret = 'whsec_90cRdQ4PD5ZCHIgmlTd19kdojsY8VvVz'
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get('stripe-signature')
        try:
            # Documentation on the event object: https://stripe.com/docs/api/events/object
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret)
            data = event['data']
        except Exception as e:
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']

    # Do backend magic with this data object
    data_object = data['object']

    print('event ' + event_type)

    if event_type == 'checkout.session.completed':
        print('🔔 Payment succeeded!', flush=True)
    elif event_type == 'customer.subscription.trial_will_end':
        print('Subscription trial will end', flush=True)
    elif event_type == 'customer.subscription.created':
        print('Subscription created %s', event.id, flush=True)
    elif event_type == 'customer.subscription.updated':
        print('Subscription created %s', event.id, flush=True)
    elif event_type == 'customer.subscription.deleted':
        # handle subscription canceled automatically based
        # upon your subscription settings. Or if the user cancels it.
        print('Subscription canceled: %s', event.id, flush=True)

    return jsonify({'status': 'success'}), 200


@app.route('/')
def hello_world():
    result = {'status': 'success'}
    # return result
    return result, 200


@app.route("/fetch_user_price_id", methods=["POST"])
@flask_praetorian.auth_required
def get_user_payment_plan():
    """

    """
    username = flask_praetorian.current_user().username
    user = User.query.filter_by(username=username).one_or_none()

    if user is None:
        ret = {'Message': 'User does not exist'}
        return jsonify(ret), 404

    stripe_customer_id = user.stripe_customer_id
    if len(stripe_customer_id) == 0:
        ret = {"Message": "User is not a Stripe customer."}
        return jsonify(ret), 400
    else:
        stripe_price_id = user.stripe_price_id
        ret = {"Message": f"User is on paid plan {stripe_price_id}"}
        return jsonify(ret), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
