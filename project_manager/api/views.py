from django.http import JsonResponse
from django.db.models import F, Sum, Q
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from datetime import date, timedelta
from project_manager.models import ActivityLogs, Holiday, Leave, Project, Activity, CustomUser
from project_manager.models import Role
from django.db import transaction
from django.contrib import messages
import calendar
from calendar import monthcalendar, SATURDAY
import pandas as pd
import json
from decimal import Decimal
from django.views.decorators.http import require_POST
from project_manager.views import get_filtered_dates, is_saturday, get_hours_worked_on_date, check_is_sun_sat
from collections import defaultdict


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

HOURS_ON_SAT = 3

def get_working_saturdays(start_date:str, end_date:str, users: list[CustomUser] = None, user: CustomUser = None):
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    public_holidays = Holiday.objects.filter(holiday_date__range = [start_date, end_date])

    date_range = pd.date_range(start=start_date, end=end_date)

    # get all saterdays
    saturdays = [date for date in date_range if date.dayofweek == 5]
    banned_saturdays = []
    for sat in saturdays:
        month_cal = monthcalendar(sat.year, sat.month)
        month_saturdays = [week[SATURDAY] for week in month_cal if week[SATURDAY] != 0]
        if len(month_saturdays) > 1:
            second_saturday = month_saturdays[1]
            last_saturday = month_saturdays[-1]
            banned_saturdays.extend([pd.Timestamp(sat.year, sat.month, second_saturday),
                                     pd.Timestamp(sat.year, sat.month, last_saturday)])
    filtered_dates = [date for date in saturdays if date not in banned_saturdays]

    holiday_dates = [pd.Timestamp(holiday.holiday_date.ctime()) for holiday in public_holidays]
    # exclude public holidays
    filtered_dates = [date for date in filtered_dates if date not in holiday_dates]
    if user and not users:
        leaves = Leave.objects.filter(
            from_user=user.id,
            start_date__lte=end_date,
            end_date__gte=start_date
        )
    else:
        leaves = Leave.objects.filter(
            from_user_id__in=users,
            start_date__lte=end_date,
            end_date__gte=start_date
        )
    leave_dates_all = []
    for leave in leaves:
        leave_dates_all += leave_start_end_cut(start_date, end_date, leave.start_date.ctime(), leave.end_date.ctime())

    leave_dates = []
    leave_dates = [date for date in leave_dates_all if date not in leave_dates]
    filtered_dates = [date for date in filtered_dates if date not in leave_dates]

    return len(filtered_dates)


def get_working_saturdays_in_leave(start_date:str, end_date:str):
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    public_holidays = Holiday.objects.filter(holiday_date__range = [start_date, end_date])

    date_range = pd.date_range(start=start_date, end=end_date)

    # get all saterdays
    saturdays = [date for date in date_range if date.dayofweek == 5]
    banned_saturdays = []
    for sat in saturdays:
        month_cal = monthcalendar(sat.year, sat.month)
        month_saturdays = [week[SATURDAY] for week in month_cal if week[SATURDAY] != 0]
        if len(month_saturdays) > 1:
            second_saturday = month_saturdays[1]
            last_saturday = month_saturdays[-1]
            banned_saturdays.extend([pd.Timestamp(sat.year, sat.month, second_saturday),
                                     pd.Timestamp(sat.year, sat.month, last_saturday)])

    filtered_dates = [date for date in saturdays if date not in banned_saturdays]

    holiday_dates = [pd.Timestamp(holiday.holiday_date.ctime()) for holiday in public_holidays]
    # exclude public holidays
    filtered_dates = [date for date in filtered_dates if date not in holiday_dates]

    return len(filtered_dates)

def leave_start_end_cut(start_cut:str, end_cut:str, start_leave:str, end_leave:str):
    """
    this function return the intersection dates between a start_leave date and end_leave date with a given
    period of time
    """
    start_cut = pd.Timestamp(start_cut)
    end_cut = pd.Timestamp(end_cut)

    start_leave = pd.Timestamp(start_leave)
    end_leave = pd.Timestamp(end_leave)

    filtered_dates = []

    date_range = pd.date_range(start=start_leave, end=end_leave)
    filtered_dates = [date for date in date_range if date >= start_cut and date <= end_cut]

    return filtered_dates

def get_firstday_lastday_specific_month(year: int, month: int):
    """
    Purpose: Given a year and a month, this function returns the first and last day of that month.
    Parameters:
        year: The year.
        month: The month (1 for January, 2 for February, and so on).
    Returns: A tuple containing the first and last day of the specified month.
    """
    first_day_current_month = date(year, month, 1)
    last_day_current_month = date(year, month, calendar.monthrange(year, month)[1])
    return first_day_current_month, last_day_current_month


def get_start_end_date(month: str, year: str):
    start_date = date.today()
    end_date = date.today()
    if month == "all":
        start_date = date(int(year), 1, 1)
        if date.today().year == int(year):
            end_date = date.today()
        else:
            end_date = date(int(year), 12, 31)
    else:
        # if the current month we take it from the first day of the month to the current day
        if date.today().month == int(month):
            start_date = date(int(year), int(month), 1)
            end_date = date.today()
        else:
            start_date = date(int(year), int(month), 1)
            if month == "12":
                last_month_day = date(int(year) + 1, 1, 1) - start_date
            else:
                last_month_day = date(int(year), int(month) + 1, 1) - start_date
            end_date = date(int(year), int(month), last_month_day.days)
    return start_date, end_date


def daterange(start_date, end_date):
    """
    Purpose: Generates a range of dates between start_date and end_date.
    Parameters:
        start_date: The start date.
        end_date: The end date.
    Yields: Each date in the range from start_date to end_date, inclusive.
    """
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def get_activity_logs(user_id: int, project_id: int, order_start: date, order_end: date):
    """
    Purpose: Retrieves activity logs for a specific user, project, and time period.
    Parameters:
        user_id: The ID of the user.
        project_id: The ID of the project. Use "all" to retrieve logs for all projects.
        order_start: The start date of the time period.
        order_end: The end date of the time period.
    Returns: QuerySet of activity logs filtered by the specified criteria.
    """
    if project_id == "all":
        return ActivityLogs.objects.filter(user=user_id, date__range=[order_start, order_end])
    else:
        return ActivityLogs.objects.filter(user=user_id, date__range=[order_start, order_end], project=project_id)


def calculate_public_holidays(order_start: date, order_end: date, users: list[CustomUser] = None, user:CustomUser = None):
    """
    Calculates the total number of public holiday hours within a time period for given some users.
    """
    pub_holidays = Holiday.objects.filter(
        holiday_date__range=[order_start, order_end]
    )
    if user and not users:
        daily_hours_total = Decimal(user.daily_hours)
    else:
        daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
    
    count_holidays = 0
    count_working_saturdays_holidays = 0
    for ho in pub_holidays:
        if not check_is_sun_sat(ho.holiday_date):
            if is_saturday(ho.holiday_date.strftime(r"%Y-%m-%d")):
                count_working_saturdays_holidays+=1
            else:
                count_holidays+=1
    hours_pub_holiday = (count_working_saturdays_holidays*HOURS_ON_SAT) + (count_holidays*daily_hours_total)

    return hours_pub_holiday


