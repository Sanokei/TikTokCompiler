from gevent import monkey
monkey.patch_all()
from flask import Flask,render_template,request,redirect,url_for,session,flash
import MySQLDatabase
import config
from TikTokApi import TikTokApi
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, Form, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired
import ast
from pathlib import Path
Path("video_files").mkdir(exist_ok=True)
# tiktok api
api = TikTokApi.get_instance(generate_static_device_id=True)

# Database
con = MySQLDatabase.sql_connection()
MySQLDatabase.initial_table_creation(con)

# Flask
app = Flask(__name__)
app.secret_key = config.secret_key

@app.route('/', methods = ['GET','POST','DELETE', 'PATCH'], strict_slashes=False)
def index():
    return render_template('index.html', template_folder='../templates')

@app.route('/filter') # list all filters
def filter():
    filters = MySQLDatabase.get_filters(con)
    return render_template('filter.html', template_folder='../templates', filters=filters)

class filter_form_create(Form):
    filter_name = StringField('Filter Name', validators=[DataRequired()])
    filter_type = SelectField(u'Select an Option', choices=[('hashtag', 'Hashtag'), ('author', 'Author')],id = 'filter_type')
    filter_value = StringField('Filter Value', validators=[DataRequired()])
    
@app.route('/filter/create/', methods=['GET','POST']) # create a filter
def create_filter():
    form = filter_form_create(request.form)
    if request.method == 'GET':
        return render_template('form.html', template_folder='../templates', form=form)
    if request.method == 'POST':
        if form.validate():
            filter_name = form.filter_name.data
            filter_type = form.filter_type.data
            filter_value = form.filter_value.data
            print("ADDING TO FILTER DB")
            print("name: " + filter_name)
            print("type: " + filter_type)
            print("value: " + filter_value)
            MySQLDatabase.insert_filter(con, filter_name, filter_type, filter_value)
            return redirect(url_for('index'))

@app.route('/filter/delete', methods=['GET','POST']) # delete a filter
def delete_filter():
    if request.method == 'GET':
        return f"Cannot delete without context go to /filter"
    if request.method == 'POST':
        filter_id = ast.literal_eval(request.form['filter'])[0]
        print("FILTER_ID: " + str(filter_id))
        MySQLDatabase.delete_filter(con, str(filter_id))
        return redirect(url_for('index'))

@app.route('/find-video/', methods=['GET','POST']) # use the filter to find videos
def data():
    if request.method == 'GET':
        filters = MySQLDatabase.get_filters(con)
        # add a default filter of name trending
        filters.append((len(filters),'trending', 'trending', 'trending'))
        return render_template('find_video_form.html', template_folder='../templates', filters=filters)
    if request.method == 'POST':
        filters_list = ast.literal_eval(request.form['filter'])
        print("FILTERS_LIST" + str(filters_list))
        filter_id = filters_list[0]
        filter_name = filters_list[1]
        filter_type = filters_list[2]
        filter_value = filters_list[3]
        all_video_id = []
        print("id: " + str(filter_id))
        print("name: " + str(filter_name))
        print("type: " + str(filter_type))
        print("value: " + str(filter_value))
        if filter_type == 'hashtag':
            filter_value = filter_value.replace('#','')
            print("filter_value: " + filter_value)
            tags = filter_value.split(',')
            for tag in tags:
                try:
                    all_video_id += api.by_hashtag(hashtag=tag,count=int(request.form['results']),offset=0, custom_verifyFp=config.tiktok_api_key)
                except:
                    print("ERROR: " + str(tag) + " is not a hashtag")
        elif filter_type == 'author':
            try:
                all_video_id = api.by_username(username=filter_value,count=int(request.form['results']),offset=0, custom_verifyFp=config.tiktok_api_key)
            except:
                print("ERROR: " + str(filter_value) + "is not a username")
        elif filter_type == 'trending':
            all_video_id = api.by_trending(count=int(request.form['results']), custom_verifyFp=config.tiktok_api_key)
        
        print("ALL_VIDEOS: " + str(all_video_id))

        videos = []
        # get the video data
        for video_id in all_video_id:
            video = api.get_video_by_tiktok(data=video_id, custom_verifyFp=config.tiktok_api_key)
            with open("video_files/{}.mp4".format(str(video_id)), 'wb') as output:
                output.write(video) # saves data to the mp4 file
        
        return render_template('find_video.html', template_folder='../templates', all_videos=videos)

@app.route('/create-video/') # 
def create_video():
    return render_template('create.html', template_folder='../templates')

Bootstrap(app)