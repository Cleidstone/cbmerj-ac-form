import os
import io
import json
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, send_file, flash, jsonify)

from database import init_db, has_submitted, save_submission, get_all_submissions, get_submission, delete_submission
from calculator import calculate_btu, recommend_ac, get_emop_codes, STANDARD_SIZES, ROOM_TYPE_FACTORS
from report import generate_unit_report, generate_consolidated_report
from obm_list import OBM_LIST, OBM_GROUPS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cbmerj-bm4-secret-2025-change-in-prod')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'bm4admin2025')

init_db()

OBM_DICT = dict(OBM_LIST)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    return render_template('form.html',
                           obm_groups=OBM_GROUPS,
                           room_types=ROOM_TYPE_FACTORS,
                           standard_sizes=STANDARD_SIZES)


@app.route('/check-unit', methods=['POST'])
def check_unit():
    obm_code = request.json.get('obm_code', '')
    submitted = has_submitted(obm_code)
    obm_name = OBM_DICT.get(obm_code, '')
    return jsonify({'submitted': submitted, 'obm_name': obm_name})


@app.route('/submit', methods=['POST'])
def submit():
    import traceback
    try:
        obm_code = request.form.get('obm_code', '').strip()
        obm_name = OBM_DICT.get(obm_code, request.form.get('obm_name', obm_code))

        if not obm_code:
            flash('Selecione sua unidade antes de enviar.')
            return redirect(url_for('index'))

        if has_submitted(obm_code):
            return render_template('already_submitted.html', obm_name=obm_name)

        # Montar lista de ambientes
        rooms = []
        room_count = int(request.form.get('room_count', 0) or 0)

        for i in range(room_count):
            name = request.form.get(f'room_{i}_name', '').strip()
            if not name:
                continue

            try:
                length = float(request.form.get(f'room_{i}_length', 0) or 0)
                width  = float(request.form.get(f'room_{i}_width', 0) or 0)
                height = float(request.form.get(f'room_{i}_height', 2.80) or 2.80)
            except (ValueError, TypeError):
                length, width, height = 0.0, 0.0, 2.80

            area   = round(length * width, 2)
            people = int(request.form.get(f'room_{i}_people', 0) or 0)
            appl   = int(request.form.get(f'room_{i}_appliances', 0) or 0)
            lamps  = int(request.form.get(f'room_{i}_lamps', 0) or 0)
            win_m  = 1 if request.form.get(f'room_{i}_window_morning') else 0
            win_a  = 1 if request.form.get(f'room_{i}_window_afternoon') else 0
            rtype  = request.form.get(f'room_{i}_type', 'standard')

            btu = calculate_btu(area, people, appl, lamps, win_m, win_a, rtype)
            rec_size, rec_qty = recommend_ac(btu)

            # Tamanho selecionado — aceita numérico direto ou fallback para recomendado
            sel_size_raw = request.form.get(f'room_{i}_selected_size', '').strip()
            try:
                sel_size = int(sel_size_raw) if sel_size_raw and sel_size_raw != 'custom' else rec_size
            except ValueError:
                sel_size = rec_size

            try:
                sel_qty = int(request.form.get(f'room_{i}_selected_qty', '') or rec_qty)
            except (ValueError, TypeError):
                sel_qty = rec_qty

            justification = request.form.get(f'room_{i}_justification', '').strip()

            rooms.append({
                'name': name,
                'length': length,
                'width': width,
                'height': height,
                'area': area,
                'people': people,
                'appliances': appl,
                'lamps': lamps,
                'window_morning': win_m,
                'window_afternoon': win_a,
                'room_type': rtype,
                'btu_calculated': round(btu, 2),
                'recommended_size': int(rec_size),
                'recommended_qty': int(rec_qty),
                'selected_size': int(sel_size),
                'selected_qty': int(sel_qty),
                'justification': justification,
            })

        if not rooms:
            flash('Adicione pelo menos um ambiente antes de enviar.')
            return redirect(url_for('index'))

        data = {
            'obm_code': obm_code,
            'obm_name': obm_name,
            'commander_name': request.form.get('commander_name', '').strip(),
            'contact_email': request.form.get('contact_email', '').strip(),
            'contact_phone': request.form.get('contact_phone', '').strip(),
            'rooms': rooms,
            'observations': request.form.get('observations', '').strip(),
        }

        sub_id = save_submission(data)
        return render_template('success.html', sub_id=sub_id, obm_name=obm_name,
                               rooms=rooms, total=sum(r['selected_qty'] for r in rooms))

    except Exception as e:
        traceback.print_exc()  # aparece nos logs do Render
        return render_template('error.html', error=str(e)), 500


@app.route('/download/<int:sub_id>')
def download_report(sub_id):
    sub = get_submission(sub_id)
    if not sub:
        return 'Submissão não encontrada.', 404
    excel = generate_unit_report(sub)
    safe_name = sub['obm_code'].replace('/', '_').replace(' ', '_')
    return send_file(
        io.BytesIO(excel),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Memoria_Calculo_{safe_name}.xlsx'
    )


# ── Admin ──────────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Senha incorreta.'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    submissions = get_all_submissions()
    for sub in submissions:
        rooms = json.loads(sub['rooms_json'])
        sub['room_count'] = len(rooms)
        sub['total_units'] = sum(r['selected_qty'] for r in rooms)
    return render_template('admin_dashboard.html', submissions=submissions,
                           total_subs=len(submissions),
                           obm_total=len(OBM_LIST))


@app.route('/admin/download/<int:sub_id>')
@admin_required
def admin_download(sub_id):
    sub = get_submission(sub_id)
    if not sub:
        return 'Não encontrado.', 404
    excel = generate_unit_report(sub)
    safe_name = sub['obm_code'].replace('/', '_').replace(' ', '_')
    return send_file(
        io.BytesIO(excel),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Memoria_Calculo_{safe_name}.xlsx'
    )


@app.route('/admin/consolidated')
@admin_required
def admin_consolidated():
    submissions = get_all_submissions()
    excel = generate_consolidated_report(submissions)
    return send_file(
        io.BytesIO(excel),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='CBMERJ_Consolidado_ACs.xlsx'
    )


@app.route('/admin/delete/<string:obm_code>', methods=['POST'])
@admin_required
def admin_delete(obm_code):
    delete_submission(obm_code)
    flash(f'Submissão de {OBM_DICT.get(obm_code, obm_code)} removida. A unidade pode preencher novamente.')
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
