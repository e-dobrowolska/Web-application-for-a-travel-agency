from flask import render_template, request, url_for, flash, redirect, abort, jsonify
from website import app, db
from website.models import Users, Tours, Customers
from datetime import date, datetime
from calendar import month_name
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
import os.path
import re

def region_destinations():
    regions_dict = dict()

    with db.engine.connect() as connection:
        query = "SELECT Destination,Region FROM Tours"
        result = connection.execute(query)

        regions_dict["All Regions"] = set()

        for tour in result:
            regions_dict["All Regions"].add(tour.Destination)
            if tour.Region in regions_dict:
                regions_dict[tour.Region].add(tour.Destination)
            else:
                regions_dict[tour.Region] = {tour.Destination}

        for element in regions_dict:
            regions_dict[element] = list(regions_dict[element])
            regions_dict[element].append("All Destinations")
            regions_dict[element][-1], regions_dict[element][0] = regions_dict[element][0], regions_dict[element][-1] # Swap first and last element
            regions_dict[element][1:] = sorted(regions_dict[element][1:])

    return regions_dict

def select_dropdown():
    alldestinations = set()
    alldurations = set()
    allregions = set()
    allcities = set()

    with db.engine.connect() as connection:
        query = "SELECT Destination,Region,Duration,City_Of_Departure FROM Tours"
        result = connection.execute(query)

        for element in result:
            alldestinations.add(element.Destination)
            alldurations.add(element.Duration)
            allregions.add(element.Region)
            allcities.add(element.City_Of_Departure)

    list_of_destinations = list(alldestinations)
    list_of_durations = list(alldurations)
    list_of_regions = list(allregions)
    list_of_cities = list(allcities)
    list_of_destinations.sort()
    list_of_durations.sort()
    list_of_regions.sort()
    list_of_cities.sort()

    return [list_of_destinations, list_of_durations, list_of_regions, list_of_cities]

@app.route('/_update_dropdown')
def update_dropdown():

    selected_class = request.args.get('selected_class', type=str)
    updated_values = region_destinations()[selected_class]
    html_string_selected = ''
    for entry in updated_values:
        html_string_selected += '<option value="{}">{}</option>'.format(entry, entry)

    return jsonify(html_string_selected=html_string_selected)

