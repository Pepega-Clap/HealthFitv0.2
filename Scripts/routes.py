import secrets, os, datetime, threading
from PIL import Image
from flask import render_template, flash, redirect, url_for, request
from Scripts.forms import RegisterForm, LoginForm, UpdateDetails, TodoList, RequestResetForm, ResetPasswordForm, HealthForm, FoodForm, ExerciseForm, SearchForm
from Scripts import app, db, bcrypt, mail
from Scripts.models import User, Schedule, Food, Fitness, Breakfast, Lunch, Dinner, HealthTrack
from random import randint
from Scripts.Fitness import Record, YourPlan, Exercise

from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
import shelve

exercises = Fitness.query.all()
bfastt = Breakfast.query.all()
lunchh = Lunch.query.all()
dinnerr = Dinner.query.all()

kcal = 0

for food in bfastt:
    kcal += food.calories
for food in lunchh:
    kcal += food.calories
for food in dinnerr:
    kcal += food.calories


totalKcalfromExercise = 0
queryExerciseKcal = Fitness.query.all()
for i in queryExerciseKcal:
    totalKcalfromExercise += i.calories
print(totalKcalfromExercise)



def deleteRecords():

    threading.Timer(300.0, deleteRecords).start()
    now = datetime.datetime.now().time()
    midnight = datetime.time(0, 0, 0)
    print(now, midnight)
    if now > midnight:
        resetBreakfast = Breakfast.query.all()
        for i in resetBreakfast:
            db.session.delete(i)
            db.session.commit()
        resetLunch = Lunch.query.all()
        for i in resetLunch:
            db.session.delete(i)
            db.session.commit()
        resetDinner = Dinner.query.all()
        for i in resetDinner:
            db.session.delete(i)
            db.session.commit()
        resetExercise = Fitness.query.all()
        for i in resetExercise:
            db.session.delete(i)
            db.session.commit()

deleteRecords()

@app.route("/")
@app.route("/home")
def home():

    if current_user.is_authenticated:
        image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    else:
        image_file = url_for('static', filename='profile_pics/default.png')
    return render_template("home.html", image_file=image_file)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(name=form.name.data, email=form.email.data.lower(), username=form.username.data.lower(),
                    password=hashed_password, age=form.age.data, weight=form.weight.data, height=form.height.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.lower()).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')

    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    flash('Logged Out successfully!', 'success')
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)

    i.save(picture_path)

    return picture_fn


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateDetails()

    exercises = Fitness.query.all()
    bfastt = Breakfast.query.all()
    lunchh = Lunch.query.all()
    dinnerr = Dinner.query.all()

    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.height = form.height.data
        current_user.weight = form.weight.data
        current_user.age = form.age.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.height.data = current_user.height
        form.weight.data = current_user.weight
        form.age.data = current_user.age

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('profile.html', title='Profile',image_file=image_file, form=form, bfastt=bfastt, lunchh=lunchh, dinnerr=dinnerr, exercise=exercises)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='app.noreply1206@gmail.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password', 'success')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route('/ExGuide')
@login_required
def guide():
    int_list = []
    exercise = ""
    exercise1 = ""
    exercise2 = ""

    # Open shelve to retrieve exercise objects (Data) for use

    storing = shelve.open('store_ex')

    while exercise == "":
        cycle = randint(0, 5)
        # Makes sure that the same exercise will not appear twice
        if cycle not in int_list:
            exercise = storing['exer' + str(cycle)]
            int_list.append(cycle)

    while exercise1 == "":
        cycle = randint(0, 5)
        if cycle not in int_list:
            exercise1 = storing['exer' + str(cycle)]
            int_list.append(cycle)

    while exercise2 == "":
        cycle = randint(0, 5)
        if cycle not in int_list:
            exercise2 = storing['exer' + str(cycle)]
            int_list.append(cycle)
    storing.close()

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)

    # Returns variable to be used in HTML
    return render_template('ExGuide.html', exercise=exercise, exercise1=exercise1, exercise2=exercise2,
                           image_file=image_file)

@app.route('/schedule')
@login_required
def schedule():
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('schedule.html', image_file=image_file)


