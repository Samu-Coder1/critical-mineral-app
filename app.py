import os  # lets you work with files and folders on your computer
import pandas as pd  # helps you read, change and save data, like from CSV files
from flask import Flask, render_template, request, redirect, session, flash  # tools for building a web app with pages, forms and messages
import folium  # used to make maps that you can interact with
from folium.plugins import MarkerCluster  # groups map points together when they are close
from branca.element import Template, MacroElement  # helps you add extra designs or notes on a map
import plotly.express as px  # used to make nice and interactive graphs easily
import plotly.io as pio  # helps to show or save your Plotly graphs
from functools import wraps  # helps when you create decorators (functions that check or control other functions)
from datetime import datetime  # used to work with dates and times
from lib.data_store import CSVStore, save_csv, load_csv  # your own file that saves and loads CSV data
from lib.entities import ENTITIES  # your own file that keeps info or settings about your data
from lib.app_utils import backup_file, ensure_csv_header  # your own tools that make backups and check if CSV files have correct headings
from lib.map_helpers import build_map_html  # your own function that helps create the map in HTML for the website

# Ensure Flask uses the project's `templates/` directory (not data/templates)
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))  # create the Flask app and show where the HTML templates are
app.secret_key = 'african_critical_minerals_2025'  # secret key for security, used to protect sessions and messages 

# Load data from CSVs
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')  # set the path to the 'data' folder where all CSV files are kept
users_df = pd.read_csv(os.path.join(DATA_DIR, 'users.csv'))  # read the users.csv file and store it in a pandas DataFrame
roles_df = pd.read_csv(os.path.join(DATA_DIR, 'roles.csv'))  # read the roles.csv file (contains user roles or permissions)
countries_df = pd.read_csv(os.path.join(DATA_DIR, 'countries.csv'))  # read the countries.csv file (list of countries and info)
minerals_df = pd.read_csv(os.path.join(DATA_DIR, 'minerals.csv'))  # read the minerals.csv file (information about minerals)
sites_df = pd.read_csv(os.path.join(DATA_DIR, 'sites.csv'))  # read the sites.csv file (mining site details)
production_df = pd.read_csv(os.path.join(DATA_DIR, 'production_stats.csv'))  # read the production_stats.csv file (production data)

users_store = CSVStore(os.path.join(DATA_DIR, 'users.csv'), id_field='UserID')  # create a store for user data, using 'UserID' as the unique ID
countries_store = CSVStore(os.path.join(DATA_DIR, 'countries.csv'), id_field='CountryID')  # store for country data, each row identified by 'CountryID'
minerals_store = CSVStore(os.path.join(DATA_DIR, 'minerals.csv'), id_field='MineralID')  # store for mineral data, each mineral identified by 'MineralID'
sites_store = CSVStore(os.path.join(DATA_DIR, 'sites.csv'), id_field='SiteID')  # store for site data, each mining site identified by 'SiteID'
production_store = CSVStore(os.path.join(DATA_DIR, 'production_stats.csv'), id_field='StatID')  # store for production data, each record identified by 'StatID'

# Load uploaded dataset (converted from Excel)
uploaded_csv = os.path.join(DATA_DIR, 'uploaded_dataset.csv')  # set the path to the uploaded dataset CSV file

if os.path.exists(uploaded_csv):  # check if the uploaded file exists
    try:
        uploaded_df = pd.read_csv(uploaded_csv)  # try to read the CSV into a pandas DataFrame
    except Exception:  # if reading fails for any reason
        uploaded_df = pd.DataFrame()  # create an empty DataFrame instead
else:
    uploaded_df = pd.DataFrame()  # if the file does not exist, create an empty DataFrame



# Dataset shares file (admin can share dataset with roles or specific users)
SHARES_CSV = os.path.join(DATA_DIR, 'dataset_shares.csv')  # path to the CSV file that stores which datasets are shared

if not os.path.exists(SHARES_CSV):  # if the shares file does not exist yet
    with open(SHARES_CSV, 'w', encoding='utf-8') as f:  # create the file
        f.write('SharedType,SharedValue,SharedBy,Timestamp\n')  # write the CSV header