def calculate_leave_days(users: list[CustomUser], order_start: date, order_end: date, with_days:bool=False):
    """
    Purpose: Calculates the total number of leave days taken by users within a time period.\n
    Parameters:
       * users: List of users.
       * order_start: The start date of the time period.
       * order_end: The end date of the time period.
       * with_days: specify if the programmer wants to return the leave days too.

    Returns: The total number of leave hours days or and leave days taken by users.
    """

    leave_requests = Leave.objects.filter(
        from_user__in=users,
        is_approved=True,
        start_date__lte=order_end,
        end_date__gte=order_start
    )

    
    hours_leave_days = 0
    leave_days = 0
    for leave_request in leave_requests:
        
        leave_start = max(leave_request.start_date, order_start)
        leave_end = min(leave_request.end_date, order_end)

        saturdays = get_working_saturdays_in_leave(leave_start.ctime(), leave_end.ctime())
        sat_hours = (saturdays * HOURS_ON_SAT)

        filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
        leave_days+=len(filtered_dates)
        total_days = len(filtered_dates) - saturdays
        hours_leave_days += total_days * leave_request.from_user.daily_hours
        hours_leave_days += sat_hours

    if with_days:
        return hours_leave_days, leave_days
    else:
        return hours_leave_days


def calculate_leave_days_user(user: CustomUser, order_start: date, order_end: date, with_days:bool=False):
    """
    Purpose: Calculates the total number of leave days taken by user within a time period.

    Parameters:
       * user: a user.
       * order_start: The start date of the time period.
       * order_end: The end date of the time period.
       * with_days: specify if the programmer wants to return the leave days too.

    Returns: The total number of leave hours days or and leave days taken by users.
    """
    hours_leave_days = 0
    leave_days = 0

    approved_leave_requests = Leave.objects.filter(
        from_user=user.id,
        is_approved=True,
        start_date__lte=order_end,
        end_date__gte=order_start
    )

    for leave_request in approved_leave_requests:
        leave_start = max(leave_request.start_date, order_start)
        leave_end = min(leave_request.end_date, order_end)
        saturdays = get_working_saturdays_in_leave(leave_start.ctime(), leave_end.ctime())
        sat_hours = (saturdays * HOURS_ON_SAT)
        filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
        leave_days+=len(filtered_dates)
        total_days = len(filtered_dates) - saturdays
        hours_leave_days += total_days * user.daily_hours
        hours_leave_days += sat_hours

    if with_days:
        return hours_leave_days, leave_days
    else:
        return hours_leave_days


def calculate_project_and_activity_data(users, project_id, date_start, date_end):
    """
    Purpose:
                Calculates and returns data on the total hours worked on projects and activities by users within a specified date range.

    Parameters:
       * users (list[CustomUser]): A list of user objects for which the activity logs are to be retrieved.
       * project_id (Any): The ID of the project to filter by. If "all", data for all projects will be included.
       * date_start (date): The start date of the period for which data is to be retrieved.
       * date_end (date): The end date of the period for which data is to be retrieved.

    Returns:
       * tuple: Contains three elements:
                * project_data (dict): A dictionary with project names as keys, each containing:
                        - 'total' (int): The total hours worked on the project.
                        - 'percentage' (int): The percentage of total worked hours dedicated to the project.
                        - 'activity_logs' (list): A list of dictionaries with details about each activity log related to the project.
                * activity_type_data (dict): A dictionary with activity type names as keys, each containing:
                        - 'total' (int): The total hours worked on the activity type.
                        - 'percentage' (int): The percentage of total worked hours dedicated to the activity type.
                        - 'activity_logs' (list): A list of dictionaries with details about each activity log related to the activity type.
                * total_worked_hours (int): The total hours worked by all users within the specified date range.
    """
    project_data = defaultdict(lambda: {'total': 0, 'percentage': 0, 'activity_logs': []})
    activity_type_data = defaultdict(lambda: {'total': 0, 'percentage': 0, 'activity_logs': []})
    total_worked_hours = 0
    
    # get all activity logs for the specified users, project, and date range
    activity_logs = ActivityLogs.objects.filter(
        Q(user__in=users),
        Q(project=project_id) if project_id != "all" else Q(),
        date__range=[date_start, date_end]
    ).select_related('project', 'activity', 'user')
    
    # loop over the fetched logs and populate project_data and activity_type_data dictionaries
    for activity_log in activity_logs:
        project_name = activity_log.project.project_name
        activity_type_name = activity_log.activity.activity_name
        fullname = activity_log.user.first_name.capitalize() + " " + activity_log.user.last_name.capitalize()
        
        project_data[project_name]['total'] += activity_log.hours_worked
        project_data[project_name]['activity_logs'].append({
            'date': activity_log.date.strftime(r'%d-%b-%Y'),
            'hours_worked': activity_log.hours_worked,
            'details': str(activity_log.details),
            'activity': activity_type_name,
            'time_added': activity_log.updated.strftime(r'%d-%b-%Y [%H:%M:%S]'),
            'user': fullname
        })
        
        activity_type_data[activity_type_name]['total'] += activity_log.hours_worked
        activity_type_data[activity_type_name]['activity_logs'].append({
            'date': activity_log.date.strftime(r'%d-%b-%Y'),
            'hours_worked': activity_log.hours_worked,
            'details': str(activity_log.details),
            'project': project_name,
            'time_added': activity_log.updated.strftime(r'%d-%b-%Y [%H:%M:%S]'),
            'user': fullname
        })
        total_worked_hours += activity_log.hours_worked
    
    return project_data, activity_type_data, total_worked_hours


def prepare_response_data(project_data:dict, activity_type_data:dict, total_hours_wleave:int, total_hours:int, total_worked_hours:float, missed_hours:float, hours_leave_days:int, hours_pub_holiday:int) -> dict:
    """
    Purpose: Prepares the response data for the overview.\n
    Parameters:
       * project_data: Dictionary containing project data.
       * activity_type_data: Dictionary containing activity type data.
       * total_hours_wleave: Total expected hours with the leave hours.
       * total_hours: Total expected hours after extracting the leave hours.
       * total_worked_hours: Total worked hours.
       * missed_hours: Total missed hours.
       * hours_leave_days: Total leave hours.
       * hours_pub_holiday: Total public holiday hours.

    Returns: 
            A dictionary containing the prepared response data.
    """
    filtered_data = {
        "projects": [],
        "activities": [],
        "all": {
            "expected_hours": total_hours,
            "missed_hours": missed_hours,
            "total_worked_hours": total_worked_hours,
            "hours_pub_holiday": hours_pub_holiday,
            "hours_leave_days": hours_leave_days,
            "percent_complete": (total_worked_hours * 100) / total_hours if total_hours > 0 else 0,
        }
    }

    for project_name, data in project_data.items():
        project_info = {
            "name": project_name,
            "total": data["total"],
            "percentage": data["total"] * 100 / total_hours if total_hours > 0 else 0,
            "activity_logs": data["activity_logs"]
        }
        filtered_data["projects"].append(project_info)

    filtered_data["projects"].append({
        "name": "Absences",
        "total": hours_leave_days,
        "percentage": hours_leave_days * 100 / total_hours_wleave if total_hours_wleave > 0 else 0
    })

    for activity_name, data in activity_type_data.items():
        activity_info = {
            "name": activity_name,
            "total": data["total"],
            "percentage": data["total"] * 100 / total_hours if total_hours > 0 else 0,
            "activity_logs": data["activity_logs"]
        }
        filtered_data["activities"].append(activity_info)

    return filtered_data


def get_emp_role():
    """
    Purpose: Retrieves the Role object for "Employee".
    
    Returns:
        Role: The Role object for "Employee".
    """
    emp = Role.objects.get(name="Employee")
    return emp


def get_admin_role():
    """
    Purpose: Retrieves the Role object for "Admin".
    
    Returns:
        Role: The Role object for "Admin".
    """
    admin = Role.objects.get(name="Admin")
    return admin


def get_manager_role():
    """
    Purpose: Retrieves the Role object for "Manager".
    
    Returns:
        Role: The Role object for "Manager".
    """
    manager = Role.objects.get(name="Manager")
    return manager


