"""Life OS API helpers (sport, food, economy, notes, calendar, health). Wraps database.py."""
from __future__ import annotations

from datetime import date, datetime

import database as db


def _today() -> str:
    return date.today().isoformat()


def map_sport(row: dict) -> dict:
    return {
        "id": str(row.get("id")),
        "sportType": row.get("sport_type") or "running",
        "sportName": row.get("name") or "",
        "icon": row.get("icon") or "🏃",
        "durationMinutes": int(row.get("duration_minutes") or 0),
        "caloriesBurned": int(row.get("calories_burned") or 0),
        "intensity": "moderate",
        "notes": row.get("notes") or "",
        "date": row.get("last_done") or row.get("created_at") or _today(),
        "sportXpEarned": int(row.get("xp_reward") or 0),
        "done": bool(row.get("done_today")),
    }


def map_meal(row: dict) -> dict:
    mt = (row.get("meal_type") or "snack").lower()
    if mt not in ("breakfast", "lunch", "dinner", "snack"):
        mt = "snack"
    return {
        "id": str(row.get("id")),
        "mealType": mt,
        "foodName": row.get("name") or "",
        "icon": row.get("icon") or "🍽️",
        "portion": float(row.get("serving") or 1),
        "calories": int(row.get("calories") or 0),
        "protein": float(row.get("protein") or 0),
        "carbs": float(row.get("carbs") or 0),
        "fat": float(row.get("fat") or 0),
        "date": row.get("log_date") or _today(),
    }


def map_tx(row: dict) -> dict:
    t = row.get("type") or "expense"
    if t not in ("income", "expense"):
        t = "expense" if t in ("pengeluaran", "out") else "income"
    return {
        "id": str(row.get("id")),
        "type": t,
        "category": row.get("category") or "",
        "amount": float(row.get("amount") or 0),
        "date": row.get("date") or row.get("date_str") or _today(),
        "notes": row.get("notes") or "",
        "name": row.get("name") or "",
        "icon": row.get("icon") or "💰",
    }


def map_debt(row: dict) -> dict:
    total = float(row.get("amount") or row.get("total_amount") or 0)
    remaining = float(row.get("remaining") or row.get("remaining_amount") or total)
    return {
        "id": str(row.get("id")),
        "title": row.get("name") or "",
        "type": "payable",
        "totalAmount": total,
        "remainingAmount": remaining,
        "dueDate": row.get("due_date") or "",
        "notes": row.get("notes") or "",
        "isPaid": bool(row.get("paid") or row.get("is_paid")),
    }


def map_note(row: dict) -> dict:
    return {
        "id": str(row.get("id")),
        "folderId": str(row["folder_id"]) if row.get("folder_id") else None,
        "title": row.get("title") or "",
        "content": row.get("content") or "",
        "isPinned": bool(row.get("pinned")),
        "isArchived": bool(row.get("archived") or row.get("is_archived")),
        "zoomLevel": int(row.get("zoom_level") or 100),
        "updatedAt": row.get("updated_at") or "",
    }


def map_folder(row: dict) -> dict:
    return {
        "id": str(row.get("id")),
        "name": row.get("name") or "",
        "icon": row.get("icon") or "📁",
        "parentId": str(row["parent_id"]) if row.get("parent_id") else None,
    }


def map_reminder(row: dict) -> dict:
    dt = str(row.get("reminder_datetime") or "")
    time = dt[11:16] if len(dt) >= 16 else (row.get("time") or "08:00")
    rep = (row.get("repeat_type") or "none").lower()
    if rep not in ("none", "daily", "weekdays", "weekly"):
        rep = "none"
    return {
        "id": str(row.get("id")),
        "title": row.get("title") or "",
        "time": time,
        "repeat": rep,
        "isActive": not bool(row.get("triggered")),
        "sound": row.get("sound_type") or "bell",
    }


def map_health(row: dict) -> dict:
    mood = (row.get("mood") or "good").lower()
    if mood not in ("great", "good", "neutral", "tired", "stressed"):
        mood = "good"
    return {
        "id": str(row.get("id")),
        "date": row.get("log_date") or _today(),
        "steps": int(row.get("steps") or 0),
        "sleepHours": float(row.get("sleep_hours") or 0),
        "weightKg": row.get("weight_kg"),
        "heartRate": int(row.get("resting_hr") or 0) or None,
        "mood": mood,
        "notes": row.get("notes") or "",
    }


