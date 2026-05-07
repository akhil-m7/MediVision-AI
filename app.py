from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import random
import tensorflow as tf
import numpy as np
from PIL import Image
import os

app= Flask(__name__)

oral_model = tf.keras.models.load_model(
    'models/oral_model.h5'
)
skin_model = tf.keras.models.load_model(
    'models/skin_model.h5'
)
skin_classes = [

    'Acne',

    'Actinic_Keratosis',

    'Benign_tumors',

    'Bullous',

    'Candidiasis',

    'DrugEruption',

    'Eczema',

    'Infestations_Bites',

    'Lichen',

    'Lupus',

    'Moles',

    'Psoriasis',

    'Rosacea',

    'Seborrh_Keratoses',

    'SkinCancer',

    'Sun_Sunlight_Damage',

    'Tinea',

    'Unknown_Normal',

    'Vascular_Tumors',

    'Vasculitis',

    'Vitiligo',

    'Warts'
]

oral_classes = [

    'Caries',

    'Gingivitis',

    'Mouth Ulcer',

    'Tooth Discoloration'
]

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['SECRET_KEY'] = 'medivisionsecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
mail=Mail(app)

login_manager = LoginManager()
otp_storage={}
login_manager.init_app(app)
login_manager.login_view = 'login'

# DATABASE MODEL
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    profile_image = db.Column(
    db.String(200),
    default='default.png'
)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    category = db.Column(db.String(50))
    disease = db.Column(db.String(100))
    confidence = db.Column(db.String(20))
    symptoms = db.Column(db.Text)
    precautions = db.Column(db.Text)
    image = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#IMAGE PREPROCESSING
def prepare_image(image_path):
    img = Image.open(image_path)
    img = img.resize((224,224))
    img = np.array(img)
    img = img / 255.0
    img = np.expand_dims(img, axis=0)
    return img

#SYMPTOM ANALYSIS
def symptom_analysis(symptoms):

    symptoms = symptoms.lower()

    if 'bleeding' in symptoms or 'swollen gums' in symptoms:

        return 'Gingivitis'

    elif 'ulcer' in symptoms or 'mouth pain' in symptoms:

        return 'Mouth Ulcer'

    elif 'tooth pain' in symptoms or 'cavity' in symptoms:

        return 'Caries'

    else:

        return None
    
#SKIN SYMPTOM ANALYSIS
def skin_symptom_analysis(symptoms):

    symptoms = symptoms.lower()

    disease_scores = {

        'Acne': 0,

        'Eczema': 0,

        'Psoriasis': 0,

        'Vitiligo': 0,

        'Warts': 0
    }

    # ACNE
    if 'pimples' in symptoms:
        disease_scores['Acne'] += 2

    if 'oily skin' in symptoms:
        disease_scores['Acne'] += 1

    # ECZEMA
    if 'itching' in symptoms:
        disease_scores['Eczema'] += 2

    if 'dry skin' in symptoms:
        disease_scores['Eczema'] += 1

    # PSORIASIS
    if 'red patches' in symptoms:
        disease_scores['Psoriasis'] += 2

    if 'scaling' in symptoms:
        disease_scores['Psoriasis'] += 1

    # VITILIGO
    if 'white patches' in symptoms:
        disease_scores['Vitiligo'] += 2

    # WARTS
    if 'small bumps' in symptoms:
        disease_scores['Warts'] += 2

    predicted_disease = max(
        disease_scores,
        key=disease_scores.get
    )

    if disease_scores[predicted_disease] == 0:

        return None

    return predicted_disease
    
# HOME PAGE
@app.route('/')
def home():
    return render_template('index.html')

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        otp = str(random.randint(100000, 999999))

        otp_storage[email] = {
            'username': username,
            'password': generate_password_hash(password),
            'otp': otp
        }

        msg = Message(
            'MediVision AI OTP Verification',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )

        msg.body = f'Your OTP is: {otp}'

        mail.send(msg)

        flash('OTP sent to your email')

        return redirect(url_for('verify_otp', email=email))

    return render_template('register.html')