def add_dataset_share(shared_type, shared_value, shared_by):  # function to add a new share
    ts = datetime.utcnow().isoformat()  # get current UTC time in ISO format
    line = f'"{shared_type}","{shared_value}","{shared_by}","{ts}"\n'  # create a line to write in CSV
    with open(SHARES_CSV, 'a', encoding='utf-8') as f:  # open the CSV in append mode
  
        f.write(line)  # add the new share
def is_dataset_shared_for_user(username, role):  # function to check if a dataset is shared with a user
    # Administrators always have access
    if role == 'Administrator':
        return True
    if not os.path.exists(SHARES_CSV):  # if shares file does not exist, return False
        return False
    try:
        with open(SHARES_CSV, 'r', encoding='utf-8') as f:  # open the shares file
            lines = f.readlines()[1:]  # skip the header
        for ln in lines:  # check each line
            parts = [p.strip('"') for p in ln.strip().split('","')]  # split the line into columns
            if len(parts) >= 4:  # make sure there are enough columns
                stype, svalue = parts[0], parts[1]  # get share type and value
                if stype == 'role' and svalue == role:  # if shared to the role
                    return True
                if stype == 'user' and svalue == username:  # if shared to the specific user
                    return True
    except Exception:  # if anything goes wrong, return False
        return False
    return False  # default: not shared

# Merge data for analysis
sites_full = sites_df.merge(countries_df, on='CountryID').merge(minerals_df, on='MineralID')  # combine sites, countries, and minerals into one DataFrame for easy analysis
prod_full = production_df.merge(countries_df, on='CountryID').merge(minerals_df, on='MineralID')  # combine production data, countries, and minerals into one DataFrame for easy analysis


def reload_all_data():
    """Reload CSV-backed DataFrames into memory and recompute merged views.
    Call this after admin changes so the running app immediately reflects updates.
    """
    global users_df, roles_df, countries_df, minerals_df, sites_df, production_df, sites_full, prod_full
    users_df = pd.read_csv(os.path.join(DATA_DIR, 'users.csv'))
    roles_df = pd.read_csv(os.path.join(DATA_DIR, 'roles.csv'))
    countries_df = pd.read_csv(os.path.join(DATA_DIR, 'countries.csv'))
    minerals_df = pd.read_csv(os.path.join(DATA_DIR, 'minerals.csv'))
    sites_df = pd.read_csv(os.path.join(DATA_DIR, 'sites.csv'))
    production_df = pd.read_csv(os.path.join(DATA_DIR, 'production_stats.csv'))
    try:
        sites_full = sites_df.merge(countries_df, on='CountryID').merge(minerals_df, on='MineralID')
    except Exception:
        sites_full = sites_df.copy()
    try:
        prod_full = production_df.merge(countries_df, on='CountryID').merge(minerals_df, on='MineralID')
    except Exception:
        prod_full = production_df.copy()

# Audit log setup
AUDIT_LOG = os.path.join(DATA_DIR, 'audit_log.csv')  # path to the CSV file where all audit events are stored
if not os.path.exists(AUDIT_LOG):  # check if audit log file exists
    # create the file with a header if it doesn't exist
    with open(AUDIT_LOG, 'w', encoding='utf-8') as f:
        f.write('Timestamp,Username,Action,Path,Details\n')  # CSV header for logging events

def log_event(username, action, path='', details=''):  # function to log an event
    ts = datetime.utcnow().isoformat()  # get current UTC timestamp in ISO format
    line = f'"{ts}","{username}","{action}","{path}","{details}"\n'  # create a line for the CSV
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:  # open audit log in append mode
        f.write(line)  # write the event to the file

def save_users_df():  # function to save the current users DataFrame to CSV
    save_csv(users_df, os.path.join(DATA_DIR, 'users.csv'))  # save users_df to the users.csv file


# Template filter for formatting large numbers
@app.template_filter('human_num')  # register a custom filter in Flask called 'human_num' for use in HTML templates
def human_num(value, decimals=0):  # function to format numbers nicely with commas
    try:
        if decimals == 0:  # if no decimal places needed
            return f"{float(value):,.0f}"  # format number with commas, no decimals
        return f"{float(value):,.{decimals}f}"  # format number with specified decimal places
    except Exception:  # if something goes wrong (like value is not a number)
        return value  # return the original value without formatting


