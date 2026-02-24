import json
import os
import re
import secrets
import subprocess
import threading
from datetime import datetime
from functools import wraps

from werkzeug.utils import secure_filename

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage, subfolder=""):
    """Save an uploaded file and return its path relative to static/."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    fname = secure_filename(file_storage.filename)
    # Ensure unique name
    base, ext = os.path.splitext(fname)
    dest_dir = os.path.join(UPLOAD_FOLDER, subfolder) if subfolder else UPLOAD_FOLDER
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, fname)
    counter = 1
    while os.path.exists(dest):
        fname = f"{base}_{counter}{ext}"
        dest = os.path.join(dest_dir, fname)
        counter += 1
    file_storage.save(dest)
    rel = os.path.relpath(dest, app.static_folder).replace(os.sep, "/")
    return rel

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONTENT_FILE = os.path.join(DATA_DIR, "content.json")
ARTICLES_FILE = os.path.join(DATA_DIR, "articles.json")
ANNOUNCEMENTS_FILE = os.path.join(DATA_DIR, "announcements.json")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


# ─── Data helpers ───────────────────────────────────────────────

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_content():
    return load_json(CONTENT_FILE)


def get_articles():
    return load_json(ARTICLES_FILE)


def get_announcements():
    return load_json(ANNOUNCEMENTS_FILE)


# ─── Template context ──────────────────────────────────────────

@app.context_processor
def inject_globals():
    content = get_content()
    site = content["site"]
    return {"site": site}


# ─── Public routes ──────────────────────────────────────────────

@app.route("/")
def index():
    data = get_content()
    return render_template("index.html", data=data)


@app.route("/about/")
def about():
    data = get_content()
    return render_template("about.html", data=data)


@app.route("/documents/")
def documents():
    data = get_content()
    return render_template("documents.html", data=data)


@app.route("/services/")
def services():
    data = get_content()
    return render_template("services.html", data=data)


@app.route("/contact/")
def contact():
    data = get_content()
    return render_template("contact.html", data=data)


@app.route("/announcements/")
def announcements():
    all_announcements = get_announcements()
    data = get_content()
    published = [a for a in all_announcements if a.get("published", False)]
    return render_template("announcements.html", announcements=published, data=data)


@app.route("/articles/")
def articles():
    all_articles = get_articles()
    data = get_content()
    published = [a for a in all_articles if a.get("published", False)]
    return render_template("articles.html", articles=published, data=data)


@app.route("/articles/<slug>/")
def article(slug):
    all_articles = get_articles()
    data = get_content()
    art = next((a for a in all_articles if a["slug"] == slug and a.get("published", False)), None)
    if art is None:
        abort(404)
    return render_template("article.html", article=art, data=data)


# ─── Admin auth ─────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Неверный пароль", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("index"))


# ─── Admin dashboard ────────────────────────────────────────────

@app.route("/admin/")
@login_required
def admin_dashboard():
    content = get_content()
    artcls = get_articles()
    anns = get_announcements()
    return render_template("admin/dashboard.html", content=content, articles=artcls, announcements=anns)


# ─── Admin: Общие настройки ────────────────────────────────────

@app.route("/admin/site", methods=["GET", "POST"])
@login_required
def admin_site():
    content = get_content()
    if request.method == "POST":
        s = content["site"]
        s["name"] = request.form.get("name", s["name"])
        s["role"] = request.form.get("role", s["role"])
        s["tagline"] = request.form.get("tagline", s["tagline"])
        s["telegram_link"] = request.form.get("telegram_link", s.get("telegram_link", ""))
        s["maks_link"] = request.form.get("maks_link", s.get("maks_link", ""))
        s["copyright_year"] = request.form.get("copyright_year", s.get("copyright_year", ""))
        save_json(CONTENT_FILE, content)
        flash("Настройки сайта сохранены", "success")
        return redirect(url_for("admin_site"))
    return render_template("admin/edit_site.html", content=content)


# ─── Admin: Главная страница ───────────────────────────────────

@app.route("/admin/index", methods=["GET", "POST"])
@login_required
def admin_index():
    content = get_content()
    if request.method == "POST":
        # Hero image upload
        hero_file = request.files.get("hero_image_file")
        if hero_file and hero_file.filename:
            new_path = save_upload(hero_file, "pages")
            if new_path:
                old = content["hero"].get("image", "")
                if old and old.startswith("uploads/"):
                    old_abs = os.path.join(app.static_folder, old)
                    if os.path.exists(old_abs):
                        os.remove(old_abs)
                content["hero"]["image"] = new_path
        if request.form.get("hero_remove_image") == "1":
            old = content["hero"].get("image", "")
            if old and old.startswith("uploads/"):
                old_abs = os.path.join(app.static_folder, old)
                if os.path.exists(old_abs):
                    os.remove(old_abs)
            content["hero"]["image"] = ""

        # Hero
        hero = content["hero"]
        hero["label"] = request.form.get("hero_label", hero["label"])
        hero["title"] = request.form.get("hero_title", hero["title"])
        hero["text"] = request.form.get("hero_text", hero["text"])
        hero["cta_text"] = request.form.get("hero_cta_text", hero["cta_text"])
        hero["secondary_cta_text"] = request.form.get("hero_secondary_cta_text", hero["secondary_cta_text"])

        # Help section
        hs = content["help_section"]
        hs["label"] = request.form.get("help_label", hs["label"])
        hs["title"] = request.form.get("help_title", hs["title"])
        items = request.form.getlist("help_items")
        hs["items"] = [i.strip() for i in items if i.strip()]

        # About preview
        # About preview image upload
        abp_file = request.files.get("about_preview_image_file")
        if abp_file and abp_file.filename:
            new_path = save_upload(abp_file, "pages")
            if new_path:
                old = content["about_preview"].get("image", "")
                if old and old.startswith("uploads/"):
                    old_abs = os.path.join(app.static_folder, old)
                    if os.path.exists(old_abs):
                        os.remove(old_abs)
                content["about_preview"]["image"] = new_path
        if request.form.get("about_preview_remove_image") == "1":
            old = content["about_preview"].get("image", "")
            if old and old.startswith("uploads/"):
                old_abs = os.path.join(app.static_folder, old)
                if os.path.exists(old_abs):
                    os.remove(old_abs)
            content["about_preview"]["image"] = ""

        abp = content["about_preview"]
        abp["label"] = request.form.get("about_preview_label", abp["label"])
        abp["title"] = request.form.get("about_preview_title", abp["title"])
        abp["cta_text"] = request.form.get("about_preview_cta_text", abp["cta_text"])
        paras = request.form.getlist("about_preview_paragraph")
        abp["paragraphs"] = [p.strip() for p in paras if p.strip()]

        # Services preview
        svp = content["services_preview"]
        svp["label"] = request.form.get("services_preview_label", svp["label"])
        svp["title"] = request.form.get("services_preview_title", svp["title"])
        svp["subtitle"] = request.form.get("services_preview_subtitle", svp["subtitle"])
        svp["cta_text"] = request.form.get("services_preview_cta_text", svp["cta_text"])
        sp_icons = request.form.getlist("sp_icon")
        sp_titles = request.form.getlist("sp_title")
        sp_texts = request.form.getlist("sp_text")
        sp_prices = request.form.getlist("sp_price")
        sp_link_ids = request.form.getlist("sp_link_id")
        svp["items"] = []
        for i in range(len(sp_titles)):
            if sp_titles[i].strip():
                svp["items"].append({
                    "icon": sp_icons[i].strip() if i < len(sp_icons) else "",
                    "title": sp_titles[i].strip(),
                    "text": sp_texts[i].strip() if i < len(sp_texts) else "",
                    "price": sp_prices[i].strip() if i < len(sp_prices) else "",
                    "link_id": sp_link_ids[i].strip() if i < len(sp_link_ids) else "",
                })

        # Process steps
        ps = content["process_steps"]
        ps["label"] = request.form.get("process_label", ps["label"])
        ps["title"] = request.form.get("process_title", ps["title"])
        step_titles = request.form.getlist("process_step_title")
        step_texts = request.form.getlist("process_step_text")
        ps["steps"] = []
        for i in range(len(step_titles)):
            if step_titles[i].strip():
                ps["steps"].append({
                    "title": step_titles[i].strip(),
                    "text": step_texts[i].strip() if i < len(step_texts) else "",
                })

        # CTA
        cta = content["cta"]
        cta["title"] = request.form.get("cta_title", cta["title"])
        cta["text"] = request.form.get("cta_text", cta["text"])
        cta["button_text"] = request.form.get("cta_button_text", cta["button_text"])

        save_json(CONTENT_FILE, content)
        flash("Главная страница сохранена", "success")
        return redirect(url_for("admin_index"))
    return render_template("admin/edit_index.html", content=content)


# ─── Admin: Обо мне ────────────────────────────────────────────

@app.route("/admin/about", methods=["GET", "POST"])
@login_required
def admin_about():
    content = get_content()
    if request.method == "POST":
        ap = content["about_page"]

        # About page image upload
        about_file = request.files.get("about_image_file")
        if about_file and about_file.filename:
            new_path = save_upload(about_file, "pages")
            if new_path:
                old = ap.get("image", "")
                if old and old.startswith("uploads/"):
                    old_abs = os.path.join(app.static_folder, old)
                    if os.path.exists(old_abs):
                        os.remove(old_abs)
                ap["image"] = new_path
        if request.form.get("about_remove_image") == "1":
            old = ap.get("image", "")
            if old and old.startswith("uploads/"):
                old_abs = os.path.join(app.static_folder, old)
                if os.path.exists(old_abs):
                    os.remove(old_abs)
            ap["image"] = ""

        ap["name"] = request.form.get("name", ap["name"])
        ap["role"] = request.form.get("role", ap["role"])

        # Intro paragraphs
        paragraphs = request.form.getlist("intro_paragraph")
        ap["intro_paragraphs"] = [p.strip() for p in paragraphs if p.strip()]

        # Approach
        approach = ap["approach"]
        approach["label"] = request.form.get("approach_label", approach["label"])
        approach["title"] = request.form.get("approach_title", approach["title"])
        approach["subtitle"] = request.form.get("approach_subtitle", approach["subtitle"])
        a_nums = request.form.getlist("approach_item_num")
        a_titles = request.form.getlist("approach_item_title")
        a_texts = request.form.getlist("approach_item_text")
        approach["items"] = []
        for i in range(len(a_titles)):
            if a_titles[i].strip():
                approach["items"].append({
                    "num": a_nums[i].strip() if i < len(a_nums) else str(i + 1),
                    "title": a_titles[i].strip(),
                    "text": a_texts[i].strip() if i < len(a_texts) else "",
                })

        # Qualifications
        quals = ap["qualifications"]
        quals["label"] = request.form.get("quals_label", quals["label"])
        quals["title"] = request.form.get("quals_title", quals["title"])
        q_years = request.form.getlist("qual_item_year")
        q_titles = request.form.getlist("qual_item_title")
        q_descs = request.form.getlist("qual_item_desc")
        quals["items"] = []
        for i in range(max(len(q_years), len(q_titles), len(q_descs), 0)):
            year = q_years[i].strip() if i < len(q_years) else ""
            title = q_titles[i].strip() if i < len(q_titles) else ""
            desc = q_descs[i].strip() if i < len(q_descs) else ""
            if year or title or desc:
                quals["items"].append({"year": year, "title": title, "desc": desc})

        # Principles
        princ = ap["principles"]
        princ["label"] = request.form.get("princ_label", princ["label"])
        princ["title"] = request.form.get("princ_title", princ["title"])
        p_icons = request.form.getlist("princ_item_icon")
        p_titles = request.form.getlist("princ_item_title")
        p_texts = request.form.getlist("princ_item_text")
        princ["items"] = []
        for i in range(len(p_titles)):
            if p_titles[i].strip():
                princ["items"].append({
                    "icon": p_icons[i].strip() if i < len(p_icons) else "",
                    "title": p_titles[i].strip(),
                    "text": p_texts[i].strip() if i < len(p_texts) else "",
                })

        # CTA
        cta = ap["cta"]
        cta["title"] = request.form.get("cta_title", cta["title"])
        cta["text"] = request.form.get("cta_text", cta["text"])
        cta["button_text"] = request.form.get("cta_button_text", cta["button_text"])

        save_json(CONTENT_FILE, content)
        flash("Страница «Обо мне» сохранена", "success")
        return redirect(url_for("admin_about"))
    return render_template("admin/edit_about.html", content=content)


# ─── Admin: Услуги ─────────────────────────────────────────────

@app.route("/admin/services", methods=["GET", "POST"])
@login_required
def admin_services():
    content = get_content()
    if request.method == "POST":
        sp = content["services_page"]
        sp["label"] = request.form.get("page_label", sp.get("label", ""))
        sp["title"] = request.form.get("page_title", sp["title"])
        sp["subtitle"] = request.form.get("page_subtitle", sp["subtitle"])

        services_list = []
        i = 0
        while request.form.get(f"svc_{i}_title") is not None:
            prefix = f"svc_{i}_"
            svc = {
                "id": request.form.get(f"{prefix}id", "").strip(),
                "title": request.form.get(f"{prefix}title", "").strip(),
                "desc": request.form.get(f"{prefix}desc", "").strip(),
                "icon": request.form.get(f"{prefix}icon", "").strip(),
                "duration": request.form.get(f"{prefix}duration", "").strip(),
                "format": request.form.get(f"{prefix}format", "").strip(),
                "for_whom": request.form.get(f"{prefix}for_whom", "").strip(),
                "highlights": [h.strip() for h in request.form.getlist(f"{prefix}highlight") if h.strip()],
                "paragraphs": [p.strip() for p in request.form.getlist(f"{prefix}paragraph") if p.strip()],
                "list_title": request.form.get(f"{prefix}list_title", "").strip(),
                "list_items": [li.strip() for li in request.form.getlist(f"{prefix}list_item") if li.strip()],
            }
            price_labels = request.form.getlist(f"{prefix}price_label")
            price_values = request.form.getlist(f"{prefix}price_value")
            svc["prices"] = [
                {"label": l.strip(), "value": v.strip()}
                for l, v in zip(price_labels, price_values)
                if l.strip() or v.strip()
            ]
            services_list.append(svc)
            i += 1
        sp["services"] = services_list

        # CTA
        cta = sp["cta"]
        cta["title"] = request.form.get("cta_title", cta["title"])
        cta["text"] = request.form.get("cta_text", cta["text"])
        cta["button_text"] = request.form.get("cta_button_text", cta["button_text"])

        save_json(CONTENT_FILE, content)
        flash("Услуги сохранены", "success")
        return redirect(url_for("admin_services"))
    return render_template("admin/edit_services.html", content=content)


# ─── Admin: Контакты ───────────────────────────────────────────

@app.route("/admin/contact", methods=["GET", "POST"])
@login_required
def admin_contact():
    content = get_content()
    if request.method == "POST":
        cp = content["contact_page"]
        cp["label"] = request.form.get("label", cp.get("label", ""))
        cp["title"] = request.form.get("title", cp["title"])
        cp["subtitle"] = request.form.get("subtitle", cp["subtitle"])

        proc = cp["process"]
        proc["label"] = request.form.get("process_label", proc["label"])
        proc["title"] = request.form.get("process_title", proc["title"])
        step_titles = request.form.getlist("step_title")
        step_texts = request.form.getlist("step_text")
        proc["steps"] = []
        for i in range(len(step_titles)):
            if step_titles[i].strip():
                proc["steps"].append({
                    "title": step_titles[i].strip(),
                    "text": step_texts[i].strip() if i < len(step_texts) else "",
                })

        cta = cp["cta"]
        cta["title"] = request.form.get("cta_title", cta["title"])
        cta["text"] = request.form.get("cta_text", cta["text"])
        cta["button_text"] = request.form.get("cta_button_text", cta["button_text"])

        save_json(CONTENT_FILE, content)
        flash("Страница контактов сохранена", "success")
        return redirect(url_for("admin_contact"))
    return render_template("admin/edit_contact.html", content=content)


# ─── Admin: Статьи ─────────────────────────────────────────────

@app.route("/admin/articles", methods=["GET", "POST"])
@login_required
def admin_articles():
    content = get_content()
    if request.method == "POST":
        acta = content.get("articles_cta", {})
        acta["title"] = request.form.get("cta_title", acta.get("title", ""))
        acta["text"] = request.form.get("cta_text", acta.get("text", ""))
        acta["button_text"] = request.form.get("cta_button_text", acta.get("button_text", ""))
        content["articles_cta"] = acta
        save_json(CONTENT_FILE, content)
        flash("CTA статей сохранён", "success")
        return redirect(url_for("admin_articles"))
    artcls = get_articles()
    return render_template("admin/articles_list.html", articles=artcls, content=content)


def slugify(text):
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    text = text.lower()
    result = []
    for ch in text:
        if ch in translit_map:
            result.append(translit_map[ch])
        elif ch.isalnum() or ch == ' ' or ch == '-':
            result.append(ch)
    slug = '-'.join(''.join(result).split())
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def ensure_unique_slug(slug, items, exclude_item=None):
    """Ensure slug is unique among items. If conflict, append -2, -3, etc."""
    existing = {a["slug"] for a in items if a is not exclude_item}
    if slug not in existing:
        return slug
    counter = 2
    while f"{slug}-{counter}" in existing:
        counter += 1
    return f"{slug}-{counter}"


@app.route("/admin/articles/new", methods=["GET", "POST"])
@login_required
def admin_article_new():
    if request.method == "POST":
        artcls = get_articles()
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip() or slugify(title)
        slug = ensure_unique_slug(slug, artcls)
        image_path = ""
        file = request.files.get("image_file")
        if file and file.filename:
            image_path = save_upload(file, "articles") or ""
        new_article = {
            "slug": slug,
            "title": title,
            "image": image_path,
            "excerpt": request.form.get("excerpt", "").strip(),
            "content": request.form.get("content", "").strip(),
            "published": "published" in request.form,
        }
        artcls.append(new_article)
        save_json(ARTICLES_FILE, artcls)
        flash("Статья создана", "success")
        return redirect(url_for("admin_articles"))
    return render_template("admin/edit_article.html", article=None, is_new=True)


@app.route("/admin/articles/<slug>/edit", methods=["GET", "POST"])
@login_required
def admin_article_edit(slug):
    artcls = get_articles()
    art = next((a for a in artcls if a["slug"] == slug), None)
    if art is None:
        abort(404)

    if request.method == "POST":
        art["title"] = request.form.get("title", art["title"]).strip()
        new_slug = request.form.get("slug", art["slug"]).strip()
        art["slug"] = ensure_unique_slug(new_slug, artcls, exclude_item=art)
        # Handle image upload
        file = request.files.get("image_file")
        if file and file.filename:
            new_image = save_upload(file, "articles")
            if new_image:
                # Delete old image if it was an upload
                old_image = art.get("image", "")
                if old_image and old_image.startswith("uploads/"):
                    old_path = os.path.join(app.static_folder, old_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                art["image"] = new_image
        # Allow removing image
        if request.form.get("remove_image") == "1":
            old_image = art.get("image", "")
            if old_image and old_image.startswith("uploads/"):
                old_path = os.path.join(app.static_folder, old_image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            art["image"] = ""
        art["excerpt"] = request.form.get("excerpt", art["excerpt"]).strip()
        art["content"] = request.form.get("content", art["content"]).strip()
        art["published"] = "published" in request.form
        save_json(ARTICLES_FILE, artcls)
        flash("Статья обновлена", "success")
        return redirect(url_for("admin_articles"))
    return render_template("admin/edit_article.html", article=art, is_new=False)


@app.route("/admin/articles/<slug>/delete", methods=["POST"])
@login_required
def admin_article_delete(slug):
    artcls = get_articles()
    idx = next((i for i, a in enumerate(artcls) if a["slug"] == slug), None)
    if idx is not None:
        art = artcls[idx]
        if art.get("image", "").startswith("uploads/"):
            old_path = os.path.join(app.static_folder, art["image"])
            if os.path.exists(old_path):
                os.remove(old_path)
        artcls.pop(idx)
    save_json(ARTICLES_FILE, artcls)
    flash("Статья удалена", "success")
    return redirect(url_for("admin_articles"))


@app.route("/admin/upload", methods=["POST"])
@login_required
def admin_upload():
    """Generic image upload endpoint. Returns JSON with the relative path."""
    file = request.files.get("file")
    subfolder = request.form.get("subfolder", "")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Файл не выбран"}), 400
    path = save_upload(file, subfolder)
    if not path:
        return jsonify({"ok": False, "error": "Недопустимый формат файла"}), 400
    return jsonify({"ok": True, "path": path})


# ─── Admin: Анонсы ──────────────────────────────────────────────

@app.route("/admin/announcements")
@login_required
def admin_announcements():
    anns = get_announcements()
    return render_template("admin/announcements_list.html", announcements=anns)


@app.route("/admin/announcements/new", methods=["GET", "POST"])
@login_required
def admin_announcement_new():
    if request.method == "POST":
        anns = get_announcements()
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip() or slugify(title)
        slug = ensure_unique_slug(slug, anns)
        image_path = ""
        file = request.files.get("image_file")
        if file and file.filename:
            image_path = save_upload(file, "announcements") or ""
        new_ann = {
            "slug": slug,
            "title": title,
            "date": request.form.get("date", "").strip(),
            "time": request.form.get("time", "").strip(),
            "location": request.form.get("location", "").strip(),
            "description": request.form.get("description", "").strip(),
            "image": image_path,
            "published": "published" in request.form,
        }
        anns.append(new_ann)
        save_json(ANNOUNCEMENTS_FILE, anns)
        flash("Анонс создан", "success")
        return redirect(url_for("admin_announcements"))
    return render_template("admin/edit_announcement.html", announcement=None, is_new=True)


@app.route("/admin/announcements/<slug>/edit", methods=["GET", "POST"])
@login_required
def admin_announcement_edit(slug):
    anns = get_announcements()
    ann = next((a for a in anns if a["slug"] == slug), None)
    if ann is None:
        abort(404)

    if request.method == "POST":
        ann["title"] = request.form.get("title", ann["title"]).strip()
        new_slug = request.form.get("slug", ann["slug"]).strip()
        ann["slug"] = ensure_unique_slug(new_slug, anns, exclude_item=ann)
        ann["date"] = request.form.get("date", ann.get("date", "")).strip()
        ann["time"] = request.form.get("time", ann.get("time", "")).strip()
        ann["location"] = request.form.get("location", ann.get("location", "")).strip()
        ann["description"] = request.form.get("description", ann.get("description", "")).strip()
        # Handle image upload
        file = request.files.get("image_file")
        if file and file.filename:
            new_image = save_upload(file, "announcements")
            if new_image:
                old_image = ann.get("image", "")
                if old_image and old_image.startswith("uploads/"):
                    old_path = os.path.join(app.static_folder, old_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                ann["image"] = new_image
        if request.form.get("remove_image") == "1":
            old_image = ann.get("image", "")
            if old_image and old_image.startswith("uploads/"):
                old_path = os.path.join(app.static_folder, old_image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            ann["image"] = ""
        ann["published"] = "published" in request.form
        save_json(ANNOUNCEMENTS_FILE, anns)
        flash("Анонс обновлён", "success")
        return redirect(url_for("admin_announcements"))
    return render_template("admin/edit_announcement.html", announcement=ann, is_new=False)


@app.route("/admin/announcements/<slug>/delete", methods=["POST"])
@login_required
def admin_announcement_delete(slug):
    anns = get_announcements()
    idx = next((i for i, a in enumerate(anns) if a["slug"] == slug), None)
    if idx is not None:
        ann = anns[idx]
        if ann.get("image", "").startswith("uploads/"):
            old_path = os.path.join(app.static_folder, ann["image"])
            if os.path.exists(old_path):
                os.remove(old_path)
        anns.pop(idx)
    save_json(ANNOUNCEMENTS_FILE, anns)
    flash("Анонс удалён", "success")
    return redirect(url_for("admin_announcements"))


# ─── Admin: Документы ───────────────────────────────────────────

@app.route("/admin/documents", methods=["GET", "POST"])
@login_required
def admin_documents():
    content = get_content()
    dp = content.setdefault("documents_page", {
        "title": "Документы и сертификаты",
        "subtitle": "",
        "button_text": "Смотреть документы",
        "docs": [],
    })

    if request.method == "POST":
        dp["title"] = request.form.get("title", dp["title"]).strip()
        dp["subtitle"] = request.form.get("subtitle", dp["subtitle"]).strip()
        dp["button_text"] = request.form.get("button_text", dp["button_text"]).strip()

        # Reorder / update existing items
        existing_ids = request.form.getlist("doc_id")
        existing_titles = request.form.getlist("doc_title")
        new_items = []
        old_map = {str(i): item for i, item in enumerate(dp["docs"])}
        for idx, doc_id in enumerate(existing_ids):
            if doc_id in old_map:
                item = old_map[doc_id]
                if idx < len(existing_titles):
                    item["title"] = existing_titles[idx].strip()
                new_items.append(item)

        # Handle deletions
        delete_ids = request.form.getlist("delete_doc")
        for did in delete_ids:
            if did in old_map:
                img = old_map[did].get("image", "")
                if img and img.startswith("uploads/"):
                    abs_path = os.path.join(app.static_folder, img)
                    if os.path.exists(abs_path):
                        os.remove(abs_path)
        new_items = [item for i, item in enumerate(new_items)
                     if str(i) not in delete_ids and str(existing_ids[i] if i < len(existing_ids) else "") not in delete_ids]

        # Handle new file uploads
        new_files = request.files.getlist("new_files")
        new_file_titles = request.form.getlist("new_file_title")
        for i, f in enumerate(new_files):
            if f and f.filename:
                path = save_upload(f, "documents")
                if path:
                    title = new_file_titles[i].strip() if i < len(new_file_titles) else ""
                    new_items.append({"image": path, "title": title})

        dp["docs"] = new_items
        save_json(CONTENT_FILE, content)
        flash("Документы сохранены", "success")
        return redirect(url_for("admin_documents"))

    return render_template("admin/edit_documents.html", content=content)


# ─── Deploy: build & push ──────────────────────────────────────

deploy_status = {"running": False, "log": [], "last_result": None}


def run_deploy():
    """Build static site and push to GitHub in a background thread."""
    deploy_status["running"] = True
    deploy_status["log"] = []
    deploy_status["last_result"] = None
    log = deploy_status["log"]
    project_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        log.append("🔨 Сборка статического сайта...")
        result = subprocess.run(
            ["python", "freeze.py"],
            capture_output=True, text=True, cwd=project_dir, timeout=120
        )
        if result.returncode != 0:
            log.append(f"❌ Ошибка сборки:\n{result.stderr}")
            deploy_status["last_result"] = "error"
            return
        log.append("✅ Сборка завершена")

        log.append("📦 Коммит изменений...")
        subprocess.run(["git", "add", "-A"], capture_output=True, text=True, cwd=project_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        result = subprocess.run(
            ["git", "commit", "-m", f"Обновление контента — {timestamp}"],
            capture_output=True, text=True, cwd=project_dir
        )
        if result.returncode != 0 and "nothing to commit" in result.stdout:
            log.append("ℹ️ Нет изменений для коммита")
        elif result.returncode != 0:
            log.append(f"❌ Ошибка git commit:\n{result.stderr}")
            deploy_status["last_result"] = "error"
            return
        else:
            log.append("✅ Изменения закоммичены")

        log.append("🚀 Отправка на GitHub...")
        result = subprocess.run(
            ["git", "push", "-u", "origin", "HEAD:main"],
            capture_output=True, text=True, cwd=project_dir, timeout=60
        )
        if result.returncode != 0:
            log.append(f"❌ Ошибка git push:\n{result.stderr}")
            deploy_status["last_result"] = "error"
            return
        log.append("✅ Отправлено в GitHub")
        log.append("🎉 Деплой завершён! GitHub Actions опубликует сайт через 1-2 минуты.")
        deploy_status["last_result"] = "success"

    except subprocess.TimeoutExpired:
        log.append("❌ Таймаут операции")
        deploy_status["last_result"] = "error"
    except Exception as e:
        log.append(f"❌ Ошибка: {e}")
        deploy_status["last_result"] = "error"
    finally:
        deploy_status["running"] = False


@app.route("/admin/deploy", methods=["POST"])
@login_required
def admin_deploy():
    if deploy_status["running"]:
        return jsonify({"ok": False, "error": "Деплой уже выполняется"}), 409
    thread = threading.Thread(target=run_deploy, daemon=True)
    thread.start()
    return jsonify({"ok": True})


@app.route("/admin/deploy/status")
@login_required
def admin_deploy_status():
    return jsonify({
        "running": deploy_status["running"],
        "log": deploy_status["log"],
        "result": deploy_status["last_result"],
    })


# ─── Error handlers ────────────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
