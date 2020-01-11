from flask import jsonify, request, session, redirect, render_template
from flask_login import login_required, login_user, current_user, logout_user
from sqlalchemy.exc import IntegrityError
from hookup import app, db
from functools import wraps
import json

from hookup.flask_ngrok import get_tunnel_url
from hookup.models import User, Page, Record


def auth_api(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(current_user.is_authenticated)
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        else:
            return jsonify({'msg': 'Not authenticated'})

    return decorated_function


@app.route("/", methods=["GET", "POST"])
def fish():
    user = User.query.first()
    current_page = user.pages[user.current_page]
    if request.method == "POST":
        r = Record()
        r.data = request.form
        current_page.records.append(r)
        user.save()
        return jsonify(current_page.records[0].data)

    current_page = user.pages[user.current_page]

    return current_page.get_source_content()


@app.route("/adminlogin", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.first()
        if user and user.password == request.form.get('password') and user.username == request.form.get("username"):
            login_user(user)
            return redirect("adminpage")
    return render_template("login.html")


@app.route('/adminpage', defaults={'path': ''})
@login_required
def main(path):
    return render_template("index.html")


@app.route("/adminlogout")
def logout():
    logout_user()
    return redirect("/")


@app.route("/api/get_ngrok_url")
def get_ngrok_url():
    return jsonify(get_tunnel_url())


@app.route("/api/page/new", methods=["POST"])
def new_page():
    if 'page' in request.files:
        page = Page(name=request.form['pageTitle'],
                    source=f"{request.form['pageTitle']}.html")
        user = User.query.first()
        user.pages.append(page)
        try:
            user.save()
            file = request.files['page']
            file.save(str(app.config['UPLOAD_FOLDER'] /
                          f"{request.form['pageTitle']}.html"))
        except IntegrityError as ex:
            return jsonify(f"{request.form['pageTitle']} isimde bir site zaten mevcut"), 500
    else:
        return jsonify(f"Kaynak dosyası eksik"), 500

    return jsonify(f"{request.form['pageTitle']} başarıyla kaydedildi"), 200


@app.route("/api/page/delete", methods=["POST"])
def delete_page():
    page_name = request.json.get('pageName')
    source_file = app.config['UPLOAD_FOLDER'] / f"{page_name}.html"
    source_file.unlink()  # delete old page
    page = Page.query.filter_by(name=page_name).one()
    db.session.delete(page)
    db.session.commit()

    return jsonify(f"{page_name} başarıyla silindi"), 200


@app.route("/api/page/get_current")
def get_current_page():
    user = User.query.first()
    if len(user.pages) == 0:
        return jsonify({})
    current_page = user.pages[user.current_page]
    return jsonify({
        "name": current_page.name,
        "source": current_page.get_source_content()
    }), 200


@app.route("/api/page/set_current", methods=["POST"])
def set_current_page():
    user = User.query.first()
    user.current_page = [i.name for i in user.pages].index(
        request.json['currentPage'])
    user.save()
    current_page = user.pages[user.current_page]
    return jsonify({
        "name": current_page.name,
        "source": current_page.get_source_content(),
        "msg": f"{current_page.name} başarıyla ayarlandı."
    }), 200


@app.route("/api/pages")
def list_pages():
    user = User.query.first()
    if len(user.pages) == 0:
        return jsonify([])
    pages = list()
    for page in user.pages:
        pages.append({
            "name": page.name,
            "source": page.get_source_content(),
            "stock": page.stock
        })
    current_page = user.pages[user.current_page]
    return jsonify(pages), 200