# Role decorators (defined early so routes can use them)
def admin_required(f):  # decorator to make sure only administrators can access a route
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):  # check if user is logged in
            return redirect('/login')  # if not logged in, send to login page
        if session.get('role') != 'Administrator':  # check if user role is Administrator
            flash('Administrator access required.', 'danger')  # show warning message
            return redirect('/dashboard')  # redirect non-admins to dashboard
        return f(*args, **kwargs)  # if all checks pass, run the original function
    return decorated  # return the decorated function


def investor_required(f):  # decorator to make sure only investors (or admins) can access a route
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):  # check if user is logged in
            return redirect('/login')  # redirect to login if not
        if session.get('role') != 'Investor' and session.get('role') != 'Administrator':  # check role
            flash('Investor access required.', 'danger')  # show warning if not investor/admin
            return redirect('/dashboard')  # redirect to dashboard
        return f(*args, **kwargs)  # if all checks pass, run the original function
    return decorated  # return the decorated function

# Routes 
@app.route('/')  # main route (home page)
def index():
    return redirect('/login')  # redirect anyone visiting '/' to the login page

@app.route('/login', methods=['GET', 'POST'])  # login page route, supports form submission
def login():
    if request.method == 'POST':  # check if the form was submitted
        username = request.form['username']  # get username from the form
        password = request.form['password']  # get password from the form
        user = users_df[users_df['Username'] == username]  # look up the username in the users DataFrame
        if not user.empty:  # if user exists
            stored_password = user.iloc[0]['PasswordHash']  # get stored password (plaintext in your CSV)
            if password == stored_password:  # check if password matches
                session['logged_in'] = True  # mark user as logged in
                session['username'] = username  # store username in session
                role_id = int(user.iloc[0]['RoleID'])  # get user's role ID
                role_name = roles_df[roles_df['RoleID'] == role_id].iloc[0]['RoleName']  # look up role name
                session['role'] = role_name  # store role in session
                # log successful login
                log_event(username, 'login_success', path='/login', details='Successful login')
                return redirect('/dashboard')  # redirect to dashboard after login
            else:
                # log failed login attempt (wrong password)
                log_event(username, 'login_failed', path='/login', details='Invalid password')
                flash('Invalid password.', 'danger')  # show error message on page
        else:
            # log failed login (username not found)
            log_event(username, 'login_failed', path='/login', details='Unknown username')
            flash('Invalid username.', 'danger')  # show error message on page
    return render_template('login.html')  # show login page if GET request or login failed

@app.route('/logout')  # logout page route
def logout():
    user = session.get('username', 'anonymous')  # get current username or 'anonymous' if not logged in
    log_event(user, 'logout', path='/logout', details='User logged out')  # log the logout event
    session.clear()  # clear all session data (log user out)
    return redirect('/login')  # send user back to login page


@app.route('/dashboard')  # route for the main dashboard page
def dashboard():
    if not session.get('logged_in'):  # check if user is logged in
        return redirect('/login')  # if not logged in, send to login page
    # If investor, redirect to investor dashboard (investors shouldn't see mineral DB here)
    if session.get('role') == 'Investor':  # check if user role is Investor
        return redirect('/investor')  # send investors to a different dashboard
    # log page view
    log_event(session.get('username','anonymous'), 'page_view', path='/dashboard', details='Visited dashboard')  # record that user visited dashboard
    total_countries = len(countries_df)  # count total countries
    total_minerals = len(minerals_df)  # count total minerals
    total_sites = len(sites_df)  # count total mining sites
    latest_year = production_df['Year'].max()  # find the latest year in production data
    total_prod = production_df[production_df['Year'] == latest_year]['Production_tonnes'].sum()  # sum production for latest year
    return render_template(
        'dashboard.html',  # render the dashboard HTML template
        role=session['role'],  # pass user role to template
        total_countries=total_countries,  # pass total countries count
        total_minerals=total_minerals,  # pass total minerals count
        total_sites=total_sites,  # pass total sites count
        total_production=f"{total_prod:,}",  # format total production with commas
        latest_year=latest_year,  # pass latest production year
        minerals=minerals_df.to_dict('records'),  # pass minerals as list of dictionaries for template
        countries=countries_df.to_dict('records'))  # pass countries as list of dictionaries for template
    