#OTP_ROUTE
@app.route('/verify/<email>', methods=['GET', 'POST'])
def verify_otp(email):

    if request.method == 'POST':

        entered_otp = request.form.get('otp')

        stored_data = otp_storage.get(email)

        if stored_data and stored_data['otp'] == entered_otp:

            user = User(
                username=stored_data['username'],
                email=email,
                password=stored_data['password']
            )

            db.session.add(user)
            db.session.commit()

            otp_storage.pop(email)

            flash('Account created successfully')

            return redirect(url_for('login'))

        flash('Invalid OTP')

    return render_template('verify_otp.html', email=email)

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid email or password')

    return render_template('login.html')

# DASHBOARD
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

#ADD SKIN ROUTE
@app.route('/skin', methods=['GET', 'POST'])
@login_required
def skin():

    if request.method == 'POST':

        symptoms = request.form.get('symptoms')

        image = request.files['image']

        filename = image.filename

        image_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            filename
        )

        image.save(image_path)

        # PREPARE IMAGE
        processed_image = prepare_image(image_path)

        # AI PREDICTION
        prediction = skin_model.predict(processed_image)

        predicted_index = np.argmax(prediction)

        confidence = np.max(prediction) * 100

        disease = skin_classes[predicted_index]

        # SYMPTOM ANALYSIS
        symptom_result = skin_symptom_analysis(symptoms)

        if symptom_result:

            disease = symptom_result

        precautions = "Consult a dermatologist for proper treatment."

        # SAVE TO DATABASE
        new_prediction = Prediction(

            user_id=current_user.id,

            category='Skin',

            disease=disease,

            confidence=f"{confidence:.2f}%",

            symptoms=symptoms,

            precautions=precautions,

            image=filename
        )

        db.session.add(new_prediction)

        db.session.commit()

        return render_template(

            'result.html',

            disease=disease,

            confidence=f"{confidence:.2f}%",

            symptoms=symptoms,

            image=filename,

            precautions=precautions
        )

    return render_template('skin.html')

#ADD ORAL ROUTE
@app.route('/oral', methods=['GET', 'POST'])
@login_required
def oral():

    if request.method == 'POST':

        symptoms = request.form.get('symptoms')

        image = request.files['image']

        filename = image.filename

        image_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            filename
        )

        image.save(image_path)

        # PREPARE IMAGE
        processed_image = prepare_image(image_path)

        # AI PREDICTION
        prediction = oral_model.predict(processed_image)

        predicted_index = np.argmax(prediction)

        confidence = np.max(prediction) * 100

        disease = oral_classes[predicted_index]

        # SYMPTOM ANALYSIS
        symptom_result = symptom_analysis(symptoms)

        if symptom_result:

            disease = symptom_result

        precautions = "Consult a dentist for proper treatment."

        # SAVE TO DATABASE
        new_prediction = Prediction(

            user_id=current_user.id,

            category='Oral',

            disease=disease,

            confidence=f"{confidence:.2f}%",

            symptoms=symptoms,

            precautions=precautions,

            image=filename
        )

        db.session.add(new_prediction)

        db.session.commit()

        return render_template(

            'result.html',

            disease=disease,

            confidence=f"{confidence:.2f}%",

            symptoms=symptoms,

            image=filename,

            precautions=precautions
        )

    return render_template('oral.html')

#HISTORY ROUTE
@app.route('/history')
@login_required
def history():

    predictions = Prediction.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        'history.html',
        predictions=predictions
    )

#PROFILE ROUTE
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    if request.method == 'POST':

        username = request.form.get('username')

        email = request.form.get('email')

        password = request.form.get('password')

        profile_pic = request.files.get('profile_pic')

        current_user.username = username

        current_user.email = email

        # CHANGE PASSWORD
        if password:

            current_user.password = generate_password_hash(password)

        # CHANGE PROFILE IMAGE
        if profile_pic and profile_pic.filename != '':

            filename = profile_pic.filename

            path = os.path.join(
                'static/profile_pics',
                filename
            )

            profile_pic.save(path)

            current_user.profile_image = filename

        db.session.commit()

        flash('Profile updated successfully')

    return render_template(
        'profile.html',
        user=current_user
    )

# CREATE DATABASE
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)