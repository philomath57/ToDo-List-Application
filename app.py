import streamlit as st
import pandas as pd

from datetime import date, datetime, timedelta


# ============================================================
# PAGE CONFIGURATION
# MUST BE THE FIRST STREAMLIT COMMAND
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
    get_tasks_by_date,
    toggle_task_status,
    update_task,
)


# ============================================================
# AUTHENTICATION
# ============================================================

def check_password():
    """Simple password protection using Streamlit secrets."""

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
        unsafe_allow_html=True,
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
        try:
            correct_password = st.secrets["APP_PASSWORD"]
        except Exception:
            st.error(
                "APP_PASSWORD is not configured in Streamlit Secrets."
            )
            return False

        if password == correct_password:
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

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

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

    .muted {
        color: #6b7280;
        font-size: 0.85rem;
    }

    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.06);
        padding: 14px;
        border-radius: 12px;
    }

    section[data-testid="stSidebar"] {
        padding-top: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CONSTANTS
# ============================================================

CATEGORIES = [
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

PRIORITIES = [
    "Low",
    "Medium",
    "High",
    "Urgent",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def money(value):
    """Format a numeric value as INR."""

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


def safe_text(value):
    if value is None:
        return ""
    return str(value)


def to_date(value):
    """
    Convert common database date representations to datetime.date.
    Returns None when conversion is not possible.
    """

    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    # ISO datetime
    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        pass

    # Common date formats
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except Exception:
            continue

    return None


def format_date(value):
    parsed = to_date(value)

    if parsed:
        return parsed.strftime("%d %b %Y")

    return "—" if not value else str(value)


def is_overdue(task):
    """Return True when a pending task's deadline has passed."""

    if safe_text(task.get("status")) == "Completed":
        return False

    deadline = to_date(task.get("deadline"))

    if not deadline:
        return False

    return deadline < date.today()


# ============================================================
# IMPORTANT DATE LOGIC
# ============================================================

def is_task_active_on_date(task, selected_date):
    """
    Decide whether a task should be considered active on a particular date.

    BUSINESS RULE:

    1. A task starts being active on its Task Date.
    2. If a Deadline exists, it remains active through the Deadline,
       including the deadline date.
    3. If no Deadline exists, it remains active only on its Task Date.
    4. Completed tasks are excluded from pending/current views.

    Example:
        Task Date = 24 Aug
        Deadline  = 25 Aug

        24 Aug -> visible
        25 Aug -> visible
        26 Aug -> not visible

    This is the main fix for the disappearing-task problem.
    """

    if safe_text(task.get("status")) == "Completed":
        return False

    task_date = to_date(task.get("task_date"))
    deadline = to_date(task.get("deadline"))

    if not task_date:
        return False

    # A task cannot become active before its scheduled task date.
    if selected_date < task_date:
        return False

    # No deadline = active only on its scheduled date.
    if not deadline:
        return selected_date == task_date

    # Deadline is inclusive.
    return selected_date <= deadline


def get_active_tasks_for_date(selected_date, include_completed=False):
    """
    Return tasks that are active on selected_date.

    This function deliberately reads all stored tasks and applies the
    business rule in Python. It avoids depending on a database query
    that only looks at task_date.
    """

    tasks = get_all_tasks()
    result = []

    for task in tasks:

        if not include_completed:
            if safe_text(task.get("status")) == "Completed":
                continue

        task_date = to_date(task.get("task_date"))
        deadline = to_date(task.get("deadline"))

        if not task_date:
            continue

        if include_completed:
            if task_date <= selected_date:
                if deadline:
                    if selected_date <= deadline:
                        result.append(task)
                elif selected_date == task_date:
                    result.append(task)
            continue

        if is_task_active_on_date(task, selected_date):
            result.append(task)

    return result


def get_pending_dashboard_tasks(start_date, end_date):
    """
    Return pending tasks that need attention between start_date and end_date.

    IMPORTANT:
    A task is included when its active period overlaps the dashboard
    window.

    Examples:

        Task Date 24 Aug, Deadline 25 Aug
            -> appears on 24 Aug and 25 Aug.

        Task Date 26 Aug, Deadline 27 Aug
            -> appears in the upcoming section on 26/27 Aug.

        Task Date 24 Aug, no deadline
            -> appears only on 24 Aug.

    Overdue tasks whose deadline is already before start_date are not
    included here because the dashboard's upcoming section is intended
    for the current date and future workload.
    """

    all_tasks = get_all_tasks()
    result = []

    for task in all_tasks:

        if safe_text(task.get("status")) == "Completed":
            continue

        task_date = to_date(task.get("task_date"))
        deadline = to_date(task.get("deadline"))

        if not task_date:
            continue

        # A task with no deadline exists only on its task date.
        if not deadline:

            if start_date <= task_date <= end_date:
                result.append(task)

            continue

        # Task's active interval:
        # task_date ---------------- deadline
        #
        # Dashboard window:
        # start_date ---------------- end_date
        #
        # Intervals overlap when:
        # task_date <= end_date AND deadline >= start_date

        if task_date <= end_date and deadline >= start_date:
            result.append(task)

    # Sort by deadline first, then task date, then priority.
    priority_order = {
        "Urgent": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    result.sort(
        key=lambda task: (
            to_date(task.get("deadline")) or date.max,
            to_date(task.get("task_date")) or date.max,
            priority_order.get(
                safe_text(task.get("priority")),
                9,
            ),
            safe_text(task.get("title")).lower(),
        )
    )

    return result


def render_task_card(task, key_prefix="task"):
    """
    Reusable task card used by Home and Tasks pages.
    """

    current_status = (
        safe_text(task.get("status")) == "Completed"
    )

    with st.container(border=True):

        col1, col2 = st.columns([0.06, 0.94])

        checked = col1.checkbox(
            "",
            value=current_status,
            key=f"{key_prefix}_status_{task['id']}",
        )

        if checked != current_status:

            toggle_task_status(
                task["id"],
                checked,
            )

            st.rerun()

        title = safe_text(task.get("title")) or "Untitled Task"

        title_display = (
            f"~~{title}~~"
            if current_status
            else title
        )

        col2.markdown(
            f"### {priority_icon(task.get('priority'))} "
            f"{title_display}"
        )

        client = safe_text(task.get("client_name"))

        if client:
            col2.caption(
                f"👤 Client: **{client}**"
            )

        meta1, meta2, meta3, meta4 = col2.columns(4)

        meta1.caption(
            f"📅 {format_date(task.get('task_date'))}"
        )

        meta2.caption(
            f"📝 {number(task.get('total_words'))} words"
        )

        meta3.caption(
            f"💻 {safe_text(task.get('software')) or '—'}"
        )

        meta4.caption(
            f"💰 {money(task.get('price'))}"
        )

        deadline = to_date(task.get("deadline"))

        if deadline:

            if (
                not current_status
                and deadline < date.today()
            ):
                col2.error(
                    f"⚠️ OVERDUE · {format_date(deadline)}"
                )

            elif deadline == date.today():

                col2.warning(
                    "⚠️ DEADLINE TODAY"
                )

            elif deadline == date.today() + timedelta(days=1):

                col2.caption(
                    f"🟠 Deadline tomorrow · "
                    f"{format_date(deadline)}"
                )

            else:

                col2.caption(
                    f"Deadline · {format_date(deadline)}"
                )

        if task.get("category"):

            col2.caption(
                f"📂 {safe_text(task.get('category'))}"
            )

        if task.get("description"):
            col2.write(
                safe_text(task.get("description"))
            )

        if task.get("notes"):

            with col2.expander("📝 Notes"):

                col2.write(
                    safe_text(task.get("notes"))
                )


def render_edit_delete(task):
    """
    Render the edit/delete section for a task.
    """

    task_id = task["id"]
    current_status = (
        safe_text(task.get("status")) == "Completed"
    )

    with st.expander("⚙️ Edit / Delete"):

        edited_title = st.text_input(
            "Task Title",
            value=safe_text(task.get("title")),
            key=f"edit_title_{task_id}",
        )

        edited_client = st.text_input(
            "Client Name",
            value=safe_text(task.get("client_name")),
            key=f"edit_client_{task_id}",
        )

        e1, e2 = st.columns(2)

        with e1:

            original_task_date = (
                to_date(task.get("task_date"))
                or date.today()
            )

            edited_date = st.date_input(
                "Task Date",
                value=original_task_date,
                key=f"edit_date_{task_id}",
            )

            original_deadline = to_date(
                task.get("deadline")
            )

            edited_deadline = st.date_input(
                "Deadline",
                value=original_deadline,
                key=f"edit_deadline_{task_id}",
            )

            edited_status = st.selectbox(
                "Status",
                ["Pending", "Completed"],
                index=1 if current_status else 0,
                key=f"edit_status_{task_id}",
            )

        with e2:

            original_category = safe_text(
                task.get("category")
            ) or "Other"

            if original_category not in CATEGORIES:
                original_category = "Other"

            edited_category = st.selectbox(
                "Category",
                CATEGORIES,
                index=CATEGORIES.index(original_category),
                key=f"edit_category_{task_id}",
            )

            original_priority = safe_text(
                task.get("priority")
            ) or "Medium"

            if original_priority not in PRIORITIES:
                original_priority = "Medium"

            edited_priority = st.selectbox(
                "Priority",
                PRIORITIES,
                index=PRIORITIES.index(original_priority),
                key=f"edit_priority_{task_id}",
            )

            edited_words = st.number_input(
                "Total Words",
                min_value=0,
                value=int(task.get("total_words") or 0),
                step=100,
                key=f"edit_words_{task_id}",
            )

            edited_price = st.number_input(
                "Price (₹)",
                min_value=0.0,
                value=float(task.get("price") or 0),
                step=5.0,
                key=f"edit_price_{task_id}",
            )

        edited_software = st.text_input(
            "Software / Work Details",
            value=safe_text(task.get("software")),
            key=f"edit_software_{task_id}",
        )

        edited_description = st.text_area(
            "Description",
            value=safe_text(task.get("description")),
            key=f"edit_description_{task_id}",
        )

        edited_notes = st.text_area(
            "Notes",
            value=safe_text(task.get("notes")),
            key=f"edit_notes_{task_id}",
        )

        b1, b2 = st.columns(2)

        with b1:

            if st.button(
                "💾 Save Changes",
                key=f"save_{task_id}",
                type="primary",
                use_container_width=True,
            ):

                if not edited_title.strip():

                    st.error(
                        "Task title cannot be empty."
                    )

                else:

                    update_task(
                        task_id=task_id,
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
                        total_words=int(edited_words),
                        software=edited_software.strip(),
                        category=edited_category,
                        priority=edited_priority,
                        price=float(edited_price),
                        notes=edited_notes.strip(),
                    )

                    st.success(
                        "Task updated successfully."
                    )

                    st.rerun()

        with b2:

            if st.button(
                "🗑️ Delete Task",
                key=f"delete_{task_id}",
                use_container_width=True,
            ):

                st.session_state[
                    f"confirm_delete_{task_id}"
                ] = True

        if st.session_state.get(
            f"confirm_delete_{task_id}",
            False,
        ):

            st.warning(
                "Are you sure you want to delete this task?"
            )

            d1, d2 = st.columns(2)

            with d1:

                if st.button(
                    "Yes, delete",
                    key=f"confirm_{task_id}",
                    type="primary",
                    use_container_width=True,
                ):

                    delete_task(task_id)

                    st.session_state[
                        f"confirm_delete_{task_id}"
                    ] = False

                    st.success("Task deleted.")

                    st.rerun()

            with d2:

                if st.button(
                    "Cancel",
                    key=f"cancel_{task_id}",
                    use_container_width=True,
                ):

                    st.session_state[
                        f"confirm_delete_{task_id}"
                    ] = False

                    st.rerun()


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
        "A quick overview of your work, tasks and earnings."
        "</div>",
        unsafe_allow_html=True,
    )

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
    # TODAY'S ACTIVE TASKS
    # --------------------------------------------------------

    today = date.today()

    st.subheader(
        f"Today's Tasks · {today.strftime('%d %B %Y')}"
    )

    today_tasks = get_active_tasks_for_date(today)

    if not today_tasks:

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

        st.caption(
            f"{len(today_tasks)} active pending task(s)"
        )

        for task in today_tasks:

            render_task_card(
                task,
                key_prefix="home",
            )

    st.divider()

    # --------------------------------------------------------
    # UPCOMING / OUTSTANDING TASKS
    # --------------------------------------------------------

    st.subheader(
        "Upcoming & Outstanding Tasks"
    )

    upcoming_end = today + timedelta(days=7)

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
            f"requiring attention from "
            f"{today.strftime('%d %b')} to "
            f"{upcoming_end.strftime('%d %b %Y')}."
        )

        for task in upcoming[:15]:

            task_date_value = task.get("task_date")
            deadline_value = task.get("deadline")

            task_date_obj = to_date(task_date_value)
            deadline_obj = to_date(deadline_value)

            # Determine the most useful status message.
            if deadline_obj:

                if deadline_obj < today:

                    deadline_status = (
                        f"⚠️ OVERDUE · "
                        f"{format_date(deadline_obj)}"
                    )

                elif deadline_obj == today:

                    deadline_status = "🔴 DUE TODAY"

                elif deadline_obj == today + timedelta(days=1):

                    deadline_status = (
                        f"🟠 DUE TOMORROW · "
                        f"{format_date(deadline_obj)}"
                    )

                else:

                    deadline_status = (
                        f"📅 Due · "
                        f"{format_date(deadline_obj)}"
                    )

            elif task_date_obj:

                if task_date_obj == today:

                    deadline_status = "📌 TASK TODAY"

                elif task_date_obj == today + timedelta(days=1):

                    deadline_status = "🟠 TASK TOMORROW"

                else:

                    deadline_status = (
                        f"📅 Scheduled · "
                        f"{format_date(task_date_obj)}"
                    )

            else:

                deadline_status = ""

            client_text = ""

            if task.get("client_name"):

                client_text = (
                    f" · 👤 {task['client_name']}"
                )

            with st.container(border=True):

                c1, c2 = st.columns([0.06, 0.94])

                c1.write("📌")

                c2.markdown(
                    f"**{safe_text(task.get('title'))}"
                    f"{client_text}**"
                )

                if deadline_status:
                    c2.caption(deadline_status)

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
        "View and manage tasks by date."
        "</div>",
        unsafe_allow_html=True,
    )

    selected_date = st.date_input(
        "Select Date",
        value=date.today(),
    )

    # IMPORTANT:
    # Do NOT use get_tasks_by_date() here because that function
    # normally filters only by task_date.
    #
    # We instead use the active-period logic so a task with:
    # Task Date = 24 Aug
    # Deadline = 25 Aug
    #
    # appears on BOTH 24 Aug and 25 Aug.

    tasks = get_active_tasks_for_date(
        selected_date,
        include_completed=True,
    )

    completed_count = sum(
        safe_text(task.get("status")) == "Completed"
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
            "No tasks active for this date."
        )

    else:

        # Sort pending tasks first, then by deadline.
        tasks.sort(
            key=lambda task: (
                safe_text(task.get("status")) == "Completed",
                to_date(task.get("deadline")) or date.max,
                safe_text(task.get("title")).lower(),
            )
        )

        for task in tasks:

            render_task_card(
                task,
                key_prefix="tasks",
            )

            render_edit_delete(task)


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
        "Add a new task to your workload."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("new_task_form"):

        st.subheader("Basic Information")

        title = st.text_input(
            "Task Title *",
            placeholder=(
                "e.g. Complete dissertation methodology"
            ),
        )

        client_name = st.text_input(
            "Client Name",
            placeholder=(
                "e.g. ABC Ltd / John / University"
            ),
        )

        description = st.text_area(
            "Task Description",
            placeholder=(
                "Briefly describe what needs to be done..."
            ),
            height=100,
        )

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
                CATEGORIES,
            )

        priority = st.select_slider(
            "Priority",
            options=PRIORITIES,
            value="Medium",
        )

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
                placeholder=(
                    "e.g. Python, Excel, SPSS"
                ),
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
            placeholder=(
                "Additional information, instructions "
                "or reminders..."
            ),
            height=100,
        )

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

            elif (
                deadline is not None
                and deadline < task_date
            ):

                st.error(
                    "Deadline cannot be earlier than the Task Date."
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
        "Analyse your workload, words and earnings."
        "</div>",
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
            format_func=lambda x: datetime(
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

        # Make sure numeric columns are numeric.
        df["total_words"] = pd.to_numeric(
            df["total_words"],
            errors="coerce",
        ).fillna(0)

        df["price"] = pd.to_numeric(
            df["price"],
            errors="coerce",
        ).fillna(0)

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
            df["total_words"].sum()
        )

        completed_words = int(
            df.loc[
                completed_mask,
                "total_words",
            ].sum()
        )

        total_value = float(
            df["price"].sum()
        )

        completed_value = float(
            df.loc[
                completed_mask,
                "price",
            ].sum()
        )

        completion_rate = (
            completed_tasks / total_tasks * 100
            if total_tasks > 0
            else 0
        )

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
            df["task_date"],
            errors="coerce",
        )

        daily_tasks = (
            df.dropna(subset=["task_date"])
            .groupby("task_date")
            .size()
            .rename("Tasks")
        )

        st.subheader("Tasks per Day")

        if not daily_tasks.empty:
            st.bar_chart(daily_tasks)
        else:
            st.info("No daily task data available.")

        daily_words = (
            df.dropna(subset=["task_date"])
            .groupby("task_date")["total_words"]
            .sum()
            .rename("Words")
        )

        st.subheader("Words per Day")

        if not daily_words.empty:
            st.line_chart(daily_words)
        else:
            st.info("No word data available.")

        daily_value = (
            df.dropna(subset=["task_date"])
            .groupby("task_date")["price"]
            .sum()
            .rename("Value")
        )

        st.subheader("Value per Day")

        if not daily_value.empty:
            st.line_chart(daily_value)
        else:
            st.info("No value data available.")

        # ----------------------------------------------------
        # CLIENT ANALYSIS
        # ----------------------------------------------------

        st.subheader("Client Summary")

        client_summary = (
            df.assign(
                client_name=df["client_name"]
                .fillna("")
                .replace("", "No Client")
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
            df.assign(
                category=df["category"]
                .fillna("Other")
            )
            .groupby("category")
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
        "Find tasks using client, title, software or other filters."
        "</div>",
        unsafe_allow_html=True,
    )

    tasks = get_all_tasks()

    if not tasks:

        st.info("No tasks available.")

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

            priority_filter = st.selectbox(
                "Priority",
                [
                    "All",
                    "Low",
                    "Medium",
                    "High",
                    "Urgent",
                ],
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

        if search.strip():

            query = search.lower().strip()

            searchable_columns = [
                "title",
                "client_name",
                "description",
                "software",
                "notes",
                "category",
                "priority",
            ]

            mask = pd.Series(
                False,
                index=filtered.index,
            )

            for column in searchable_columns:

                if column not in filtered.columns:
                    continue

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
                        regex=False,
                    )
                )

            filtered = filtered[mask]

        if status_filter != "All":

            filtered = filtered[
                filtered["status"] == status_filter
            ]

        if priority_filter != "All":

            filtered = filtered[
                filtered["priority"] == priority_filter
            ]

        if category_filter != "All":

            filtered = filtered[
                filtered["category"] == category_filter
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

            display_columns = [
                column
                for column in display_columns
                if column in filtered.columns
            ]

            display_df = filtered[
                display_columns
            ].copy()

            display_df.columns = [
                {
                    "title": "Task",
                    "client_name": "Client",
                    "task_date": "Date",
                    "deadline": "Deadline",
                    "status": "Status",
                    "total_words": "Words",
                    "software": "Software",
                    "category": "Category",
                    "priority": "Priority",
                    "price": "Price",
                }.get(column, column)
                for column in display_df.columns
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
        "Export and review your stored task data."
        "</div>",
        unsafe_allow_html=True,
    )

    tasks = get_all_tasks()

    if not tasks:

        st.info("No data available.")

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
                pd.to_numeric(
                    df["total_words"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            ),
        )

        c3.metric(
            "Total Value",
            money(
                pd.to_numeric(
                    df["price"],
                    errors="coerce",
                )
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

        st.subheader("Stored Data")

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

        display_columns = [
            column
            for column in display_columns
            if column in df.columns
        ]

        display_df = df[
            display_columns
        ].copy()

        display_df.columns = [
            {
                "title": "Task",
                "client_name": "Client",
                "task_date": "Date",
                "deadline": "Deadline",
                "status": "Status",
                "total_words": "Words",
                "software": "Software",
                "category": "Category",
                "priority": "Priority",
                "price": "Price",
            }.get(column, column)
            for column in display_df.columns
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