@app.route('/map')  # route for the interactive map page
def map_view():
    if not session.get('logged_in'):  # check if user is logged in
        return redirect('/login')  # redirect to login if not logged in
    log_event(session.get('username','anonymous'), 'page_view', path='/map', details='Viewed map')  # log that user viewed the map
    # Build the map HTML using helper
    map_html = build_map_html(sites_full)  # generate interactive map HTML using the sites_full DataFrame
    return render_template('map.html', map_html=map_html, role=session['role'])  # render the map page and pass the map and user role



@app.route('/country/<int:country_id>')  # route to show profile of a specific country
def country_profile(country_id):
    if not session.get('logged_in'):  # check if user is logged in
        return redirect('/login')  # redirect to login if not logged in
    log_event(session.get('username','anonymous'), 'page_view', path=f'/country/{country_id}', details=f'Viewed country {country_id}')  # log the page view
    country_row = countries_df[countries_df['CountryID'] == country_id]  # get country info from countries_df
    if country_row.empty:  # if country not found
        flash('Country not found.', 'warning')  # show warning message
        return redirect('/dashboard')  # redirect to dashboard
    country = country_row.iloc[0]  # get the first (and only) row of country data
    prod_data = prod_full[prod_full['CountryID'] == country_id]  # get production data for this country
    if not prod_data.empty:  # if there is production data
        fig1 = px.line(prod_data, x='Year', y='Production_tonnes', color='MineralName', title='Production Trends (tonnes)', markers=True)  # line chart for production trends
        fig2 = px.bar(prod_data, x='Year', y='ExportValue_BillionUSD', color='MineralName', title='Export Value (Billion USD)')  # bar chart for export value
        prod_chart = pio.to_html(fig1, full_html=False)  # convert line chart to HTML for template
        export_chart = pio.to_html(fig2, full_html=False)  # convert bar chart to HTML for template
    else:  # if no production data
        prod_chart = "<p>No production data available.</p>"  # message for production chart
        export_chart = "<p>No export data available.</p>"  # message for export chart
    return render_template(
        'country.html',  # render country profile template
        country=country,  # pass country info to template ( pass meaning sending to the html files)
        prod_chart=prod_chart,  # pass production chart HTML
        export_chart=export_chart,  # pass export chart HTML
        role=session['role'])  # pass user role
    

# uploaded dataset routes
@app.route('/dataset')  # route for the uploaded dataset page
def dataset_view():
    if not session.get('logged_in'):  # check if user is logged in
        return redirect('/login')  # redirect to login if not logged in
    # show uploaded dataset
    user = session.get('username','anonymous')  # get current username, or 'anonymous' if not set
    role = session.get('role')  # get current user role
    # check sharing
    if not is_dataset_shared_for_user(user, role):  # check if dataset is shared with this user or role
        flash('Dataset not shared with you.','warning')  # show warning message
        return redirect('/dashboard')  # redirect to dashboard if user cannot access dataset
    log_event(user, 'page_view', path='/dataset', details='Viewed uploaded dataset')  # log that user viewed dataset
    records = uploaded_df.to_dict('records') if not uploaded_df.empty else []  # convert dataset to list of dicts for template
    cols = list(uploaded_df.columns) if not uploaded_df.empty else []  # get column names for template
    return render_template('dataset.html', role=session.get('role'), records=records, cols=cols)  # render dataset template and pass role, records, and column names


@app.route('/admin/dataset/upload', methods=['GET','POST'])
@admin_required  # only admins can access this route
def admin_dataset_upload():
    global uploaded_df  # allow modifying the global uploaded_df variable
    if request.method == 'POST':  # check if form was submitted
        f = request.files.get('file')  # get uploaded file from the form
        if not f:  # if no file was uploaded
            flash('No file uploaded.','warning')  # show warning message
            return redirect('/admin/dataset/upload')  # reload the upload page
        # accept only Excel or CSV
        filename = f.filename
        target = os.path.join(DATA_DIR, 'uploaded_dataset.csv')  # target path for uploaded dataset
        try:
            if filename.lower().endswith('.csv'):  # if CSV file
                f.save(target)  # save it to target path
                uploaded_df = pd.read_csv(target)  # read CSV into DataFrame
            else:  # assume Excel file
                tmp = os.path.join(DATA_DIR, 'tmp_uploaded.xlsx')  # temporary file path
                f.save(tmp)  # save uploaded Excel temporarily
                xls = pd.ExcelFile(tmp)
                df = pd.read_excel(xls, xls.sheet_names[0])  # read first sheet
                df.to_csv(target, index=False)  # save it as CSV
                uploaded_df = df  # update global DataFrame
                os.remove(tmp)  # remove temporary file
            # log successful upload
            log_event(session.get('username','admin'), 'dataset_upload', path='/admin/dataset/upload', details=f'Uploaded {filename}')
            flash('Dataset uploaded successfully.','success')  # success message
            return redirect('/admin')  # redirect to admin dashboard
        except Exception as e:  # if something goes wrong
            flash(f'Failed to process file: {e}','danger')  # show error message
            return redirect('/admin/dataset/upload')  # reload upload page
    return render_template('admin_dataset_upload.html', role=session.get('role'))  # show upload page on GET

