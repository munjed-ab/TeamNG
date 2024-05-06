from django.http import JsonResponse
from django.db.models import F, Sum, Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from datetime import date, timedelta
from project_manager.models import ActivityLogs, Holiday, Leave, Project, Activity, CustomUser
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib import messages
import calendar
import pandas as pd
import json
from decimal import Decimal
from django.views.decorators.http import require_POST
from ..views import get_filtered_dates
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
        end_date = date(int(year), 12, 31)
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


def calculate_public_holidays(order_start: date, order_end: date, users_count: int):
    """
    Calculate the total number of public holiday hours within a time period.
    """
    pub_holidays = Holiday.objects.filter(
        holiday_date__range=[order_start, order_end]
    ).count()

    hours_pub_holiday = pub_holidays * 8 * users_count
    return hours_pub_holiday


def calculate_leave_days(users: list[CustomUser], order_start: date, order_end: date)-> int:
    """
    Purpose: Calculates the total number of leave days taken by users within a time period.
    Parameters:
        users: QuerySet of users.
        order_start: The start date of the time period.
        order_end: The end date of the time period.
    Returns: The total number of leave days taken by users.
    """
    hours_leave_days = 0
    for user in users:
        approved_leave_requests = Leave.objects.filter(
            from_user=user.id,
            is_approved=True,
            start_date__lte=order_end,
            end_date__gte=order_start
        )
        for leave_request in approved_leave_requests:
            leave_start = max(leave_request.start_date, order_start)
            leave_end = min(leave_request.end_date, order_end)
            filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
            hours_leave_days += len(filtered_dates) * 8
    return hours_leave_days


def calculate_project_and_activity_data(users, project_id, date_start, date_end):

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
        user_username = activity_log.user.username
        
        project_data[project_name]['total'] += activity_log.hours_worked
        project_data[project_name]['activity_logs'].append({
            'date': activity_log.date.strftime('%Y-%m-%d'),
            'hours_worked': activity_log.hours_worked,
            'details': activity_log.details,
            'activity': activity_type_name,
            'time_added': activity_log.updated.strftime('%Y-%m-%d [%H:%M:%S]'),
            'user': user_username
        })
        
        activity_type_data[activity_type_name]['total'] += activity_log.hours_worked
        activity_type_data[activity_type_name]['activity_logs'].append({
            'date': activity_log.date.strftime('%Y-%m-%d'),
            'hours_worked': activity_log.hours_worked,
            'details': activity_log.details,
            'project': project_name,
            'time_added': activity_log.updated.strftime('%Y-%m-%d [%H:%M:%S]'),
            'user': user_username
        })
        total_worked_hours += activity_log.hours_worked
    
    return project_data, activity_type_data, total_worked_hours


