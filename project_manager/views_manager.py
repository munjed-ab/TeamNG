from django.shortcuts import render, redirect
from .models import CustomUser, Project, Activity, Holiday, Department, Location
from django.contrib import messages


def manager_overview(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.is_manager:
        redirect("dashboard")

    manager = request.user
    department_id = str(manager.department.id)
    dept_name = str(manager.department.dept_name)
    location_id = str(manager.location.id)
    loc_name = str(manager.location.loc_name)
    users = CustomUser.objects.filter(
        is_superuser = False,
        is_admin=False,
        department=manager.department,
        location=manager.location
    ).order_by("username")
    projects = Project.objects.all()

    context = {
        "users":users,
        "projects" : projects,
        "department_id" : department_id,
        "location_id" : location_id,
        "dept_name":dept_name,
        "loc_name":loc_name
    }
    return render(request, "project_manager/manager/analysis_overview/overview_manager.html", context)

def report_manager_act(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")

    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()
    users = CustomUser.objects.filter(
        is_superuser=False,
        is_admin=False,
        location=user.location.id,
        department=user.department.id
    )

    context = {
        "user" : user,
        "projects" : projects,
        "users" : users
    }
    return render(request, "project_manager/reports/managers/report_manager_activities.html", context)

def report_manager_pro(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")

    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()
    users = CustomUser.objects.filter(
        is_superuser=False,
        is_admin=False,
        location=user.location.id,
        department=user.department.id
    )

    context = {
        "user" : user,
        "projects" : projects,
        "users" : users
    }
    return render(request, "project_manager/reports/managers/report_manager_projects.html", context)

def report_manager_leave(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")

    user = CustomUser.objects.get(id=pk)
    users = CustomUser.objects.filter(
        is_superuser=False,
        is_admin=False,
        location=user.location.id,
        department=user.department.id
    )

    context = {
        "user" : user,
        "users" : users
    }
    return render(request, "project_manager/reports/managers/report_manager_leaves.html", context)

def report_manager_overview(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")

    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()
    users = CustomUser.objects.filter(
        is_superuser=False,
        is_admin=False,
        location=user.location.id,
        department=user.department.id
    )

    context = {
        "user" : user,
        "projects" : projects,
        "users" : users
    }
    return render(request, "project_manager/reports/managers/report_manager_expected_hours.html", context)

def report_manager_pro_act(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")

    user = CustomUser.objects.get(id=pk)
    users = CustomUser.objects.filter(
        is_superuser=False,
        is_admin=False,
        location=user.location.id,
        department=user.department.id
    )

    context = {
        "user" : user,
        "users":users,
    }
    return render(request, "project_manager/reports/managers/report_manager_pro_act.html", context)