@app.route('/admin/dataset/share', methods=['GET','POST'])
@admin_required  # only admins can access this route
def admin_dataset_share():
    if request.method == 'POST':  # check if form was submitted
        shared_type = request.form['shared_type']  # 'role' or 'user'
        shared_value = request.form['shared_value']  # which role/user to share with
        add_dataset_share(shared_type, shared_value, session.get('username'))  # add the share entry
        log_event(session.get('username','admin'), 'dataset_share', path='/admin/dataset/share', details=f'Shared dataset with {shared_type}:{shared_value}')  # log sharing event
        flash('Dataset shared.','success')  # success message
        return redirect('/admin')  # go back to admin dashboard
    return render_template('admin_dataset_share.html', role=session.get('role'))  # show dataset sharing page on GET


# Admin utilities and routes
@app.route('/investor')
@investor_required  # only investors (or admins) can access this route
def investor_dashboard():
    # Log page view
    log_event(session.get('username','anonymous'), 'page_view', path='/investor', details='Visited investor dashboard')  # record page visit

    # Prepare production trends per mineral
    prod = production_df.copy()  # make a copy of production data
    # Group production by Year and Mineral
    prod_summary = prod.groupby(['Year','MineralID'])['Production_tonnes'].sum().reset_index()  # sum production per year per mineral
    prod_summary = prod_summary.merge(minerals_df, on='MineralID')  # add mineral names

    # Compute simple profitability proxy: export value per tonne
    pf = production_df.copy()
    pf = pf.merge(minerals_df, on='MineralID').merge(countries_df, on='CountryID')  # merge production with minerals and countries
    pf['Export_per_tonne_BUSD'] = pf['ExportValue_BillionUSD'] / pf['Production_tonnes']  # calculate export value per tonne

    # Recent years overview: use last N years to give a stable multi-mineral view
    latest_year = int(production_df['Year'].max())  # get the latest year
    YEARS_WINDOW = 3  # include this many years (best-effort)
    available_years = sorted(production_df['Year'].unique())
    # pick the last up-to-N years available
    years_to_use = available_years[-YEARS_WINDOW:]
    recent = pf[pf['Year'].isin(years_to_use)]
    # per-mineral totals across the selected years
    mineral_overview = recent.groupby('MineralName').agg({'Production_tonnes':'sum','ExportValue_BillionUSD':'sum'}).reset_index()
    # make a human-readable label for the years included
    years_label = f"{min(years_to_use)}" if len(years_to_use)==1 else f"{min(years_to_use)}–{max(years_to_use)}"

    # convert charts to HTML using plotly
    try:
        fig_trends = px.line(prod_summary, x='Year', y='Production_tonnes', color='MineralName', title='Production Trends by Mineral', markers=True)  # line chart for trends
        fig_export = px.bar(mineral_overview, x='MineralName', y='ExportValue_BillionUSD', title=f'Export Value by Mineral ({years_label})')  # bar chart for export value
        trends_html = pio.to_html(fig_trends, full_html=False)  # convert line chart to HTML
        export_html = pio.to_html(fig_export, full_html=False)  # convert bar chart to HTML
    except Exception:
        trends_html = '<p>Charts unavailable.</p>'  # fallback if chart fails
        export_html = '<p>Charts unavailable.</p>'

    # Provide a simple loss/profit hint: compare export value growth year-over-year
    yoy = production_df.groupby('Year')['ExportValue_BillionUSD'].sum().pct_change().fillna(0)  # compute year-over-year % change
    yoy_latest = yoy.loc[latest_year] if latest_year in yoy.index else 0  # get the latest year growth

    # give investors a quick access list of countries to view profiles (charts, exports, production)
    countries = countries_df.to_dict('records')  # convert countries to list of dictionaries for template
    return render_template(
        'investor_dashboard.html',  # render investor dashboard template
        role=session['role'],  # pass user role
        trends_html=trends_html,  # pass line chart HTML
        export_html=export_html,  # pass bar chart HTML
    mineral_overview=mineral_overview.to_dict('records'),  # pass per-mineral totals
        yoy_pct=round(float(yoy_latest)*100,2),  # pass YoY growth % rounded to 2 decimals
        latest_year=latest_year,  # pass latest year
    years_label=years_label,
        countries=countries) # pass list of countries for quick access
    

