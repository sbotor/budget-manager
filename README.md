# budget-manager
<h3>Requirements</h3>

- Download Python
- Set up a virtual environment (for example with venv: https://docs.python.org/3/tutorial/venv.html). It is not really that important, can be omitted.
- Download the requirements with pip:
  - <i>pip install -r requirements.txt</i>
- Create a key.txt file in the project root folder and paste a valid secret key (a key generator can be used).

<h3>How does it work?</h3>
A Django project is made up of semi-isolated apps that provide some separate functionality. In the root project folder there is another folder with the same name as the project. All the project settings are there and also some other stuff. There are also the apps folders and a manage.py script which acts as a command line interface of the whole project.
  
Django is based on a Model-View-Template pattern and basically works like this:
1. An HTTP request is sent to a specified URL.
2. Django looks in the urls.py file for the URL and passes an HttpRequest object to the view attached to the URL.
3. The view is a function (or a special object) defined in views.py that has to do something with the request and return an HttpResponse object.
4. This can be done by rendering a template which is an html file with special elements that get processed into desired values.
    - The elements can be variables that get passed as a python dictionary with string keys (variable names referenced in the template) and values that can be interpretted as strings (probably).
    - Templates can be inherited similarly to classes, to override something you have to first define a block in the parent template.
    - If statements and for loops can be used, other things as well.
5. An HTTP response is sent and the client may be redirected to another page.

<h3>Running the project</h3>
Everything is done by providing arguments to the manage.py script. First you have to make migrations (prepare the database scripts):

- <i>python manage.py makemigrations</i>

Then the database has to be created and updated:
- <i>python manage.py migrate</i>

Finally, the server can start:
- <i>python manage.py runserver</i>

This will create the db and server locally on port 8000.

<h3>Help</h3>

- https://docs.djangoproject.com/en/4.0/
- https://getbootstrap.com/docs/5.1/getting-started/introduction/
- https://docs.python.org/3/
