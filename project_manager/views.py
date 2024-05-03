from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .models import CustomUser, Project, Activity, Leave, Holiday, ActivityLogs, Profile
from .forms import ProfileImageForm
from decimal import Decimal
from datetime import *
import calendar
from django.contrib import messages
from datetime import datetime, timedelta
from django.db.models import Q
from django.db import transaction
from .tasks import send_notification_email
import pandas as pd
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO



#################################################################################
#  _    _      _                   ______                _   _                  #
# | |  | |    | |                 |  ____|              | | (_)                 #
# | |__| | ___| |_ __   ___ _ __  | |__ _   _ _ __   ___| |_ _  ___  _ __  ___  #
# |  __  |/ _ \ | '_ \ / _ \ '__| |  __| | | | '_ \ / __| __| |/ _ \| '_ \/ __| #
# | |  | |  __/ | |_) |  __/ |    | |  | |_| | | | | (__| |_| | (_) | | | \__ \ #
# |_|  |_|\___|_| .__/ \___|_|    |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/ #
#               | |                                                             #
#               |_|                                                             #
#################################################################################


def get_firstday_current_last_month():
    # Get the first day of the current month
    today = date.today()

    # Get the first day of the last month
    last_month = today.month - 1 if today.month > 1 else 12
    last_year = today.year if today.month > 1 else today.year - 1
    first_day_last_month = date(last_year, last_month, 1)
    first_day_last_month.strftime(f'%Y-%m-%d')

    # Get the last day of the current month
    last_day_current_month = calendar.monthrange(today.year, today.month)[1]
    last_day_current_month = date(today.year, today.month, last_day_current_month)
    last_day_current_month.strftime(f'%Y-%m-%d')
    return  first_day_last_month, last_day_current_month



def isLeaveDay(user, date):
    first_day_last_month, last_day_current_month = get_firstday_current_last_month()

    leave_days = Leave.objects.filter(
        from_user=user,
        start_date__range=[first_day_last_month, last_day_current_month],
        is_approved = True
    )
    # need improvement
    datetime_object = datetime.strptime(date, f"%Y-%m-%d")
    date_object = datetime_object.date()

    return any(leave.start_date <= date_object <= leave.end_date for leave in leave_days)


def is_before_11th():
    """
        check if today is earlier than 11
    """
    today = date.today()
    return today.day <= 11