def map_pomo(row: dict) -> dict:
    mins = int(row.get("duration_minutes") or row.get("minutes") or 0)
    return {
        "id": str(row.get("id")),
        "durationMinutes": mins,
        "completedAt": row.get("completed_at") or row.get("created_at") or "",
        "xpEarned": int(row.get("xp") or mins * 2),
        "goldEarned": int(row.get("gold") or 0),
        "label": row.get("task_name") or row.get("label") or "",
    }


def map_supply(row: dict) -> dict:
    return {
        "id": str(row.get("id")),
        "name": row.get("name") or "",
        "category": row.get("category") or "",
        "unit": row.get("unit") or "pcs",
        "stock": float(row.get("stock") or 0),
        "minStock": float(row.get("min_stock") or 0),
        "price": float(row.get("price") or 0),
        "location": row.get("location") or "",
        "notes": row.get("notes") or "",
    }


def map_task_folder(row: dict) -> dict:
    return {
        "id": str(row.get("id")),
        "name": row.get("name") or "",
        "icon": row.get("icon") or "📁",
        "mode": row.get("mode") or "habit",
        "color": "#10b981",
    }


def snapshot(uid: int) -> dict:
    try:
        sports = [map_sport(r) for r in db.get_sport_activities(uid)]
    except Exception:
        sports = []
    try:
        meals = [map_meal(r) for r in db.get_food_logs(uid)]
    except Exception:
        meals = []
    try:
        goal = int(db.get_water_goal(uid) or 2500)
        total = int(db.get_water_total(uid) or 0)
        water = {"date": _today(), "amountMl": total, "targetMl": goal}
    except Exception:
        water = {"date": _today(), "amountMl": 0, "targetMl": 2500}
    try:
        txs = [map_tx(r) for r in db.get_economy_items(uid)]
    except Exception:
        txs = []
    try:
        debts = [map_debt(r) for r in db.get_debts(uid, include_paid=True)]
    except Exception:
        debts = []
    try:
        notes = [map_note(r) for r in db.get_notes(uid, include_archived=True)]
    except Exception:
        notes = []
    try:
        note_folders = [map_folder(r) for r in db.get_note_folders(uid)]
    except Exception:
        note_folders = []
    try:
        rems = [map_reminder(r) for r in db.get_reminders(uid)]
    except Exception:
        rems = []
    try:
        health = [map_health(r) for r in db.get_health_logs(uid, days=30)]
    except Exception:
        health = []
    try:
        pomos = [map_pomo(r) for r in db.get_recent_pomodoros(uid, limit=20)]
    except Exception:
        pomos = []
    try:
        cal = db.get_calendar_notes(uid) or []
        calendarNotes = [
            {"date": r.get("note_date") or r.get("date"), "note": r.get("note") or ""}
            for r in cal
        ]
    except Exception:
        calendarNotes = []
    try:
        supplies = [map_supply(r) for r in db.get_supplies_items(uid)]
    except Exception:
        supplies = []
    try:
        task_folders = []
        for mode in ("habit", "daily", "todo", "sport"):
            task_folders.extend(map_task_folder(r) for r in (db.get_task_folders(uid, mode) or []))
    except Exception:
        task_folders = []
    try:
        savings = [
            {
                "id": str(r.get("id")),
                "name": r.get("name") or "",
                "icon": r.get("icon") or "🏦",
                "targetAmount": float(r.get("target_amount") or 0),
                "currentAmount": float(r.get("current_amount") or 0),
                "targetDate": r.get("target_date") or "",
                "notes": r.get("notes") or "",
            }
            for r in (db.get_savings(uid) or [])
        ]
    except Exception:
        savings = []
    try:
        investments = [
            {
                "id": str(r.get("id")),
                "name": r.get("name") or "",
                "icon": r.get("icon") or "📈",
                "amount": float(r.get("amount") or 0),
                "notes": r.get("notes") or "",
            }
            for r in (db.get_investments(uid) or [])
        ]
    except Exception:
        investments = []
    try:
        subscriptions = [
            {
                "id": str(r.get("id")),
                "name": r.get("name") or "",
                "icon": r.get("icon") or "📅",
                "amount": float(r.get("amount") or 0),
                "dueDate": r.get("due_date") or "",
                "period": r.get("period") or "monthly",
                "notes": r.get("notes") or "",
            }
            for r in (db.get_subscriptions(uid) or [])
        ]
    except Exception:
        subscriptions = []
    try:
        debt_notes = [
            {
                "id": str(r.get("id")),
                "personName": r.get("person_name") or "",
                "amount": float(r.get("amount") or 0),
                "date": r.get("date") or "",
                "notes": r.get("notes") or "",
                "status": r.get("status") or "unpaid",
            }
            for r in (db.get_debt_notes(uid) or [])
        ]
    except Exception:
        debt_notes = []
    return {
        "sportLogs": sports,
        "mealLogs": meals,
        "waterLog": water,
        "transactions": txs,
        "debts": debts,
        "notes": notes,
        "noteFolders": note_folders,
        "reminders": rems,
        "healthLogs": health,
        "pomodoroSessions": pomos,
        "calendarNotes": calendarNotes,
        "supplies": supplies,
        "taskFolders": task_folders,
        "savings": savings,
        "investments": investments,
        "subscriptions": subscriptions,
        "debtNotes": debt_notes,
    }