@app.route('/admin')
@admin_required  # only admins can access this route
def admin_dashboard():
    with open(AUDIT_LOG,'r',encoding='utf-8') as f:  # open the audit log CSV
        lines = f.readlines()[-200:]  # take the last 200 lines
    logs=[]  # list to store processed log entries
    for ln in lines[1:]:  # skip header
        parts=[p.strip('"') for p in ln.strip().split('\",\"')]  # split line into columns
        if len(parts)>=4:  # check if line has enough columns
            logs.append({'Timestamp':parts[0],'Username':parts[1],'Action':parts[2],'Path':parts[3],'Details':parts[4].strip('"')})  # store as dict
    return render_template('admin_dashboard.html', role=session['role'], logs=logs, users=load_csv(os.path.join(DATA_DIR,'users.csv')).to_dict('records'))  # render template and pass role, logs, and users


@app.route('/admin/audit/clear', methods=['POST'])
@admin_required  # only admins can access
def admin_audit_clear():
    # create a timestamped backup then clear the audit log (keep header)
    backup = AUDIT_LOG.replace('.csv', '') + '_' + datetime.utcnow().strftime('%Y%m%dT%H%M%SZ') + '.bak.csv'  # backup file name
    try:
        # copy existing audit log to backup
        with open(AUDIT_LOG, 'r', encoding='utf-8') as src, open(backup, 'w', encoding='utf-8') as dst:
            dst.write(src.read())  # copy all content
        # recreate the audit log with header and a single clearing event
        with open(AUDIT_LOG, 'w', encoding='utf-8') as f:
            f.write('Timestamp,Username,Action,Path,Details\n')  # write header
            ts = datetime.utcnow().isoformat()  # current timestamp
            f.write(f'"{ts}","{session.get("username","admin")}","audit_cleared","/admin/audit/clear","Cleared recent audit log and backed up to {os.path.basename(backup)}"\n')  # log clearing event
        flash('Audit log cleared (backup created).', 'success')  # show success message
        log_event(session.get('username','admin'), 'audit_clear', path='/admin/audit/clear', details=f'Backup: {os.path.basename(backup)}')  # log the audit_clear event
    except Exception as e:
        flash(f'Failed to clear audit log: {e}', 'danger')  # show error if fails
    return redirect('/admin')  # go back to admin dashboard


def load_entity_df(entity):
    cfg=ENTITIES[entity]  # get entity configuration
    return load_csv(os.path.join(DATA_DIR, cfg['csv']))  # load CSV of the entity as DataFrame


@app.route('/admin/<entity>')
@admin_required  # only admins can access this route
def admin_entity_list(entity):
    if entity not in ENTITIES:
        flash('Unknown entity','warning')  # show warning if entity doesn't exist
        return redirect('/admin')  # go back to admin dashboard
    cfg=ENTITIES[entity]  # get entity configuration
    df=load_entity_df(entity)  # load entity data from CSV
    items=df.to_dict('records')  # convert data to list of dicts for template
    return render_template('admin_list.html', role=session['role'], items=items, title=cfg['title'], fields=cfg['fields'], base_endpoint=entity)  # render template with role, data, title and fields


