from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
import os
from werkzeug.utils import secure_filename
from nlp_backend import process_grievances, send_email_response
from credentials import ADMIN_USERNAME, ADMIN_PASSWORD
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))

    grievances = []
    filename = None

    if request.method == 'POST':
        file = request.files['file']
        if file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            df = pd.read_csv(filepath)
            processed_df, _ = process_grievances(df)
            processed_df.sort_values(by='priority_score', ascending=False, inplace=True)

            output_file = os.path.join(PROCESSED_FOLDER, f'processed_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv')
            processed_df.to_csv(output_file, index=False)

            grievances = processed_df.to_dict(orient='records')
            session['grievances'] = grievances
            session['csv_file'] = output_file

    elif 'grievances' in session:
        grievances = session['grievances']

    return render_template('dashboard.html', grievances=grievances)

@app.route('/send_email/<int:index>')
def send_email(index):
    if 'grievances' in session:
        try:
            row = session['grievances'][index]
            send_email_response(row)
        except Exception as e:
            print(f"Email error: {e}")
    return redirect(url_for('dashboard'))

@app.route('/export')
def export():
    if 'csv_file' in session:
        return send_file(session['csv_file'], as_attachment=True)
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