def getUserSupervisor(user: CustomUser):
    """
    Purpose: Finds the supervisor of a given user based on their role, location, and department.
    
    Parameters:
       * user (CustomUser): The user object for whom the supervisor is to be found.
        
    Returns:
       * str: The full name of the supervisor if found, otherwise an empty string.
    """
    if user.role.name=="Admin" or user.role.name=="Director":
        return ""
    
    # discover the filter conditions based on the user's role
    filter_conditions = Q(location=user.location, is_superuser=False)
    if user.role.name=="Manager":
        filter_conditions &= Q(role=get_admin_role())
    elif user.role.name=="Employee":
        filter_conditions &= Q(role=get_manager_role(), department=user.department)

    
    # query deez database to find the supervisor
    supervisor = CustomUser.objects.filter(filter_conditions).first()
    return str(supervisor.get_full_name()) if supervisor else ""


def prepare_report_activity_logs(users, project_id, start_date, end_date):
    """
    Purpose:
                Prepares a report of activity logs for specified users and project within a given date range.
    
    Parameters:
       * users (list): A list of user objects for whom the activity logs are to be retrieved.
       * project_id (str): The ID of the project to filter by. If "all", data for all projects will be included.
       * start_date (date): The start date of the period for which data is to be retrieved.
       * end_date (date): The end date of the period for which data is to be retrieved.
    
    Returns:
       * dict: A dictionary containing the activity logs, structured as follows:
                - activity_logs (list): A list of dictionaries with details about each activity log, including:
                    - 'time_added' (str): The timestamp when the log was updated.
                    - 'username' (str): The username of the user who created the log.
                    - 'project' (str): The name of the project associated with the log.
                    - 'activity' (str): The name of the activity associated with the log.
                    - 'department' (str): The department name of the user who created the log.
                    - 'date' (str): The date when the log was created.
                    - 'hours_worked' (Decimal): The number of hours worked as recorded in the log.
                    - 'details' (str): Additional details about the log entry.
    """
    logs = {"activity_logs": []}
 
    # gettin all activity logs for the specified users and project within the date range
    activity_logs = ActivityLogs.objects.filter(
        Q(user__in=users),
        Q(project=project_id) if project_id != "all" else Q(),
        date__range=[start_date, end_date]
    ).select_related('project', 'activity', 'user__department')

    # loop over the fetched logs and prepare the response data
    for log in activity_logs:
        project_name = log.project.project_name
        logs["activity_logs"].append({
            'time_added': log.updated.strftime(r'%d-%b-%Y [%H:%M:%S]'),
            'username': log.user.first_name.capitalize() + " " + log.user.last_name.capitalize(),
            'project': project_name,
            'activity': log.activity.activity_name,
            'department': log.user.department.dept_name,
            'location':str(log.user.location.loc_name).upper(),
            'date': log.date.strftime(r'%d-%b-%Y'),
            "hours_worked": Decimal(log.hours_worked),
            "details": log.details,
        })
    
    return logs


def prepare_report_projects(users: list[CustomUser], project_id: int, start_date: date, end_date: date)-> dict:
    """
    Purpose: Prepares a report of projects detailing worked hours for specified users within a given date range.
    
    Parameters:
       * users (list[CustomUser]): A list of CustomUser objects for whom the project reports are to be generated.
       * project_id (int): The ID of the project to filter by.
       * start_date (date): The start date of the period for which data is to be retrieved.
       * end_date (date): The end date of the period for which data is to be retrieved.
    
    Returns:
       * dict: A dictionary containing project details and worked hours, structured as follows:
                - "projects" (list): A list of dictionaries with details about each project, including:
                    - 'project' (str): The name of the project.
                    - 'department' (str): The department associated with the user who worked on the project.
                    - 'location' (str): The location associated with the user who worked on the project.
                    - 'worked_hours' (int): The total hours worked on the project.
    """
    projects = defaultdict(lambda: {"project":"", "department":"", "location":"" ,"worked_hours":0})
    logs = {"projects":[]}

    activity_logs: list[ActivityLogs]
    if project_id == "all":
        activity_logs = ActivityLogs.objects.filter(
            user_id__in=users,
            date__range=[start_date, end_date],
        ).values('project__project_name', 'user__department__dept_name', 'user__location__loc_name').annotate(total_hours_worked=Sum('hours_worked'))
    else:
        activity_logs = ActivityLogs.objects.filter(
            user_id__in=users,
            date__range=[start_date, end_date],
            project_id=project_id
        ).values('project__project_name', 'user__department__dept_name', 'user__location__loc_name').annotate(total_hours_worked=Sum('hours_worked'))


    for log in activity_logs:
        project_name = log["project__project_name"]
        dept = log["user__department__dept_name"]
        loc = log["user__location__loc_name"]
        projects[project_name]["project"] = project_name
        projects[project_name]["department"] = dept
        projects[project_name]["location"] = str(loc).upper()
        projects[project_name]["worked_hours"] += log["total_hours_worked"]

    logs["projects"] = list(projects.values())
    return logs


