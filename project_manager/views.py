import calendar
import copy
import html
from calendar import SATURDAY, monthcalendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

import pandas as pd
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from PIL import Image

from .forms import ProfileImageForm
from .models import (
    Activity,
    ActivityLogs,
    CustomUser,
    Holiday,
    Leave,
    Profile,
    Project,
    Role,
)
from .tasks import (
    send_notification_email,
    send_notification_email_recieve_admin,
    send_notification_email_recieve_manager,
)

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


def leave_overlap(user, start_date, end_date):
    leave_requests = Leave.objects.filter(
        Q(is_rejected=False),
        from_user=user.id,
        start_date__lte=end_date,
        end_date__gte=start_date,   
    )
    return any(leave_requests)


def is_saturday(date_str:str):
    date = datetime.strptime(date_str, r"%Y-%m-%d")
    if date.isoweekday() == 6:
        return True
    return False


def get_firstday_current_last_month():
    # Get the first day of the current month
    today = date.today()

    # Get the first day of the last month
    last_month = today.month - 1 if today.month > 1 else 12
    last_year = today.year if today.month > 1 else today.year - 1
    first_day_last_month = date(last_year, last_month, 1)
    first_day_last_month.strftime(r'%Y-%m-%d')

    # Get the last day of the current month
    last_day_current_month = calendar.monthrange(today.year, today.month)[1]
    last_day_current_month = date(today.year, today.month, last_day_current_month)
    last_day_current_month.strftime(r'%Y-%m-%d')
    return  first_day_last_month, last_day_current_month


def isLeaveDay(user, date):
    first_day_last_month, last_day_current_month = get_firstday_current_last_month()

    leave_days = Leave.objects.filter(
        from_user=user,
        start_date__range=[first_day_last_month, last_day_current_month],
        is_rejected = False
    )
    # need improvement
    datetime_object = datetime.strptime(date, r"%Y-%m-%d")
    date_object = datetime_object.date()

    return any(leave.start_date <= date_object <= leave.end_date for leave in leave_days)


def is_before_11th():
    """
        check if today is earlier than 11
    """
    today = date.today()
    return today.day <= 18

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
        if date.dayofweek == 6:  # Sunday
            return True
        if date.dayofweek == 5:  # Saturday
            month_cal = monthcalendar(date.year, date.month)
            saturdays = [week[SATURDAY] for week in month_cal if week[SATURDAY] != 0]
            second_saturday = saturdays[1]
            last_saturday = saturdays[-1]
            if date.day == second_saturday or date.day == last_saturday:
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
    hours_worked_on_date = sum(Decimal(entry.hours_worked) for entry in entrylogs)
    return hours_worked_on_date


def checkActivityInLeaveDays(user, start_date, end_date):
    data = ActivityLogs.objects.filter(user=user, date__range=[start_date, end_date])
    return any(log.hours_worked > 0 for log in data)

# def checkLeavesInLeaveDays(user, start_date, end_date):
#     data = Leave.objects.filter(
#             user=user,
#             start_date__lte=end_date,
#             end_date__gte=start_date
#     )

#     return any(log.days > 0 for log in data)

def get_filtered_dates(start_date:str, end_date:str, with_holidays:bool=True, extra_info:bool=False):
    """
        this helper function takes a range dates and calculate the filtered days (no sat2,4 or sun) and returns:
        list of all dates.
        takes:
            start_date: a string of the date
            end_date: same as the start_date
            with_holidays: a bool that determines whether we should execlude the public holidays too
            extra_info: it scale the returns to extra infos, like "weekends_count" in this range of dates, and
                "pub_holidays_count" too with the filtered_dates
    """

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

    banned_saturdays = []
    for sat in saturdays:
        month_cal = monthcalendar(sat.year, sat.month)
        month_saturdays = [week[SATURDAY] for week in month_cal if week[SATURDAY] != 0]
        if len(month_saturdays) > 1:
            second_saturday = month_saturdays[1]
            last_saturday = month_saturdays[-1]
            banned_saturdays.extend([pd.Timestamp(sat.year, sat.month, second_saturday),
                                     pd.Timestamp(sat.year, sat.month, last_saturday)])

    filtered_dates = [date for date in filtered_dates if date not in banned_saturdays]

    count_no_holidays = len(filtered_dates)
    weekends_count = len(date_range) - len(filtered_dates)
    pub_holidays_count = 0

    if(with_holidays):
        holiday_dates = [pd.Timestamp(holiday.holiday_date.ctime()) for holiday in public_holidays]
        # exclude public holidays
        filtered_dates = [date for date in filtered_dates if date not in holiday_dates]
        pub_holidays_count = count_no_holidays - len(filtered_dates)

    if extra_info:
        return filtered_dates, weekends_count, pub_holidays_count
    else:
        return filtered_dates




