import streamlit as st
import pandas as pd

from datetime import date, datetime, timedelta




# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="TaskFlow",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
)

from database import (
    add_task,
    delete_task,
    get_all_tasks,
    get_monthly_tasks,
    get_statistics,
    get_tasks_between_dates,
    get_tasks_by_date,
    toggle_task_status,
    update_task,
)

# ============================================================
# AUTHENTICATION
# ============================================================

def check_password():

    if st.session_state.get("authenticated", False):
        return True

    st.markdown(
        """
        <div style="
            max-width: 500px;
            margin: 100px auto 40px auto;
            text-align: center;
        ">
            <div style="font-size: 60px;">✅</div>
            <h1>TaskFlow</h1>
            <p style="color:#6b7280;">
                Personal Task & Productivity Manager
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    password = st.text_input(
        "Application Password",
        type="password",
        placeholder="Enter your password",
    )

    if st.button(
        "Sign In",
        type="primary",
        use_container_width=True,
    ):

        if password == st.secrets["APP_PASSWORD"]:

            st.session_state.authenticated = True
            st.rerun()

        else:

            st.error("Incorrect password.")

    return False


if not check_password():
    st.stop()


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Application title */
    .app-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .app-subtitle {
        color: #6b7280;
        margin-top: 4px;
        margin-bottom: 1.5rem;
    }

    /* Task title */
    .task-title {
        font-size: 1.05rem;
        font-weight: 600;
    }

    /* Secondary text */
    .muted {
        color: #6b7280;
        font-size: 0.85rem;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.06);
        padding: 14px;
        border-radius: 12px;
    }

    /* Reduce excessive vertical spacing */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.5rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        padding-top: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def money(value):
    """Format a numeric value as GBP."""

    try:
        return f"₹{float(value or 0):,.2f}"
    except Exception:
        return "₹0.00"


def number(value):
    """Format an integer with commas."""

    try:
        return f"{int(value or 0):,}"
    except Exception:
        return "0"


def priority_icon(priority):

    return {
        "Urgent": "🔴",
        "High": "🟠",
        "Medium": "🟡",
        "Low": "🟢",
    }.get(priority, "⚪")


def format_date(value):

    if not value:
        return "—"

    try:

        if isinstance(value, date):
            return value.strftime("%d %b %Y")

        return datetime.strptime(
            str(value),
            "%Y-%m-%d"
        ).strftime("%d %b %Y")

    except Exception:

        return str(value)


def is_overdue(task):

    if task.get("status") == "Completed":
        return False

    deadline = task.get("deadline")

    if not deadline:
        return False

    try:

        if isinstance(deadline, date):

            deadline_date = deadline

        else:

            deadline_date = datetime.strptime(
                str(deadline),
                "%Y-%m-%d"
            ).date()

        return deadline_date < date.today()

    except Exception:

        return False


def safe_text(value):

    if value is None:
        return ""

    return str(value)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## ✅ TaskFlow")

    st.caption(
        "Personal Task & Productivity Manager"
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Home",
            "📅 Tasks",
            "➕ Add Task",
            "📊 Reports",
            "🔍 Search",
            "💾 Data",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    if st.button(
        "🔄 Refresh",
        use_container_width=True,
    ):

        st.rerun()

    if st.button(
        "🔒 Lock",
        use_container_width=True,
    ):

        st.session_state.authenticated = False
        st.rerun()

    st.divider()

    st.caption(
        f"Today: {date.today().strftime('%d %B %Y')}"
    )


# ============================================================
# HOME
# ============================================================

if page == "🏠 Home":

    st.markdown(
        '<div class="app-title">Dashboard</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="app-subtitle">'
        'A quick overview of your work, tasks and earnings.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # GLOBAL STATISTICS
    # --------------------------------------------------------

    stats = get_statistics()

    total_tasks = stats["total_tasks"]
    completed_tasks = stats["completed_tasks"]
    pending_tasks = stats["pending_tasks"]

    completion_rate = (
        completed_tasks / total_tasks * 100
        if total_tasks > 0
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Tasks",
        number(total_tasks),
    )

    c2.metric(
        "Completed",
        number(completed_tasks),
    )

    c3.metric(
        "Pending",
        number(pending_tasks),
    )

    c4.metric(
        "Completion Rate",
        f"{completion_rate:.1f}%",
    )

    st.write("")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Words",
        number(stats["total_words"]),
    )

    c2.metric(
        "Completed Words",
        number(stats["completed_words"]),
    )

    c3.metric(
        "Total Value",
        money(stats["total_price"]),
    )

    c4.metric(
        "Completed Value",
        money(stats["completed_price"]),
    )

    st.divider()

    # --------------------------------------------------------
    # TODAY'S TASKS
    # --------------------------------------------------------

    st.subheader(
        f"Today's Tasks · {date.today().strftime('%d %B %Y')}"
    )

    today = date.today()

st.subheader(
    f"Today's Tasks · {today.strftime('%d %B %Y')}"
)

all_tasks = get_all_tasks()

active_today_tasks = []

for task in all_tasks:

    # Completed tasks should not appear in the
    # pending/current task section.
    if task.get("status") == "Completed":
        continue

    task_date_value = task.get("task_date")
    deadline_value = task.get("deadline")

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

    show_task = False

    # ----------------------------------------------------
    # Task scheduled for today
    # ----------------------------------------------------

    if task_date_obj == today:
        show_task = True

    # ----------------------------------------------------
    # Task was scheduled earlier but is still within
    # its deadline
    # ----------------------------------------------------

    elif (
        task_date_obj
        and task_date_obj < today
        and deadline_obj
        and deadline_obj >= today
    ):
        show_task = True

    # ----------------------------------------------------
    # Task deadline is today
    # ----------------------------------------------------

    elif deadline_obj == today:
        show_task = True

    if show_task:
        active_today_tasks.append(task)


if not active_today_tasks:

    st.info(
        "No pending tasks for today."
    )

    if st.button(
        "➕ Add a task for today",
        type="primary",
    ):

        st.info(
            "Use the 'Add Task' section from the sidebar."
        )

else:

    completed_count = sum(
        task.get("status") == "Completed"
        for task in active_today_tasks
    )

    pending_count = (
        len(active_today_tasks)
        - completed_count
    )

    st.caption(
        f"{len(active_today_tasks)} active task(s)"
    )

    for task in active_today_tasks:

        current_status = (
            task["status"] == "Completed"
        )

        with st.container(border=True):

            col1, col2 = st.columns(
                [0.06, 0.94]
            )

            checked = col1.checkbox(
                "",
                value=current_status,
                key=f"home_status_{task['id']}",
            )

            if checked != current_status:

                toggle_task_status(
                    task["id"],
                    checked,
                )

                st.rerun()

            title = safe_text(
                task.get("title")
            )

            client = safe_text(
                task.get("client_name")
            )

            if current_status:
                title_display = f"~~{title}~~"
            else:
                title_display = title

            col2.markdown(
                f"**{priority_icon(task.get('priority'))} "
                f"{title_display}**"
            )

            if client:

                col2.caption(
                    f"👤 {client}"
                )

            # ------------------------------------------------
            # Deadline indicator
            # ------------------------------------------------

            deadline_value = task.get("deadline")

            if deadline_value:

                try:

                    deadline_date = datetime.strptime(
                        str(deadline_value),
                        "%Y-%m-%d"
                    ).date()

                    if deadline_date < today:

                        col2.error(
                            f"⚠️ OVERDUE · "
                            f"{format_date(deadline_value)}"
                        )

                    elif deadline_date == today:

                        col2.warning(
                            "⚠️ DEADLINE TODAY"
                        )

                    else:

                        col2.caption(
                            f"Deadline · "
                            f"{format_date(deadline_value)}"
                        )

                except Exception:
                    pass

            meta1, meta2, meta3, meta4 = col2.columns(4)

            meta1.caption(
                f"📝 {number(task.get('total_words'))} words"
            )

            meta2.caption(
                f"💻 {safe_text(task.get('software')) or '—'}"
            )

            meta3.caption(
                f"💰 {money(task.get('price'))}"
            )

            meta4.caption(
                f"📂 {safe_text(task.get('category')) or 'Other'}"
            )

            if task.get("description"):

                col2.write(
                    task["description"]
                )

    if not today_tasks:

        st.info(
            "No tasks scheduled for today."
        )

        if st.button(
            "➕ Add a task for today",
            type="primary",
        ):

            st.info(
                "Use the 'Add Task' section from the sidebar."
            )

    else:

        today_completed = sum(
            task["status"] == "Completed"
            for task in today_tasks
        )

        today_pending = (
            len(today_tasks) - today_completed
        )

        st.caption(
            f"{today_pending} pending · "
            f"{today_completed} completed"
        )

        for task in today_tasks:

            current_status = (
                task["status"] == "Completed"
            )

            with st.container(border=True):

                col1, col2 = st.columns(
                    [0.06, 0.94]
                )

                checked = col1.checkbox(
                    "",
                    value=current_status,
                    key=f"home_status_{task['id']}",
                )

                if checked != current_status:

                    toggle_task_status(
                        task["id"],
                        checked,
                    )

                    st.rerun()

                title = safe_text(
                    task.get("title")
                )

                client = safe_text(
                    task.get("client_name")
                )

                if current_status:
                    title_display = f"~~{title}~~"
                else:
                    title_display = title

                col2.markdown(
                    f"**{priority_icon(task.get('priority'))} "
                    f"{title_display}**"
                )

                if client:

                    col2.caption(
                        f"👤 {client}"
                    )

                meta1, meta2, meta3, meta4 = col2.columns(4)

                meta1.caption(
                    f"📝 {number(task.get('total_words'))} words"
                )

                meta2.caption(
                    f"💻 {safe_text(task.get('software')) or '—'}"
                )

                meta3.caption(
                    f"💰 {money(task.get('price'))}"
                )

                meta4.caption(
                    f"📂 {safe_text(task.get('category')) or 'Other'}"
                )

    st.divider()

    # --------------------------------------------------------
    # UPCOMING TASKS
    # --------------------------------------------------------

    st.subheader("Upcoming Tasks")

    # --------------------------------------------------------
# UPCOMING / OUTSTANDING TASKS
# --------------------------------------------------------

st.subheader(
    "Upcoming & Outstanding Tasks"
)

today = date.today()

upcoming_end = (
    today
    + timedelta(days=7)
)

upcoming = get_pending_dashboard_tasks(
    start_date=today,
    end_date=upcoming_end,
)

if not upcoming:

    st.success(
        "No pending tasks in the next 7 days."
    )

else:

    st.caption(
        f"{len(upcoming)} pending task(s) "
        f"requiring attention."
    )

    for task in upcoming[:15]:

        task_date_value = task.get(
            "task_date"
        )

        deadline_value = task.get(
            "deadline"
        )

        # -----------------------------------------------
        # Determine status
        # -----------------------------------------------

        deadline_status = ""

        if deadline_value:

            try:

                deadline_obj = datetime.strptime(
                    str(deadline_value),
                    "%Y-%m-%d"
                ).date()

                if deadline_obj < today:

                    deadline_status = "⚠️ OVERDUE"

                elif deadline_obj == today:

                    deadline_status = "🔴 DUE TODAY"

                elif deadline_obj == today + timedelta(days=1):

                    deadline_status = "🟠 DUE TOMORROW"

                else:

                    deadline_status = (
                        f"📅 Due "
                        f"{format_date(deadline_value)}"
                    )

            except Exception:

                deadline_status = ""

        else:

            deadline_status = (
                f"📅 Task date "
                f"{format_date(task_date_value)}"
            )

        client_text = ""

        if task.get("client_name"):

            client_text = (
                f" · 👤 {task['client_name']}"
            )

        with st.container(border=True):

            c1, c2 = st.columns(
                [0.06, 0.94]
            )

            c1.write("📌")

            c2.markdown(
                f"**{task.get('title')}**"
                f"{client_text}"
            )

            c2.caption(
                deadline_status
            )

            meta1, meta2, meta3 = c2.columns(3)

            meta1.caption(
                f"📝 {number(task.get('total_words'))} words"
            )

            meta2.caption(
                f"💻 "
                f"{safe_text(task.get('software')) or '—'}"
            )

            meta3.caption(
                f"💰 {money(task.get('price'))}"
            )

    if not upcoming:

        st.success(
            "No pending tasks in the next 7 days."
        )

    else:

        for task in upcoming[:10]:

            client_text = ""

            if task.get("client_name"):

                client_text = (
                    f" · {task['client_name']}"
                )

            if is_overdue(task):

                icon = "⚠️"

            else:

                icon = "📌"

            st.write(
                f"{icon} "
                f"**{format_date(task.get('task_date'))}** · "
                f"{task.get('title')}"
                f"{client_text}"
            )


# ============================================================
# TASKS
# ============================================================

elif page == "📅 Tasks":

    st.markdown(
        '<div class="app-title">Tasks</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="app-subtitle">'
        'View and manage tasks by date.'
        '</div>',
        unsafe_allow_html=True,
    )

    selected_date = st.date_input(
        "Select Date",
        value=date.today(),
    )

    tasks = get_tasks_by_date(
        selected_date.isoformat()
    )

    completed_count = sum(
        task["status"] == "Completed"
        for task in tasks
    )

    pending_count = (
        len(tasks) - completed_count
    )

    total_words = sum(
        int(task.get("total_words") or 0)
        for task in tasks
    )

    total_value = sum(
        float(task.get("price") or 0)
        for task in tasks
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Tasks",
        len(tasks),
    )

    c2.metric(
        "Completed",
        completed_count,
    )

    c3.metric(
        "Pending",
        pending_count,
    )

    c4.metric(
        "Value",
        money(total_value),
    )

    st.caption(
        f"Total words: {number(total_words)}"
    )

    st.divider()

    if not tasks:

        st.info(
            "No tasks found for this date."
        )

    else:

        for task in tasks:

            current_status = (
                task["status"] == "Completed"
            )

            with st.container(border=True):

                top1, top2 = st.columns(
                    [0.06, 0.94]
                )

                checked = top1.checkbox(
                    "",
                    value=current_status,
                    key=f"status_{task['id']}",
                )

                if checked != current_status:

                    toggle_task_status(
                        task["id"],
                        checked,
                    )

                    st.rerun()

                title = safe_text(
                    task.get("title")
                )

                if current_status:

                    title = f"~~{title}~~"

                client = safe_text(
                    task.get("client_name")
                )

                top2.markdown(
                    f"### "
                    f"{priority_icon(task.get('priority'))} "
                    f"{title}"
                )

                if client:

                    top2.caption(
                        f"👤 Client: **{client}**"
                    )

                # --------------------------------------------
                # Task information
                # --------------------------------------------

                i1, i2, i3, i4, i5 = st.columns(5)

                i1.caption(
                    f"📅 {format_date(task.get('task_date'))}"
                )

                i2.caption(
                    f"📝 {number(task.get('total_words'))} words"
                )

                i3.caption(
                    f"💻 {safe_text(task.get('software')) or '—'}"
                )

                i4.caption(
                    f"💰 {money(task.get('price'))}"
                )

                i5.caption(
                    f"🎯 {safe_text(task.get('priority'))}"
                )

                if task.get("deadline"):

                    if is_overdue(task):

                        st.error(
                            f"⚠️ Overdue · "
                            f"{format_date(task.get('deadline'))}"
                        )

                    else:

                        st.caption(
                            f"Deadline · "
                            f"{format_date(task.get('deadline'))}"
                        )

                if task.get("description"):

                    st.write(
                        task["description"]
                    )

                if task.get("notes"):

                    with st.expander("📝 Notes"):

                        st.write(
                            task["notes"]
                        )

                # --------------------------------------------
                # EDIT / DELETE
                # --------------------------------------------

                with st.expander(
                    "⚙️ Edit / Delete"
                ):

                    edited_title = st.text_input(
                        "Task Title",
                        value=safe_text(
                            task.get("title")
                        ),
                        key=f"edit_title_{task['id']}",
                    )

                    edited_client = st.text_input(
                        "Client Name",
                        value=safe_text(
                            task.get("client_name")
                        ),
                        key=f"edit_client_{task['id']}",
                    )

                    e1, e2 = st.columns(2)

                    with e1:

                        edited_date = st.date_input(
                            "Task Date",
                            value=datetime.strptime(
                                task["task_date"],
                                "%Y-%m-%d"
                            ).date(),
                            key=f"edit_date_{task['id']}",
                        )

                        deadline_value = None

                        if task.get("deadline"):

                            try:

                                deadline_value = datetime.strptime(
                                    task["deadline"],
                                    "%Y-%m-%d"
                                ).date()

                            except Exception:

                                deadline_value = None

                        edited_deadline = st.date_input(
                            "Deadline",
                            value=deadline_value,
                            key=f"edit_deadline_{task['id']}",
                        )

                        edited_status = st.selectbox(
                            "Status",
                            [
                                "Pending",
                                "Completed",
                            ],
                            index=(
                                1
                                if current_status
                                else 0
                            ),
                            key=f"edit_status_{task['id']}",
                        )

                    with e2:

                        edited_category = st.selectbox(
                            "Category",
                            [
                                "Dissertation",
                                "Assignment",
                                "Data Analysis",
                                "Programming",
                                "Machine Learning",
                                "Research",
                                "Report",
                                "Presentation",
                                "Other",
                            ],
                            index=(
                                [
                                    "Dissertation",
                                    "Assignment",
                                    "Data Analysis",
                                    "Programming",
                                    "Machine Learning",
                                    "Research",
                                    "Report",
                                    "Presentation",
                                    "Other",
                                ].index(
                                    task.get(
                                        "category",
                                        "Other"
                                    )
                                )
                                if task.get(
                                    "category",
                                    "Other"
                                ) in [
                                    "Dissertation",
                                    "Assignment",
                                    "Data Analysis",
                                    "Programming",
                                    "Machine Learning",
                                    "Research",
                                    "Report",
                                    "Presentation",
                                    "Other",
                                ]
                                else 8
                            ),
                            key=f"edit_category_{task['id']}",
                        )

                        edited_priority = st.selectbox(
                            "Priority",
                            [
                                "Low",
                                "Medium",
                                "High",
                                "Urgent",
                            ],
                            index=(
                                [
                                    "Low",
                                    "Medium",
                                    "High",
                                    "Urgent",
                                ].index(
                                    task.get(
                                        "priority",
                                        "Medium"
                                    )
                                )
                                if task.get(
                                    "priority",
                                    "Medium"
                                ) in [
                                    "Low",
                                    "Medium",
                                    "High",
                                    "Urgent",
                                ]
                                else 1
                            ),
                            key=f"edit_priority_{task['id']}",
                        )

                        edited_words = st.number_input(
                            "Total Words",
                            min_value=0,
                            value=int(
                                task.get("total_words")
                                or 0
                            ),
                            step=100,
                            key=f"edit_words_{task['id']}",
                        )

                        edited_price = st.number_input(
                            "Price (₹)",
                            min_value=0.0,
                            value=float(
                                task.get("price")
                                or 0
                            ),
                            step=5.0,
                            key=f"edit_price_{task['id']}",
                        )

                    edited_software = st.text_input(
                        "Software / Work Details",
                        value=safe_text(
                            task.get("software")
                        ),
                        key=f"edit_software_{task['id']}",
                    )

                    edited_description = st.text_area(
                        "Description",
                        value=safe_text(
                            task.get("description")
                        ),
                        key=f"edit_description_{task['id']}",
                    )

                    edited_notes = st.text_area(
                        "Notes",
                        value=safe_text(
                            task.get("notes")
                        ),
                        key=f"edit_notes_{task['id']}",
                    )

                    b1, b2 = st.columns(2)

                    with b1:

                        if st.button(
                            "💾 Save Changes",
                            key=f"save_{task['id']}",
                            type="primary",
                            use_container_width=True,
                        ):

                            update_task(
                                task_id=task["id"],
                                title=edited_title.strip(),
                                client_name=edited_client.strip(),
                                task_date=edited_date.isoformat(),
                                deadline=(
                                    edited_deadline.isoformat()
                                    if edited_deadline
                                    else None
                                ),
                                description=edited_description.strip(),
                                status=edited_status,
                                total_words=int(
                                    edited_words
                                ),
                                software=edited_software.strip(),
                                category=edited_category,
                                priority=edited_priority,
                                price=float(
                                    edited_price
                                ),
                                notes=edited_notes.strip(),
                            )

                            st.success(
                                "Task updated successfully."
                            )

                            st.rerun()

                    with b2:

                        if st.button(
                            "🗑️ Delete Task",
                            key=f"delete_{task['id']}",
                            use_container_width=True,
                        ):

                            st.session_state[
                                f"confirm_delete_{task['id']}"
                            ] = True

                    if st.session_state.get(
                        f"confirm_delete_{task['id']}",
                        False,
                    ):

                        st.warning(
                            "Are you sure you want to delete this task?"
                        )

                        d1, d2 = st.columns(2)

                        with d1:

                            if st.button(
                                "Yes, delete",
                                key=f"confirm_{task['id']}",
                                type="primary",
                                use_container_width=True,
                            ):

                                delete_task(
                                    task["id"]
                                )

                                st.session_state[
                                    f"confirm_delete_{task['id']}"
                                ] = False

                                st.success(
                                    "Task deleted."
                                )

                                st.rerun()

                        with d2:

                            if st.button(
                                "Cancel",
                                key=f"cancel_{task['id']}",
                                use_container_width=True,
                            ):

                                st.session_state[
                                    f"confirm_delete_{task['id']}"
                                ] = False

                                st.rerun()


# ============================================================
# ADD TASK
# ============================================================

elif page == "➕ Add Task":

    st.markdown(
        '<div class="app-title">Add Task</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="app-subtitle">'
        'Add a new task to your workload.'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.form("new_task_form"):

        # ----------------------------------------------------
        # BASIC INFORMATION
        # ----------------------------------------------------

        st.subheader("Basic Information")

        title = st.text_input(
            "Task Title *",
            placeholder="e.g. Complete dissertation methodology",
        )

        client_name = st.text_input(
            "Client Name",
            placeholder="e.g. ABC Ltd / John / University",
        )

        description = st.text_area(
            "Task Description",
            placeholder="Briefly describe what needs to be done...",
            height=100,
        )

        # ----------------------------------------------------
        # DATE / CATEGORY
        # ----------------------------------------------------

        st.subheader("Planning")

        c1, c2, c3 = st.columns(3)

        with c1:

            task_date = st.date_input(
                "Task Date",
                value=date.today(),
            )

        with c2:

            deadline = st.date_input(
                "Deadline",
                value=None,
            )

        with c3:

            category = st.selectbox(
                "Category",
                [
                    "Dissertation",
                    "Assignment",
                    "Data Analysis",
                    "Programming",
                    "Machine Learning",
                    "Research",
                    "Report",
                    "Presentation",
                    "Other",
                ],
            )

        priority = st.select_slider(
            "Priority",
            options=[
                "Low",
                "Medium",
                "High",
                "Urgent",
            ],
            value="Medium",
        )

        # ----------------------------------------------------
        # WORK DETAILS
        # ----------------------------------------------------

        st.subheader("Work Details")

        c1, c2, c3 = st.columns(3)

        with c1:

            words = st.number_input(
                "Total Words",
                min_value=0,
                value=0,
                step=100,
            )

        with c2:

            software = st.text_input(
                "Software / Tools",
                placeholder="e.g. Python, Excel, SPSS",
            )

        with c3:

            price = st.number_input(
                "Price (₹)",
                min_value=0.0,
                value=0.0,
                step=5.0,
            )

        notes = st.text_area(
            "Notes",
            placeholder="Additional information, instructions or reminders...",
            height=100,
        )

        # ----------------------------------------------------
        # SUBMIT
        # ----------------------------------------------------

        st.write("")

        save = st.form_submit_button(
            "💾 Save Task",
            type="primary",
            use_container_width=True,
        )

        if save:

            if not title.strip():

                st.error(
                    "Please enter a task title."
                )

            else:

                add_task(
                    title=title.strip(),
                    client_name=client_name.strip(),
                    task_date=task_date.isoformat(),
                    deadline=(
                        deadline.isoformat()
                        if deadline
                        else None
                    ),
                    description=description.strip(),
                    total_words=int(words),
                    software=software.strip(),
                    category=category,
                    priority=priority,
                    price=float(price),
                    notes=notes.strip(),
                )

                st.success(
                    "✅ Task added successfully."
                )

                st.info(
                    "You can find the task under the Tasks section."
                )


# ============================================================
# REPORTS
# ============================================================

elif page == "📊 Reports":

    st.markdown(
        '<div class="app-title">Reports</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="app-subtitle">'
        'Analyse your workload, words and earnings.'
        '</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:

        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=date.today().year,
        )

    with c2:

        month = st.selectbox(
            "Month",
            range(1, 13),
            format_func=lambda x:
                datetime(
                    2000,
                    x,
                    1,
                ).strftime("%B"),
            index=date.today().month - 1,
        )

    tasks = get_monthly_tasks(
        int(year),
        int(month),
    )

    if not tasks:

        st.info(
            "No tasks recorded for this month."
        )

    else:

        df = pd.DataFrame(tasks)

        completed_mask = (
            df["status"] == "Completed"
        )

        total_tasks = len(df)

        completed_tasks = int(
            completed_mask.sum()
        )

        pending_tasks = (
            total_tasks - completed_tasks
        )

        total_words = int(
            df["total_words"]
            .fillna(0)
            .sum()
        )

        completed_words = int(
            df.loc[
                completed_mask,
                "total_words"
            ]
            .fillna(0)
            .sum()
        )

        total_value = float(
            df["price"]
            .fillna(0)
            .sum()
        )

        completed_value = float(
            df.loc[
                completed_mask,
                "price"
            ]
            .fillna(0)
            .sum()
        )

        completion_rate = (
            completed_tasks
            / total_tasks
            * 100
        )

        # ----------------------------------------------------
        # MAIN MONTHLY METRICS
        # ----------------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Tasks",
            number(total_tasks),
        )

        c2.metric(
            "Completed",
            number(completed_tasks),
        )

        c3.metric(
            "Pending",
            number(pending_tasks),
        )

        c4.metric(
            "Completion",
            f"{completion_rate:.1f}%",
        )

        st.write("")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total Words",
            number(total_words),
        )

        c2.metric(
            "Completed Words",
            number(completed_words),
        )

        c3.metric(
            "Total Value",
            money(total_value),
        )

        c4.metric(
            "Completed Value",
            money(completed_value),
        )

        st.divider()

        # ----------------------------------------------------
        # DAILY ANALYSIS
        # ----------------------------------------------------

        df["task_date"] = pd.to_datetime(
            df["task_date"]
        )

        daily_tasks = (
            df.groupby("task_date")
            .size()
            .rename("Tasks")
        )

        st.subheader("Tasks per Day")

        st.bar_chart(
            daily_tasks
        )

        daily_words = (
            df.groupby("task_date")[
                "total_words"
            ]
            .sum()
            .rename("Words")
        )

        st.subheader("Words per Day")

        st.line_chart(
            daily_words
        )

        daily_value = (
            df.groupby("task_date")[
                "price"
            ]
            .sum()
            .rename("Value")
        )

        st.subheader("Value per Day")

        st.line_chart(
            daily_value
        )

        # ----------------------------------------------------
        # CLIENT ANALYSIS
        # ----------------------------------------------------

        st.subheader("Client Summary")

        client_summary = (
            df.assign(
                client_name=df[
                    "client_name"
                ].fillna("No Client")
            )
            .groupby("client_name")
            .agg(
                Tasks=("id", "count"),
                Words=("total_words", "sum"),
                Value=("price", "sum"),
            )
            .reset_index()
            .sort_values(
                "Value",
                ascending=False,
            )
        )

        st.dataframe(
            client_summary,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # CATEGORY ANALYSIS
        # ----------------------------------------------------

        st.subheader("Category Summary")

        category_summary = (
            df.groupby("category")
            .agg(
                Tasks=("id", "count"),
                Words=("total_words", "sum"),
                Value=("price", "sum"),
            )
            .reset_index()
            .sort_values(
                "Tasks",
                ascending=False,
            )
        )

        st.dataframe(
            category_summary,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# SEARCH
# ============================================================

elif page == "🔍 Search":

    st.markdown(
        '<div class="app-title">Search</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="app-subtitle">'
        'Find tasks using client, title, software or other filters.'
        '</div>',
        unsafe_allow_html=True,
    )

    tasks = get_all_tasks()

    if not tasks:

        st.info(
            "No tasks available."
        )

    else:

        df = pd.DataFrame(tasks)

        search = st.text_input(
            "Search Tasks",
            placeholder=(
                "Search client, title, description, "
                "software or notes..."
            ),
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            status_filter = st.selectbox(
                "Status",
                [
                    "All",
                    "Pending",
                    "Completed",
                ],
            )

        with c2:

            priority_options = [
                "All",
                "Low",
                "Medium",
                "High",
                "Urgent",
            ]

            priority_filter = st.selectbox(
                "Priority",
                priority_options,
            )

        with c3:

            categories = sorted(
                df["category"]
                .fillna("Other")
                .unique()
                .tolist()
            )

            category_filter = st.selectbox(
                "Category",
                ["All"] + categories,
            )

        clients = sorted(
            df["client_name"]
            .fillna("")
            .replace("", "No Client")
            .unique()
            .tolist()
        )

        client_filter = st.selectbox(
            "Client",
            ["All"] + clients,
        )

        filtered = df.copy()

        # ----------------------------------------------------
        # TEXT SEARCH
        # ----------------------------------------------------

        if search.strip():

            query = search.lower().strip()

            searchable_columns = [
                "title",
                "client_name",
                "description",
                "software",
                "notes",
                "category",
            ]

            mask = pd.Series(
                False,
                index=filtered.index,
            )

            for column in searchable_columns:

                mask = (
                    mask
                    |
                    filtered[column]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        query,
                        na=False,
                    )
                )

            filtered = filtered[mask]

        # ----------------------------------------------------
        # FILTERS
        # ----------------------------------------------------

        if status_filter != "All":

            filtered = filtered[
                filtered["status"]
                == status_filter
            ]

        if priority_filter != "All":

            filtered = filtered[
                filtered["priority"]
                == priority_filter
            ]

        if category_filter != "All":

            filtered = filtered[
                filtered["category"]
                == category_filter
            ]

        if client_filter != "All":

            if client_filter == "No Client":

                filtered = filtered[
                    filtered["client_name"]
                    .fillna("")
                    == ""
                ]

            else:

                filtered = filtered[
                    filtered["client_name"]
                    == client_filter
                ]

        st.divider()

        st.caption(
            f"{len(filtered)} task(s) found"
        )

        if len(filtered) > 0:

            display_columns = [
                "title",
                "client_name",
                "task_date",
                "deadline",
                "status",
                "total_words",
                "software",
                "category",
                "priority",
                "price",
            ]

            display_df = filtered[
                display_columns
            ].copy()

            display_df.columns = [
                "Task",
                "Client",
                "Date",
                "Deadline",
                "Status",
                "Words",
                "Software",
                "Category",
                "Priority",
                "Price",
            ]

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )

            csv = filtered.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Download Search Results",
                csv,
                "task_search.csv",
                "text/csv",
            )

        else:

            st.info(
                "No tasks match your search."
            )


# ============================================================
# DATA / EXPORT
# ============================================================

elif page == "💾 Data":

    st.markdown(
        '<div class="app-title">Data</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="app-subtitle">'
        'Export and review your stored task data.'
        '</div>',
        unsafe_allow_html=True,
    )

    tasks = get_all_tasks()

    if not tasks:

        st.info(
            "No data available."
        )

    else:

        df = pd.DataFrame(tasks)

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Tasks",
            len(df),
        )

        c2.metric(
            "Words",
            number(
                df["total_words"]
                .fillna(0)
                .sum()
            ),
        )

        c3.metric(
            "Total Value",
            money(
                df["price"]
                .fillna(0)
                .sum()
            ),
        )

        st.divider()

        csv = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Export All Tasks as CSV",
            csv,
            (
                f"task_backup_"
                f"{date.today().isoformat()}.csv"
            ),
            "text/csv",
            use_container_width=True,
        )

        st.divider()

        st.subheader(
            "Stored Data"
        )

        display_columns = [
            "title",
            "client_name",
            "task_date",
            "status",
            "total_words",
            "software",
            "category",
            "priority",
            "price",
        ]

        display_df = df[
            display_columns
        ].copy()

        display_df.columns = [
            "Task",
            "Client",
            "Date",
            "Status",
            "Words",
            "Software",
            "Category",
            "Priority",
            "Price",
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "TaskFlow · Personal Task & Productivity Manager"
)