@app.route('/schedule/ToDoList', methods=['GET', 'POST'])
@login_required
def todolist():
    form = TodoList()
    Todos = Schedule.query.all()
    if form.validate_on_submit():
        activity = Schedule(description=form.description.data, remarks=form.remarks.data, name=current_user)
        db.session.add(activity)
        db.session.commit()
        app.logger.debug('Activities added')
        flash('Activity have been added to your schedule', 'success')
        return redirect(url_for('todolist'))
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('todolist.html', title='ToDoList', image_file=image_file, form=form, Todos=Todos)

@app.route('/schedule/ToDoList/<int:todo_id>')
@login_required
def todo(todo_id):
    todo = Schedule.query.get_or_404(todo_id)
    return render_template('todo.html', title=todo.description, todo=todo)

# @app.route('/schedule/ToDoList/<int:todo_id>/edit', methods=['GET', 'POST'])
# @login_required
# def edit_todo(todo_id):
#     activity = Schedule.query.get_or_404(todo_id)
#     form = TodoList()
#     if form.validate_on_submit():
#         activity.description = form.description.data
#         activity.remarks = form.remarks.data
#         db.session.commit()
#         flash('Your to-do has been updated!', 'success')
#         return redirect(url_for('todo', todo_id=todo.id))
#     elif request.method == 'GET':
#         form.description.data = form.description
#         form.remarks.data = form.remarks
#     return render_template('todolist.html', title='HealthFit - Edit to-do-list', form=form, legend='Edit To-Do-List')

@app.route('/schedule/ToDoList/<int:todo_id>/delete', methods=['POST'])
@login_required
def delete_todo(todo_id):
    todo = Schedule.query.get_or_404(todo_id)
    db.session.delete(todo)
    db.session.commit()
    flash('Your to-do has been deleted!', 'danger')
    return redirect(url_for('todolist'))

@app.route('/HealthTracker', methods=['GET', 'POST'])
@login_required
def HealthTracker():
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('HealthTracker.html', image_file=image_file)


@app.route('/HealthTracker/submit', methods=['POST'])
@login_required
def submit_heartrate():
    flash("Your heart rate has been successfully updated!", "success")
    return redirect(url_for('HealthTracker'))

@app.route('/food', methods=['GET', 'POST'])
@login_required
def _Food():
    global kcal
    global totalKcalfromExercise
    form = SearchForm()
    try:
        if form.meal.data == 'breakfast':
            searches = Food.query.filter_by(name=form.name.data).first()
            app.logger.debug(form.meal.data)
            breakfast = Breakfast(name=current_user, foodname=searches.name, mass=searches.mass,
                                  calories=searches.calories,
                                  protein=searches.protein, carbohydrates=searches.carbohydrates, fats=searches.fats)
            db.session.add(breakfast)
            flash('Commit!', 'success')
        elif form.meal.data == 'lunch':
            searches = Food.query.filter_by(name=form.name.data).first()
            lunch = Lunch(name=current_user, foodname=searches.name, mass=searches.mass, calories=searches.calories,
                          protein=searches.protein, carbohydrates=searches.carbohydrates, fats=searches.fats)
            db.session.add(lunch)
            flash('Commit!', 'success')
        elif form.meal.data == 'dinner':
            searches = Food.query.filter_by(name=form.name.data).first()
            dinner = Dinner(name=current_user, foodname=searches.name, mass=searches.mass, calories=searches.calories,
                            protein=searches.protein, carbohydrates=searches.carbohydrates, fats=searches.fats)
            db.session.add(dinner)
            flash('Commit!', 'success')
        else:
            searches = ""
        db.session.commit()
    except AttributeError:
        flash('The Food is not available in the database!','warning')


    # daily intake
    if kcal > 0:
        mtcalories = ((447.593 + (9.247 * current_user.weight) + (3.098 * current_user.height * 100) - (
                    4.33 * current_user.age)) * 1.55) - kcal + totalKcalfromExercise
    else:
        mtcalories = ((447.593 + (9.247 * current_user.weight) + (3.098 * current_user.height * 100) - (
                    4.33 * current_user.age)) * 1.55) + totalKcalfromExercise
    simplifiedmt = round(mtcalories)

    # macronutrients left
    protein25 = round(simplifiedmt * 0.25)
    fat25 = round(simplifiedmt * 0.25)
    carb50 = round(simplifiedmt * 0.5)
    cprotein25 = round(protein25 / 4)
    cfat25 = round(fat25 / 9)
    ccarb50 = round(carb50 / 4)

    r1 = Record('food1')
    p1 = YourPlan(simplifiedmt, ccarb50, cprotein25, cfat25)
    e1 = Exercise(totalKcalfromExercise)

    now = datetime.datetime.now()
    midnight = datetime.time(0, 0, 0)
    if now == midnight:
        resetBreakfast = Breakfast.query.all()
        for i in resetBreakfast:
            db.session.delete(i)
            db.session.commit()
        resetLunch = Lunch.query.all()
        for i in resetLunch:
            db.session.delete(i)
            db.session.commit()
        resetDinner = Dinner.query.all()
        for i in resetDinner:
            db.session.delete(i)
            db.session.commit()

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('food.html', items=r1, kcal=p1, exer=e1, image_file=image_file, form=form, searches=searches)