def handle_get(path: str, uid: int):
    if path == "/api/sport":
        return {"ok": True, "sportLogs": snapshot(uid)["sportLogs"]}
    if path == "/api/food/logs":
        return {"ok": True, "mealLogs": snapshot(uid)["mealLogs"]}
    if path == "/api/food/items":
        try:
            items = db.get_food_items(uid, include_default=True) or []
        except Exception:
            items = []
        return {
            "ok": True,
            "items": [
                {
                    "id": str(r.get("id")),
                    "name": r.get("name") or "",
                    "icon": r.get("icon") or "🍽️",
                    "calories": int(r.get("calories") or 0),
                    "protein": float(r.get("protein") or 0),
                    "carbs": float(r.get("carbs") or 0),
                    "fat": float(r.get("fat") or 0),
                    "isCustom": bool(r.get("is_custom")),
                }
                for r in items
            ],
        }
    if path == "/api/nutrition/goals":
        try:
            g = db.get_nutrition_goals(uid) or {}
        except Exception:
            g = {}
        return {
            "ok": True,
            "goals": {
                "calories": int(g.get("daily_calories") or 2000),
                "protein": float(g.get("daily_protein") or 50),
                "carbs": float(g.get("daily_carbs") or 250),
                "fat": float(g.get("daily_fat") or 70),
            },
        }
    if path == "/api/water":
        s = snapshot(uid)
        return {"ok": True, "waterLog": s["waterLog"]}
    if path == "/api/economy":
        return {"ok": True, "transactions": snapshot(uid)["transactions"]}
    if path == "/api/debts":
        return {"ok": True, "debts": snapshot(uid)["debts"]}
    if path == "/api/notes":
        s = snapshot(uid)
        return {"ok": True, "notes": s["notes"], "noteFolders": s["noteFolders"]}
    if path == "/api/reminders":
        return {"ok": True, "reminders": snapshot(uid)["reminders"]}
    if path == "/api/health":
        return {"ok": True, "healthLogs": snapshot(uid)["healthLogs"]}
    if path == "/api/health/bmi":
        try:
            bmi = db.get_user_bmi_settings(uid) or {}
        except Exception:
            bmi = {}
        return {"ok": True, "bmi": bmi}
    if path == "/api/pomodoro":
        return {"ok": True, "pomodoroSessions": snapshot(uid)["pomodoroSessions"]}
    if path == "/api/calendar":
        return {"ok": True, "calendarNotes": snapshot(uid)["calendarNotes"]}
    if path == "/api/supplies":
        return {"ok": True, "items": snapshot(uid)["supplies"]}
    if path.startswith("/api/templates/"):
        mode = path.split("/api/templates/", 1)[-1] or "habit"
        if mode in ("apply",):
            return None
        try:
            items = db.get_templates_by_mode(mode) or []
        except Exception:
            items = []
        return {"ok": True, "templates": items}
    if path == "/api/task-folders":
        return {"ok": True, "taskFolders": snapshot(uid)["taskFolders"]}
    if path == "/api/holidays":
        from datetime import date as _d
        year = _d.today().year
        try:
            import holidays as hol
            data = hol.get_holidays_for_year(year) or {}
        except Exception:
            data = {}
        items = []
        for ds, names in data.items():
            if isinstance(names, (list, tuple)) and len(names) >= 2:
                name_id, name_en = names[0], names[1]
            else:
                name_id = name_en = str(names)
            items.append({"date": ds, "nameId": name_id, "nameEn": name_en, "type": "national"})
        return {"ok": True, "year": year, "holidays": items}
    return None