#########################################################
#  __  __       _        __      ___                    #
# |  \/  |     (_)       \ \    / (_)                   #
# | \  / | __ _ _ _ __    \ \  / / _  _____      _____  #
# | |\/| |/ _` | | '_ \    \ \/ / | |/ _ \ \ /\ / / __| #
# | |  | | (_| | | | | |    \  /  | |  __/\ V  V /\__ \ #
# |_|  |_|\__,_|_|_| |_|     \/   |_|\___| \_/\_/ |___/ #
#########################################################


# def login_view(request):
#     if request.method == 'POST':
#         form = AuthenticationForm(request, request.POST)
#         if form.is_valid():
#             if hasattr(request, "loc_name"):
#                 location = request.loc_name
#                 user = form.get_user()
#                 if user.location.loc_name == str(location):
#                     login(request, user)
#                     if request.user.role.name == "Director":
#                         return redirect('overview')
#                     else:
#                         return redirect('dashboard')
#                 else:
#                     messages.error(request,f"Your location is {user.location.loc_name}.activity.teamnigeria.com.ng")
#             else:
#                 messages.error(request,f"Sorry, something went wrong.")
#         else:
#             messages.error(request,f"Sorry, your credentials are incorrect.")
#         return redirect("login")
#     else:
#         form = AuthenticationForm()
#     return render(request, 'project_manager/login.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if request.user.role.name == "Director":
                return redirect('overview')
            else:
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'project_manager/login.html', {'form': form})


@login_required
def logout_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are disabled.")

        logout(request)
        return redirect("login")
    
    logout(request)
    return redirect("login")


def check_location(request) -> str | None:
    """
    Goal: checks if a request from a user does have the same loc_name (prefix url) as the user location.
    Parameter:
                 only the request to extract the user info and the loc_name.   
    Returns:
                 the name of the loc_name if no errors, else it returns None
    """
    if hasattr(request, "loc_name"):
        if request.user.location.loc_name == str(request.loc_name):
            location = request.loc_name
        else:
            messages.error(request, f"Your Location is: {request.user.location.loc_name}.activity.teamnigeria.com.ng")
            return None
    else:
        messages.error(request, "Someting went wrong with you location url.")
        return None
    return str(location)


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are disabled.")

        logout(request)
        return redirect("login")

    # location = check_location(request)
    # if not location:
    #     logout(request)
    #     return redirect("login")
    
    projects = Project.objects.all()

    user = request.user
    context = {"user":user, "projects":projects}
    return render(request, 'project_manager/dashboard.html', context)


def registerhours(request, date_picked):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are disabled.")
        
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    q = date_picked
    
    today = datetime.strptime(str(q), r"%Y-%m-%d").date()
    yesterday = (today - timedelta(days=1)).strftime(r"%Y-%m-%d")
    tomorrow = (today + timedelta(days=1)).strftime(r"%Y-%m-%d")

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

        ##############
        # is to check if the date is (sundays or 2nd, 4th of saterday)
        if check_is_sun_sat(q):
            can_edit = False
            is_holiday = True


        # is to check if the date are actually a holiday date
        ###############
        first_day_last_month, last_day_current_month = get_firstday_current_last_month()
        holidays = Holiday.objects.filter(
            holiday_date__range=[first_day_last_month, last_day_current_month]
        )
        
        if check_holiday(holidays, q_date):
            is_holiday = True
        ###############
    except Exception:
        messages.error(request,"Canceled. Invalid Date.")

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
        "is_holiday":is_holiday,
        "yesterday":yesterday,
        "tomorrow":tomorrow
            }
    return render(request, 'project_manager/main_pages/registerhours.html', context)