@app.route('/exercise', methods=['GET', 'POST'])
@login_required
def exercise():
    form = ExerciseForm()
    global kcal
    global totalKcalfromExercise
    if form.intensity.data == 'light':
        if form.duration.data == 'ten':
            time = 10
            intensity = 1
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
            flash('Exercise successfully Added!','success')
        elif form.duration.data == 'twenty':
            time = 20
            intensity = 1
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'thirty':
            time = 30
            intensity = 1
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'forty':
            time = 40
            intensity = 1
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'fifty':
            time = 50
            intensity = 1
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'sixty':
            time = 60
            intensity = 1
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
    else:
        totalexercises = 0
    if form.intensity.data == 'moderate':
        if form.duration.data == 'ten':
            time = 10
            intensity = 2
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'twenty':
            time = 20
            intensity = 2
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'thirty':
            time = 30
            intensity = 2
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'forty':
            time = 40
            intensity = 2
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'fifty':
            time = 50
            intensity = 2
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'sixty':
            time = 60
            intensity = 2
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
    else:
        totalexercises = 0
    if form.intensity.data == 'vigorious':
        if form.duration.data == 'ten':
            time = 10
            intensity = 3
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'twenty':
            time = 20
            intensity = 3
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'thirty':
            time = 30
            intensity = 3
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data,
            calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'forty':
            time = 40
            intensity = 3
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'fifty':
            time = 50
            intensity = 3
            totalexercises = round(time * (intensity * 3.33))
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
        elif form.duration.data == 'sixty':
            time = 60
            intensity = 3
            totalexercises = round(time * (intensity * 3.33))
            print(totalexercises)
            exer = Fitness(name=current_user, exercisename=form.name.data, intensity=form.name.data, duration=form.duration.data, calories=totalexercises)
            db.session.add(exer)
            db.session.commit()
    else:
        totalexercises = 0
    #app.logger.debug(totalKcalfromExercise)

    # daily intake
    if kcal > 0:
        mtcalories = ((447.593 + (9.247 * current_user.weight) + (3.098 * current_user.height * 100) - (
                    4.33 * current_user.age)) * 1.55) - kcal + totalKcalfromExercise
    else:
        mtcalories = ((447.593 + (9.247 * current_user.weight) + (3.098 * current_user.height * 100) - (
                    4.33 * current_user.age)) * 1.55) + totalKcalfromExercise
    simplifiedmt = round(mtcalories)

    # macronutrients left
    protein25 = round(simplifiedmt * 0.25)
    fat25 = round(simplifiedmt * 0.25)
    carb50 = round(simplifiedmt * 0.5)
    cprotein25 = round(protein25 / 4)
    cfat25 = round(fat25 / 9)
    ccarb50 = round(carb50 / 4)

    r1 = Record('food1')
    p1 = YourPlan(simplifiedmt, ccarb50, cprotein25, cfat25)
    e1 = Exercise(totalKcalfromExercise)

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('exercise.html', items=r1, kcal=p1, exer=e1, image_file=image_file, form=form, totalKcalfromExercise=totalKcalfromExercise)

@app.route('/addfood', methods=['GET', 'POST'])
def addFood():
    form = FoodForm()
    if form.validate_on_submit():
        print('asd')
        food = Food(name=form.name.data, mass=form.mass.data, calories=form.calories.data, protein=form.protein.data,
                    carbohydrates=form.carbohydrates.data, fats=form.fats.data)
        db.session.add(food)
        db.session.commit()
        flash('Your entry has been entered!', 'success')

    return render_template('addFood.html', form=form)