def _last_sport_id(uid):
    rows = db.get_sport_activities(uid) or []
    if not rows:
        return None
    return rows[-1].get("id") if isinstance(rows[-1], dict) else rows[0].get("id")


def handle_post(path: str, uid: int, body: dict, parts: list):
    if path == "/api/sport":
        intensity = (body.get("intensity") or "moderate").lower()
        diff = {"light": "easy", "moderate": "medium", "vigorous": "hard"}.get(intensity, "medium")
        db.add_sport_activity(
            uid,
            body.get("sportName") or body.get("name") or "Workout",
            sport_type=body.get("sportType") or "running",
            icon=body.get("icon") or "🏃",
            difficulty=diff,
            notes=body.get("notes") or "",
            calories_burned=int(body.get("caloriesBurned") or 0),
            duration_minutes=int(body.get("durationMinutes") or 30),
        )
        result = {"ok": True}
        if body.get("complete", False):
            sid = _last_sport_id(uid)
            if sid is not None:
                try:
                    result = db.complete_sport_activity(uid, sid) or result
                except Exception as e:
                    result = {"ok": False, "msg": str(e)}
        return {"result": result}

    if len(parts) >= 4 and parts[1] == "sport":
        sid = int(parts[2])
        if parts[3] == "complete":
            return {"result": db.complete_sport_activity(uid, sid)}
        if parts[3] == "delete":
            db.delete_sport_activity(uid, sid)
            return {"result": {"ok": True}}
        if parts[3] == "duplicate":
            return {"result": db.duplicate_sport_activity(uid, sid)}
        if parts[3] == "reps":
            return {"result": db.add_sport_rep_log(
                uid, sid, int(body.get("reps") or 0), int(body.get("sets") or 1),
                note=body.get("note") or "")}

    if path == "/api/sport/template":
        key = body.get("key") or "running_starter_s"
        n = db.apply_template_by_mode(uid, "sport", key)
        return {"result": {"ok": True, "n": n}}

    if path == "/api/food/custom":
        result = db.add_custom_food(
            uid,
            (body.get("foodName") or body.get("name") or "Food").strip(),
            body.get("icon") or "🍽️",
            int(body.get("calories") or 0),
            float(body.get("protein") or 0),
            float(body.get("carbs") or 0),
            float(body.get("fat") or 0),
        )
        return {"result": result}

    if path == "/api/food/log":
        fid = body.get("foodId") or body.get("food_id")
        if fid not in (None, "", "null"):
            try:
                fid = int(fid)
            except Exception:
                fid = None
        else:
            fid = None
        name = (body.get("foodName") or body.get("name") or "Food").strip()
        if not fid:
            try:
                fid = db.get_default_food_id_by_name(name)
            except Exception:
                fid = None
        if not fid:
            created = db.add_custom_food(
                uid, name, body.get("icon") or "🍽️",
                int(body.get("calories") or 0),
                float(body.get("protein") or 0),
                float(body.get("carbs") or 0),
                float(body.get("fat") or 0),
            )
            fid = created.get("id") if isinstance(created, dict) else created
        result = db.log_food(
            uid, fid,
            float(body.get("portion") or 1),
            body.get("mealType") or "snack",
            body.get("date") or _today(),
            body.get("notes") or "",
        )
        return {"result": result}

    if len(parts) >= 5 and parts[1] == "food" and parts[2] == "log" and parts[4] == "delete":
        db.delete_food_log(uid, int(parts[3]))
        return {"result": {"ok": True}}

    if path == "/api/water":
        result = db.add_water_log(uid, int(body.get("amountMl") or 0))
        return {"result": result}

    if path == "/api/water/reset":
        result = db.reset_water_today(uid)
        return {"result": result or {"ok": True}}

    if path == "/api/water/goal":
        db.set_water_goal(uid, int(body.get("targetMl") or body.get("daily_ml") or 2000))
        return {"result": {"ok": True}}

    if path == "/api/task-folders":
        mode = (body.get("mode") or "habit").strip() or "habit"
        result = db.add_task_folder(uid, mode, body.get("name") or "Folder", body.get("icon") or "📁")
        return {"result": result}

    if len(parts) >= 4 and parts[1] == "task-folders" and parts[3] == "delete":
        mode = (body.get("mode") or "habit").strip() or "habit"
        db.delete_task_folder(uid, int(parts[2]), mode)
        return {"result": {"ok": True}}

    if path == "/api/templates/apply":
        n = db.apply_template_by_mode(uid, body.get("mode") or "habit", body.get("key") or "")
        return {"result": {"ok": True, "count": n}}

    if path == "/api/savings":
        result = db.add_saving(
            uid,
            body.get("name") or "Saving",
            body.get("icon") or "🏦",
            float(body.get("targetAmount") or 0),
            float(body.get("currentAmount") or 0),
            body.get("targetDate"),
            body.get("notes") or "",
        )
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "savings":
        sid = int(parts[2])
        if parts[3] == "add":
            return {"result": db.add_to_saving(sid, uid, float(body.get("amount") or 0))}
        if parts[3] == "withdraw":
            return {"result": db.withdraw_from_saving(sid, uid, float(body.get("amount") or 0))}
        if parts[3] == "delete":
            db.delete_saving(sid, uid)
            return {"result": {"ok": True}}

    if path == "/api/investments":
        result = db.add_investment(
            uid,
            body.get("name") or "Investment",
            body.get("icon") or "📈",
            float(body.get("amount") or 0),
            body.get("notes") or "",
        )
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "investments":
        iid = int(parts[2])
        if parts[3] == "return":
            return {"result": db.collect_investment_return(iid, uid, float(body.get("percent") or 5))}
        if parts[3] == "withdraw":
            return {"result": db.withdraw_investment(iid, uid)}

    if path == "/api/subscriptions":
        result = db.add_subscription(
            uid,
            body.get("name") or "Subscription",
            body.get("icon") or "📅",
            float(body.get("amount") or 0),
            body.get("dueDate") or _today(),
            body.get("period") or "monthly",
            bool(body.get("isRecurring", True)),
            body.get("notes") or "",
        )
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "subscriptions":
        sid = int(parts[2])
        if parts[3] == "delete":
            db.delete_subscription(sid, uid)
            return {"result": {"ok": True}}
        if parts[3] == "renew":
            return {"result": db.renew_subscription(sid, uid, bool(body.get("autoPay", True)))}

    if path == "/api/debt-notes":
        result = db.add_debt_note(
            uid,
            body.get("personName") or body.get("name") or "",
            float(body.get("amount") or 0),
            body.get("date") or _today(),
            body.get("notes") or "",
        )
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "debt-notes":
        nid = int(parts[2])
        if parts[3] == "settle":
            return {"result": db.settle_debt_note(uid, nid)}
        if parts[3] == "delete":
            return {"result": db.delete_debt_note(uid, nid)}

    if path == "/api/economy":
        typ = body.get("type") or "expense"
        result = db.add_economy_item(
            uid,
            body.get("name") or body.get("category") or typ,
            "💰",
            typ,
            float(body.get("amount") or 0),
            body.get("category") or "",
            body.get("date") or _today(),
            notes=body.get("notes") or "",
        )
        return {"result": result}

    if len(parts) >= 4 and parts[1] == "economy" and parts[3] == "delete":
        db.delete_economy_item(uid, int(parts[2]))
        return {"result": {"ok": True}}

    if path == "/api/debts":
        result = db.add_debt(
            uid,
            body.get("title") or body.get("name") or "Debt",
            float(body.get("totalAmount") or body.get("amount") or 0),
            due_date=body.get("dueDate"),
            notes=body.get("notes") or "",
        )
        return {"result": result}

    if len(parts) >= 4 and parts[1] == "debts":
        did = int(parts[2])
        if parts[3] == "pay":
            return {"result": db.pay_debt_installment(did, uid, float(body.get("amount") or 0))}
        if parts[3] == "delete":
            db.delete_debt(did, uid)
            return {"result": {"ok": True}}

    if path == "/api/notes":
        folder = body.get("folderId")
        folder_id = int(folder) if folder not in (None, "", "null") else None
        result = db.add_note(uid, folder_id, body.get("title") or "Note", body.get("content") or "")
        return {"result": result}

    if path == "/api/notes/preview-math":
        try:
            from mathtools import latex_to_unicode
            raw = body.get("content") or ""
            return {"result": {"ok": True, "preview": latex_to_unicode(raw)}, "skip_snap": True}
        except Exception as e:
            return {"result": {"ok": False, "msg": str(e)}, "skip_snap": True}

    if path == "/api/note-folders":
        result = db.add_note_folder(uid, body.get("name") or "Folder", body.get("icon") or "📁", body.get("parentId"))
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "note-folders" and parts[3] == "delete":
        db.delete_note_folder(int(parts[2]), uid)
        return {"result": {"ok": True}}

    if len(parts) >= 4 and parts[1] == "notes":
        nid = int(parts[2])
        if parts[3] == "update":
            result = db.update_note(
                nid, uid,
                title=body.get("title"),
                content=body.get("content"),
                folder_id=int(body["folderId"]) if body.get("folderId") else None,
                zoom_level=body.get("zoomLevel") or body.get("zoom_level"),
            )
            return {"result": result}
        if parts[3] == "delete":
            db.delete_note(nid, uid)
            return {"result": {"ok": True}}
        if parts[3] == "archive":
            return {"result": db.archive_note(nid, uid, bool(body.get("archived", True)))}
        if parts[3] == "duplicate":
            dest = body.get("folderId")
            dest_id = int(dest) if dest not in (None, "", "null") else None
            return {"result": db.duplicate_note(uid, nid, dest_id)}

    if path == "/api/reminders":
        t = body.get("time") or "08:00"
        dt = f"{_today()} {t}:00"
        result = db.add_reminder(
            uid, body.get("title") or "Reminder", body.get("description") or "",
            dt, sound_type=body.get("sound") or "default",
            repeat_type=body.get("repeat") or "none",
        )
        return {"result": result}

    if len(parts) >= 4 and parts[1] == "reminders":
        rid = int(parts[2])
        if parts[3] == "delete":
            db.delete_reminder(rid, uid)
            return {"result": {"ok": True}}
        if parts[3] == "toggle":
            rem = db.get_reminder(rid, uid)
            if rem:
                trig = not bool(rem.get("triggered"))
                db.update_reminder(rid, uid, triggered=1 if trig else 0)
            return {"result": {"ok": True}}

    if path == "/api/calendar/note":
        result = db.save_calendar_note(uid, body.get("date") or _today(), body.get("note") or "")
        return {"result": result}

    if path == "/api/health/bmi":
        result = db.update_user_bmi_settings(
            uid,
            float(body.get("height_cm") or body.get("heightCm") or 170),
            float(body.get("weight_kg") or body.get("weightKg") or 70),
            int(body.get("age") or 25),
            body.get("gender") or "male",
            float(body.get("activity_factor") or body.get("activityFactor") or 1.55),
        )
        return {"result": result}
    if path == "/api/health":
        result = db.add_health_log(
            uid, _today(),
            steps=int(body.get("steps") or 0),
            sleep_hours=float(body.get("sleepHours") or 0),
            weight_kg=body.get("weightKg"),
            resting_hr=int(body.get("heartRate") or 0),
            mood=body.get("mood") or "good",
            notes=body.get("notes") or "",
        )
        return {"result": result}

    if path == "/api/pomodoro/complete":
        result = db.complete_pomodoro(uid, int(body.get("durationMinutes") or 25), body.get("label") or "")
        return {"result": result}

    if path == "/api/supplies":
        result = db.add_supply_item(
            uid,
            body.get("name") or "Item",
            category=body.get("category") or "",
            unit=body.get("unit") or "pcs",
            stock=float(body.get("stock") or 0),
            min_stock=float(body.get("minStock") or body.get("min_stock") or 0),
            price=float(body.get("price") or 0),
            location=body.get("location") or "",
            notes=body.get("notes") or "",
        )
        return {"result": result}
    if len(parts) >= 4 and parts[1] == "supplies":
        sid = int(parts[2])
        action = parts[3]
        if action == "delete":
            db.delete_supply_item(uid, sid)
            return {"result": {"ok": True}}
        if action == "tx":
            return {"result": db.record_supply_tx(
                uid, sid, body.get("kind") or "in", float(body.get("qty") or 0), body.get("note") or "")}
        if action == "update":
            kw = {}
            for src, dst in (("name", "name"), ("location", "location"), ("category", "category"), ("unit", "unit"), ("notes", "notes")):
                if src in body:
                    kw[dst] = body.get(src)
            if "minStock" in body or "min_stock" in body:
                kw["min_stock"] = float(body.get("minStock") if "minStock" in body else body.get("min_stock") or 0)
            if "price" in body:
                kw["price"] = float(body.get("price") or 0)
            return {"result": db.update_supply_item(uid, sid, **kw)}

    return None