def prepare_report_leaves(users, start_date, end_date):
    """
    Purpose: Prepares a report of leave records for specified users within a given date range.
    
    Parameters:
       * users (list): A list of user objects for whom the leave records are to be retrieved.
       * start_date (date): The start date of the period for which leave data is to be retrieved.
       * end_date (date): The end date of the period for which leave data is to be retrieved.
    
    Returns:
       * dict: A dictionary containing the leave records, structured as follows:
                - "leaves" (list): A list of dictionaries with details about each leave record, including:
                        - 'from' (str): The username of the user who requested the leave.
                        - 'to' (str): The username of the user to whom the leave was requested.
                        - 'start_date' (str): The start date of the leave.
                        - 'end_date' (str): The end date of the leave.
                        - 'total_leave_days' (int): The total number of leave days requested.
                        - 'actual_leave_days' (int): The actual number of leave days excluding weekends and public holidays.
                        - 'weekends_count' (int): The number of weekends within the leave period.
                        - 'pub_holidays_count' (int): The number of public holidays within the leave period.
                        - 'type' (str): The type of leave requested.
                        - 'respond' (str): The status of the leave request ('reject', 'accept', or 'pending').
    """
    leaves = []
    logs = {"leaves": []}
    
    # fetch deez leave records for the specified users and time period where it's in users
    leaves_queryset = Leave.objects.filter(
        from_user__in=users,
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    
    # Iterate through leave records to prepare leave data
    for log in leaves_queryset:
        filtered_dates, weekends_count, pub_holidays_count = get_filtered_dates(log.start_date, log.end_date, extra_info=True)
        leaves.append({
            "from": log.from_user.first_name.capitalize() + " " + log.from_user.last_name.capitalize() if log.from_user else "__",
            "to": log.to_user.first_name.capitalize() + " " + log.to_user.last_name.capitalize() if log.to_user else "__",
            "department": str(log.from_user.department.dept_name).capitalize(),
            "location": str(log.from_user.location.loc_name).upper(),
            "start_date": log.start_date.strftime(r"%d-%b-%Y"),
            "end_date": log.end_date.strftime(r"%d-%b-%Y"),
            "total_leave_days":log.total_leave_days,
            "actual_leave_days":len(filtered_dates),
            "weekends_count": weekends_count,
            "pub_holidays_count":pub_holidays_count,
            "type": log.leave_type,
            "respond": "reject" if log.is_rejected else "accept" if log.is_approved else "pending"
        })

    logs["leaves"] = leaves
    return logs


def prepare_report_expected_projects_workes(users: list[CustomUser], project_id: int, total_hours: int, date_start: date, date_end: date):
    """
    Purpose: Prepares a report of expected project work for specified users within a given date range,
             calculating the total and percentage of hours worked on each project.

    Parameters:
       * users (list[CustomUser]): A list of CustomUser objects for whom the project work report is to be generated.
       * project_id (int): The ID of the project to filter by. If "all", data for all projects will be included.
       * total_hours (int): The total expected hours to be worked on the projects.
       * date_start (date): The start date of the period for which data is to be retrieved.
       * date_end (date): The end date of the period for which data is to be retrieved.

    Returns:
       * tuple: Contains two elements:
                - project_data (dict): A dictionary with project names as keys, each containing:
                        - 'total' (float): The total hours worked on the project.
                        - 'percentage' (float): The percentage of total expected hours dedicated to the project.
                - total_worked_hours (float): The total hours worked by all users within the specified date range.
    """
    project_data = defaultdict(lambda: {'total': 0, 'percentage': 0})

    activity_logs: list[ActivityLogs]
    if project_id == "all":
        activity_logs = ActivityLogs.objects.filter(
            user_id__in=users,
            date__range=[date_start, date_end],
        ).values('project__project_name').annotate(total_hours_worked=Sum('hours_worked'))
    else:
        activity_logs = ActivityLogs.objects.filter(
            user_id__in=users,
            date__range=[date_start, date_end],
            project_id=project_id
        ).values('project__project_name').annotate(total_hours_worked=Sum('hours_worked'))

    # Aggregate the total worked hours
    total_worked_hours = 0
    for log in activity_logs:
        project_name = log['project__project_name']
        project_hours = log['total_hours_worked']
        project_data[project_name]['total'] += project_hours
        total_worked_hours += project_hours

    # Fetch project details
    projects = Project.objects.all() if project_id == "all" else Project.objects.filter(id=project_id)

    for project in projects:
        project_name = project.project_name
        if total_hours > 0:
            project_data[project_name]['percentage'] = (project_data[project_name]['total'] * 100 / total_hours)
        else:
            project_data[project_name]['percentage'] = 0

    return project_data, total_worked_hours


def prepare_report_pro_act_percentages(users: list[CustomUser], total_hours, date_start: date, date_end: date):
    """
    Purpose: Prepares a report of project and activity percentages for specified users within a given date range,
             calculating the total hours worked on each project and activity and their respective percentages.

    Parameters:
       * users (list[CustomUser]): A list of CustomUser objects for whom the project and activity percentages report is to be generated.
       * total_hours (int): The total expected hours to be worked on the projects and activities.
       * date_start (date): The start date of the period for which data is to be retrieved.
       * date_end (date): The end date of the period for which data is to be retrieved.

    Returns:
       * tuple: Contains three elements:
                - project_activities (dict): A nested dictionary with project names as keys and dictionaries of activity names as values,
                                            each containing the total hours worked on the activity within the project.
                - project_percentages (dict): A dictionary with project names as keys and the percentage of total expected hours
                                            dedicated to each project.
                - activity_percentages (dict): A dictionary with activity names as keys and the percentage of total expected hours
                                            dedicated to each activity.
    """
    project_totals = defaultdict(float)
    activity_totals = defaultdict(float)
    project_activities = defaultdict(lambda: defaultdict(float))

    _projects = Project.objects.all()
    _activitys = Activity.objects.all()
    for pro in _projects:
        project_name = pro.project_name
        project_totals[project_name] = 0
        for act in _activitys:
            activity_name = act.activity_name
            activity_totals[activity_name] = 0
            project_activities[project_name][activity_name] = 0


    activity_logs = ActivityLogs.objects.filter(
        user_id__in=users,
        date__range=[date_start, date_end],
    ).values('project__project_name', 'activity__activity_name').annotate(total_hours_worked=Sum('hours_worked'))


    for activity_log in activity_logs:
        project_name = activity_log["project__project_name"]
        activity_name = activity_log["activity__activity_name"]
        hours_worked = activity_log["total_hours_worked"]

        project_totals[project_name] += hours_worked
        activity_totals[activity_name] += hours_worked

        project_activities[project_name][activity_name] += hours_worked

    # Calculate percentages
    project_percentages = {project_name: ((hours / total_hours) * 100) if total_hours>0 else 0 for project_name, hours in project_totals.items()}
    activity_percentages = {activity_name: ((hours / total_hours) * 100) if total_hours>0 else 0 for activity_name, hours in activity_totals.items()}
    return project_activities, project_percentages, activity_percentages, project_totals, activity_totals


def prepare_report_pro_user_percentages(users: list[CustomUser], total_hours, date_start: date, date_end: date):

    project_totals = defaultdict(float)
    user_totals = defaultdict(float)
    project_users = defaultdict(lambda: defaultdict(float))

    _projects = Project.objects.all()
    for pro in _projects:
        project_name = pro.project_name
        project_totals[project_name] = 0
        for user in users:
            username = user.first_name + " " + user.last_name
            user_totals[username] = 0
            project_users[project_name][username] = 0
            

    worked_hours = 0
    activity_logs = ActivityLogs.objects.filter(
        user_id__in=users,
        date__range=[date_start, date_end],
    ).values('project__project_name', 'user__first_name', 'user__last_name').annotate(total_hours_worked=Sum('hours_worked'))


    for activity_log in activity_logs:
        project_name = activity_log["project__project_name"]
        username = activity_log["user__first_name"] + " " + activity_log["user__last_name"]
        hours_worked = activity_log["total_hours_worked"]

        project_totals[project_name] += hours_worked
        user_totals[username] += hours_worked

        project_users[project_name][username] += hours_worked
        worked_hours += hours_worked


#TODO: make up your mind about whether to consider the leave a project or execlude the leeave hours
    # for user in users:
    #     username = user.first_name + " " + user.last_name
    #     hours_leave_days = calculate_leave_days_user(user, date_start, date_end)
    #     project_users["leave"][username] = hours_leave_days
    #     project_totals.update({"leave":hours_leave_days})
    #     user_totals[username] += hours_leave_days
#like here v
    # for user in users:
    #     hours_leave_days = calculate_leave_days_user(user, date_start, date_end)
    #     total_hours-=hours_leave_days

    # Calculate percentages
    project_percentages = {project_name: ((hours / total_hours) * 100) if total_hours>0 else 0 for project_name, hours in project_totals.items()}
    user_percentages = {username: ((hours / total_hours) * 100) if total_hours>0 else 0 for username, hours in user_totals.items()}
    return project_users, project_percentages, user_percentages, project_totals, user_totals, worked_hours


def calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users:list[CustomUser] = None, user:CustomUser = None):
    """
    # Parameters:

         - start_date: the start of the date filter Date object.
        
         - end_date: the end of the date filter Date object.
         
         - daily_hours_total: the total number of daily hours for selected users (from user.daily_hours)

         - working_saturdays: the number of working saturdays from start_date to end_date (1st, 2nd, 5th)

         - users: a list of users [CustomUser] objects [Optional].

         - user: a user [CustomUser] object [Optional].

    # Explanation:
         - HOURS_ON_SAT: the number of working hours on saturdays for every user.
        
         - total_days: has the number of days between start_date and end_date execluding (weekly holidays)
                      and (leave days) and (working saturdays) and (public holidays).
        
         - daily_hours_total: the total number of daily hours for selected users (from user.daily_hours)
        
         - total_hours: (daily_hours_total * total_days) + (working_saturdays * users.count() * HOURS_ON_SAT)
        
         - hours_leave_days: the number of hours of leaves for all users from start_date to end_date.
        
         - total_hours_wleave: total_hours + leave days hours + (working_saturdays * users.count() * HOURS_ON_SAT)
        
         - working_saturdays: the number of working saturdays from start_date to end_date (1st, 2nd, 5th)
    # Returns:
         - total_hours
         - total_hours_wleave
         - hours_leave_days
         - hours_pub_holiday
    """
    # getting the list of filtered days without weekly holidays and public holidays
    total_days_list = get_filtered_dates(start_date, end_date)
    total_days = len(total_days_list)

    # getting the number of hours and days of leaves for all users
    if user and not users:
        hours_leave_days, leave_days = calculate_leave_days_user(user, start_date, end_date, with_days=True)
    else:
        hours_leave_days, leave_days = calculate_leave_days(users, start_date, end_date, with_days=True)
    # calculating the total number of expected working days (we will add the working saturdays later for 3 hours)
    total_days -= working_saturdays
    # first we calculate the total hours by multiplying the previous daily hours with the total days above
    total_hours = (daily_hours_total * total_days) - hours_leave_days
    # total hours with leave this is for calculating the percentage of leave project from the expected total hours
    # and since we subtract the leave days before from the total hours we add the leave hours here
    total_hours_wleave = total_hours + hours_leave_days

    if user and not users:
        # since the total hours has no working saturdays now we add the sat to the total hours with leave
        total_hours_wleave += (working_saturdays * HOURS_ON_SAT)
        # and we do the same thing with the non-leave total hours
        total_hours += (working_saturdays * HOURS_ON_SAT)
        # calculating the public holiday hours (working saturdays in calculation in calculate_public_holidays too)
        hours_pub_holiday = calculate_public_holidays(start_date, end_date, user=user)
    else:
        total_hours_wleave += (working_saturdays * users.count() * HOURS_ON_SAT)
        total_hours += (working_saturdays * users.count() * HOURS_ON_SAT)
        hours_pub_holiday = calculate_public_holidays(start_date, end_date, users=users)

    # subtracting public holiday hours from both total hours and total hours with leave
    return total_hours, total_hours_wleave, hours_leave_days, hours_pub_holiday