@app.route('/admin/<entity>/add', methods=['GET','POST'])
@admin_required  # only admins can use this
def admin_entity_add(entity):
    if entity not in ENTITIES:
        flash('Unknown entity','warning'); return redirect('/admin')  # warn if entity invalid
    cfg=ENTITIES[entity]  # get entity config
    df=load_entity_df(entity)  # load existing CSV data
    if request.method=='POST':  # form submitted
        new_id = int(df[cfg['id']].max())+1 if not df.empty else 1  # generate new ID
        row={}  # new row dict
        errors = []
        for f in cfg['fields']:
            if f==cfg['id']:
                row[f]=new_id  # assign ID
            else:
                row[f]=request.form.get(f,'')  # get form value
        # basic validation for sites
        if cfg['csv']=='sites.csv':
            try:
                lat = float(request.form.get('Latitude',''))
                if not -90 <= lat <= 90:
                    errors.append('Latitude must be between -90 and 90')
            except Exception:
                errors.append('Latitude must be a valid number')
            try:
                lon = float(request.form.get('Longitude',''))
                if not -180 <= lon <= 180:
                    errors.append('Longitude must be between -180 and 180')
            except Exception:
                errors.append('Longitude must be a valid number')
            try:
                prod_val = float(request.form.get('Production_tonnes','0') or 0)
                if prod_val < 0:
                    errors.append('Production_tonnes must be non-negative')
            except Exception:
                errors.append('Production_tonnes must be a number')
        if errors:
            # re-render form with errors and previous form values
            selects={}
            for k,v in ENTITIES[entity].get('selects',{}).items():
                sel_df = load_csv(os.path.join(DATA_DIR, v[0]+'.csv'))
                selects[k]=sel_df.to_dict('records')
            return render_template('admin_edit_generic.html', role=session['role'], title='Add '+cfg['title'], fields=[f for f in cfg['fields'] if f!=cfg['id']], item=None, base_endpoint=entity, select_options=selects, form=request.form, errors=errors)
        df.loc[len(df)]=row  # append row
        save_csv(df, os.path.join(DATA_DIR, cfg['csv']))  # save CSV
        reload_all_data()
        log_event(session.get('username','admin'),'entity_add', path=f'/admin/{entity}/add', details=f'Added {entity} {new_id}')  # log event
        flash('Added.','success')  # success message
        return redirect(f'/admin/{entity}')  # redirect back
    # prepare selects for GET
    selects={}  # prepare dropdowns
    for k,v in ENTITIES[entity].get('selects',{}).items():
        sel_df = load_csv(os.path.join(DATA_DIR, v[0]+'.csv'))
        selects[k]=sel_df.to_dict('records')  # convert to list of dicts
    return render_template('admin_edit_generic.html', role=session['role'], title='Add '+cfg['title'], fields=[f for f in cfg['fields'] if f!=cfg['id']], item=None, base_endpoint=entity, select_options=selects)


