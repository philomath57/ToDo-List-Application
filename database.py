import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone


# ============================================================
# SUPABASE CONNECTION
# ============================================================

@st.cache_resource
def get_supabase() -> Client:

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]

    return create_client(url, key)


supabase = get_supabase()


# ============================================================
# TASK OPERATIONS
# ============================================================

def add_task(
    title,
    client_name,
    task_date,
    deadline,
    description,
    total_words,
    software,
    category,
    priority,
    price,
    notes
):

    data = {
        "title": title,
        "client_name": client_name,
        "task_date": task_date,
        "deadline": deadline,
        "description": description,
        "status": "Pending",
        "total_words": int(total_words),
        "software": software,
        "category": category,
        "priority": priority,
        "price": float(price),
        "notes": notes,
    }

    response = (
        supabase
        .table("tasks")
        .insert(data)
        .execute()
    )

    return response.data


def get_task(task_id):

    response = (
        supabase
        .table("tasks")
        .select("*")
        .eq("id", task_id)
        .single()
        .execute()
    )

    return response.data


def get_all_tasks():

    response = (
        supabase
        .table("tasks")
        .select("*")
        .order("task_date", desc=True)
        .order("id", desc=True)
        .execute()
    )

    return response.data or []


def get_tasks_by_date(task_date):

    response = (
        supabase
        .table("tasks")
        .select("*")
        .eq("task_date", task_date)
        .order("id", desc=True)
        .execute()
    )

    return response.data or []


def get_tasks_between_dates(start_date, end_date):
    """
    Get pending tasks that are relevant between start_date
    and end_date.

    A task is considered relevant if:

    1. Its task_date falls within the period, OR
    2. Its deadline falls within the period, OR
    3. It started before the period but is still pending and
       has a deadline after the start date.
    """

    response = (
        supabase
        .table("tasks")
        .select("*")
        .eq("status", "Pending")
        .or_(
            f"and(task_date.gte.{start_date},task_date.lte.{end_date}),"
            f"and(deadline.gte.{start_date},deadline.lte.{end_date}),"
            f"and(task_date.lt.{start_date},deadline.gte.{start_date})"
        )
        .order("deadline", desc=False)
        .execute()
    )

    return response.data or []


def get_monthly_tasks(year, month):

    start_date = f"{year}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    response = (
        supabase
        .table("tasks")
        .select("*")
        .gte("task_date", start_date)
        .lt("task_date", end_date)
        .order("task_date")
        .execute()
    )

    return response.data or []


def update_task(
    task_id,
    title,
    client_name,
    task_date,
    deadline,
    description,
    status,
    total_words,
    software,
    category,
    priority,
    price,
    notes
):

    data = {
        "title": title,
        "client_name": client_name,
        "task_date": task_date,
        "deadline": deadline,
        "description": description,
        "status": status,
        "total_words": int(total_words),
        "software": software,
        "category": category,
        "priority": priority,
        "price": float(price),
        "notes": notes,
    }

    existing = get_task(task_id)

    if status == "Completed":

        if existing and existing.get("status") != "Completed":

            data["completed_at"] = datetime.now(
                timezone.utc
            ).isoformat()

    else:

        data["completed_at"] = None

    (
        supabase
        .table("tasks")
        .update(data)
        .eq("id", task_id)
        .execute()
    )


def toggle_task_status(task_id, completed):

    if completed:

        data = {
            "status": "Completed",
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

    else:

        data = {
            "status": "Pending",
            "completed_at": None
        }

    (
        supabase
        .table("tasks")
        .update(data)
        .eq("id", task_id)
        .execute()
    )


def delete_task(task_id):

    (
        supabase
        .table("tasks")
        .delete()
        .eq("id", task_id)
        .execute()
    )


# ============================================================
# STATISTICS
# ============================================================

def get_statistics():

    tasks = get_all_tasks()

    total_tasks = len(tasks)

    completed_tasks = sum(
        t["status"] == "Completed"
        for t in tasks
    )

    pending_tasks = total_tasks - completed_tasks

    total_words = sum(
        int(t.get("total_words") or 0)
        for t in tasks
    )

    completed_words = sum(
        int(t.get("total_words") or 0)
        for t in tasks
        if t["status"] == "Completed"
    )

    total_price = sum(
        float(t.get("price") or 0)
        for t in tasks
    )

    completed_price = sum(
        float(t.get("price") or 0)
        for t in tasks
        if t["status"] == "Completed"
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_words": total_words,
        "completed_words": completed_words,
        "total_price": total_price,
        "completed_price": completed_price,
    }
