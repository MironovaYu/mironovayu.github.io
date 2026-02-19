"""
Генерация статических файлов для GitHub Pages.
Запуск: python freeze.py
Результат будет в папке build/
"""
import shutil
import warnings
from flask_frozen import Freezer
from app import app, get_articles

warnings.filterwarnings("ignore", "Nothing frozen for endpoints")

app.config["FREEZER_DESTINATION"] = "build"
app.config["FREEZER_RELATIVE_URLS"] = True
app.config["FREEZER_IGNORE_MIMETYPE_WARNINGS"] = True

freezer = Freezer(app, with_no_argument_rules=False)


@freezer.register_generator
def index():
    yield {}


@freezer.register_generator
def about():
    yield {}


@freezer.register_generator
def services():
    yield {}


@freezer.register_generator
def contact():
    yield {}


@freezer.register_generator
def articles():
    yield {}


@freezer.register_generator
def documents():
    yield {}


@freezer.register_generator
def announcements():
    yield {}


@freezer.register_generator
def article():
    """Генерирует URL для каждой опубликованной статьи."""
    for art in get_articles():
        if art.get("published"):
            yield {"slug": art["slug"]}


if __name__ == "__main__":
    freezer.freeze()
    # Remove admin pages from build if accidentally generated
    admin_dir = "build/admin"
    shutil.rmtree(admin_dir, ignore_errors=True)
    print("✅ Сайт успешно собран в папку build/")