##########################################################################
#   _____      _                _                       _____ _____      #
#  / ____|    | |              | |                /\   |  __ \_   _|     #
# | |     __ _| | ___ _ __   __| | __ _ _ __     /  \  | |__) || |  ___  #
# | |    / _` | |/ _ \ '_ \ / _` |/ _` | '__|   / /\ \ |  ___/ | | / __| #
# | |___| (_| | |  __/ | | | (_| | (_| | |     / ____ \| |    _| |_\__ \ #
#  \_____\__,_|_|\___|_| |_|\__,_|\__,_|_|    /_/    \_\_|   |_____|___/ #
##########################################################################


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def calendar_data_view(request):

    try:
        if request.method == "GET":
            year = int(request.GET.get("year"))
            month = int(request.GET.get("month"))

            start_date, end_date = get_firstday_lastday_specific_month(year, month)

            # get activity logs for the requested month
            activity_logs = ActivityLogs.objects.filter(
                user=request.user,
                date__range=[start_date, end_date]
            ).annotate(day=F('date')).values('day').annotate(total_hours=Sum('hours_worked')).order_by("day")

            # make a dictionary to store data for each day of the month
            all_month_days = {
                str(start_date + timedelta(days=i)): 0 for i in range((end_date - start_date).days + 1)
            }
            # update deez dictionary with total hours worked for each day from activity logs
            all_month_days.update({
                str(log['day']): log['total_hours'] for log in activity_logs
            })

            return JsonResponse(all_month_days)
    except Exception as e:
        messages.error(request, "Something went wrong, I cannot fetch the working hours for you :(")
        return JsonResponse({'error': str(e)}, status=500)



@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def calendar_holiday_data(request):
    try:
        if request.method == "GET":
            dates = request.GET.getlist("dates[]")
            holiday_data = {}
            # get all holiday data for the given dates in a single query
            holidays = Holiday.objects.filter(holiday_date__in=dates)
            # dict holiday data dictionary
            holiday_data = {str(holiday.holiday_date):holiday.holiday_name for holiday in holidays}

            # fill in missing dates with None
            # EDIT: doesn't have to do that, we send only holidays
            # and if the date of the calender exist it puts the name of the holiday
            # for date in dates:
            #     if date not in holiday_data:
            #         holiday_data[date] = None

            return JsonResponse(holiday_data)
    except Exception as e:
        messages.error(request, "Something went wrong, I cannot fetch the Holiday dates :(")
        return JsonResponse({"error": str(e)}, status=500)
    



@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def calendar_leave_data(request):
    try:
        if request.method == "GET":
            dates = request.GET.getlist("dates[]")

            leave_data = {}

            start_cut = dates[0]
            end_cut = dates[-1]
            # get all holiday data for the given dates in a single query
            leaves = Leave.objects.filter(
                from_user=request.user,
                is_approved=True,
                start_date__lte=end_cut,  # Leave starts before or on order_end
                end_date__gte=start_cut  # Leave ends after or on order_start
            )
            # dict holiday data dictionary
            intersection = [date.strftime(r'%Y-%m-%d')
                            for leave in leaves
                            for date in leave_start_end_cut(start_cut, end_cut, leave.start_date.ctime(), leave.end_date.ctime())]
            
            leave_data = {str(date):True for date in intersection}

            return JsonResponse(leave_data)
    except Exception as e:
        messages.error(request, "Something went wrong, I cannot fetch the Leave dates :(")
        return JsonResponse({"error": str(e)}, status=500)





##############################################################################################
#  _____            _     _              _    _                                 _____ _____  #
# |  __ \          (_)   | |            | |  | |                          /\   |  __ \_   _| #
# | |__) |___  __ _ _ ___| |_ ___ _ __  | |__| | ___  _   _ _ __ ___     /  \  | |__) || |   #
# |  _  // _ \/ _` | / __| __/ _ \ '__| |  __  |/ _ \| | | | '__/ __|   / /\ \ |  ___/ | |   #
# | | \ \  __/ (_| | \__ \ ||  __/ |    | |  | | (_) | |_| | |  \__ \  / ____ \| |    _| |_  #
# |_|  \_\___|\__, |_|___/\__\___|_|    |_|  |_|\___/ \__,_|_|  |___/ /_/    \_\_|   |_____| #
#              __/ |                                                                         #
#             |___/                                                                          #
##############################################################################################


# @api_view(['POST'])
@require_POST
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def post_activity_data(request):
    try:
        if request.method == "POST":
            data_str = request.body.decode('utf-8')
            data_dict = json.loads(data_str)
            activity_data = json.loads(data_dict['data'])
            date = activity_data[0].get("date")
            daily_expected_hours = request.user.daily_hours

            if not request.user.is_authenticated:
                messages.error(request, "Access Denied.")
                return JsonResponse({"error": "Access Denied"}, status=405)
            
            if not date:
                messages.error(request, "Invalid Request.")
                return JsonResponse({"error": "Invalid request data"}, status=405)

            if is_saturday(date):
                daily_expected_hours = HOURS_ON_SAT
            
            total_hours_to_register = sum(Decimal(item["hours"]) for item in activity_data)
            total_hours_registered = get_hours_worked_on_date(request.user, date)

            total_hours = total_hours_registered + total_hours_to_register

            if total_hours > daily_expected_hours:
                messages.error(request, "Exceeded hours on saturday.")
                return JsonResponse({"error": "Exceeded hours"}, status=405)


            with transaction.atomic():
                project_names = set(item["project"] for item in activity_data)
                activity_names = set(item["activity"] for item in activity_data)

                projects = {project.project_name: project for project in Project.objects.filter(project_name__in=project_names)}
                activities = {activity.activity_name: activity for activity in Activity.objects.filter(activity_name__in=activity_names)}

                logs_to_create = []

                for item in activity_data:
                    project = projects.get(item["project"])
                    activity = activities.get(item["activity"])

                    if not project or not activity:
                        return JsonResponse({"error": "Invalid project or activity"}, status=405)

                    logs_to_create.append(ActivityLogs(
                        user=request.user,
                        project=project,
                        activity=activity,
                        date=date,
                        details=item["details"],
                        hours_worked=item["hours"]
                    ))

                # bulk create activity logs
                ActivityLogs.objects.bulk_create(logs_to_create)

                messages.success(request, "Activities have been saved successfully.")
                return JsonResponse({"message": "success"})
        else:
            return JsonResponse({"error": "Invalid request method"}, status=405)
    except Exception as e:
        messages.error(request, "Something went wrong. Please contact the admin.")
        return JsonResponse({"error": str(e)}, status=500)
    


