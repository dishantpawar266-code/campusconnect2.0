import os
from flask import Flask, render_template, redirect, url_for, session
from config import Config
from database import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.faculty import faculty_bp
    from routes.club import club_bp
    from routes.common import common_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(club_bp)
    app.register_blueprint(common_bp)

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    # Auto-create tables and seed initial data if running on online DB or first run
    with app.app_context():
        try:
            db.create_all()
            from seed import seed_database
            seed_database()
        except Exception as e:
            app.logger.warning(f"Database auto-init status: {e}")

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
