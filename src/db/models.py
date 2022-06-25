# TODO: Switch to own DB management.
from flask_praetorian import Praetorian
from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()
guard = Praetorian()


class Feedback(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(1024))
    email = db.Column(db.String(128))


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(64),
        db.ForeignKey('users.username'),
        index=True,
        nullable=False)
    # TODO: What does this field store? Required by Praetorian.
    # Contains comma-separated roles.
    roles = db.Column(db.Text)
    # TODO: what should the length of the hashed password be?
    # https://stackoverflow.com/a/49430457/4570472
    stripe_customer_id = db.Column(db.String(255), nullable=False, default="")
    stripe_price_id = db.Column(db.String(255), nullable=False, default="")
    stripe_subscription_id = db.Column(db.String(255), index=True, unique=True, nullable=False)
    permitted_actions = db.Column(db.String(255))


    def __repr__(self):
        return '<Payment {}>'.format(self.stripe_subscription_id)

    @property
    def identity(self):
        """
        *Required Attribute or Property*

        flask-praetorian requires that the user class has an ``identity`` instance
        attribute or property that provides the unique id of the user instance
        """
        return self.id

    @property
    def rolenames(self):
        """
        *Required Attribute or Property*

        flask-praetorian requires that the user class has a ``rolenames`` instance
        attribute or property that provides a list of strings that describe the roles
        attached to the user instance
        """
        try:
            return self.roles.split(",")
        except Exception:
            return []

    @classmethod
    def lookup(cls, username: str):
        """
        *Required Method*

        flask-praetorian requires that the user class implements a ``lookup()``
        class method that takes a single ``username`` argument and returns that
        user's subscriptions.
        """
        return cls.query.filter_by(username=username).all()

    @classmethod
    def identify(cls, id):
        """
        *Required Method*

        flask-praetorian requires that the user class implements an ``identify()``
        class method that takes a single ``id`` argument and returns user instance if
        there is one that matches or ``None`` if there is not.
        """
        return cls.query.get(id)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), index=True, nullable=False)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    # TODO: What does this field store?
    roles = db.Column(db.Text)
    # TODO: what should the length of the hashed password be
    hashed_password = db.Column(db.String(256), nullable=False)
    signup_datetime = db.Column(db.DateTime)
    # TODO: What is is_active needed for?
    is_active = db.Column(db.Boolean, default=True, server_default='true')
    payments = db.relationship(
        'Payment',
        backref="users",  # Declare a new property in Payment. Can now do payment.user
        lazy=True,  # defines when SQLAlchemy will load data from database
    )
    createdAt = db.Column(db.DateTime, default=datetime.datetime.utcnow())
    avatar = db.Column(db.String(256), index=True, nullable=True) # stored in S3 and url is put here
    cover = db.Column(db.String(256), index=True, nullable=True) # stored in S3 and url is put here
    about = db.Column(db.String(512), index=True, nullable=True)
    videos = db.Column(db.String(256), index=True, nullable=True)
    # videoLikes = db.relationship('videoLike', back_populates='users')
    # comments = db.relationship('Comment', back_populates='users')
    # # TODO: Is subscribers and subscribed to a many to many or a one to many relationship?
    # # https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html#one-to-many
    # # https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html#many-to-many
    # subscribers = db.relationship('subscription', back_populates='users')
    # subscribedTo = db.relationship('subscription', back_populates='users')
    # views = db.relationship('View', back_populates='users')
    
