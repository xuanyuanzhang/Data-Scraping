#!/usr/bin/env python2.7
from bs4 import BeautifulSoup
import urllib2
import json
import codecs
import re
import locale
from scraping import scraping

import sqlite3 as lite
import sys
import hashlib
import csv
import os
import pygal
import webbrowser
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, flash, session, request, render_template, g, redirect, Response, url_for

reload(sys)
sys.setdefaultencoding("utf-8")

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DEBUG = True

SECRET_KEY = 'development key'

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.config.from_object(__name__)

scraping()

username = None

conn = None

cur = None

def encrypt_password(password):
  encrypted_pass = hashlib.sha1(password.encode('utf-8')).hexdigest()
  return encrypted_pass

conn = lite.connect('orbis.sqlite')
cur = conn.cursor()
data = cur.execute("SELECT * FROM holding")

with open('csv_files/output.csv', 'wb') as f:
  writer = csv.writer(f)
  writer.writerow(['Column 1', 'Column 2', 'Column 3'])
  writer.writerows(data)

conn.close()

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    conn = lite.connect('orbis.sqlite', isolation_level = None)
    conn.create_function('encrypt', 1, encrypt_password)
    cur = conn.cursor()
  except:
    print ("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    conn.close()
  except Exception as e:
    pass

# Methods that connect to webs
@app.route('/')
def index():
  return render_template('index.html')

#login
@app.route('/login', methods=['GET', 'POST'])
def login():

  global username
  
  error = None
  
  if request.method == 'POST':

    conn = lite.connect('orbis.sqlite', isolation_level = None)
    conn.create_function('encrypt', 1, encrypt_password)
    cur = conn.cursor()

    result = cur.execute('SELECT COUNT(*) FROM users U WHERE U.username =?',
                         (request.form['username'],))
    userExists = (result.fetchone()[0] != 0)

    if not userExists:
      error = 'Invalid Username'
    if userExists:
      result = cur.execute('SELECT password FROM users U WHERE U.username =?',
                              (request.form['username'],))
      password = str.split(str(result.fetchone()[0]))[0]
      if encrypt_password(request.form['password']) != password:
        session['logged_in'] = False
        error = 'Invalid Password.'
      else:
        session['logged_in'] = True
        username = request.form['username']
        flash('Login Complete')
        return redirect(url_for('index'))
    result.close()
  return render_template('login.html', error=error)

# Log out
@app.route('/logout')
def logout():

  global username 

  session.pop('logged_in', None)
  username = None
  flash('User Logged Out')
  return redirect(url_for('index'))

# Register
@app.route('/register',methods=['GET','POST'])
def register():

  error = None
  if request.method == 'POST':

    conn = lite.connect('orbis.sqlite', isolation_level = None)
    conn.create_function('encrypt', 1, encrypt_password)
    cur = conn.cursor()
    
    result = cur.execute('SELECT COUNT(*) FROM users U WHERE U.email =?',
                            (request.form['email'],))
    emailExists = (result.fetchone()[0]!=0)

    print("email checked!")

    result = cur.execute('SELECT COUNT(*) FROM users U WHERE U.username =?',
                            (request.form['username'],))
    userExists = (result.fetchone()[0]!=0)

    print("username checked!")
    
    if request.form['password']!=request.form['passwordAgain']:
      error = 'Passwords Do Not Match'
    elif emailExists:
      error = 'Email Already Exists'
    elif userExists:
      error = 'Username Already Exists'
    else:
      cur.execute('INSERT INTO users VALUES (?, ?, ?, encrypt(?))',
                     (request.form['username'],request.form['email'],request.form['name'],request.form['password']))
      print("insertion succeeds")
      session['logged_in'] = True
      flash('Account Created')
      result.close()
      return redirect(url_for('index'))
    result.close()
  return render_template('register.html',error=error)

@app.route('/getCSV',methods=['GET','POST'])
def getCSV():
  if request.method == 'GET':
    with open('csv_files/output.csv') as fp:
      csv = fp.read()
        
    return Response(
      csv,
      mimetype="text/csv",
      headers={"Content-disposition":
               "attachment; filename=output.csv"})
  return render_template('search.html')

@app.route('/ceramic',methods=['GET','POST'])
def ceramic():
    error = None
    context = dict(error=error)
    if request.method == 'GET':
        result = cur.execute('SELECT a.name, a.url FROM AuctionGood a, Genre g \
          WHERE a.url = g.url AND g.class = %s', 'ceramic')
        good_list = []

        for row in result:
            good_list.append(row)

        context["good_list"] = good_list

        return render_template('ceramic.html', **context)
    return render_template('ceramic.html')

#Search for certain Fund
@app.route('/search', methods=['POST', 'GET'])
def search():
  conn = lite.connect('orbis.sqlite')
  cur = conn.cursor()
  error = None
  context = dict(error=error)
  if request.method == 'POST':
    if request.form['Fund']!='':
      good_list = []
      try:
        result = cur.execute('SELECT * FROM {}'.format(request.form['Fund']))

        for row in result:
          good_list.append(row)

      except lite.OperationalError:
        good_list.append("N/A")

      hist = pygal.Histogram()
      hist.title = "Top Ten Funds"
      name = []
      weight = []
      for row in good_list:
        name.append(row[0])
        data = float(row[1][:4])
        weight.append(data)
      i=0
      while i<len(name):
        hist.add(name[i],[(weight[i],i,i+1)])
        i += 1
      chart = hist.render()
        
      context["good_list"] = good_list
      context["chart"] = chart
      
    return render_template('search.html', **context)
  return render_template('search.html')

#auction search
@app.route('/auction', methods=['POST', 'GET'])
def auction():
    error = None
    context = dict(error=error)
    if request.method == 'POST':
        if request.form['location']!='--' and request.form['house']!='--'and request.form['year']!='--' and request.form['month']!= '--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.name = %s \
                AND d.year = %s \
                AND d.month = %s \
                AND u.location = %s \
                GROUP BY a.name, u.title, p.hammerprice', request.form['house'], request.form['year'], request.form['month'], request.form['location'])
        elif request.form['location']=='--' and request.form['house']!='--'and request.form['year']!='--'and request.form['month']!= '--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.name = %s \
                AND d.year = %s\
                AND d.month = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['house'], request.form['year'], request.form['month'])
        elif request.form['location']=='--' and request.form['house']=='--'and request.form['year']!='--' and request.form['month']!='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND d.year = %s \
                AND d.month = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['year'], request.form['month'])
        elif request.form['location']=='--' and request.form['house']=='--'and request.form['year']=='--' and request.form['month']!='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND d.month = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['month'])
        elif request.form['location']=='--' and request.form['house']=='--'and request.form['year']=='--' and request.form['month']=='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                GROUP BY a.name, u.title, p.hammerprice')
        elif request.form['location']!='--' and request.form['house']=='--'and request.form['year']!='--' and request.form['month']!='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.year = %s \
                AND u.month = %s \
                AND u.location = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['year'], request.form['month'], request.form['location'])
        elif request.form['location']!='--' and request.form['house']=='--'and request.form['year']=='--' and request.form['month']!='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.month = %s \
                AND u.location = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['month'], request.form['location'])
        elif request.form['location']!='--' and request.form['house']=='--'and request.form['year']=='--' and request.form['month']=='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.location = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['location'])
        elif request.form['location']!='--' and request.form['house']!='--'and request.form['year']=='--' and request.form['month']!='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.name = %s \
                AND u.month = %s \
                AND u.location = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['house'], request.form['month'], request.form['location'])
        elif request.form['location']!='--' and request.form['house']!='--'and request.form['year']=='--' and request.form['month']=='--':
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.name = %s \
                AND u.location = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['house'], request.form['location'])
        else:
                result = cur.execute('SELECT a.name, u.title, p.hammerprice \
                FROM AuctionGood a, Auction u, Auctionhouse h, Dealtime d, Price p WHERE u.title = a.title \
                AND a.url = p.url \
                AND u.year = d.year \
                AND u.month = d.month \
                AND u.name = h.name \
                AND u.name = %s \
                AND u.month = %s \
                AND u.location = %s\
                GROUP BY a.name, u.title, p.hammerprice', request.form['house'], request.form['month'], request.form['location'])

        
        auction_list = []
        for row in result:
                auction_list.append(row)

        context["auction_list"] = auction_list

        return render_template('auction.html', **context)
    return render_template('auction.html')


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  cur.execute('INSERT INTO test VALUES (NULL, ?)', name)
  return redirect('/')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print ("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