############################################################################
#   ____                       _                          _____ _____      #
#  / __ \                     (_)                   /\   |  __ \_   _|     #
# | |  | |_   _____ _ ____   ___  _____      __    /  \  | |__) || |  ___  #
# | |  | \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / /   / /\ \ |  ___/ | | / __| #
# | |__| |\ V /  __/ |   \ V /| |  __/\ V  V /   / ____ \| |    _| |_\__ \ #
#  \____/  \_/ \___|_|    \_/ |_|\___| \_/\_/   /_/    \_\_|   |_____|___/ #
############################################################################


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def overview_data(request):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        project_id = request.GET.get("project")

        if month and year and user_id and department_id and project_id:
            start_date, end_date = get_start_end_date(month, year)

            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )

            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            
            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, total_hours_wleave, hours_leave_days, hours_pub_holiday = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)
            project_data, activity_type_data, total_worked_hours = calculate_project_and_activity_data(users, project_id, start_date, end_date)
            missed_hours = total_hours - Decimal(total_worked_hours)
            filtered_data = prepare_response_data(project_data, activity_type_data, total_hours_wleave, total_hours , Decimal(total_worked_hours), missed_hours, hours_leave_days, hours_pub_holiday)

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Invalid request parameters")
            return JsonResponse({"error": "Invalid request"}, status=400)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Server error"}, status=500)



@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def overview_manager_data(request):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        location_id = request.GET.get("location")
        department_id = request.GET.get("department")
        project_id = request.GET.get("project")

        if month and year and user_id and department_id and project_id:
            start_date, end_date = get_start_end_date(month, year)

            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            users = CustomUser.objects.filter(
                ~Q(is_superuser=True),
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                department=int(department_id),
                location=int(location_id)
            ).order_by("username")
            
            if user_id != "all":
                users = users.filter(id=int(user_id))

            total_hours:int = 0

            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, total_hours_wleave, hours_leave_days, hours_pub_holiday = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)


            project_data, activity_type_data, total_worked_hours = calculate_project_and_activity_data(users, project_id, start_date, end_date)
            missed_hours = total_hours - total_worked_hours
            filtered_data = prepare_response_data(project_data, activity_type_data, total_hours_wleave, total_hours , total_worked_hours, missed_hours, hours_leave_days, hours_pub_holiday)

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Invalid request parameters")
            return JsonResponse({"error": "Invalid request"}, status=400)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Server error"}, status=500)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def overview_user_data(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")

        if month and year and user_id and project_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(
                    id = user_id
                )

            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, total_hours_wleave, hours_leave_days, hours_pub_holiday = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)
            project_data, activity_type_data, total_worked_hours = calculate_project_and_activity_data(users, project_id, start_date, end_date)
            missed_hours = total_hours - total_worked_hours
            filtered_data = prepare_response_data(project_data, activity_type_data, total_hours_wleave, total_hours, total_worked_hours, missed_hours, hours_leave_days, hours_pub_holiday)

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Invalid request parameters")
            return JsonResponse({"error": "Invalid request"}, status=400)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Server error"}, status=500)


################################################################
#  _____                       _              _____ _____      #
# |  __ \                     | |       /\   |  __ \_   _|     #
# | |__) |___ _ __   ___  _ __| |_     /  \  | |__) || |  ___  #
# |  _  // _ \ '_ \ / _ \| '__| __|   / /\ \ |  ___/ | | / __| #
# | | \ \  __/ |_) | (_) | |  | |_   / ____ \| |    _| |_\__ \ #
# |_|  \_\___| .__/ \___/|_|   \__| /_/    \_\_|   |_____|___/ #
#            | |                                               #
#            |_|                                               #
################################################################


