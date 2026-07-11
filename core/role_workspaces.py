"""Single source of truth for role dashboards and feature permissions."""

from django.utils.text import slugify

ROLE_WORKSPACES = {
    "super_admin": {
        "title": "Super Admin",
        "scope": "SkillBuddy Company · All colleges",
        "accent": "#6c5ce7",
        "metrics": ["Total Colleges", "Active Colleges", "Trial Colleges", "Subscription Revenue", "Active Users", "Total Students", "Total Faculty", "Total Courses", "AI Usage", "Storage Usage", "Server Health", "Payment Status", "Support Tickets"],
        "sections": {
            "Manage Colleges": ["Add College", "Edit College", "Delete College", "Activate College", "Suspend College", "Extend Subscription", "Upgrade Plan", "Change Domain", "Assign Storage", "View College Analytics"],
            "Tenant Settings": ["College Logo", "Theme", "Email Settings", "SMS Settings", "AI Settings", "Payment Settings", "Branding"],
            "User Management": ["View College Users", "Reset Password", "Lock User", "Unlock User", "Disable Login", "Force Logout", "Verify Email"],
            "Roles": ["Create Roles", "Assign Roles", "Edit Roles", "Delete Roles", "Permission Matrix"],
            "Reports": ["Revenue", "Subscriptions", "Renewals", "AI Usage", "Active Users", "Server Reports"],
        },
    },
    "college_admin": {
        "title": "College Admin / Principal", "scope": "Single-college administration", "accent": "#2563eb",
        "metrics": ["Total Students", "Total Faculty", "Departments", "Attendance", "Results", "Placement Rate", "Fees", "AI Usage", "High Risk Students", "Notifications"],
        "sections": {
            "Management": ["Students", "Faculty", "Courses", "Departments", "Semesters", "Subjects", "Timetable", "Exams", "Fees", "Placements", "Certificates", "Reports", "Analytics"],
            "User Management": ["Create Student", "Create Faculty", "Reset Password", "Lock User", "Unlock User", "Disable Login", "Activate User", "Assign Role", "Change Department"],
        },
    },
    "hod": {
        "title": "Head of Department", "scope": "Department operations", "accent": "#0891b2",
        "metrics": ["Department Students", "Faculty", "Attendance", "Results", "Department Analytics", "Risk Students", "Approvals", "Reports"],
        "sections": {"Department": ["Department Students", "Faculty", "Attendance", "Results", "Department Analytics", "Risk Students", "Approvals", "Reports"]},
        "restrictions": ["Cannot create colleges", "Cannot manage subscriptions"],
        "capabilities": ["Approve faculty"],
    },
    "faculty": {
        "title": "Faculty", "scope": "Teaching workspace", "accent": "#ea580c",
        "metrics": ["Today's Classes", "Attendance", "Assignments", "Quizzes", "Student Performance", "Notifications"],
        "sections": {
            "Teaching": ["Today's Classes", "Attendance", "Assignments", "Quizzes", "Question Bank", "Student Performance"],
            "AI Tools": ["Faculty Copilot", "AI Question Generator"],
        },
        "capabilities": ["Take attendance", "Create assignments", "Generate quizzes", "Evaluate students", "View analytics"],
        "restrictions": ["Cannot manage users", "Cannot delete students", "Cannot assign roles"],
    },
    "student": {
        "title": "Student", "scope": "Personal learning workspace", "accent": "#16a34a",
        "metrics": ["Courses", "Assignments", "Results", "Attendance", "Certificates", "Placement Tracker"],
        "sections": {
            "Learning": ["Courses", "Assignments", "Results", "Attendance", "AI Tutor", "Study Planner"],
            "Career": ["Resume Builder", "Placement Tracker", "Certificates", "Profile"],
        },
        "restrictions": ["Cannot edit other users"],
    },
    "placement_officer": {
        "title": "Placement Officer", "scope": "Career and placement operations", "accent": "#db2777",
        "metrics": ["Eligible Students", "Companies", "Interviews", "Offers", "Placed Students", "Resume Reviews"],
        "sections": {"Placements": ["Eligible Students", "Companies", "Interviews", "Offers", "Placed Students", "Resume Reviews", "Analytics"]},
    },
}


def feature_slug(label):
    return slugify(label.replace("&", "and"))


def allowed_features(role):
    workspace = ROLE_WORKSPACES.get(role, {})
    return {
        feature_slug(item)
        for items in workspace.get("sections", {}).values()
        for item in items
    } | {feature_slug(item) for item in workspace.get("metrics", [])}


def feature_label(role, slug):
    workspace = ROLE_WORKSPACES.get(role, {})
    labels = workspace.get("metrics", []) + [item for values in workspace.get("sections", {}).values() for item in values]
    return next((label for label in labels if feature_slug(label) == slug), None)
