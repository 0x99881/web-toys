from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import abort, flash, redirect, render_template, request, url_for

from .store import DISABLED, ENABLED, ExcelStore


# ?????????????????????????
def register_routes(app, store: ExcelStore) -> None:
    @app.context_processor
    def inject_shared_data() -> dict[str, Any]:
        return {
            "excel_filename": store.workbook_path.name,
            "quick_scores": store.get_quick_scores(),
            "asset_version": "20260403-3",
        }

    @app.after_request
    def disable_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/")
    def index():
        return redirect(url_for("score_entry"))

    @app.route("/scores")
    def score_entry():
        return render_template(
            "scores.html",
            active_members=store.get_active_members(),
            score_summary=store.get_score_summary(),
            selected_date=datetime.now().strftime("%Y-%m-%d"),
        )

    @app.post("/scores/save")
    def save_scores():
        selected_date = request.form.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        entries = []
        for member in store.get_active_members():
            name = member["name"]
            score_text = request.form.get(f"score_{name}", "").strip()
            if score_text:
                try:
                    int(score_text)
                except ValueError:
                    flash(f"{name} ?????????", "error")
                    return redirect(url_for("score_entry"))
            entries.append(
                {
                    "name": name,
                    "score": score_text,
                    "before_balance": request.form.get(f"before_{name}", "").strip(),
                    "after_balance": request.form.get(f"after_{name}", "").strip(),
                    "manual_wear": request.form.get(f"manual_wear_{name}", "").strip(),
                    "income": request.form.get(f"income_{name}", "").strip(),
                }
            )
        try:
            result = store.save_scores_and_wear(selected_date, entries)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("score_entry"))
        flash(
            f"??? {result['target_column']}????? {result['wear_rows_added']} ??????????? {result['window_size']} ??????",
            "success",
        )
        return redirect(url_for("score_entry"))

    @app.route("/wear")
    def wear_entry():
        return render_template("wear.html", wear_sheet=store.get_wear_sheet_view())

    @app.route("/profit-calendar")
    def profit_calendar():
        members = store.get_members()
        if not members:
            abort(404)
        member_names = [item["name"] for item in members]
        selectable_names = ["all", *member_names]
        selected_name = request.args.get("name", "").strip() or "all"
        if selected_name not in selectable_names:
            selected_name = "all"
        year = request.args.get("year", type=int) or datetime.now().year
        month = request.args.get("month", type=int) or datetime.now().month
        calendar_data = store.get_member_profit_calendar(selected_name, year, month)
        return render_template(
            "profit_calendar.html",
            members=members,
            selectable_names=selectable_names,
            selected_name=selected_name,
            calendar_data=calendar_data,
        )

    @app.route("/members")
    def members():
        all_members = store.get_members()
        enabled_count = sum(1 for item in all_members if item["status"] == ENABLED)
        return render_template("members.html", members=all_members, enabled_count=enabled_count)

    @app.post("/members/add")
    def add_member():
        name = request.form.get("name", "").strip()
        note = request.form.get("note", "").strip()
        try:
            store.add_member(name, note)
            flash(f"??????{name}", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("members"))

    @app.post("/members/update")
    def update_member():
        name = request.form.get("name", "").strip()
        note = request.form.get("note", "").strip()
        status = request.form.get("status", "").strip()
        try:
            store.update_member(name, note, status=status)
            if status == ENABLED:
                flash(f"??????{name}", "success")
            elif status == DISABLED:
                flash(f"??????{name}", "success")
            else:
                flash(f"??????{name}", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("members"))

    @app.route("/members/<name>")
    def member_detail(name: str):
        year = request.args.get("year", type=int) or datetime.now().year
        month = request.args.get("month", type=int) or datetime.now().month
        return redirect(url_for("profit_calendar", name=name, year=year, month=month))
