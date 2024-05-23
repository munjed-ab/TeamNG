from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CustomUser, Project, Activity, Holiday, Department, Location, Role
from datetime import *
from django.db.models import F, Sum, Q
from django.contrib import messages
from django.db import transaction
from .forms import CustomUserForm, CustomUserUpdateForm, ProjectForm, ActivityForm, DepartmentForm, LocationForm, HolidayForm
from django.core.exceptions import ValidationError
from .tasks import send_signup_email
from .api.views import getUserSupervisor

#########################################################################
#              _           _          _____            _             _  #
#     /\      | |         (_)        / ____|          | |           | | #
#    /  \   __| |_ __ ___  _ _ __   | |     ___  _ __ | |_ _ __ ___ | | #
#   / /\ \ / _` | '_ ` _ \| | '_ \  | |    / _ \| '_ \| __| '__/ _ \| | #
#  / ____ \ (_| | | | | | | | | | | | |___| (_) | | | | |_| | | (_) | | #
# /_/    \_\__,_|_| |_| |_|_|_| |_|  \_____\___/|_| |_|\__|_|  \___/|_| #
#########################################################################


@login_required(login_url="login")
def users(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")
    
    users = CustomUser.objects.filter(
        is_superuser = False,
    ).order_by("username")

    _users = []
    for user in users:
        _user = {}
        _user["ID"] = str(user.id)
        _user["profile"] = str(user.profile.profile_img.url)
        _user["username"] = str(user.username)
        _user["first_name"] = str(user.first_name)
        _user["last_name"] = str(user.last_name)
        _user["email"] = str(user.email)
        _user["role"] = str(user.role)
        _user["super"] = getUserSupervisor(user)
        _users.append(_user)

    context = {
        "users":_users
    }
    return render(request, "project_manager/admin_control/users/users.html", context)


@login_required(login_url="login")
def create_new_user(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    form = CustomUserForm()
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['password1'] == form.cleaned_data['password2']:
                user = form.save(commit=False)
                form.clean_daily_hours()
                user.username = user.username.lower()
                user.save()
                messages.success(request,
                "User has been created successfully.")
                send_signup_email.delay(user.email)
                return redirect('users')  # Redirect to a success page
            else:
                messages.error(request,
                "Passwords are different, please check again.")
        else:
            messages.error(request,
            "Invalid inputs, please check again!")

    context = {
        "form":form
    }
    return render(request, "project_manager/admin_control/users/create_user.html", context)


@login_required(login_url="login")
def edit_user(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    user = CustomUser.objects.get(
        id=int(pk)
    )
    form = CustomUserUpdateForm(instance=user)

    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            with transaction.atomic():
            # Get the cleaned data from the form
                cleaned_data = form.cleaned_data
                form.clean_daily_hours()
                # Apply changes to the user object
                user.username = cleaned_data['username'].lower()
                user.first_name = cleaned_data['first_name']
                user.last_name = cleaned_data['last_name']
                user.email = cleaned_data['email']
                user.daily_hours = cleaned_data['daily_hours']
                user.department = cleaned_data['department']
                user.location = cleaned_data['location']
                user.role = cleaned_data['role']

                try:
                    user.full_clean()  # Validate the user object
                    user.save()
                    messages.success(request, "User information has been updated successfully.")
                    return redirect('users')  # Redirect to a success page
                except ValidationError as e:
                    messages.error(request, e.message_dict)
        else:
            messages.error(request, "Invalid inputs, please check again!")

    context = {
        "form": form
    }
    return render(request, "project_manager/admin_control/users/edit_user.html", context)


@login_required(login_url="login")
def projects(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")
    
    projects = Project.objects.all()

    context = {
        "projects":projects
    }
    return render(request, "project_manager/admin_control/projects/projects.html", context)


@login_required(login_url="login")
def create_project(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    form = ProjectForm()
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Project has been added successfully.")
            return redirect("projects")
        else:
            messages.error(request, "Invalid inputs")
    
    context = {
        "form":form
    }
    return render(request, "project_manager/admin_control/projects/create_project.html", context)


@login_required(login_url="login")
def edit_project(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    project = Project.objects.get(id=pk)
    if request.method == "POST":
        name = request.POST["project_name"]
        project.project_name = name
        project.save()
        messages.success(request, "Project information has been updated successfully.")
        return redirect("projects")
    
    context = {
        "project":project
    }
    return render(request, "project_manager/admin_control/projects/edit_project.html", context)


@login_required(login_url="login")
def activities(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")
    
    activities = Activity.objects.all()
    context = {
        "activities":activities
    }
    return render(request, "project_manager/admin_control/activity/activities.html", context)


@login_required(login_url="login")
def create_activity(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    form = ActivityForm()
    if request.method == "POST":
        form = ActivityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Activity has been added successfully.")
            return redirect("activities")
        else:
            messages.error(request, "Invalid inputs")
    
    context = {
        "form":form
    }
    return render(request, "project_manager/admin_control/activity/create_activity.html", context)


@login_required(login_url="login")
def edit_activity(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    activity = Activity.objects.get(id=pk)
    if request.method == "POST":
        name = request.POST["activity_name"]
        activity.activity_name = name
        activity.save()
        messages.success(request, "Activity information has been updated successfully.")
        return redirect("activities")
    
    context = {
        "activity":activity
    }
    return render(request, "project_manager/admin_control/activity/edit_activity.html", context)


@login_required(login_url="login")
def departments(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")
    
    departments = Department.objects.all()
    context = {
        "departments":departments
    }
    return render(request, "project_manager/admin_control/departments/departments.html", context)


@login_required(login_url="login")
def create_dept(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    form = DepartmentForm()
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department has been added successfully.")
            return redirect("departments")
        else:
            messages.error(request, "Invalid inputs")
    
    context = {
        "form":form
    }
    return render(request, "project_manager/admin_control/departments/create_dept.html", context)


@login_required(login_url="login")
def edit_dept(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    dept = Department.objects.get(id=pk)
    if request.method == "POST":
        name = request.POST["dept_name"]
        dept.dept_name = name
        dept.save()
        messages.success(request, "Department information has been updated successfully.")
        return redirect("departments")
    
    context = {
        "dept":dept
    }
    return render(request, "project_manager/admin_control/departments/edit_dept.html", context)


@login_required(login_url="login")
def locations(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")
    
    locations = Location.objects.all()
    context = {
        "locations":locations
    }
    return render(request, "project_manager/admin_control/locations/locations.html", context)


@login_required(login_url="login")
def create_loc(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    form = LocationForm()
    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Location has been added successfully.")
            return redirect("locations")
        else:
            messages.error(request, "Invalid inputs")
    
    context = {
        "form":form
    }
    return render(request, "project_manager/admin_control/locations/create_loc.html", context)


@login_required(login_url="login")
def edit_loc(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    loc = Location.objects.get(id=pk)
    if request.method == "POST":
        name = request.POST["loc_name"]
        loc.loc_name = name
        loc.save()
        messages.success(request, "Location information has been updated successfully.")
        return redirect("locations")
    
    context = {
        "loc":loc
    }
    return render(request, "project_manager/admin_control/locations/edit_loc.html", context)


@login_required(login_url="login")
def holidays(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")
    
    holidays = Holiday.objects.all()
    context = {
        "holidays":holidays
    }
    return render(request, "project_manager/admin_control/holidays/holidays.html", context)


@login_required(login_url="login")
def create_holiday(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    form = HolidayForm()
    if request.method == "POST":
        form = HolidayForm(request.POST)
        if form.is_valid():
            try:
                date = request.POST["holiday_date"]
                form.holiday_date = date
                form.clean_name()
                form.save()
                messages.success(request, "Holiday has been added successfully.")
                return redirect("holidays")
            except:
                messages.error(request, "Holiday name must not be numerical.")
        else:
            messages.error(request, "Invalid inputs")
    
    context = {
        "form":form
    }
    return render(request, "project_manager/admin_control/holidays/create_holiday.html", context)


@login_required(login_url="login")
def edit_holiday(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not request.user.role.name=="Admin":
        redirect("dashboard")

    holiday = Holiday.objects.get(id=pk)
    if request.method == "POST":
        name = request.POST["holiday_name"]
        date = request.POST["holiday_date"]
        if str(name).isdigit():
            messages.error(request, "Holiday name must not be numerical.")
            return redirect("holidays")
        holiday.holiday_name = name
        holiday.holiday_date = date
        holiday.save()
        messages.success(request, "Holiday information has been updated successfully.")
        return redirect("holidays")
    
    context = {
        "holiday":holiday
    }
    return render(request, "project_manager/admin_control/holidays/edit_holiday.html", context)





##########################################################################################
#                       _           _        ____                       _                #
#     /\               | |         (_)      / __ \                     (_)               #
#    /  \   _ __   __ _| |_   _ ___ _ ___  | |  | |_   _____ _ ____   ___  _____      __ #
#   / /\ \ | '_ \ / _` | | | | / __| / __| | |  | \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / / #
#  / ____ \| | | | (_| | | |_| \__ \ \__ \ | |__| |\ V /  __/ |   \ V /| |  __/\ V  V /  #
# /_/    \_\_| |_|\__,_|_|\__, |___/_|___/  \____/  \_/ \___|_|    \_/ |_|\___| \_/\_/   #
#                          __/ |                                                         #
#                         |___/                                                          #
##########################################################################################


@login_required(login_url='login')
def overview(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    if not (request.user.ov or request.user.role.name == "Admin" or request.user.role.name == "Director"):
        redirect("dashboard")
    
    dir = Role.objects.get(name="Director")
    users = CustomUser.objects.filter(
        ~Q(role=dir.id),
        ~Q(is_superuser=True)
    ).order_by("username")

    departments = Department.objects.all()
    projects = Project.objects.all()

    context = {
        "users":users,
        "departments":departments,
        "projects" : projects
    }
    return render(request, "project_manager/admin_control/analysis_overview/overview.html", context)



###########################################################################
#              _           _         _____                       _        #
#     /\      | |         (_)       |  __ \                     | |       #
#    /  \   __| |_ __ ___  _ _ __   | |__) |___ _ __   ___  _ __| |_ ___  #
#   / /\ \ / _` | '_ ` _ \| | '_ \  |  _  // _ \ '_ \ / _ \| '__| __/ __| #
#  / ____ \ (_| | | | | | | | | | | | | \ \  __/ |_) | (_) | |  | |_\__ \ #
# /_/    \_\__,_|_| |_| |_|_|_| |_| |_|  \_\___| .__/ \___/|_|   \__|___/ #
#                                              | |                        #
#                                              |_|                        #
###########################################################################


def report_admin_act(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    elif not (request.user.role.name=="Admin" or request.user.role.name=="Director"):
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")

    user = CustomUser.objects.get(id=pk)

    dir = Role.objects.get(name="Director")
    users = CustomUser.objects.filter(
        ~Q(role=dir.id),
        ~Q(is_superuser=True)
    ).order_by("username")
    departments = Department.objects.all()
    projects = Project.objects.all()

    context = {
        "user":user,
        "users":users,
        "departments":departments,
        "projects" : projects
    }
    return render(request, "project_manager/reports/admins/report_admin_activities.html", context)

def report_admin_pro(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    elif not (request.user.role.name=="Admin" or request.user.role.name=="Director"):
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    dir = Role.objects.get(name="Director")
    users = CustomUser.objects.filter(
        ~Q(role=dir.id),
        ~Q(is_superuser=True)
    ).order_by("username")
    departments = Department.objects.all()
    projects = Project.objects.all()

    context = {
        "user":user,
        "users":users,
        "departments":departments,
        "projects" : projects
    }
    return render(request, "project_manager/reports/admins/report_admin_projects.html", context)


def report_admin_leave(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    elif not (request.user.role.name=="Admin" or request.user.role.name=="Director"):
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    dir = Role.objects.get(name="Director")
    users = CustomUser.objects.filter(
        ~Q(role=dir.id),
        ~Q(is_superuser=True)
    ).order_by("username")
    departments = Department.objects.all()
    projects = Project.objects.all()

    context = {
        "user":user,
        "users":users,
        "departments":departments,
        "projects" : projects
    }
    return render(request, "project_manager/reports/admins/report_admin_leaves.html", context)


def report_admin_overview(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    elif not (request.user.role.name=="Admin" or request.user.role.name=="Director"):
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    dir = Role.objects.get(name="Director")
    users = CustomUser.objects.filter(
        ~Q(role=dir.id),
        ~Q(is_superuser=True)
    ).order_by("username")
    departments = Department.objects.all()
    projects = Project.objects.all()

    context = {
        "user":user,
        "users":users,
        "departments":departments,
        "projects" : projects
    }
    return render(request, "project_manager/reports/admins/report_admin_expected_hours.html", context)



def report_admin_pro_act(request, pk):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    elif not (request.user.role.name=="Admin" or request.user.role.name=="Director"):
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    user = CustomUser.objects.get(id=pk)
    dir = Role.objects.get(name="Director")
    users = CustomUser.objects.filter(
        ~Q(role=dir.id),
        ~Q(is_superuser=True)
    ).order_by("username")
    departments = Department.objects.all()
    projects_count = Project.objects.all().count()
    activities_count = Activity.objects.all().count()
    
    context = {
        "user":user,
        "users":users,
        "departments":departments,
        "projects_count":projects_count,
        "activities_count":activities_count
    }
    return render(request, "project_manager/reports/admins/report_admin_pro_act.html", context)


def report_holiday(request):
    if not request.user.is_authenticated:
        redirect('login')
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are banned.")
        return redirect("login")
    elif not (request.user.role.name=="Admin" or request.user.role.name=="Director"):
        messages.error(request,
        "Access Denied.")
        return redirect("dashboard")
    
    return render(request, "project_manager/reports/admins/report_admin_holidays.html", context={})
    