def activity_log(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    today = date.today()
    q = request.GET.get("q",today)
    
    date_picked = datetime.strptime(str(q), r"%Y-%m-%d").date()
    yesterday = (date_picked - timedelta(days=1)).strftime(r"%Y-%m-%d")
    tomorrow = (date_picked + timedelta(days=1)).strftime(r"%Y-%m-%d")
    entry_logs = ActivityLogs.objects.filter(
        user = request.user.id,
        date = q
    ).order_by("-created")

    context = {
        "entry_logs":entry_logs,
        "date":date_picked,
        "yesterday":str(yesterday),
        "tomorrow":str(tomorrow)
          }
    return render(request, 'project_manager/main_pages/activity_log.html', context)

@transaction.atomic
def update_entry(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    user = request.user
    projects = Project.objects.all()
    activities = Activity.objects.all()
    old_entry = ActivityLogs.objects.get(id=pk)
    old_unescaped_details = html.unescape(old_entry.details)
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
                #checking if tthe user is on a working day saterday
                daily_user_hours = user.daily_hours
                if is_saturday(date_picked):
                    daily_user_hours = 3 #thus setting the daily hours to 3
                hours = Decimal(hours)
                left_hours_on_date = get_hours_worked_on_date(user, date_picked) - Decimal(old_entry.hours_worked)
                if hours + left_hours_on_date > daily_user_hours:
                    messages.error(request,f"Canceled. \
                    You exeeded {daily_user_hours} hours on {date_picked}.")
                    return redirect("activitylogs")
            else:
                messages.error(request,"Canceled. \
                Something went wrong with inputs :(")
                return redirect("activitylogs")

            # Finally updating the data
            if html.unescape(old_entry.details) != html.unescape(details):
                old_entry.details = details
            old_entry.date = date_picked
            old_entry.activity = activity
            old_entry.project = project
            old_entry.hours_worked = hours
            old_entry.save()
            messages.success(request,
            "Activity has been updated successfully.")
        except Exception:
            messages.error(request,"Canceled. \
            Something went wrong :(")
            return redirect("activitylogs")

        return redirect("activitylogs")

    context = {"old_entry": old_entry,
               "old_unescaped_details":old_unescaped_details,
                "projects": projects,
                "activities": activities,
                "holidays":holidays
            }
    return render(request, "project_manager/main_pages/update_entry.html", context)

def delete_entry(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")
    
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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    manager_role = Role.objects.get(name="Manager")
    admin_role = Role.objects.get(name="Admin")

    admins = CustomUser.objects.filter(
        Q(role=admin_role.id),
        ~Q(is_superuser=True),
        location = request.user.location
    )

    managers = CustomUser.objects.filter(
        Q(role=manager_role.id),
        ~Q(is_superuser=True),
        location = request.user.location,
        department = request.user.department,
    )
    if not managers:
        managers = copy.deepcopy(admins)

    if request.method == "POST":
        start_date = request.POST.get("startDate")
        end_date = request.POST.get("endDate")
        leave_type = request.POST.get("leaveType")

        try:
            total_leave_days = 0 #real days to view it
            if start_date and end_date:

                start_date = datetime.strptime(start_date, r"%Y-%m-%d")
                start_date = start_date.date()
                end_date = datetime.strptime(end_date, r"%Y-%m-%d")
                end_date = end_date.date()
                total_leave_days = (end_date - start_date).days + 1

                if checkActivityInLeaveDays(request.user, start_date, end_date):
                    messages.error(request,
                    "Canceled. Pick dates where you have not worked on.")
                    return redirect('addleave')

                # if checkLeavesInLeaveDays(request.user, start_date, end_date):
                #     print("check")
                #     messages.error(request,
                #     "Canceled. You already requested in these dates.")
                #     return redirect('addleave')
                if leave_overlap(request.user, start_date, end_date):
                    messages.error(request,
                    "Canceled. You already have a leave on these days.")
                    return redirect('addleave')
            else:
                messages.error(request,
                "Something went wrong!")
                return redirect('addleave')
            
            if request.user.role.name == "Admin":
                Leave.objects.create(
                    from_user = request.user,
                    start_date = start_date,
                    end_date = end_date,
                    total_leave_days = total_leave_days,
                    leave_type = leave_type,
                    is_approved = True
                )
                send_notification_email_recieve_admin.delay(request.user.email, "Absence request", "approved")
            elif request.user.role.name == "Manager":
                admin_name = request.POST.get("adminName")
                admin = CustomUser.objects.get(username = admin_name)
                admin.has_notification = True
                admin.save()
                Leave.objects.create(
                    from_user = request.user,
                    to_user = admin,
                    start_date = start_date,
                    end_date = end_date,
                    total_leave_days = total_leave_days,
                    leave_type = leave_type
                )
                send_notification_email_recieve_manager.delay(admin.email, "Absence request", request.user.username)

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
                    total_leave_days = total_leave_days,
                    leave_type = leave_type
                )
                send_notification_email_recieve_manager.delay(manager.email, "Absence request", request.user.username)
            messages.success(request,
            "Request has been sent successfully.")

        except Exception:
            messages.error(request, "Canceled. \
            Something went wrong :(")
            return redirect('addleave')

    context = {"admins":admins, "managers":managers}
    return render(request, "project_manager/main_pages/add_leave.html", context)


def notifications(request):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")
    
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

            if response == "rejected":
                leave.is_rejected = True
                from_user = leave.from_user
                from_user.has_notification = True
                from_user.save()
                leave.save()
                email_to = from_user.email
                producer =  leave.to_user.username
                send_notification_email.delay(email_to, response, producer)

            elif response == "approved":
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

        except Exception:
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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")
    
    leave_logs = Leave.objects.filter(
        from_user = request.user.id
    ).order_by("-created")
    leaves = []
    today = date.today()
    month_pass = timedelta(days=30)

    for leave in leave_logs:
        # TO REJECT EVERY LEAVE REQUEST THAT BEEN OVER A MONTH CREATED
        if not (leave.is_approved or leave.is_rejected) and leave.created.date() + month_pass <= today:
            leave.is_rejected = True
            leave.save()

        filtered_dates, weekends_count, pub_holidays_count = get_filtered_dates(leave.start_date, leave.end_date, extra_info=True)

        leaves.append({
            "id":leave.id,
            "from_user":leave.from_user.first_name.capitalize() + " " + leave.from_user.last_name.capitalize(),
            "to_user": "__" if not leave.to_user else leave.to_user.first_name.capitalize() + " " + leave.to_user.last_name.capitalize(),
            "start_date":leave.start_date,
            "end_date":leave.end_date,
            "total_leave_days":leave.total_leave_days,
            "actual_leave_days":len(filtered_dates),
            "weekends_count": weekends_count,
            "pub_holidays_count":pub_holidays_count,
            "leave_type":leave.leave_type,
            "created":leave.created,
            "updated":leave.updated,
            "is_approved":leave.is_approved,
            "is_rejected":leave.is_rejected
        })

    context = {"leave_logs":leaves}
    return render(request, 'project_manager/main_pages/leave_log.html', context)


def update_leave(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    leave = Leave.objects.get(id=pk)

    manager_role = Role.objects.get(name="Manager")
    admin_role = Role.objects.get(name="Admin")

    admins = CustomUser.objects.filter(
        Q(role=admin_role.id),
        ~Q(is_superuser=True),
        location = request.user.location
    )

    managers = CustomUser.objects.filter(
        Q(role=manager_role.id),
        ~Q(is_superuser=True),
        location = request.user.location,
        department = request.user.department,
    )
    if not managers:
        managers = copy.deepcopy(admins)

    if request.method == "POST":
        if leave.is_approved or leave.is_rejected:
            messages.error(request, "Canceled. \
            You already have a response for your request, check your Notifications.")
            return redirect('leave_logs')
        
        start_date = request.POST.get("startDate")
        end_date = request.POST.get("endDate")
        leave_type = request.POST.get("leaveType")

        start_date = datetime.strptime(start_date, r"%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, r"%Y-%m-%d").date()
        days = (end_date - start_date).days + 1

        if checkActivityInLeaveDays(request.user, start_date, end_date):
            messages.error(request,
            "Canceled. Pick dates where you have not worked at.")
            return redirect('leave_logs')
        if leave_overlap(request.user, start_date, end_date):
            messages.error(request,
            "Canceled. You already have an Absence on these days.")
            return redirect('addleave')
        try:
            with transaction.atomic():
                if request.user.role.name=="Manager":
                    admin_name = request.POST.get("adminName")
                    admin = CustomUser.objects.get(username=admin_name)
                    admin.has_notification = True
                    admin.save()
                    leave.to_user = admin

                elif request.user.role.name=="Employee":
                    manager_name = request.POST.get("managerName")
                    manager = CustomUser.objects.get(username=manager_name)
                    manager.has_notification = True
                    manager.save()
                    leave.to_user = manager
                
                leave.start_date = start_date
                leave.end_date = end_date
                leave.total_leave_days = days
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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")
    
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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")
    
    user  = CustomUser.objects.get(id = pk)
    
    return render(request, "project_manager/profile/profile.html", {"user":user})


@login_required(login_url="login")
@transaction.atomic
def upload_profile_image(request):
    if request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")
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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")
    
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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    user = CustomUser.objects.get(id=pk)

    context = {
        "user" : user,
    }
    return render(request, "project_manager/reports/users/report_user_leaves.html", context)


def report_user_expectedhours(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

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
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    user = CustomUser.objects.get(id=pk)
    projects_count = Project.objects.count()
    activities_count = Activity.objects.count()

    context = {
        "user" : user,
        "projects_count":projects_count,
        "activities_count":activities_count
    }
    return render(request, "project_manager/reports/users/report_user_pro_act.html", context)


def report_user_pro_user(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    elif request.user.disabled:
        messages.error(request,"Sorry. You are banned.")
        logout(request)
        return redirect("login")
    # if not check_location(request):
    #     logout(request)
    #     return redirect("login")

    user = CustomUser.objects.get(id=pk)
    projects_count = Project.objects.count()

    context = {
        "user" : user,
        "projects_count":projects_count
    }
    return render(request, "project_manager/reports/users/report_user_pro_user.html", context)