# model User {
#   id           String         @id @default(uuid())
#   createdAt    DateTime       @default(now())
#   username     String
#   email        String         @unique
#   avatar       String         @default("https://reedbarger.nyc3.digitaloceanspaces.com/default-avatar.png")
#   cover        String         @default("https://reedbarger.nyc3.digitaloceanspaces.com/default-cover-banner.png")
#   about        String         @default("")
#   videos       Video[]
#   videoLikes   VideoLike[]
#   comments     Comment[]
#   subscribers  Subscription[] @relation("subscriber")
#   subscribedTo Subscription[] @relation("subscribedTo")
#   views        View[]
# }

    def __repr__(self):
        return '<User {}>'.format(self.username)

    @property
    def identity(self):
        """
        *Required Attribute or Property*

        flask-praetorian requires that the user class has an ``identity`` instance
        attribute or property that provides the unique id of the user instance
        """
        return self.id

    @property
    def rolenames(self):
        """
        *Required Attribute or Property*

        flask-praetorian requires that the user class has a ``rolenames`` instance
        attribute or property that provides a list of strings that describe the roles
        attached to the user instance
        """
        try:
            return self.roles.split(",")
        except Exception:
            return []

    @property
    def password(self):
        """
        *Required Attribute or Property*

        flask-praetorian requires that the user class has a ``password`` instance
        attribute or property that provides the hashed password assigned to the user
        instance
        """
        return self.hashed_password

    @classmethod
    def lookup(cls, username):
        """
        *Required Method*

        flask-praetorian requires that the user class implements a ``lookup()``
        class method that takes a single ``username`` argument and returns a user
        instance if there is one that matches or ``None`` if there is not.
        """
        return cls.query.filter_by(username=username).one_or_none()

    @classmethod
    def identify(cls, id):
        """
        *Required Method*

        flask-praetorian requires that the user class implements an ``identify()``
        class method that takes a single ``id`` argument and returns user instance if
        there is one that matches or ``None`` if there is not.
        """
        return cls.query.get(id)

    def is_valid(self):
        # TODO: What is this function doing?
        return self.is_active

class Content(db.Model):
    __tablename__ = "content"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


# Copied from https://www.freecodecamp.org/news/build-youtube-with-react/
# TODO: Update to SQLAlchemy Syntax
# model User {
#   id           String         @id @default(uuid())
#   createdAt    DateTime       @default(now())
#   username     String
#   email        String         @unique
#   avatar       String         @default("https://reedbarger.nyc3.digitaloceanspaces.com/default-avatar.png")
#   cover        String         @default("https://reedbarger.nyc3.digitaloceanspaces.com/default-cover-banner.png")
#   about        String         @default("")
#   videos       Video[]
#   videoLikes   VideoLike[]
#   comments     Comment[]
#   subscribers  Subscription[] @relation("subscriber")
#   subscribedTo Subscription[] @relation("subscribedTo")
#   views        View[]
# }
#
# model Comment {
#   id        String   @id @default(uuid())
#   createdAt DateTime @default(now())
#   text      String
#   userId    String
#   videoId   String
#   user      User     @relation(fields: [userId], references: [id])
#   video     Video    @relation(fields: [videoId], references: [id])
# }
#
# model Subscription {
#   id             String   @id @default(uuid())
#   createdAt      DateTime @default(now())
#   subscriberId   String
#   subscribedToId String
#   subscriber     User     @relation("subscriber", fields: [subscriberId], references: [id])
#   subscribedTo   User     @relation("subscribedTo", fields: [subscribedToId], references: [id])
# }
#
# model Video {
#   id          String      @id @default(uuid())
#   createdAt   DateTime    @default(now())
#   title       String
#   description String?
#   url         String
#   thumbnail   String
#   userId      String
#   user        User        @relation(fields: [userId], references: [id])
#   videoLikes  VideoLike[]
#   comments    Comment[]
#   views       View[]
# }
#
# model VideoLike {
#   id        String   @id @default(uuid())
#   createdAt DateTime @default(now())
#   like      Int      @default(0)
#   userId    String
#   videoId   String
#   user      User     @relation(fields: [userId], references: [id])
#   video     Video    @relation(fields: [videoId], references: [id])
# }
#
# model View {
#   id        String   @id @default(uuid())
#   createdAt DateTime @default(now())
#   userId    String?
#   videoId   String
#   user      User?    @relation(fields: [userId], references: [id])
#   video     Video    @relation(fields: [videoId], references: [id])
# }
