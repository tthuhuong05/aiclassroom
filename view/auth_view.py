from flask import render_template

class AuthView:
    def show_home(self, username=None, role=None):
        if username:
            return f"Welcome, {username}! Your role is {role}."
        else:
            return "Welcome, guest! Please <a href='/login'>login</a> or <a href='/register'>register</a>."

    def show_register_form(self):
        return render_template("auth/register.html")

    def show_login_form(self):
        return render_template("auth/login.html")

    def show_home(self, username=None, role=None):
        return render_template("auth/home.html", username=username, role=role)