def is_within_current_past_month(q_date):
    """
        check if the q_date : Date is within the current month
        and is it within the previous month
    """
    today = date.today()
    current_month_start = date(today.year, today.month, 1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = date(previous_month_end.year, previous_month_end.month, 1)


    is_within_current_month = current_month_start <= q_date <= today # false if q_date after today (no future allowed)
    is_within_previous_month = previous_month_start <= q_date <= previous_month_end

    return is_within_current_month, is_within_previous_month

def check_is_sun_sat(date):
    if date:
        date = pd.Timestamp(date)
        if date.dayofweek == 6:
            return True
        if date.dayofweek == 5:
            if 7 < date.day <= 14 or 21 < date.day <= 28:
                return True
            else:
                return False
        else:
            return False
    else:
        return True

def check_holiday(holidays, q_date):
    return any(holiday.holiday_date == q_date for holiday in holidays)


def get_hours_worked_on_date(user, date):
    entrylogs = ActivityLogs.objects.filter(
Q(date=date, user = user)
)
    hours_worked_on_date = sum(entry.hours_worked for entry in entrylogs)
    return hours_worked_on_date


def checkActivityInLeaveDays(user, start_date, end_date):
    data = ActivityLogs.objects.filter(user=user, date__range=[start_date, end_date])
    return any(log.hours_worked > 0 for log in data)

def get_filtered_dates(start_date:str, end_date:str, with_holidays:bool=True):
    # convert start_date and end_date to pandas Timestamp objects
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    # get holidays
    public_holidays:Holiday
    if(with_holidays):
        public_holidays = Holiday.objects.filter(holiday_date__range = [start_date, end_date])

    filtered_dates = []

    date_range = pd.date_range(start=start_date, end=end_date)
    filtered_dates = [date for date in date_range if date.dayofweek != 6]

    # get all saterdays
    saturdays = [date for date in filtered_dates if date.dayofweek == 5]
    banned_saterdays = [
        saturday
        for saturday in saturdays
        if (7 < saturday.day <= 14) or (21 < saturday.day <= 28)
    ]

    filtered_dates = [date for date in filtered_dates if date not in banned_saterdays]

    if(with_holidays):
        holiday_dates = [pd.Timestamp(holiday.holiday_date.ctime()) for holiday in public_holidays]
        # exclude public holidays
        filtered_dates = [date for date in filtered_dates if date not in holiday_dates]

    return filtered_dates



#########################################################
#  __  __       _        __      ___                    #
# |  \/  |     (_)       \ \    / (_)                   #
# | \  / | __ _ _ _ __    \ \  / / _  _____      _____  #
# | |\/| |/ _` | | '_ \    \ \/ / | |/ _ \ \ /\ / / __| #
# | |  | | (_| | | | | |    \  /  | |  __/\ V  V /\__ \ #
# |_|  |_|\__,_|_|_| |_|     \/   |_|\___| \_/\_/ |___/ #
#########################################################


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')  # Redirect to dashboard or any other page
    else:
        form = AuthenticationForm()
    return render(request, 'project_manager/login.html', {'form': form})

@login_required
def logout_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    logout(request)
    return redirect("login")

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    projects = Project.objects.all()

    user = request.user
    context = {"user":user, "projects":projects}
    return render(request, 'project_manager/dashboard.html', context)


def registerhours(request, date_picked):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    q = date_picked
    can_edit = False
    is_holiday = False
    try:
        # is to check if the date are in the approved leave dates of the user
        ###############
        if isLeaveDay(request.user, q):
            messages.error(request,
            f"You have choosed a leave date {q}.")
            return redirect("dashboard")
        ##############

        # is to check if the date is (sundays or 2nd, 4th of saterday)
        if check_is_sun_sat(q):
            messages.error(request,
            f"You have choosed a holiday date {q}.")
            return redirect("dashboard")

        # is to check whether the date are ok to edit if include:
        # - current month -> ok
        # - past month and today is earlier than 11th -> ok
        # - else -> not ok
        ##############
        q_date = datetime.strptime(date_picked, "%Y-%m-%d").date()
        is_within_current_month, is_within_previous_month = is_within_current_past_month(q_date)
        is_today_before_11th = is_before_11th()

        if is_within_current_month:
            can_edit = True
        elif is_within_previous_month and is_today_before_11th:
            can_edit = True
        else:
            can_edit = False
        ###############

        # is to check if the date are actually a holiday date
        ###############
        first_day_last_month, last_day_current_month = get_firstday_current_last_month()
        holidays = Holiday.objects.filter(
            holiday_date__range=[first_day_last_month, last_day_current_month]
        )
        
        if check_holiday(holidays, q_date):
            is_holiday = True
        ###############
    except:
        messages.error(request,f"Canceled. \
        Invalid Date.")
        return redirect("dashboard")

    entry_logs = ActivityLogs.objects.filter(
        user = request.user.id,
        date = q
    ).order_by("-created")

    total = sum(entry.hours_worked for entry in entry_logs)

    user = request.user
    projects = Project.objects.all()
    activities = Activity.objects.all()

    context = {
        "user":user,
        "projects":projects,
        "activities":activities,
        "holidays": holidays,
        "date":q,
        "entry_logs":entry_logs,
        "total":total,
        "can_edit":can_edit,
        "is_holiday":is_holiday
            }
    return render(request, 'project_manager/main_pages/registerhours.html', context)


def activity_log(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    today = date.today()
    q = request.GET.get("q",today)

    entry_logs = ActivityLogs.objects.filter(
        user = request.user.id,
        date = q
    ).order_by("-created")

    context = {"entry_logs":entry_logs, "date":q}
    return render(request, 'project_manager/main_pages/activity_log.html', context)

@transaction.atomic
def update_entry(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    user = request.user
    projects = Project.objects.all()
    activities = Activity.objects.all()
    old_entry = ActivityLogs.objects.get(id=pk)
    first_day_last_month, last_day_current_month = get_firstday_current_last_month()

    holidays = Holiday.objects.filter(
        holiday_date__range=[first_day_last_month, last_day_current_month]
    )

    if request.method == "POST":
        project_name = request.POST.get("projectName")
        project = Project.objects.get(project_name = project_name)

        activity_name = request.POST.get("activityName")
        activity = Activity.objects.get(activity_name = activity_name)

        hours = request.POST.get("quantity")
        date_picked = request.POST.get("datepicker")
        details = request.POST.get("details")

        if isLeaveDay(user, date_picked):
            messages.error(request,f"Canceled. \
            You have choosed a leave date {date_picked}.")
            return redirect("activitylogs")
        
        if check_is_sun_sat(date_picked):
            messages.error(request,
            f"You have choosed a holiday date {date_picked}.")
            return redirect("dashboard")
        
        try:
            q_date = datetime.strptime(date_picked, "%Y-%m-%d").date()
            is_within_current_month, is_within_previous_month = is_within_current_past_month(q_date)
            is_today_before_11th = is_before_11th()

            if is_within_current_month:
                pass
            elif is_within_previous_month and is_today_before_11th:
                pass
            else:
                messages.error(request,f"Canceled. \
                You can not edit on this date {date_picked}.")
                return redirect("activitylogs")

            first_day_last_month, last_day_current_month = get_firstday_current_last_month()
            holidays = Holiday.objects.filter(
                holiday_date__range=[first_day_last_month, last_day_current_month]
            )
            
            if check_holiday(holidays, date_picked):
                    messages.error(request,f"Canceled. \
                    This date is a Holiday {date_picked}.")
                    return redirect("activitylogs")

            # Check if hours entered are not None (always gonna be :) and Decimal it. else -> return
            if hours is not None:
                hours = Decimal(hours)
                if hours + get_hours_worked_on_date(user, date_picked) >= 20:
                    messages.error(request,"Canceled. \
                    You exeeded 20 hours on {date_picked}.")
                    return redirect("activitylogs")
            else:
                messages.error(request,"Canceled. \
                Something went wrong with inputs :(")
                return redirect("activitylogs")

            # Finally updating the data
            old_entry.details = details
            old_entry.date = date_picked
            old_entry.activity = activity
            old_entry.project = project
            old_entry.hours_worked = hours
            old_entry.save()
            messages.success(request,
            "Activity has been updated successfully.")
        except:
            messages.error(request,"Canceled. \
            Something went wrong :(")
            return redirect("activitylogs")

        return redirect("activitylogs")

    context = {"old_entry": old_entry,
                "projects": projects,
                "activities": activities,
                "holidays":holidays
            }
    return render(request, "project_manager/main_pages/update_entry.html", context)


def delete_entry(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    entry = ActivityLogs.objects.get(id = pk)

    if request.method == "POST":
        entry.delete()
        messages.success(request,
        "Activity has been deleted successfully.")
        return redirect("activitylogs")
    
    return render(request, "project_manager/main_pages/delete_entry.html", {"entry":entry})


def addleave(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    admins = CustomUser.objects.filter(
        is_superuser = True
    )

    managers = CustomUser.objects.all()
    if request.method == "POST":
        start_date = request.POST.get("startDate")
        end_date = request.POST.get("endDate")
        leave_type = request.POST.get("leaveType")

        try:
            days = 0 #filtered days
            v_days = 0 #real days to view it
            if start_date and end_date:
                filtered_dates = get_filtered_dates(start_date, end_date)
                days = len(filtered_dates)

                start_date = datetime.strptime(start_date, f"%Y-%m-%d")
                start_date = start_date.date()
                end_date = datetime.strptime(end_date, f"%Y-%m-%d")
                end_date = end_date.date()
                v_days = (end_date - start_date).days + 1

                if checkActivityInLeaveDays(request.user, start_date, end_date):
                    messages.error(request,
                    "Canceled. Pick dates where you have not worked on.")
                    return redirect('addleave')
            else:
                messages.error(request,
                "Something went wrong!")
                return redirect('addleave')
            
            if request.user.is_admin:
                Leave.objects.create(
                    from_user = request.user,
                    start_date = start_date,
                    end_date = end_date,
                    days = days,
                    v_days = v_days,
                    leave_type = leave_type,
                    is_approved = True
                )
            elif request.user.is_manager:
                admin_name = request.POST.get("adminName")
                admin = CustomUser.objects.get(username = admin_name)
                admin.has_notification = True
                admin.save()
                Leave.objects.create(
                    from_user = request.user,
                    to_user = admin,
                    start_date = start_date,
                    end_date = end_date,
                    days = days,
                    v_days = v_days,
                    leave_type = leave_type
                )
                send_notification_email.delay(admin.email, "leave request", request.user.username)

            else:
                manager_name = request.POST.get("managerName")
                manager = CustomUser.objects.get(username = manager_name)
                manager.has_notification = True
                manager.save()
                Leave.objects.create(
                    from_user = request.user,
                    to_user = manager,
                    start_date = start_date,
                    end_date = end_date,
                    days = days,
                    v_days = v_days,
                    leave_type = leave_type
                )
                send_notification_email.delay(manager.email, "leave request", request.user.username)
            messages.success(request,
            "Request has been sent successfully.")

        except:
            messages.error(request, "Canceled. \
            Something went wrong :(")
            return redirect('addleave')

    context = {"admins":admins, "managers":managers}
    return render(request, "project_manager/main_pages/add_leave.html", context)

def notifications(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    user = request.user

    leave_requests = Leave.objects.filter(
        to_user = user,
        is_approved = False,
        is_rejected = False
    )
    
    user.has_notification = False
    user.save()

    end = date.today()
    start = end - timedelta(days=90)  # 90 days ago

    #Filter leaves from the last 3 months, including future dates
    leave_response_rejected = Leave.objects.filter(
        from_user=user,
        is_rejected=True,
        start_date__range=[start, end + timedelta(days=365)]  # Include future dates for 1 year
    )

    leave_response_approved = Leave.objects.filter(
        from_user=user,
        is_approved=True,
        start_date__range=[start, end + timedelta(days=365)]
    )


    if request.method == "POST":
        request_id = request.POST.get("leaveRequestId")
        response = request.POST.get("response")
        try:
            leave = Leave.objects.get(id=request_id)

            if response == "reject":
                leave.is_rejected = True
                from_user = leave.from_user
                from_user.has_notification = True
                from_user.save()
                leave.save()
                email_to = from_user.email
                producer =  leave.to_user.username
                send_notification_email.delay(email_to, response, producer)

            elif response == "accept":
                leave.is_approved = True
                from_user = leave.from_user
                from_user.has_notification = True
                from_user.save()
                leave.save()
                email_to = from_user.email
                producer =  leave.to_user.username
                send_notification_email.delay(email_to, response, producer)
            else:
                messages.error(request, "Canceled. \
                Invalid Operation.")
                return redirect('notifications')

        except:
            messages.error(request,"Canceled. \
            something went wrong :(")
            return redirect('notifications')

    context = {
        "leave_requests": leave_requests,
        "leave_response_rejected":leave_response_rejected,
        "leave_response_approved":leave_response_approved
        }
    return render(request, "project_manager/notifications.html", context )

def leave_log(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    leave_logs = Leave.objects.filter(
        from_user = request.user.id
    ).order_by("-created")

    # TO REJECT EVERY LEAVE REQUEST THAT START FROM THE SAME DAY IT WAS REQUESTED
    # EDIT: IF REQUESTER ALREADY HAS NO WORKING HOURS ON "today" HE PROPABLY CAN REQUEST (HIDE FOR NOW)
    # today = date.today()
    # for leave in leave_logs:
    #     if not (leave.is_approved or leave.is_rejected) and leave.start_date == today:
    #         leave.is_rejected = True
    #         leave.save()

    context = {"leave_logs":leave_logs}
    return render(request, 'project_manager/main_pages/leave_log.html', context)


def update_leave(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    leave = Leave.objects.get(id=pk)
    admins = CustomUser.objects.filter(
        is_superuser=True
    )

    managers = CustomUser.objects.filter(
        is_manager=True,
        department=request.user.department
    )

    if request.method == "POST":
        if leave.is_approved or leave.is_rejected:
            messages.error(request, "Canceled. \
            You already have a response for your request, check your Notifications.")
            return redirect('leave_logs')
        
        start_date = request.POST.get("startDate")
        end_date = request.POST.get("endDate")
        leave_type = request.POST.get("leaveType")

        start_date = datetime.strptime(start_date, f"%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, f"%Y-%m-%d").date()
        days = (end_date - start_date).days

        if checkActivityInLeaveDays(request.user, start_date, end_date):
            messages.error(request,
            "Canceled. Pick dates where you have not worked at.")
            return redirect('leave_logs')
        
        try:
            with transaction.atomic():
                if request.user.is_manager:
                    admin_name = request.POST.get("adminName")
                    admin = CustomUser.objects.get(username=admin_name)
                    admin.has_notification = True
                    admin.save()
                    leave.to_user = admin

                elif not request.user.is_manager and not request.user.is_superuser:
                    manager_name = request.POST.get("managerName")
                    manager = CustomUser.objects.get(username=manager_name)
                    manager.has_notification = True
                    manager.save()
                    leave.to_user = manager
                
                leave.start_date = start_date
                leave.end_date = end_date
                leave.days = days
                leave.leave_type = leave_type
                leave.save()

            messages.success(request,
            "Request has been updated successfully.")
        except Exception as e:
            messages.error(request, f"Canceled. Something went wrong: {str(e)}")
            return redirect('leave_logs')

        return redirect('leave_logs')

    context = {"admins": admins, "managers": managers, "leave": leave}
    return render(request, "project_manager/main_pages/update_leave.html", context)



def delete_leave(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    leave  = Leave.objects.get(id = pk)

    if request.method == "POST":
        if leave.is_approved or leave.is_rejected:
            messages.error(request, "Canceled. \
            You already have a respond for your request, check your Notifications.")
            return redirect('leave_logs')
        user = leave.to_user
        user.has_notification = False
        user.save()
        leave.delete()
        messages.success(request,
        "Request has been deleted successfully.")
        return redirect("leave_logs")
    
    return render(request, "project_manager/main_pages/delete_leave.html", {"leave":leave})


###############################
#    ___           ____ __    #
#   / _ \_______  / _(_) /__  #
#  / ___/ __/ _ \/ _/ / / -_) #
# /_/  /_/  \___/_//_/_/\__/  #
###############################


def profile(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    user  = CustomUser.objects.get(id = pk)
    
    return render(request, "project_manager/profile/profile.html", {"user":user})

@login_required(login_url="login")
@transaction.atomic
def upload_profile_image(request):
    if request.method == 'POST':
        try:
            # Check if a profile already exists for the user
            profile = Profile.objects.get(user=request.user)
            form = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if profile.profile_img: #delete old image from the folder
                if profile.profile_img.name != "user_def.png":
                    profile.profile_img.delete()
        except Profile.DoesNotExist:
            # If no profile exists, create a new one
            form = ProfileImageForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.cleaned_data['profile_img']
            profile = form.save(commit=False)
            profile.user = request.user

            # Open the image using PIL
            image = Image.open(profile.profile_img)

            # Check if the image is not square
            if image.width != image.height:
                # Crop non-square images to make them square
                min_size = min(image.width, image.height)
                left = (image.width - min_size) / 2
                top = (image.height - min_size) / 2
                right = (image.width + min_size) / 2
                bottom = (image.height + min_size) / 2
                image = image.crop((left, top, right, bottom))

            # Resize the image to a desired size (e.g., 200x200 pixels)
            size = (200, 200)
            image.thumbnail(size)

            # Convert the image to RGB mode (if not already in RGB)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Compress and save the image
            output = BytesIO()
            image.save(output, format='JPEG', quality=80)
            output.seek(0)

            # Create an InMemoryUploadedFile from the compressed image
            profile.profile_img = InMemoryUploadedFile(
                output,
                'ImageField',
                "%s.jpg" % profile.profile_img.name.split('.')[0],
                'image/jpeg',
                output.getbuffer().nbytes,
                None
            )

            profile.save()
            return redirect('profile', request.user.id)  # Redirect to profile page after successful upload
    else:
        # If the request method is not POST, create a new form
        form = ProfileImageForm()
    
    return render(request, 'project_manager/profile/upload_profile_img.html', {'form': form})


####################
#   ____ ___  ____ #
#  / / // _ \/ / / #
# /_  _/ // /_  _/ #
#  /_/ \___/ /_/   #
####################

def handler404(request, exception):
    return render(request, 'project_manager/404.html', status=404)


########################################################
#   __  __               ___                    __     #
#  / / / /__ ___ ____   / _ \___ ___  ___  ____/ /____ #
# / /_/ (_-</ -_) __/  / , _/ -_) _ \/ _ \/ __/ __(_-< #
# \____/___/\__/_/    /_/|_|\__/ .__/\___/_/  \__/___/ #
#                             /_/                      #
########################################################


def report_user_activity(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()

    context = {
        "projects" : projects,
        "user" : user,
    }
    return render(request, "project_manager/reports/users/report_user_activities.html", context)

def report_user_project(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()

    context = {
        "projects" : projects,
        "user" : user,
    }
    return render(request, "project_manager/reports/users/report_user_project.html", context)


def report_user_leave(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    user = CustomUser.objects.get(id=pk)

    context = {
        "user" : user,
    }
    return render(request, "project_manager/reports/users/report_user_leaves.html", context)


def report_user_expectedhours(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")
    
    user = CustomUser.objects.get(id=pk)
    projects = Project.objects.all()

    context = {
        "projects" : projects,
        "user" : user,
    }
    return render(request, "project_manager/reports/users/report_user_expectedhours.html", context)

def report_user_pro_act(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,f"Sorry. \
        You are disabled.")
        return redirect("login")

    user = CustomUser.objects.get(id=pk)
    projects_count = Project.objects.all().count()
    activities_count = Activity.objects.all().count()

    context = {
        "user" : user,
        "projects_count":projects_count,
        "activities_count":activities_count
    }
    return render(request, "project_manager/reports/users/report_user_pro_act.html", context)