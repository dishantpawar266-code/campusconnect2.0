from flask import Blueprint, render_template, jsonify, request, abort
from database import db
from models import Notice, ExternalResource, Department, Division
from routes.auth import login_required

common_bp = Blueprint('common', __name__)

@common_bp.route('/notice/<int:notice_id>')
@login_required
def notice_detail(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        abort(404)
    return render_template('notice_detail.html', notice=notice)

@common_bp.route('/resources')
@login_required
def resources():
    category = request.args.get('category')
    if category:
        resources_list = ExternalResource.query.filter_by(category=category).all()
    else:
        resources_list = ExternalResource.query.all()
    return render_template('resources.html', resources=resources_list, selected_category=category)

@common_bp.route('/api/departments')
def get_departments():
    depts = Department.query.all()
    return jsonify([{'id': d.id, 'name': d.name, 'code': d.code} for d in depts])

@common_bp.route('/api/divisions/<int:department_id>')
def get_divisions(department_id):
    divisions = Division.query.filter_by(department_id=department_id).all()
    return jsonify([{'id': d.id, 'name': d.name} for d in divisions])
