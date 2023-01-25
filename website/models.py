from website import db, app, login_manager
import pandas as pd
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
import os

Tours_df = pd.read_csv(os.path.join(os.path.dirname(__file__), r'static\datasets\tours_df.csv'))
Customers_df = pd.read_csv(os.path.join(os.path.dirname(__file__), r'static\datasets\customers_df.csv'))
Bookings_df = pd.read_csv(os.path.join(os.path.dirname(__file__), r'static\datasets\bookings_df.csv'))
Users_df = pd.read_csv(os.path.join(os.path.dirname(__file__), r'static\datasets\users_df.csv'))

Users_df["Password"] = Users_df["Password"].map(lambda x: generate_password_hash(str(x), method='sha256')) # hash passwords
Tours_df['img_file'] = Tours_df['Destination'].map(lambda x: 'destination-'+x+'.jpg' if os.path.exists(os.path.join(app.static_folder, 'img', 'destination-'+x+'.jpg')) else 'destination-default.jpg')

@login_manager.user_loader
def load_user(id):
    return Users.query.get(int(id))

bookings = db.Table('bookings',
    db.Column('tour_id', db.Integer, db.ForeignKey('tours.id')),
    db.Column('customer_id', db.Integer, db.ForeignKey('customers.id'))
)

class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(150))
    Email = db.Column(db.String(150), unique=True)
    Password = db.Column(db.String(150))
    customers = db.relationship('Customers', back_populates='user', lazy=True) # all the customers assigned to the user

class Tours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Destination = db.Column(db.String)
    Region = db.Column(db.String)
    Start_Date = db.Column(db.Date)
    End_Date = db.Column(db.Date)
    Duration = db.Column(db.Integer)
    City_Of_Departure = db.Column(db.String)
    Price = db.Column(db.Integer)
    Children = db.Column(db.String)
    img_file = db.Column(db.String)

class Customers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String)
    Surname = db.Column(db.String)
    Date_Of_Birth = db.Column(db.Date)
    Passport_Number = db.Column(db.String)
    Passport_Expiration_Date = db.Column(db.Date)
    Phone_Number = db.Column(db.String)
    SSN = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    travelling = db.relationship('Tours', secondary=bookings, backref='travellers') # all the tours in which the customer participates
    user = db.relationship('Users', back_populates='customers', lazy=True) # assigned user

with app.app_context():
    db.create_all()

with db.engine.connect() as connection:
    if not connection.execute("select count(1) where exists (select * from tours)").fetchone()[0]: #if the table is empty
        Tours_df.to_sql(name='tours', con=connection, if_exists='append', index=False)

    if not connection.execute("select count(1) where exists (select * from customers)").fetchone()[0]: #if the table is empty
        Customers_df.to_sql(name='customers', con=connection, if_exists='append', index=False)

    if not connection.execute("select count(1) where exists (select * from bookings)").fetchone()[0]: #if the table is empty
        Bookings_df.to_sql(name='bookings', con=connection, if_exists='append', index=False)

    if not connection.execute("select count(1) where exists (select * from users)").fetchone()[0]: #if the table is empty
        admin = Users(Name='Ewa', Email='contact@adventureclub.com', #admin account
                      Password=generate_password_hash('adventureclub', method='sha256'))

        first_user = Users(Name='John', Email='john@email.com', #non-admin account
                      Password=generate_password_hash('haslomaslo', method='sha256'))

        db.session.add_all([admin,first_user])
        db.session.commit()

        Users_df.to_sql(name='users', con=connection, if_exists='append', index=False)