@app.route('/admin/<entity>/edit/<int:obj_id>', methods=['GET','POST'])
@admin_required  # only admins can access
def admin_entity_edit(entity,obj_id):
    if entity not in ENTITIES:
        flash('Unknown entity','warning'); return redirect('/admin')  # invalid entity
    cfg=ENTITIES[entity]  # get entity config
    df=load_entity_df(entity)  # load CSV data
    row=df[df[cfg['id']]==obj_id]  # find row by ID
    if row.empty:
        flash('Not found','warning'); return redirect(f'/admin/{entity}')  # row not found
    if request.method=='POST':  # form submitted
        idx=row.index[0]  # index of row
        errors = []
        for f in cfg['fields']:
            if f==cfg['id']: continue  # skip ID
            df.at[idx,f]=request.form.get(f,df.at[idx,f])  # update fields
        # validation for sites on edit
        if cfg['csv']=='sites.csv':
            try:
                lat = float(request.form.get('Latitude',''))
                if not -90 <= lat <= 90:
                    errors.append('Latitude must be between -90 and 90')
            except Exception:
                errors.append('Latitude must be a valid number')
            try:
                lon = float(request.form.get('Longitude',''))
                if not -180 <= lon <= 180:
                    errors.append('Longitude must be between -180 and 180')
            except Exception:
                errors.append('Longitude must be a valid number')
            try:
                prod_val = float(request.form.get('Production_tonnes','0') or 0)
                if prod_val < 0:
                    errors.append('Production_tonnes must be non-negative')
            except Exception:
                errors.append('Production_tonnes must be a number')
        if errors:
            selects={}
            for k,v in ENTITIES[entity].get('selects',{}).items():
                sel_df=load_csv(os.path.join(DATA_DIR, v[0]+'.csv'))
                selects[k]=sel_df.to_dict('records')
            item = {c: (request.form.get(c) if c!='SiteID' else obj_id) for c in cfg['fields']}
            return render_template('admin_edit_generic.html', role=session['role'], title='Edit '+cfg['title'], fields=[f for f in cfg['fields'] if f!=cfg['id']], item=item, base_endpoint=entity, select_options=selects, form=request.form, errors=errors)
        save_csv(df, os.path.join(DATA_DIR, cfg['csv']))  # save CSV
        reload_all_data()
        log_event(session.get('username','admin'),'entity_edit', path=f'/admin/{entity}/edit/{obj_id}', details=f'Edited {entity} {obj_id}')  # log edit
        flash('Updated.','success')  # success message
        return redirect(f'/admin/{entity}')  # redirect back
    item=row.iloc[0].to_dict()  # prepare row for form
    selects={}
    for k,v in ENTITIES[entity].get('selects',{}).items():  # dropdown options
        sel_df=load_csv(os.path.join(DATA_DIR, v[0]+'.csv'))
        selects[k]=sel_df.to_dict('records')  # convert to dict list
    return render_template('admin_edit_generic.html', role=session['role'], title='Edit '+cfg['title'], fields=[f for f in cfg['fields'] if f!=cfg['id']], item=item, base_endpoint=entity, select_options=selects)


@app.route('/admin/<entity>/delete/<int:obj_id>', methods=['POST'])
@admin_required  # only admins
def admin_entity_delete(entity,obj_id):
    if entity not in ENTITIES:
        flash('Unknown entity','warning'); return redirect('/admin')  # invalid entity
    cfg=ENTITIES[entity]  # entity config
    df=load_entity_df(entity)  # load CSV
    df=df[df[cfg['id']]!=obj_id]  # remove row by ID
    save_csv(df, os.path.join(DATA_DIR, cfg['csv']))  # save updated CSV
    reload_all_data()
    log_event(session.get('username','admin'),'entity_delete', path=f'/admin/{entity}/delete/{obj_id}', details=f'Deleted {entity} {obj_id}')  # log deletion
    flash('Deleted.','success')  # success message
    return redirect(f'/admin/{entity}')  # back to entity list


@app.route('/admin/sites/by_country/<int:country_id>')
@admin_required  # only admins
def admin_sites_by_country(country_id):
    cfg = ENTITIES['sites']  # sites config
    df = load_entity_df('sites')  # load all sites
    country_df = load_csv(os.path.join(DATA_DIR, 'countries.csv'))  # load countries
    country_row = country_df[country_df['CountryID'] == country_id]  # find country
    if country_row.empty:
        flash('Country not found.', 'warning'); return redirect('/admin/sites')  # warn if missing
    country_name = country_row.iloc[0]['CountryName']  # get country name
    items = df[df['CountryID'] == country_id].to_dict('records')  # sites in that country
    return render_template('admin_sites_by_country.html', role=session['role'], items=items, country_id=country_id, country_name=country_name)


@app.route('/admin/sites/delete_by_country/<int:country_id>', methods=['POST'])
@admin_required  # only admins
def admin_sites_delete_by_country(country_id):
    cfg = ENTITIES['sites']  # sites config
    df = load_entity_df('sites')  # load sites
    before = len(df)  # count before deletion
    df = df[df['CountryID'] != country_id]  # remove all for this country
    save_csv(df, os.path.join(DATA_DIR, cfg['csv']))  # save updated CSV
    reload_all_data()
    after = len(df)
    deleted = before - after  # count deleted
    log_event(session.get('username','admin'), 'entity_bulk_delete', path=f'/admin/sites/delete_by_country/{country_id}', details=f'Deleted {deleted} sites for country {country_id}')  # log bulk deletion
    flash(f'Deleted {deleted} site(s) for the country.', 'success')  # feedback
    return redirect(f'/admin/sites')  # back to sites list

if __name__ == '__main__':
    app.run(debug=True)  # start Flask app in debug mode