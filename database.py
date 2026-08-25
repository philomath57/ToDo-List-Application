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

def get_pending_dashboard_tasks(
    start_date=None,
    end_date=None
):
    """
    Returns pending tasks that are relevant to the dashboard.

    A pending task is included when:

    - It is scheduled within the selected period, OR
    - Its deadline falls within the selected period, OR
    - It was scheduled earlier but its deadline has not passed yet.

    Tasks without deadlines remain visible if their task date
    is within the selected period.
    """

    if start_date is None:
        start_date = date.today()

    if end_date is None:
        end_date = (
            start_date
            + timedelta(days=7)
        )

    tasks = get_all_tasks()

    relevant_tasks = []

    for task in tasks:

        # Only pending tasks
        if task.get("status") == "Completed":
            continue

        task_date_value = task.get("task_date")
        deadline_value = task.get("deadline")

        # ----------------------------------------------------
        # Convert dates
        # ----------------------------------------------------

        try:

            task_date_obj = (
                datetime.strptime(
                    str(task_date_value),
                    "%Y-%m-%d"
                ).date()
                if task_date_value
                else None
            )

        except Exception:

            task_date_obj = None

        try:

            deadline_obj = (
                datetime.strptime(
                    str(deadline_value),
                    "%Y-%m-%d"
                ).date()
                if deadline_value
                else None
            )

        except Exception:

            deadline_obj = None

        # ----------------------------------------------------
        # Determine relevance
        # ----------------------------------------------------

        relevant = False

        # Future/current scheduled task
        if task_date_obj:

            if start_date <= task_date_obj <= end_date:
                relevant = True

        # Deadline falls within period
        if deadline_obj:

            if start_date <= deadline_obj <= end_date:
                relevant = True

        # Previously scheduled task that is still pending
        # and deadline has not passed
        if task_date_obj and task_date_obj < start_date:

            if deadline_obj:

                if deadline_obj >= start_date:
                    relevant = True

        if relevant:

            relevant_tasks.append(task)

    # --------------------------------------------------------
    # Sort by deadline first, then task date
    # --------------------------------------------------------

    relevant_tasks.sort(
        key=lambda task: (
            task.get("deadline") or "9999-12-31",
            task.get("task_date") or "9999-12-31",
        )
    )

    return relevant_tasks
