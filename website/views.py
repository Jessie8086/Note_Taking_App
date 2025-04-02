from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text
from .models import Note, Tag
from . import db
from datetime import datetime
import json

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        note = request.form.get('note')
        tag_ids_str = request.form.get('tags')
        selected_tag_ids = tag_ids_str.split(',') if tag_ids_str else []

        if len(note) < 1:
            flash('Note is too short!', category = 'error')
        else:
            new_note = Note(data=note, user_id=current_user.id)
            # allocate new tags
            if selected_tag_ids:
                for tag_id in selected_tag_ids:
                    tag = Tag.query.get(int(tag_id))
                    if tag and tag.user_id == current_user.id:
                        new_note.tags.append(tag)

            db.session.add(new_note)
            db.session.commit()
            flash('Note added!', category = 'success')

    all_tags = Tag.query.filter_by(user_id=current_user.id).all()
    return render_template("home.html", user=current_user, tags=all_tags)


@views.route('/delete-note', methods=['POST'])
def delete_note():
    note = json.loads(request.data)
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()
            
    return jsonify({})


@views.route('/delete-tag-global', methods=['POST'])
@login_required
def delete_tag_global():
    data = request.get_json()
    tag_id = data.get('tag_id')

    tag = Tag.query.get(tag_id)

    if tag and tag.user_id == current_user.id:
        # Remove tag from all notes first
        for note in tag.notes:
            note.tags.remove(tag)
        db.session.commit()

        # Now delete the tag itself
        db.session.delete(tag)
        db.session.commit()

        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Tag not found or unauthorized'})



@views.route('/edit-note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        flash("You are not authorized to edit this note.", category='error')
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        new_data = request.form.get('note')
        tag_ids_str = request.form.get('tags')
        selected_tag_ids = tag_ids_str.split(',') if tag_ids_str else []

        if len(new_data) < 1:
            flash('Note is too short!', category='error')
        else:
            note.data = new_data

            note.tags.clear()
            for tag_id in selected_tag_ids:
                tag = Tag.query.get(int(tag_id))
                if tag and tag.user_id == current_user.id:
                    note.tags.append(tag)

            db.session.commit()
            flash('Note updated!', category='success')
            return redirect(url_for('views.home'))

    all_tags = Tag.query.filter_by(user_id=current_user.id).all()
    note_tag_ids = [tag.id for tag in note.tags]

    note_tag_dicts = [{'id': tag.id, 'name': tag.name} for tag in note.tags]

    return render_template("edit_note.html",
                            user=current_user,
                            note=note,
                            tags=all_tags,
                            note_tag_ids=note_tag_ids,
                            note_tag_dicts=note_tag_dicts)




@views.route('/search-notes', methods=['GET', 'POST'])
@login_required
def search_notes():
    notes = []
    filter_summary = []
    start_date = end_date = keyword = ""
    selected_tag_ids = []

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        keyword = request.form.get('keyword')
        selected_tag_ids = request.form.getlist('tags')

        if not start_date and not end_date and not keyword and not selected_tag_ids:
            flash("Please specify at least one search condition.", category='error')
        else:
            sql = "SELECT DISTINCT n.* FROM note n LEFT JOIN note_tags nt ON n.id = nt.note_id "
            sql += "LEFT JOIN tag t ON t.id = nt.tag_id WHERE n.user_id = :uid"
            params = {"uid": current_user.id}

            if start_date and end_date:
                sql += " AND DATE(n.date) BETWEEN :start AND :end"
                params["start"] = start_date
                params["end"] = end_date
                filter_summary.append(f"Date range: {start_date} to {end_date}")

            if keyword:
                sql += " AND LOWER(n.data) LIKE LOWER(:kw)"
                params["kw"] = f"%{keyword}%"
                filter_summary.append(f"Keyword: '{keyword}'")


            if selected_tag_ids:
                tag_placeholders = ','.join([f":tag{i}" for i in range(len(selected_tag_ids))])
                sql += f" AND t.id IN ({tag_placeholders})"
                for i, tid in enumerate(selected_tag_ids):
                    params[f"tag{i}"] = int(tid)
                tag_names = [Tag.query.get(int(tid)).name for tid in selected_tag_ids if Tag.query.get(int(tid))]
                filter_summary.append(f"Tags: {', '.join(tag_names)}")

            sql += " ORDER BY n.date DESC"
            stmt = text(sql)
            result = db.session.execute(stmt, params)
            notes_raw = result.mappings().all()
        
            for row in notes_raw:
                note_dict = dict(row)
                note_dict["date"] = note_dict["date"] if isinstance(note_dict["date"], datetime) else datetime.fromisoformat(str(note_dict["date"]))
                notes.append(note_dict)

            # convert date field to datetime object for rendering
            for note in notes:
                note["date"] = note["date"] if isinstance(note["date"], datetime) else datetime.fromisoformat(str(note["date"]))

    all_tags = Tag.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "search_notes.html",
        user=current_user,
        notes=notes,
        all_tags=all_tags,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        selected_tag_ids=selected_tag_ids,
        filter_summary=filter_summary
    )



@views.route('/delete-note-direct', methods=['POST'])
@login_required
def delete_note_direct():
    note_id = request.form.get('noteId')
    note = Note.query.get(note_id)
    if note and note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()
        flash("Note deleted!", category='success')
    else:
        flash("Note not found or not yours.", category='error')
    return redirect(url_for('views.search_notes'))




@views.route('/create-tag', methods=['POST'])
@login_required
def create_tag():
    from .models import Tag
    data = request.get_json()
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Empty tag name'})

    existing = Tag.query.filter_by(name=name, user_id=current_user.id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Tag already exists'})

    new_tag = Tag(name=name, user_id=current_user.id)
    db.session.add(new_tag)
    db.session.commit()

    return jsonify({'success': True, 'id': new_tag.id})