def prepare_response_data(project_data:dict, activity_type_data:dict, total_hours:int, total_worked_hours:float, missed_hours:float, hours_leave_days:int, hours_pub_holiday:int) -> dict:
    """
    Purpose: Prepares the response data for the overview.
    Parameters:
        project_data: Dictionary containing project data.
        activity_type_data: Dictionary containing activity type data.
        total_hours: Total expected hours.
        total_worked_hours: Total worked hours.
        missed_hours: Total missed hours.
        hours_leave_days: Total leave hours.
        hours_pub_holiday: Total public holiday hours.
    Returns: A dictionary containing the prepared response data.
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
        "name": "Leaves",
        "total": hours_leave_days,
        "percentage": hours_leave_days * 100 / total_hours if total_hours > 0 else 0
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


def getUserSupervisor(user):
    if user.is_admin:
        return ""
    
    # discover the filter conditions based on the user's role
    filter_conditions = Q(location=user.location, department=user.department)
    if user.is_manager:
        filter_conditions &= Q(is_admin=True)
    else:
        filter_conditions &= Q(is_manager=True)
    
    # query deez database to find the supervisor
    supervisor = CustomUser.objects.filter(filter_conditions).first()
    return str(supervisor.get_full_name()) if supervisor else ""


def prepare_report_activity_logs(users, project_id, start_date, end_date):
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
            'time_added': log.updated.strftime('%Y-%m-%d [%H:%M:%S]'),
            'username': log.user.username,
            'project': project_name,
            'activity': log.activity.activity_name,
            'department': log.user.department.dept_name,
            'date': log.date.strftime('%Y-%m-%d'),
            "hours_worked": Decimal(log.hours_worked),
            "details": log.details,
        })
    
    return logs



def prepare_report_projects(users: list[CustomUser], project_id: int, start_date: date, end_date: date)-> dict:
    projects = defaultdict(lambda: {"project":"", "username":"", "department":"", "location":"", "supervisor":"","worked_hours":0})
    logs = {"projects":[]}
    for user in users:
        activity_logs = get_activity_logs(user.id, project_id, start_date, end_date)
        supervisor = getUserSupervisor(user)
        username = user.username
        dept = user.department.dept_name
        loc = user.location.loc_name

        for log in activity_logs:
            project_name = log.project.project_name
            projects[project_name]["project"] = project_name
            projects[project_name]["username"] = username
            projects[project_name]["department"] = dept
            projects[project_name]["location"] = loc
            projects[project_name]["supervisor"] = supervisor
            projects[project_name]["worked_hours"] += log.hours_worked

    logs["projects"] = list(projects.values())
    return logs


def prepare_report_leaves(users, start_date, end_date):
    leaves = []
    logs = {"leaves": []}
    
    # fetch deez leave records for the specified users and time period where it\'s in users
    leaves_queryset = Leave.objects.filter(
        from_user__in=users,
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    
    # Iterate through leave records to prepare leave data
    for log in leaves_queryset:
        leave_data = {
            "from": log.from_user.username if log.from_user else None,
            "to": log.to_user.username if log.to_user else None,
            "start_date": log.start_date.strftime(r"%Y-%m-%d"),
            "end_date": log.end_date.strftime(r"%Y-%m-%d"),
            "days": log.v_days,
            "actual_days": log.days,
            "type": log.leave_type,
            "respond": "reject" if log.is_rejected else "accept" if log.is_approved else "pending"
        }
        leaves.append(leave_data)

    logs["leaves"] = leaves
    return logs


def prepare_report_expected_projects_workes(users: list[CustomUser], project_id: int, total_hours: int, date_start: date, date_end: date):
    project_data = defaultdict(lambda: {'total':0, 'percentage': 0})
    total_worked_hours:float = 0
    for user in users:
        activity_logs = get_activity_logs(user.id, project_id, date_start, date_end)
        for activity_log in activity_logs:
            project_name = activity_log.project.project_name

            project_data[project_name]['total'] += activity_log.hours_worked
            total_worked_hours+=activity_log.hours_worked

        projects:Project
        if project_id == "all":
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(id=int(project_id))

        for project in projects:
            project_data[project.project_name]['percentage'] = project_data[project.project_name]['total']*100 / total_hours

    return project_data, total_worked_hours


def prepare_report_pro_act_percentages(users: list[CustomUser], total_hours, date_start: date, date_end: date):
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

    for user in users:
        activity_logs = get_activity_logs(user.id, "all", date_start, date_end)
        for activity_log in activity_logs:
            project_name = activity_log.project.project_name
            activity_name = activity_log.activity.activity_name
            hours_worked = activity_log.hours_worked

            project_totals[project_name] += hours_worked
            activity_totals[activity_name] += hours_worked

            project_activities[project_name][activity_name] += hours_worked

    # Calculate percentages
    project_percentages = {project_name: (hours / total_hours) * 100 for project_name, hours in project_totals.items()}
    activity_percentages = {activity_name: (hours / total_hours) * 100 for activity_name, hours in activity_totals.items()}
    return project_activities, project_percentages, activity_percentages


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

            if not request.user.is_authenticated:
                messages.error(request, "Access Denied.")
                return JsonResponse({"error": "Access Denied"}, status=405)
            
            if not date:
                messages.error(request, "Invalid Request.")
                return JsonResponse({"error": "Invalid request data"}, status=405)

            total_hours = sum(Decimal(item["hours"]) for item in activity_data)

            if total_hours > request.user.daily_hours:
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
def overview_data(request):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        project_id = request.GET.get("project")
        # if not request.user.is_admin:
        #     messages.error(request, "Access Denied")
        #     return JsonResponse({"error": "Access Denied"}, status=400)
    
        if month and year and user_id and department_id and project_id:
            start_date, end_date = get_start_end_date(month, year)

            users = CustomUser.objects.filter(is_superuser=False)
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=department_id)

            user_count = users.count()

            total_hours = 8 * len(get_filtered_dates(start_date, end_date)) * user_count

            hours_leave_days = calculate_leave_days(users, start_date, end_date)
            hours_pub_holiday = calculate_public_holidays(start_date, end_date, user_count)
            total_hours -= hours_pub_holiday

            project_data, activity_type_data, total_worked_hours = calculate_project_and_activity_data(users, project_id, start_date, end_date)
            missed_hours = total_hours - float(total_worked_hours)
            filtered_data = prepare_response_data(project_data, activity_type_data, total_hours, float(total_worked_hours), missed_hours, hours_leave_days, hours_pub_holiday)

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Invalid request parameters")
            return JsonResponse({"error": "Invalid request"}, status=400)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Server error"}, status=500)



@api_view(['GET'])
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


            users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id,
                    location=location_id,
                    is_admin=False
                )
            if user_id != "all":
                users = users.filter(id=int(user_id))

            total_hours = 8 * len(get_filtered_dates(start_date, end_date)) * len(users)

            hours_leave_days = calculate_leave_days(users, start_date, end_date)
            hours_pub_holiday = calculate_public_holidays(start_date, end_date, len(users))
            total_hours -= hours_pub_holiday

            project_data, activity_type_data, total_worked_hours = calculate_project_and_activity_data(users, project_id, start_date, end_date)
            missed_hours = total_hours - total_worked_hours
            filtered_data = prepare_response_data(project_data, activity_type_data, total_hours, total_worked_hours, missed_hours, hours_leave_days, hours_pub_holiday)

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Invalid request parameters")
            return JsonResponse({"error": "Invalid request"}, status=400)
    except Exception as e:
        messages.error(request, f"Something went wrong: {e}")
        return JsonResponse({"error": "Server error"}, status=500)


@api_view(['GET'])
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
            total_hours = 8 * len(get_filtered_dates(start_date, end_date))

            hours_leave_days = calculate_leave_days(users, start_date, end_date)
            hours_pub_holiday = calculate_public_holidays(start_date, end_date, 1)
            total_hours -= hours_pub_holiday

            project_data, activity_type_data, total_worked_hours = calculate_project_and_activity_data(users, project_id, start_date, end_date)
            missed_hours = total_hours - total_worked_hours
            filtered_data = prepare_response_data(project_data, activity_type_data, total_hours, total_worked_hours, missed_hours, hours_leave_days, hours_pub_holiday)

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
                is_superuser = False,
            )
            logs = prepare_report_activity_logs(users, project_id, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
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
                is_superuser = False,
            )
            logs = prepare_report_projects(users, project_id, start_date, end_date)

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
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
                is_superuser = False,
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

            user = CustomUser.objects.filter(id=user_id, is_superuser=False)
            total_hours:int = 0
            users_count = 1

            filtered_dates_satge1 = get_filtered_dates(start_date.ctime(), end_date.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            hours_leave_days = calculate_leave_days(user, start_date, end_date)
            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours

            hours_pub_holiday:int = calculate_public_holidays(start_date, end_date, users_count)
            total_hours -= hours_pub_holiday

            project_data, total_worked_hours = prepare_report_expected_projects_workes(user, project_id, total_hours, start_date, end_date)
            total_worked_hours = float(total_worked_hours)
            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours
            missed_hours = total_hours - total_worked_hours

            filtered_data = {
                "date_range":{"start":start_date.strftime(r"%Y/%m/%d"), "end":end_date.strftime(r"%Y/%m/%d")},
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
                "name": "Leaves",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
            })

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
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

            users = CustomUser.objects.filter(id=user_id, is_superuser=False)
            total_hours:int = 0
            users_count = 1

            filtered_dates_satge1 = get_filtered_dates(start_date.ctime(), end_date.ctime())
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            project_activities, project_percentages, activity_percentages =\
                  prepare_report_pro_act_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": []}

            # append project and activity to filtered data
            for project_name, activities in project_activities.items():
                for activity_name, hours_worked in activities.items():
                    project_info = {
                        "project": {"name": project_name, "percentage": project_percentages.get(project_name, 0)},
                        "activity": {"name": activity_name, "percentage": activity_percentages.get(activity_name, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)



##########################################################################
#    __  ___                               ___                    __     #
#   /  |/  /__ ____  ___ ____ ____ ____   / _ \___ ___  ___  ____/ /____ #
#  / /|_/ / _ `/ _ \/ _ `/ _ `/ -_) __/  / , _/ -_) _ \/ _ \/ __/ __(_-< #
# /_/  /_/\_,_/_//_/\_,_/\_, /\__/_/    /_/|_|\__/ .__/\___/_/  \__/___/ #
#                       /___/                   /_/                      #
##########################################################################



@api_view(['GET'])
@ensure_csrf_cookie
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
            users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=manager.department.id,
                    location=manager.location.id,
                    is_admin=False
                )
            if user_id != "all":
                users = users.filter(id=int(user_id))

            logs = prepare_report_activity_logs(users, project_id, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
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

            users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=manager.department.id,
                    location=manager.location.id,
                    is_admin=False
                )
            if user_id != "all":
                users = users.filter(id=int(user_id))

            logs = prepare_report_projects(users, project_id, start_date, end_date)

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
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

            users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=manager.department.id,
                    location=manager.location.id,
                    is_admin=False
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

            users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=manager.department.id,
                    location=manager.location.id,
                    is_admin=False
                )
            if user_id != "all":
                users = users.filter(id=int(user_id))
            
            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(start_date.ctime(), end_date.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            hours_leave_days = calculate_leave_days(users, start_date, end_date)
            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours

            hours_pub_holiday:int = calculate_public_holidays(start_date, end_date, users_count)
            total_hours -= hours_pub_holiday

            project_data, total_worked_hours = prepare_report_expected_projects_workes(users, project_id, total_hours, start_date, end_date)
            total_worked_hours = float(total_worked_hours)
            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours
            missed_hours = total_hours - total_worked_hours

            filtered_data = {
                "date_range":{"start":start_date.strftime(r"%Y/%m/%d"), "end":end_date.strftime(r"%Y/%m/%d")},
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
                "name": "Leaves",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
            })

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
def get_manager_pro_act_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        manager_id = int(pk)

        if month and year and manager_id and user_id:
            start_date, end_date = get_start_end_date(month, year)
            manager = CustomUser.objects.get(id=manager_id)
            users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=manager.department.id,
                    location=manager.location.id,
                    is_admin=False
                )
            if user_id != "all":
                users = users.filter(id=int(user_id))

            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(start_date.ctime(), end_date.ctime())
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            project_activities, project_percentages, activity_percentages =\
                  prepare_report_pro_act_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": []}

            # append project and activity to filtered data
            for project_name, activities in project_activities.items():
                for activity_name, hours_worked in activities.items():
                    project_info = {
                        "project": {"name": project_name, "percentage": project_percentages.get(project_name, 0)},
                        "activity": {"name": activity_name, "percentage": activity_percentages.get(activity_name, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)
    


###############################################################
#    ___     __      _          ___                    __     #
#   / _ |___/ /_ _  (_)__      / _ \___ ___  ___  ____/ /____ #
#  / __ / _  /  ' \/ / _ \    / , _/ -_) _ \/ _ \/ __/ __(_-< #
# /_/ |_\_,_/_/_/_/_/_//_/   /_/|_|\__/ .__/\___/_/  \__/___/ #
#                                    /_/                      #
###############################################################


@api_view(['GET'])
@ensure_csrf_cookie
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
            users = CustomUser.objects.filter(is_superuser=False)
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            logs = prepare_report_activity_logs(users, project_id, start_date, end_date)
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
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
            users = CustomUser.objects.filter(is_superuser=False)
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            logs = prepare_report_projects(users, project_id, start_date, end_date)

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
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
            users = CustomUser.objects.filter(is_superuser=False)
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
            users = CustomUser.objects.filter(is_superuser=False)
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))
            
            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(start_date.ctime(), end_date.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            hours_leave_days = calculate_leave_days(users, start_date, end_date)
            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours

            hours_pub_holiday:int = calculate_public_holidays(start_date, end_date, users_count)
            total_hours -= hours_pub_holiday

            project_data, total_worked_hours = prepare_report_expected_projects_workes(users, project_id, total_hours, start_date, end_date)
            total_worked_hours = float(total_worked_hours)
            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours
            missed_hours = total_hours - total_worked_hours

            filtered_data = {
                "date_range":{"start":start_date.strftime(r"%Y/%m/%d"), "end":end_date.strftime(r"%Y/%m/%d")},
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
                "name": "Leaves",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
            })

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['GET'])
@ensure_csrf_cookie
def get_admin_pro_act_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        admin_id = int(pk)

        if month and year and admin_id and user_id and department_id:
            start_date, end_date = get_start_end_date(month, year)
            users = CustomUser.objects.filter(is_superuser=False)
            if user_id != "all":
                users = users.filter(id=int(user_id))
            if department_id != "all":
                users = users.filter(department=int(department_id))

            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(start_date.ctime(), end_date.ctime())
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            project_activities, project_percentages, activity_percentages =\
                  prepare_report_pro_act_percentages(users, total_hours, start_date, end_date)

            filtered_data = {"report": []}

            # append project and activity to filtered data
            for project_name, activities in project_activities.items():
                for activity_name, hours_worked in activities.items():
                    project_info = {
                        "project": {"name": project_name, "percentage": project_percentages.get(project_name, 0)},
                        "activity": {"name": activity_name, "percentage": activity_percentages.get(activity_name, 0)},
                        "hours_worked": hours_worked
                    }
                    filtered_data["report"].append(project_info)
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


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
                filtered_data["report"].append({"name":holiday_name, "date":holiday.holiday_date.strftime(r"%Y-%m-%d")})
            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)