#######################################################
#   __  __              ___                    __     #
#  / / / /_____ ____   / _ \___ ___  ___  ____/ /____ #
# / /_/ (_-< -_) __/  / , _/ -_) _ \/ _ \/ __/ __(_-< #
# \____/___|__/_/    /_/|_|\__/ .__/\___/_/  \__/___/ #
#                            /_/                      #
#######################################################


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_user_activity_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")
        if month and year and user_id and project_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(
                id = user_id,
                is_superuser = False
            )
            logs = prepare_report_activity_logs(users, project_id, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_user_project_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")

        if month and year and user_id and project_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(
                id = user_id,
                is_superuser = False
            )
            logs = prepare_report_projects(users, project_id, start_date, end_date)

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_user_leave_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)

        if month and year and user_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(
                id = user_id,
                is_superuser = False
            )
            logs = prepare_report_leaves(users, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Invalid request")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, "Something went wrong")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_user_overview_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")

        if month and year and user_id and project_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(
                id = user_id,
                is_superuser = False
            )

            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, total_hours_wleave, hours_leave_days, hours_pub_holiday = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)

            hours_leave_days_percentage = 0
            if total_hours_wleave > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours_wleave

            project_data, total_worked_hours = prepare_report_expected_projects_workes(users, project_id, total_hours, start_date, end_date)
            total_worked_hours = Decimal(total_worked_hours)
            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours
            missed_hours = total_hours - total_worked_hours

            filtered_data = {
                "date_range":{"start":start_date.strftime(r"%d-%b-%Y"), "end":end_date.strftime(r"%d-%b-%Y")},
                "projects": [],
                "all": {
                    "expected_hours": total_hours,
                    "missed_hours" : missed_hours,
                    "total_worked_hours": total_worked_hours,
                    "hours_pub_holiday": hours_pub_holiday,
                    "hours_leave_days": hours_leave_days,
                    "percent_complete": percent_complete,
                }
            }

            for project_name, data in project_data.items():
                project_info = {
                    "name": project_name,
                    "total": data["total"],
                    "percentage": data["percentage"],
                }
                filtered_data["projects"].append(project_info)

            filtered_data["projects"].append({
                "name": "Absences",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
            })

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_user_pro_act_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)

        if month and year and user_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(
                id = user_id,
                is_superuser = False
            )
            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, _, _, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)


            project_activities, project_percentages, activity_percentages, project_totals, activity_totals =\
                  prepare_report_pro_act_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": []}

            # append project and activity to filtered data
            for project_name, activities in project_activities.items():
                for activity_name, hours_worked in activities.items():
                    project_info = {
                        "project": {"name": project_name, "total_hours":project_totals[project_name] ,"percentage": project_percentages.get(project_name, 0)},
                        "activity": {"name": activity_name, "total_hours":activity_totals[activity_name] ,"percentage": activity_percentages.get(activity_name, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_user_pro_user_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)

        if month and year and user_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(
                id = user_id,
                is_superuser = False
            )
            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, _, _, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)


            project_users, project_percentages, user_percentages, project_totals, user_totals, worked_hours =\
                  prepare_report_pro_user_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": [], "all":[]}

            # append project and activity to filtered data
            for project_name, users in project_users.items():
                for username, hours_worked in users.items():
                    project_info = {
                        "project": {"name": project_name, "total_hours":project_totals[project_name], "percentage": project_percentages.get(project_name, 0)},
                        "user": {"name": username, "total_hours":user_totals[username], "percentage": user_percentages.get(username, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            percentage_all = (worked_hours/total_hours)*100 if total_hours > 0 else 0
            filtered_data["all"].append({"total_hours": worked_hours, "total_percentage":percentage_all})
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong :( :{e}")
        return JsonResponse({"error": f"Invalid request: {e}"}, status=405)



##########################################################################
#    __  ___                               ___                    __     #
#   /  |/  /__ ____  ___ ____ ____ ____   / _ \___ ___  ___  ____/ /____ #
#  / /|_/ / _ `/ _ \/ _ `/ _ `/ -_) __/  / , _/ -_) _ \/ _ \/ __/ __(_-< #
# /_/  /_/\_,_/_//_/\_,_/\_, /\__/_/    /_/|_|\__/ .__/\___/_/  \__/___/ #
#                       /___/                   /_/                      #
##########################################################################



@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_manager_activity_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        project_id = request.GET.get("project")
        manager_id = int(pk)

        if month and year and manager_id and project_id and user_id:
            start_date, end_date = get_start_end_date(month, year)

            manager = CustomUser.objects.get(id=manager_id)

            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            users = CustomUser.objects.filter(
                ~Q(is_superuser=True),
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                department=manager.department.id,
                location=manager.location.id
            )

            if user_id != "all":
                users = users.filter(id=int(user_id))

            logs = prepare_report_activity_logs(users, project_id, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_manager_project_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        project_id = request.GET.get("project")
        manager_id = int(pk)

        if month and year and manager_id and project_id and user_id:
            start_date, end_date = get_start_end_date(month, year)

            manager = CustomUser.objects.get(id=manager_id)


            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            users = CustomUser.objects.filter(
                ~Q(is_superuser=True),
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                department=manager.department.id,
                location=manager.location.id
            )

            if user_id != "all":
                users = users.filter(id=int(user_id))

            logs = prepare_report_projects(users, project_id, start_date, end_date)

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_manager_leave_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        manager_id = int(pk)

        if month and year and manager_id and user_id:
            start_date, end_date = get_start_end_date(month, year)
            manager = CustomUser.objects.get(id=manager_id)


            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            users = CustomUser.objects.filter(
                ~Q(is_superuser=True),
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                department=manager.department.id,
                location=manager.location.id
            )

            if user_id != "all":
                users = users.filter(id=int(user_id))

            logs = prepare_report_leaves(users, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Invalid request")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, "Something went wrong")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_manager_overview_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        project_id = request.GET.get("project")
        manager_id = int(pk)

        if month and year and manager_id and project_id and user_id:
            start_date, end_date = get_start_end_date(month, year)

            manager = CustomUser.objects.get(id=manager_id)


            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            users = CustomUser.objects.filter(
                ~Q(is_superuser=True),
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                department=manager.department.id,
                location=manager.location.id
            )

            if user_id != "all":
                users = users.filter(id=int(user_id))
            
            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, total_hours_wleave, hours_leave_days, hours_pub_holiday = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)

            hours_leave_days_percentage = 0
            if total_hours_wleave > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours_wleave

            project_data, total_worked_hours = prepare_report_expected_projects_workes(users, project_id, total_hours, start_date, end_date)
            total_worked_hours = Decimal(total_worked_hours)
            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours
            missed_hours = total_hours - total_worked_hours

            filtered_data = {
                "date_range":{"start":start_date.strftime(r"%d-%b-%Y"), "end":end_date.strftime(r"%d-%b-%Y")},
                "projects": [],
                "all": {
                    "expected_hours": total_hours,
                    "missed_hours" : missed_hours,
                    "total_worked_hours": total_worked_hours,
                    "hours_pub_holiday": hours_pub_holiday,
                    "hours_leave_days": hours_leave_days,
                    "percent_complete": percent_complete,
                }
            }

            for project_name, data in project_data.items():
                project_info = {
                    "name": project_name,
                    "total": data["total"],
                    "percentage": data["percentage"],
                }
                filtered_data["projects"].append(project_info)

            filtered_data["projects"].append({
                "name": "Absences",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
            })

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


#TODO:
@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_manager_missed_report(request, pk):
    try:
        user_id = request.GET.get("user")
        month = request.GET.get("month")
        year = request.GET.get("year")
        manager_id = int(pk)

        if month and year and manager_id and user_id:
            start_date, end_date = get_start_end_date(month, year)
            manager = CustomUser.objects.get(id=manager_id)

            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            users = CustomUser.objects.filter(
                ~Q(is_superuser=True),
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                department=manager.department.id,
                location=manager.location.id
            )
            if user_id != "all":
                users = users.filter(id=int(user_id))
            

            user_report = []

            for user in users:
                # getting the total number of daily hours for selected users
                daily_hours = Decimal(user.daily_hours)
                # getting the number of working saturdays since the number of daily hours in sat is 3 always
                working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), user=user)
                # getting the hours for all needed elements
                total_hours, total_hours_wleave, hours_leave_days, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours, working_saturdays, user=user)

                # Calculate total expected hours
                total_expected_hours = total_hours
                # with the leave hours
                total_actual_hours = total_hours_wleave

                # Calculate total worked hours
                activity_logs = get_activity_logs(user.id, "all", start_date, end_date)
                total_worked_hours = sum(Decimal(log.hours_worked) for log in activity_logs)

                # Calculate missed hours
                missed_hours = total_expected_hours - total_worked_hours

                if missed_hours > 0:
                    user_report.append({
                        "name": user.first_name.capitalize() + " " + user.last_name.capitalize(),
                        "role": user.role.name,
                        "department":str(user.department.dept_name).capitalize(),
                        "location":str(user.location.loc_name).upper(),
                        "expected_hours": total_actual_hours,
                        "worked_hours":total_worked_hours,
                        "leave_hours":hours_leave_days,
                        "missed_hours": missed_hours,
                    })
            return JsonResponse({"users": user_report})

        else:
            messages.error(request, "Invalid request parameters")
            return JsonResponse({"error": "Invalid request"}, status=400)

    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Server error"}, status=500)

@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_manager_pro_act_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        manager_id = int(pk)

        if month and year and manager_id and user_id:
            start_date, end_date = get_start_end_date(month, year)
            manager = CustomUser.objects.get(id=manager_id)

            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            users = CustomUser.objects.filter(
                ~Q(is_superuser=True),
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                department=manager.department.id,
                location=manager.location.id
            )


            if user_id != "all":
                users = users.filter(id=int(user_id))

            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, _, _, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)


            project_activities, project_percentages, activity_percentages, project_totals, activity_totals =\
                  prepare_report_pro_act_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": []}

            # append project and activity to filtered data
            for project_name, activities in project_activities.items():
                for activity_name, hours_worked in activities.items():
                    project_info = {
                        "project": {"name": project_name, "total_hours":project_totals[project_name] ,"percentage": project_percentages.get(project_name, 0)},
                        "activity": {"name": activity_name, "total_hours":activity_totals[activity_name] ,"percentage": activity_percentages.get(activity_name, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_manager_pro_user_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        manager_id = int(pk)
        if month and year and manager_id and user_id:
            start_date, end_date = get_start_end_date(month, year)
            dir = Role.objects.get(name="Director")
            adm = Role.objects.get(name="Admin")
            manager = CustomUser.objects.get(id=manager_id)
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(role=adm.id),
                ~Q(is_superuser=True),
                location=manager.location.id,
                department=manager.department.id
            )
            if user_id != "all":
                users = users.filter(id=int(user_id))


            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, _, _, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)

            project_users, project_percentages, user_percentages, project_totals, user_totals, worked_hours =\
                  prepare_report_pro_user_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": [], "all":[]}

            # append project and activity to filtered data
            for project_name, users in project_users.items():
                for username, hours_worked in users.items():
                    project_info = {
                        "project": {"name": project_name, "total_hours":project_totals[project_name], "percentage": project_percentages.get(project_name, 0)},
                        "user": {"name": username, "total_hours":user_totals[username], "percentage": user_percentages.get(username, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            percentage_all = (worked_hours/total_hours)*100 if total_hours > 0 else 0
            filtered_data["all"].append({"total_hours": worked_hours, "total_percentage":percentage_all})
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong :( :{e}")
        return JsonResponse({"error": f"Invalid request: {e}"}, status=405)




###############################################################
#    ___     __      _          ___                    __     #
#   / _ |___/ /_ _  (_)__      / _ \___ ___  ___  ____/ /____ #
#  / __ / _  /  ' \/ / _ \    / , _/ -_) _ \/ _ \/ __/ __(_-< #
# /_/ |_\_,_/_/_/_/_/_//_/   /_/|_|\__/ .__/\___/_/  \__/___/ #
#                                    /_/                      #
###############################################################


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_admin_activity_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        project_id = request.GET.get("project")
        department_id = request.GET.get("department")
        admin_id = int(pk)

        if month and year and admin_id and project_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)

            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )

            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            logs = prepare_report_activity_logs(users, project_id, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_admin_project_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        project_id = request.GET.get("project")
        department_id = request.GET.get("department")
        admin_id = int(pk)

        if month and year and admin_id and project_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)
            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            logs = prepare_report_projects(users, project_id, start_date, end_date)

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_admin_leave_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        admin_id = int(pk)

        if month and year and admin_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)
            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            logs = prepare_report_leaves(users, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Invalid request")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, "Something went wrong")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_admin_overview_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        project_id = request.GET.get("project")
        department_id = request.GET.get("department")
        admin_id = int(pk)

        if month and year and admin_id and project_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)
            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, total_hours_wleave, hours_leave_days, hours_pub_holiday = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)

            hours_leave_days_percentage = 0
            if total_hours_wleave > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours_wleave

            project_data, total_worked_hours = prepare_report_expected_projects_workes(users, project_id, total_hours, start_date, end_date)
            total_worked_hours = Decimal(total_worked_hours)
            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours
            missed_hours = total_hours - total_worked_hours

            filtered_data = {
                "date_range":{"start":start_date.strftime(r"%d-%b-%Y"), "end":end_date.strftime(r"%d-%b-%Y")},
                "projects": [],
                "all": {
                    "expected_hours": total_hours,
                    "missed_hours" : missed_hours,
                    "total_worked_hours": total_worked_hours,
                    "hours_pub_holiday": hours_pub_holiday,
                    "hours_leave_days": hours_leave_days,
                    "percent_complete": percent_complete,
                }
            }

            for project_name, data in project_data.items():
                project_info = {
                    "name": project_name,
                    "total": data["total"],
                    "percentage": data["percentage"],
                }
                filtered_data["projects"].append(project_info)

            filtered_data["projects"].append({
                "name": "Absences",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
            })

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Invalid request"}, status=405)


#TODO:
@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_admin_missed_report(request, pk):
    try:
        user_id = request.GET.get("user")
        month = request.GET.get("month")
        year = request.GET.get("year")
        department_id = request.GET.get("department")
        admin_id = int(pk)

        if month and year and admin_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)
            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            user_report = []
            for user in users:
                # getting the total number of daily hours for selected users
                daily_hours = Decimal(user.daily_hours)
                # getting the number of working saturdays since the number of daily hours in sat is 3 always
                working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), user=user)
                # getting the hours for all needed elements
                total_hours, total_hours_wleave, hours_leave_days, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours, working_saturdays, user=user)

                # Calculate total expected hours
                total_expected_hours = total_hours
                # with the leave hours
                total_actual_hours = total_hours_wleave

                # Calculate total worked hours
                activity_logs = get_activity_logs(user.id, "all", start_date, end_date)
                total_worked_hours = sum(Decimal(log.hours_worked) for log in activity_logs)

                # Calculate missed hours
                missed_hours = total_expected_hours - total_worked_hours

                if missed_hours > 0:
                    user_report.append({
                        "name": user.first_name.capitalize() + " " + user.last_name.capitalize(),
                        "role": user.role.name,
                        "department": str(user.department.dept_name).capitalize(),
                        "location":str(user.location.loc_name).upper(),
                        "expected_hours": total_actual_hours,
                        "worked_hours":total_worked_hours,
                        "leave_hours":hours_leave_days,
                        "missed_hours": missed_hours,
                    })

            return JsonResponse({"users": user_report})

        else:
            messages.error(request, "Invalid request parameters")
            return JsonResponse({"error": "Invalid request"}, status=400)

    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Server error"}, status=500)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_admin_pro_act_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        admin_id = int(pk)

        if month and year and admin_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)
            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, _, _, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)

            project_activities, project_percentages, activity_percentages, project_totals, activity_totals =\
                  prepare_report_pro_act_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": []}

            # append project and activity to filtered data
            for project_name, activities in project_activities.items():
                for activity_name, hours_worked in activities.items():
                    project_info = {
                        "project": {"name": project_name, "total_hours":project_totals[project_name] ,"percentage": project_percentages.get(project_name, 0)},
                        "activity": {"name": activity_name, "total_hours":activity_totals[activity_name] ,"percentage": activity_percentages.get(activity_name, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": f"Invalid request {e}"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_holiday_report(request):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        if month and year:
            start_date, end_date = get_start_end_date(month, year)

            _holidays = Holiday.objects.filter(
                holiday_date__range = [start_date, end_date]
            )

            filtered_data = {"report": []}
            for holiday in _holidays:
                holiday_name = holiday.holiday_name
                filtered_data["report"].append({"name":holiday_name, "date":holiday.holiday_date.strftime(r"%d-%b-%Y")})
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": f"Invalid request {e}"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_admin_pro_user_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        admin_id = int(pk)
        if month and year and admin_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)
            dir = Role.objects.get(name="Director")
            users = CustomUser.objects.filter(
                ~Q(role=dir.id),
                ~Q(is_superuser=True),
                location=request.user.location.id
            )

            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            # getting the total number of daily hours for selected users
            daily_hours_total = sum([Decimal(user.daily_hours) for user in users])
            # getting the number of working saturdays since the number of daily hours in sat is 3 always
            working_saturdays = get_working_saturdays(start_date.ctime(), end_date.ctime(), users)
            # getting the hours for all needed elements
            total_hours, _, _, _ = calc_total_hours_for_all_sections(start_date, end_date, daily_hours_total, working_saturdays, users)

            project_users, project_percentages, user_percentages, project_totals, user_totals, worked_hours =\
                  prepare_report_pro_user_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": [], "all":[]}

            # append project and activity to filtered data
            for project_name, users in project_users.items():
                for username, hours_worked in users.items():
                    project_info = {
                        "project": {"name": project_name, "total_hours":project_totals[project_name], "percentage": project_percentages.get(project_name, 0)},
                        "user": {"name": username, "total_hours":user_totals[username], "percentage": user_percentages.get(username, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            percentage_all = (worked_hours/total_hours)*100 if total_hours > 0 else 0
            filtered_data["all"].append({"total_hours": worked_hours, "total_percentage":percentage_all})
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, f"Something went wrong :( :{e}")
        return JsonResponse({"error": f"Invalid request: {e}"}, status=405)