@app.route("/", methods=["POST", "GET"])
@app.route("/home", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        selected_destination = request.form["destination"]
        selected_start_date = request.form["start_date"]
        selected_end_date = request.form["end_date"]
        selected_duration = request.form["duration"]

        if selected_start_date:
            start_date_split = selected_start_date.split('/')
            start_date_url = start_date_split[0] + '%' + start_date_split[1] + '%' + start_date_split[2]
        else:
            start_date_url = 'start_date_url'

        if selected_end_date:
            end_date_split = selected_end_date.split('/')
            end_date_url = end_date_split[0] + '%' + end_date_split[1] + '%' + end_date_split[2]
        else:
            end_date_url = 'end_date_url'

        return redirect(url_for("destinations", destination_url=selected_destination, region_url="All Regions", start_date_url=start_date_url, end_date_url=end_date_url,
                                min_price_url="min_price_url", max_price_url="max_price_url", duration_url=selected_duration, city_url="All Cities", children_url="Children"))
    else:
        return render_template('index.html', alldestinations=select_dropdown()[0], alldurations=select_dropdown()[1], region_destinations=region_destinations())

@app.route("/about", methods=["POST", "GET"])
def about():
    if request.method == "POST":
        if request.form['action'] == 'search':
            selected_destination = request.form["destination"]
            selected_start_date = request.form["start_date"]
            selected_end_date = request.form["end_date"]
            selected_duration = request.form["duration"]

            if selected_start_date:
                start_date_split = selected_start_date.split('/')
                start_date_url = start_date_split[0] + '%' + start_date_split[1] + '%' + start_date_split[2]
            else:
                start_date_url = 'start_date_url'

            if selected_end_date:
                end_date_split = selected_end_date.split('/')
                end_date_url = end_date_split[0] + '%' + end_date_split[1] + '%' + end_date_split[2]
            else:
                end_date_url = 'end_date_url'

            return redirect(url_for("destinations", destination_url=selected_destination, region_url="All Regions",
                                    start_date_url=start_date_url, end_date_url=end_date_url,
                                    min_price_url="min_price_url", max_price_url="max_price_url",
                                    duration_url=selected_duration, city_url="All Cities", children_url="Children"))
        elif request.form['action'] == 'register':
            name = request.form['name']
            email = request.form['email']
            password1 = request.form['password1']
            password2 = request.form['password2']

            user = Users.query.filter_by(Email=email).first()

            if user:
                flash('Email already exists.', category='error')
            elif not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
                flash('Email is not valid.', category='error')
            elif password1 != password2:
                flash('Passwords don\'t match.', category='error')
            elif len(password1) < 7:
                flash('Password must be at least 7 characters.', category='error')
            else:
                new_user = Users(Name=name, Email=email, Password=generate_password_hash(password1, method='sha256'))
                db.session.add(new_user)
                db.session.commit()

                login_user(new_user, remember=True)
                flash('Account created!', category='success')
                return redirect(url_for('index'))
    else:
        return render_template('about.html', alldestinations=select_dropdown()[0], alldurations=select_dropdown()[1])

@app.route("/timetable")
def timetable():
    with db.engine.connect() as connection:
        query = f'''SELECT id, Destination,Region,Start_Date,End_Date,Duration,City_Of_Departure,Price,Children FROM tours '''
        selected_tours_cursor = connection.execute(query)

        tours_dict = dict()

        for tour in selected_tours_cursor:
            tour_start_date = datetime.strptime(tour.Start_Date, '%Y-%m-%d').date()
            if tour_start_date.year not in tours_dict:
                tours_dict[tour_start_date.year] = [[] for i in range(12)]
            tours_dict[tour_start_date.year][tour_start_date.month-1].append(tour)

        for year in tours_dict:
            for month in tours_dict[year]:
                month.sort(key=lambda tour: datetime.strptime(tour.Start_Date, '%Y-%m-%d'))

        years = list(tours_dict)
        years.sort()

        return render_template('timetable.html', title='Timetable', years=years, tours_dict=tours_dict, month_name=month_name)

@app.route("/destinations",methods=["POST", "GET"])
@app.route("/destinations/<destination_url>/<region_url>/<start_date_url>/<end_date_url>/<min_price_url>/<max_price_url>/<duration_url>/<city_url>/<children_url>",methods=["POST", "GET"])
def destinations(destination_url="All Destinations", region_url="All Regions", start_date_url="start_date_url", end_date_url="end_date_url", min_price_url="min_price_url", max_price_url="max_price_url", duration_url="Duration", city_url="All Cities", children_url="Children"):
    if request.method == "POST":
        selected_region = request.form["selected_class"]
        selected_destination = request.form["destination"]
        selected_start_date = request.form["start_date"]
        selected_end_date = request.form["end_date"]
        selected_children = request.form["children"]
        selected_duration = request.form["duration"]
        selected_city = request.form["city"]
        selected_min_price = request.form["min_price"]
        selected_max_price = request.form["max_price"]

        if selected_duration != 'Duration':
            selected_duration = int(selected_duration)

        if selected_start_date:
            start_date_split = selected_start_date.split('/')
            start_date_url = start_date_split[0] + '%' + start_date_split[1] + '%' + start_date_split[2]
        else:
            start_date_url = 'start_date_url'

        if selected_end_date:
            end_date_split = selected_end_date.split('/')
            end_date_url = end_date_split[0] + '%' + end_date_split[1] + '%' + end_date_split[2]
        else:
            end_date_url = 'end_date_url'

        if not selected_min_price:
            selected_min_price = 'min_price_url'

        if not selected_max_price:
            selected_max_price = 'max_price_url'

        return redirect(url_for("destinations", destination_url=selected_destination, region_url=selected_region, start_date_url=start_date_url, end_date_url=end_date_url,
                                min_price_url=selected_min_price, max_price_url=selected_max_price, duration_url=selected_duration, children_url=selected_children, city_url=selected_city))

    else:
        startdate_select = ''
        enddate_select = ''
        startdate_display = ''
        enddate_display = ''

        if start_date_url!='start_date_url':
            start_date_split = start_date_url.split('%')
            selected_start_date = date(int(start_date_split[2]), int(start_date_split[0]), int(start_date_split[1]))
            startdate_select = datetime.strftime(selected_start_date, '%Y-%m-%d')
            startdate_display = datetime.strftime(selected_start_date, '%m/%d/%Y')

        if end_date_url!='end_date_url':
            end_date_split = end_date_url.split('%')
            selected_end_date = date(int(end_date_split[2]), int(end_date_split[0]), int(end_date_split[1]))
            enddate_select = datetime.strftime(selected_end_date, '%Y-%m-%d')
            enddate_display = datetime.strftime(selected_end_date, '%m/%d/%Y')

        query = f'''SELECT id,Destination,Region,Start_Date,End_Date,Duration,City_Of_Departure,Price,Children FROM Tours WHERE Destination {"='" + destination_url + "'" if destination_url != 'All Destinations' else 'IS NOT NULL'} 
         {"AND Region = '" + region_url + "'" if region_url != 'All Regions' else ''}
         {"AND Start_Date >= '" + startdate_select +"'" if start_date_url!="start_date_url" and  end_date_url == "end_date_url" else ''}
         {"AND End_Date <= '" + enddate_select  +"'" if start_date_url =="start_date_url" and end_date_url !="end_date_url" else ''}
         {"AND (Start_Date BETWEEN '" + startdate_select + "' AND '" + enddate_select + "')"if start_date_url!='start_date_url' and end_date_url!='end_date_url' else ''}
         {"AND (End_Date BETWEEN '" + startdate_select + "' AND '" + enddate_select + "')" if start_date_url!='start_date_url' and end_date_url!='end_date_url' else ''}
         {"AND Price >= '" + str(min_price_url) +"'" if min_price_url!="min_price_url" and  max_price_url == "max_price_url" else ''}
         {"AND Price <= '" + str(max_price_url) +"'" if min_price_url =="min_price_url" and max_price_url !="max_price_url" else ''}
         {"AND (Price BETWEEN " + str(min_price_url) + " AND " + str(max_price_url) + ")" if min_price_url!="min_price_url" and  max_price_url != "max_price_url"  else ''}
         {"AND Duration = " + duration_url if duration_url != 'Duration' else ''}
         {"AND City_Of_Departure = '"+city_url+"'" if city_url != 'All Cities' else ''}
         {"AND Children = '"+children_url+"'" if children_url != 'Children' else ''};'''

        tours = db.session.query(Tours). \
            from_statement(text(query)). \
            all()

        minprice = int(min_price_url) if min_price_url != 'min_price_url' else ''
        maxprice = int(max_price_url) if max_price_url != 'max_price_url' else ''

        keys = list(region_destinations().keys())
        default_classes = [keys[0]]
        default_classes.extend(sorted(keys[1:]))
        default_values = region_destinations()[region_url]

        return render_template('destinations.html', title='Destinations', tours=tours, alldestinations=default_values,
                               alldurations=select_dropdown()[1], allregions=default_classes, allcities=select_dropdown()[3], region_url=region_url,destination_url=destination_url, city_url=city_url,
                               startdate_display=startdate_display, enddate_display=enddate_display, minprice=minprice, maxprice=maxprice, duration_url=duration_url, children_url=children_url)

@app.route("/contact", methods=["POST", "GET"])
def contact():
    if request.method == "POST":
        selected_destination = request.form["destination"]
        selected_start_date = request.form["start_date"]
        selected_end_date = request.form["end_date"]
        selected_duration = request.form["duration"]

        if selected_start_date:
            start_date_split = selected_start_date.split('/')
            start_date_url = start_date_split[0] + '%' + start_date_split[1] + '%' + start_date_split[2]
        else:
            start_date_url = 'start_date_url'

        if selected_end_date:
            end_date_split = selected_end_date.split('/')
            end_date_url = end_date_split[0] + '%' + end_date_split[1] + '%' + end_date_split[2]
        else:
            end_date_url = 'end_date_url'

        return redirect(url_for("destinations", destination_url=selected_destination, region_url="All Regions",
                                start_date_url=start_date_url, end_date_url=end_date_url,
                                min_price_url="min_price_url", max_price_url="max_price_url",
                                duration_url=selected_duration, city_url="All Cities", children_url="Children"))
    else:
        return render_template('contact.html', alldestinations=select_dropdown()[0], alldurations=select_dropdown()[1])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Users.query.filter_by(Email=email).first()

        if user:
            if check_password_hash(user.Password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('index'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password1 = request.form['password1']
        password2 = request.form['password2']

        user = Users.query.filter_by(Email=email).first()

        if user:
            flash('Email already exists.', category='error')
        elif not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
            flash('Email is not valid.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            new_user = Users(Name=name, Email=email, Password=generate_password_hash(password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('index'))

    return render_template("sign_up.html", user=current_user)

@app.route("/account")
@login_required
def account():
    return render_template('account.html', title='Account')

@app.route("/add_trip", methods=['GET', 'POST'])
@login_required
def add_trip():
    if current_user.Email.split('@')[1]=='adventureclub.com':
        if request.method == 'POST':
            region = request.form['region']
            Destination = request.form['Destination']
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            children = request.form['children']
            price = request.form['price']
            City = request.form['City']

            start = datetime.strptime(start_date, '%m/%d/%Y').date()
            end = datetime.strptime(end_date, '%m/%d/%Y').date()
            duration = (end-start).days

            img_file = 'destination-' + Destination + '.jpg' if os.path.exists(url_for('static', filename='img/destination-' + Destination + '.jpg')) else 'destination-default.jpg'

            with db.engine.connect() as connection:
                 connection.execute("INSERT INTO tours VALUES(?,?,?,?,?,?,?,?,?,?)",(None,Destination,region,start,end, duration, City, price, children,img_file))

            flash('Trip added!', category='success')
            return redirect(url_for('destinations'))

        else:
            return render_template('add_trip.html', title='Add Trip', allregions=select_dropdown()[2])
    else:
        abort(403)

@app.route("/update_trip/<int:id>", methods=['GET', 'POST'])
@login_required
def update_trip(id):
    if current_user.Email.split('@')[1]=='adventureclub.com':
        if request.method == 'POST':
            region = request.form['region']
            destination = request.form['Destination']
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            children = request.form['children']
            price = request.form['price']
            city = request.form['City']

            start = datetime.strptime(start_date, '%m/%d/%Y').date()
            end = datetime.strptime(end_date, '%m/%d/%Y').date()
            duration = (end-start).days

            tour = Tours.query.filter_by(id=id).first()
            tour.Region = region
            tour.Destination = destination
            tour.Start_Date = start
            tour.End_Date = end
            tour.Children = children
            tour.Duration = duration
            tour.Price = price
            tour.City_Of_Departure = city

            db.session.commit()
            flash('Trip updated!', category='success')
            return redirect(url_for('destinations'))
        else:
            tour = Tours.query.filter_by(id=id).first()
            startdate_display = datetime.strftime(tour.Start_Date, '%m/%d/%Y')
            enddate_display = datetime.strftime(tour.End_Date, '%m/%d/%Y')
            return render_template('update_trip.html', title='Update Trip', trip=tour, allregions=select_dropdown()[2], startdate_display=startdate_display, enddate_display=enddate_display)
    else:
        abort(403)

@app.route("/delete_trip/<int:id>", methods=['GET', 'POST'])
@login_required
def delete_trip(id):
    if current_user.Email.split('@')[1]=='adventureclub.com':
        with db.engine.connect() as connection:
            connection.execute(f"DELETE FROM tours WHERE id={id};")
        flash('Trip deleted!', category='success')
        return redirect(url_for('destinations'))
    else:
        abort(403)

@app.route("/enroll/<int:id>", methods=['GET', 'POST'])
@login_required
def enroll(id):
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        date_of_birth = request.form['date_of_birth']
        passport_number = request.form['passport_number']
        passport_expiration_date = request.form['passport_expiration_date']
        phone_number = request.form['phone_number']
        ssn = request.form['ssn']

        date_of_birth = datetime.strptime(date_of_birth, '%m/%d/%Y').date()
        passport_expiration_date = datetime.strptime(passport_expiration_date, '%m/%d/%Y').date()

        tour = Tours.query.filter_by(id=id).first()
        age = tour.Start_Date.year - date_of_birth.year - ((tour.Start_Date.month, tour.Start_Date.day) < (date_of_birth.month, date_of_birth.day))

        if date_of_birth > datetime.today().date():
            flash('Date of birth can\'t be after today\'s date.', category='error')
        elif age < 18 and tour.Children == "No":
            flash('Children are not allowed to participate in this trip.', category='error')
        elif not re.match(re.compile("^[A-Z]\\d{8}$"), passport_number):
            flash('Invalid passport format.', category='error')
        elif passport_expiration_date < tour.End_Date:
            flash('Passport expires before tour ends.', category='error')
        elif not re.match(re.compile("^\\d{10}$"), phone_number):
            flash('Invalid phone number.', category='error')
        elif not re.match(re.compile("^(?!666|000|9\\d{2})\\d{3}(?!00)\\d{2}(?!0{4})\\d{4}$"), ssn):
            flash('Invalid SSN.', category='error')

        else:
            customer = Customers.query.filter_by(Passport_Number=passport_number).first()

            if customer:
                if customer.user_id != current_user.id:
                    flash('Customer is already assigned to another account.', category='error')
                if customer.Name != name:
                    flash('Incorrect name. Provide a correct name or update the customer data in your account page.', category='error')
                if customer.Surname != surname:
                    flash('Incorrect surname. Provide a correct surname or update the customer data in your account page.', category='error')
                if customer.Date_Of_Birth != date_of_birth:
                    flash('Incorrect date of birth. Provide a correct date of birth or update the customer data in your account page.', category='error')
                if customer.Passport_Number != passport_number:
                    flash('Incorrect passport number. Provide a correct passport number or update the customer data in your account page.', category='error')
                if customer.Passport_Expiration_Date != passport_expiration_date:
                    flash('Incorrect passport expiration date. Provide a correct passport expiration date or update the customer data in your account page.', category='error')
                if customer.Phone_Number != phone_number:
                    flash('Incorrect phone number. Provide a correct phone number or update the customer data in your account page.', category='error')

            else:
                new_customer = Customers(Name=name, Surname=surname, Date_Of_Birth=date_of_birth, Passport_Number=passport_number, Passport_Expiration_Date=passport_expiration_date, Phone_Number=phone_number, SSN=ssn, user_id=current_user.id)
                db.session.add(new_customer)
                db.session.commit()
                customer = Customers.query.filter_by(Passport_Number=passport_number).first()

            customer.travelling.append(tour)
            db.session.commit()
            flash('Booking successful!', category='success')
            return redirect(url_for('account'))
        return render_template('enroll.html', tour=tour, title='Buy a Trip')
    else:
        with db.engine.connect() as connection:
            tour = connection.execute(f"SELECT * FROM tours WHERE id={id}").fetchone()

        return render_template('enroll.html', tour = tour, title='Buy a Trip')

@app.route("/resign/<int:tour_id>/<int:customer_id>")
@login_required
def resign(tour_id, customer_id):
    customer = Customers.query.filter_by(id=customer_id).first()
    if customer.user_id == current_user.id or current_user.Email.split('@')[1] == 'adventureclub.com':
        tour = Tours.query.filter_by(id=tour_id).first()
        customer.travelling.remove(tour)
        db.session.commit()
        if customer.user_id == current_user.id:
            flash('Resignation successful.', category='success')
            return redirect(url_for('account'))
        else:
            flash('Participant deleted.', category='success')
            return redirect(url_for('destinations'))
    else:
        abort(403)

@app.route("/update_customer/<int:customer_id>", methods=['GET', 'POST'])
@login_required
def update_customer(customer_id):
    customer = Customers.query.filter_by(id=customer_id).first()
    if customer.user_id == current_user.id or current_user.Email.split('@')[1] == 'adventureclub.com':
        if request.method == 'POST':
            name = request.form['name']
            surname = request.form['surname']
            date_of_birth = request.form['date_of_birth']
            passport_number = request.form['passport_number']
            passport_expiration_date = request.form['passport_expiration_date']
            phone_number = request.form['phone_number']
            ssn = request.form['ssn']
            date_of_birth = datetime.strptime(date_of_birth, '%m/%d/%Y').date()
            passport_expiration_date = datetime.strptime(passport_expiration_date, '%m/%d/%Y').date()

            if date_of_birth > datetime.today().date():
                flash('Date of birth can\'t be after today\'s date.', category='error')
            elif not re.match(re.compile("^[A-Z]\\d{8}$"), passport_number):
                flash('Invalid passport format.', category='error')
            elif not re.match(re.compile("^\\d{10}$"), phone_number):
                flash('Invalid phone number.', category='error')
            elif not re.match(re.compile("^(?!666|000|9\\d{2})\\d{3}(?!00)\\d{2}(?!0{4})\\d{4}$"), ssn):
                flash('Invalid SSN.', category='error')
            else:
                customer = Customers.query.filter_by(id=customer_id).first()
                customer.Name = name
                customer.Surname = surname
                customer.Date_Of_Birth = date_of_birth
                customer.Passport_Number = passport_number
                customer.Passport_Expiration_Date = passport_expiration_date
                customer.Phone_Number = phone_number
                customer.SSN = ssn
                db.session.commit()
                flash('Customer data updated!', category='success')
                if customer.user_id == current_user.id:
                    return redirect(url_for('account'))
                else:
                    return redirect(url_for('destinations'))
            return redirect(url_for('update_customer', customer_id=customer_id))
        else:
            customer = Customers.query.filter_by(id=customer_id).first()
            dob_display = datetime.strftime(customer.Date_Of_Birth, '%m/%d/%Y')
            ped_display = datetime.strftime(customer.Passport_Expiration_Date, '%m/%d/%Y')

            return render_template('update_customer.html', title='Update Customer', customer=customer, dob_display=dob_display, ped_display=ped_display)
    else:
        abort(403)

@app.route("/participants/<int:tour_id>", methods=['GET', 'POST'])
@login_required
def participants(tour_id):
    if current_user.Email.split('@')[1]=='adventureclub.com':
        tour = Tours.query.filter_by(id=tour_id).first()
        return render_template('participants.html', tour=tour)
    else:
        abort(403)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def permission_denied(e):
    return render_template('403.html'), 403


