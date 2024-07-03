from django.shortcuts import render, redirect
from .models import CustomUser, Project, Activity, Role
from django.contrib import messages
from django.db.models import F, Sum, Q


#################################################
#  __  __                                       #
# |  \/  |                                      #
# | \  / | __ _ _ __   __ _  __ _  ___ _ __     #
# | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__|    #
# | |  | | (_| | | | | (_| | (_| |  __/ |       #
# |_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|       #
#                            __/ |              #
#   ____                    |___/               #
#  / __ \                     (_)               #
# | |  | |_   _____ _ ____   ___  _____      __ #
# | |  | \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / / #
# | |__| |\ V /  __/ |   \ V /| |  __/\ V  V /  #
#  \____/  \_/ \___|_|    \_/ |_|\___| \_/\_/   #
#################################################


def manager_overview(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Manager":
        redirect("dashboard")

    manager = request.user

    department_id = str(manager.department.id)
    dept_name = str(manager.department.dept_name)
    location_id = str(manager.location.id)
    loc_name = str(manager.location.loc_name)

    dir = Role.objects.get(name="Director")
    adm = Role.objects.get(name="Admin")
    users = CustomUser.objects.filter(
        ~Q(is_superuser=True),
        ~Q(role=dir.id),
        ~Q(role=adm.id),
        department=manager.department.id,
        location=manager.location.id
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



##################################################################################
#  __  __                                                               _        #
# |  \/  |                                                             | |       #
# | \  / | __ _ _ __   __ _  __ _  ___ _ __   _ __ ___ _ __   ___  _ __| |_ ___  #
# | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__| | '__/ _ \ '_ \ / _ \| '__| __/ __| #
# | |  | | (_| | | | | (_| | (_| |  __/ |    | | |  __/ |_) | (_) | |  | |_\__ \ #
# |_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|    |_|  \___| .__/ \___/|_|   \__|___/ #
#                            __/ |                    | |                        #
#                           |___/                     |_|                        #
##################################################################################


def report_manager_act(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    elif not request.user.role.name=="Manager":
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    
    projects = Project.objects.all()
    dir = Role.objects.get(name="Director")
    adm = Role.objects.get(name="Admin")
    users = CustomUser.objects.filter(
        ~Q(is_superuser=True),
        ~Q(role=dir.id),
        ~Q(role=adm.id),
        department=user.department.id,
        location=user.location.id
    ).order_by("username")

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
    elif not request.user.role.name=="Manager":
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()
    dir = Role.objects.get(name="Director")
    adm = Role.objects.get(name="Admin")
    users = CustomUser.objects.filter(
        ~Q(is_superuser=True),
        ~Q(role=dir.id),
        ~Q(role=adm.id),
        department=user.department.id,
        location=user.location.id
    ).order_by("username")

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
    elif not request.user.role.name=="Manager":
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    dir = Role.objects.get(name="Director")
    adm = Role.objects.get(name="Admin")
    users = CustomUser.objects.filter(
        ~Q(is_superuser=True),
        ~Q(role=dir.id),
        ~Q(role=adm.id),
        department=user.department.id,
        location=user.location.id
    ).order_by("username")

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
    elif not request.user.role.name=="Manager":
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()
    dir = Role.objects.get(name="Director")
    adm = Role.objects.get(name="Admin")
    users = CustomUser.objects.filter(
        ~Q(is_superuser=True),
        ~Q(role=dir.id),
        ~Q(role=adm.id),
        department=user.department.id,
        location=user.location.id
    ).order_by("username")

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
    elif not request.user.role.name=="Manager":
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    dir = Role.objects.get(name="Director")
    adm = Role.objects.get(name="Admin")
    users = CustomUser.objects.filter(
        ~Q(is_superuser=True),
        ~Q(role=dir.id),
        ~Q(role=adm.id),
        department=user.department.id,
        location=user.location.id
    ).order_by("username")
    
    projects_count = Project.objects.all().count()
    activities_count = Activity.objects.all().count()

    context = {
        "user" : user,
        "users":users,
        "projects_count":projects_count,
        "activities_count":activities_count
    }
    return render(request, "project_manager/reports/managers/report_manager_pro_act.html", context)

def report_manager_missed_hours(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    elif not request.user.role.name=="Manager":
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()
    dir = Role.objects.get(name="Director")
    adm = Role.objects.get(name="Admin")
    users = CustomUser.objects.filter(
        ~Q(is_superuser=True),
        ~Q(role=dir.id),
        ~Q(role=adm.id),
        department=user.department.id,
        location=user.location.id
    ).order_by("username")

    context = {
        "user" : user,
        "projects" : projects,
        "users" : users
    }
    return render(request, "project_manager/reports/managers/report_manager_missed_hours.html", context)