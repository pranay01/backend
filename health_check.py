from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)

# only route is / and the health check is passed so we can have a container we exec into and troubleshoot
# if you do use this make sure you are in a staging environment and update the task definition to run this command instead of app.py
@app.route('/')
def hello_world():
    result = {'Message': 'OK'}
    # return result
    return result, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)