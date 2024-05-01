from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from .models import CustomUser, Project, Activity, Leave, Holiday, ActivityLogs, Department, Location
from decimal import Decimal
from datetime import *
import calendar
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import View
from datetime import timedelta
import json
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from .views import get_filtered_dates
from collections import defaultdict
import pandas as pd
from django.db.models import F, Sum
from datetime import datetime, timedelta


# API VIEWS
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


class CalendarDataView(View):
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_firstday_lastday_specific_month(self, year, month):
        first_day_current_month = date(year, month, 1)
        last_day_current_month = date(year, month, calendar.monthrange(year, month)[1])
        return first_day_current_month, last_day_current_month

    def get(self, request):
        try:
            if request.method == "GET":
                year = int(request.GET.get("year"))
                month = int(request.GET.get("month"))

                # Get the start and end dates of the requested month
                start_date, end_date = self.get_firstday_lastday_specific_month(year, month)

                # Retrieve activity logs for the requested month
                activity_logs = ActivityLogs.objects.filter(
                    user=request.user,
                    date__range=[start_date, end_date]
                ).annotate(day=F('date')).values('day').annotate(total_hours=Sum('hours_worked')).order_by("day")

                # Create a dictionary to store data for each day of the month
                all_month_days = {
                    str(start_date + timedelta(days=i)): 0 for i in range((end_date - start_date).days + 1)
                }
                # Update the dictionary with total hours worked for each day from activity logs
                all_month_days.update({
                    str(log['day']): log['total_hours'] for log in activity_logs
                })

                # NO MUCH DIFFERENCE FROM THE ABOVE CODE (in speed) BUT THE "update()" MORE READABLE
                # for log in activity_logs:
                #     date_str = str(log['day'])
                #     all_month_days[date_str] = log['total_hours']

                return JsonResponse(all_month_days)
        except Exception as e:
            messages.error(request, "Something went wrong, I can not fetch the working hours for you :(")
            return JsonResponse({'error': str(e)}, status=500)


@ensure_csrf_cookie
def get_holiday_data(request):
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


@ensure_csrf_cookie
def get_leave_data(request):
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


@ensure_csrf_cookie
def post_activity_data(request):
    try:
        if request.method == "POST":
            data_str = request.body.decode('utf-8')
            data_dict = json.loads(data_str)
            activity_data = json.loads(data_dict['data'])
            date = activity_data[0].get("date")
 
            if not date:
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


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def get_activity_logs(user_id, project_id, order_start, order_end):
    if project_id == "all":
        return ActivityLogs.objects.filter(user=user_id, date__range=[order_start, order_end])
    else:
        return ActivityLogs.objects.filter(user=user_id, date__range=[order_start, order_end], project=project_id)


def calculate_public_holidays(order_start, order_end, users_count):
    pub_holidays = Holiday.objects.filter(holiday_date__range=[order_start, order_end])
    hours_pub_holiday = len(pub_holidays) * 8 * users_count
    return hours_pub_holiday


@login_required(login_url="login")
@ensure_csrf_cookie
def overview_data(request):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        project_id = request.GET.get("project")
        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and department_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    id=int(user_id)
                )
            if department_id != "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id
                )
                
            total_hours:int = 0
            users_count = len(users)
            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            hours_leave_days:int = 0
            for user in users:
                approved_leave_requests = Leave.objects.filter(
                    from_user=user.id,
                    is_approved=True,
                    start_date__lte=order_end,  # Leave starts before or on order_end
                    end_date__gte=order_start  # Leave ends after or on order_start
                )
                for leave_request in approved_leave_requests:
                    # Find the intersection of leave dates and the range (order_start, order_end)
                    leave_start = max(leave_request.start_date, order_start)
                    leave_end = min(leave_request.end_date, order_end)
                    filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
                    hours_leave_days += len(filtered_dates) * 8


            hours_pub_holiday:int = calculate_public_holidays(order_start, order_end, users_count)
            total_hours -= hours_pub_holiday

            project_data = defaultdict(lambda: {'total':0, 'percentage': 0, 'activity_logs': []})
            total_worked_hours:float = 0
            activity_type_data = defaultdict(lambda: {'total':0, 'percentage': 0, 'activity_logs': []})

            for user in users:
                activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)
                for activity_log in activity_logs:
                    project_name = activity_log.project.project_name

                    project_data[project_name]['total'] += activity_log.hours_worked
                    total_worked_hours+=activity_log.hours_worked
                    project_data[project_name]['activity_logs'].append({
                        'date': activity_log.date.strftime(f'%Y-%m-%d'),
                        'hours_worked': activity_log.hours_worked,
                        'details':activity_log.details,
                        'activity':activity_log.activity.activity_name,
                        'time_added':activity_log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                        "user":user.username
                    })

                    activity_type_name = activity_log.activity.activity_name
                    activity_type_data[activity_type_name]['total'] += activity_log.hours_worked
                    activity_type_data[activity_type_name]['activity_logs'].append({
                        'date': activity_log.date.strftime(f'%Y-%m-%d'),
                        'hours_worked': activity_log.hours_worked,
                        'details':activity_log.details,
                        'project':activity_log.project.project_name,
                        'time_added':activity_log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                        "user":user.username
                    })

            projects:Project
            if project_id == "all":
                projects = Project.objects.all()
            else:
                projects = Project.objects.filter(id=int(project_id))
            for project in projects:
                project_data[project.project_name]['percentage'] = project_data[project.project_name]['total']*100 / total_hours

            activities = Activity.objects.all()
            for activity in activities:
                activity_type_data[activity.activity_name]['percentage'] = activity_type_data[activity.activity_name]['total']*100 / total_hours

            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours
            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours

            missed_hours = total_hours - total_worked_hours
            filtered_data = {
                "projects": [],
                "activities": [],
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
                    "activity_logs": data["activity_logs"]
                }
                filtered_data["projects"].append(project_info)

            filtered_data["projects"].append({
                "name": "Leaves",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
                # "logs": []
            })

            for activity_name, data in activity_type_data.items():
                activity_info = {
                    "name": activity_name,
                    "total": data["total"],
                    "percentage": data["percentage"],
                    "activity_logs": data["activity_logs"]
                }
                filtered_data["activities"].append(activity_info)

            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


@ensure_csrf_cookie
def overview_manager_data(request):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        location_id = request.GET.get("location")
        project_id = request.GET.get("project")

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and department_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id,
                    location=location_id,
                    is_admin=False
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    id=int(user_id),
                    department=department_id,
                    location=location_id,
                    is_admin=False
                )

            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count
            hours_leave_days:int = 0
            for user in users:
                approved_leave_requests = Leave.objects.filter(
                    from_user=user.id,
                    is_approved=True,
                    start_date__lte=order_end,  # Leave starts before or on order_end
                    end_date__gte=order_start  # Leave ends after or on order_start
                )
                for leave_request in approved_leave_requests:
                    # Find the intersection of leave dates and the range (order_start, order_end)
                    leave_start = max(leave_request.start_date, order_start)
                    leave_end = min(leave_request.end_date, order_end)
                    filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
                    hours_leave_days += len(filtered_dates) * 8

            hours_pub_holiday:int = calculate_public_holidays(order_start, order_end, users_count)
            total_hours -= hours_pub_holiday


            project_data = defaultdict(lambda: {'total':0, 'percentage': 0, 'activity_logs': []})
            total_worked_hours:float = 0
            activity_type_data = defaultdict(lambda: {'total':0, 'percentage': 0, 'activity_logs': []})

            for user in users:
                activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)

                for activity_log in activity_logs:
                    project_name = activity_log.project.project_name

                    project_data[project_name]['total'] += activity_log.hours_worked
                    total_worked_hours+=activity_log.hours_worked
                    project_data[project_name]['activity_logs'].append({
                        'date': activity_log.date.strftime(f'%Y-%m-%d'),
                        'hours_worked': activity_log.hours_worked,
                        'details':activity_log.details,
                        'activity':activity_log.activity.activity_name,
                        'time_added':activity_log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                        "user":user.username
                    })

                    activity_type_name = activity_log.activity.activity_name
                    activity_type_data[activity_type_name]['total'] += activity_log.hours_worked
                    activity_type_data[activity_type_name]['activity_logs'].append({
                        'date': activity_log.date.strftime(f'%Y-%m-%d'),
                        'hours_worked': activity_log.hours_worked,
                        'details':activity_log.details,
                        'project':activity_log.project.project_name,
                        'time_added':activity_log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                        "user":user.username
                    })

            projects:Project
            if project_id == "all":
                projects = Project.objects.all()
            else:
                projects = Project.objects.filter(id=int(project_id))
            
            for project in projects:
                project_data[project.project_name]['percentage'] = project_data[project.project_name]['total']*100 / total_hours


            activities = Activity.objects.all()
            for activity in activities:
                activity_type_data[activity.activity_name]['percentage'] = activity_type_data[activity.activity_name]['total']*100 / total_hours
            
            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours


            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours


            missed_hours = total_hours - total_worked_hours
            filtered_data = {
                "projects": [],
                "activities": [],
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
                    "activity_logs": data["activity_logs"]
                }
                filtered_data["projects"].append(project_info)

            
            filtered_data["projects"].append({
                "name": "Leaves",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
            })

            for activity_name, data in activity_type_data.items():
                activity_info = {
                    "name": activity_name,
                    "total": data["total"],
                    "percentage": data["percentage"],
                    "activity_logs": data["activity_logs"]
                }
                filtered_data["activities"].append(activity_info)


            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


@ensure_csrf_cookie
def overview_user_data(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            user = CustomUser.objects.get(id=user_id)
            total_hours:int = 0
            users_count = 1

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count
            hours_leave_days:int = 0

            approved_leave_requests = Leave.objects.filter(
                from_user=user,
                is_approved=True,
                start_date__lte=order_end,  # Leave starts before or on order_end
                end_date__gte=order_start  # Leave ends after or on order_start
            )
            for leave_request in approved_leave_requests:
                # Find the intersection of leave dates and the range (order_start, order_end)
                leave_start = max(leave_request.start_date, order_start)
                leave_end = min(leave_request.end_date, order_end)
                filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
                hours_leave_days += len(filtered_dates) * 8


            hours_pub_holiday:int = calculate_public_holidays(order_start, order_end, users_count)
            total_hours -= hours_pub_holiday


            project_data = defaultdict(lambda: {'total':0, 'percentage': 0, 'activity_logs': []})
            total_worked_hours:float = 0
            activity_type_data = defaultdict(lambda: {'total':0, 'percentage': 0, 'activity_logs': []})


            activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)
            for activity_log in activity_logs:
                project_name = activity_log.project.project_name

                project_data[project_name]['total'] += activity_log.hours_worked
                total_worked_hours+=activity_log.hours_worked
                project_data[project_name]['activity_logs'].append({
                    'date': activity_log.date.strftime(f'%Y-%m-%d'),
                    'hours_worked': activity_log.hours_worked,
                    'details':activity_log.details,
                    'activity':activity_log.activity.activity_name,
                    'time_added':activity_log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                    "user":user.username
                })

                activity_type_name = activity_log.activity.activity_name
                activity_type_data[activity_type_name]['total'] += activity_log.hours_worked
                activity_type_data[activity_type_name]['activity_logs'].append({
                    'date': activity_log.date.strftime(f'%Y-%m-%d'),
                    'hours_worked': activity_log.hours_worked,
                    'details':activity_log.details,
                    'project':activity_log.project.project_name,
                    'time_added':activity_log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                    "user":user.username
                })

            projects:Project
            if project_id == "all":
                projects = Project.objects.all()
            else:
                projects = Project.objects.filter(id=int(project_id))
            
            for project in projects:
                project_data[project.project_name]['percentage'] = project_data[project.project_name]['total']*100 / total_hours


            activities = Activity.objects.all()
            for activity in activities:
                activity_type_data[activity.activity_name]['percentage'] = activity_type_data[activity.activity_name]['total']*100 / total_hours

            
            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours

            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours

            missed_hours = total_hours - total_worked_hours
            # total hours : float
            filtered_data = {
                "projects": [],
                "activities": [],
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
                    "activity_logs": data["activity_logs"]
                }
                filtered_data["projects"].append(project_info)

            
            filtered_data["projects"].append({
                "name": "Leaves",
                "total": hours_leave_days,
                "percentage": hours_leave_days_percentage
                # "activity_logs": []  # Assuming no activity logs for leave days
            })

            for activity_name, data in activity_type_data.items():
                activity_info = {
                    "name": activity_name,
                    "total": data["total"],
                    "percentage": data["percentage"],
                    "activity_logs": data["activity_logs"]
                }
                filtered_data["activities"].append(activity_info)


            return JsonResponse(filtered_data)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)
    

# USER REPORTS
@ensure_csrf_cookie
def get_user_activity_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")
        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            logs = {"activity_logs":[]}
            activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)
            for log in activity_logs:
                project_name = log.project.project_name
                logs["activity_logs"].append({
                    'time_added':log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                    'username': log.user.username,
                    'project': project_name,
                    'activity':log.activity.activity_name,
                    'department':log.user.department.dept_name,
                    'date':log.date.strftime(f'%Y-%m-%d'),
                    "hours_worked":Decimal(log.hours_worked),
                    "details":log.details,
                    
                })

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)
    

@ensure_csrf_cookie
def get_user_project_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")
        order_start = date.today()
        order_end = date.today()

        if month and year and user_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users = CustomUser.objects.filter(
                is_superuser=False
            )
            supervisor = ""
            for sup in users:
                if not (user.is_admin or user.is_manager):
                    if sup.location == user.location and sup.department == user.department and sup.is_manager:
                        supervisor = str(sup.get_full_name())
                        break
                elif user.is_manager:
                    if sup.location == user.location and sup.department == user.department and sup.is_admin:
                        supervisor = str(sup.get_full_name())
                        break
                elif user.is_admin:
                    supervisor = ""
                    break

            projects = defaultdict(lambda: {"project":"", "username":"", "department":"", "location":"", "supervisor":"","worked_hours":0})
            logs = {"projects":[]}
            activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)

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

            # Convert defaultdict to list of dictionaries
            logs["projects"] = list(projects.values())
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


@ensure_csrf_cookie
def get_user_leave_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        order_start = date.today()
        order_end = date.today()

        if month and year and user_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)
            leaves = []
            logs = {"leaves": []}
            leaves_queryset = Leave.objects.filter(
                from_user_id=user_id,
                start_date__lte=order_end,  # Leave starts before or on order_end
                end_date__gte=order_start  # Leave ends after or on order_start
            )

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
            return JsonResponse(logs)
        else:
            messages.error(request, "Invalid request")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, "Something went wrong")
        return JsonResponse({"error": str(e)}, status=500)


@ensure_csrf_cookie
def get_user_overview_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)
        project_id = request.GET.get("project")

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            user = CustomUser.objects.get(id=user_id)
            total_hours:int = 0
            users_count = 1

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count
            hours_leave_days:int = 0

            approved_leave_requests = Leave.objects.filter(
                from_user=user,
                is_approved=True,
                start_date__lte=order_end,  # Leave starts before or on order_end
                end_date__gte=order_start  # Leave ends after or on order_start
            )
            for leave_request in approved_leave_requests:
                # Find the intersection of leave dates and the range (order_start, order_end)
                leave_start = max(leave_request.start_date, order_start)
                leave_end = min(leave_request.end_date, order_end)
                filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
                hours_leave_days += len(filtered_dates) * 8


            hours_pub_holiday:int = calculate_public_holidays(order_start, order_end, users_count)
            total_hours -= hours_pub_holiday

            project_data = defaultdict(lambda: {'total':0, 'percentage': 0})
            
            total_worked_hours:float = 0
            activity_logs = get_activity_logs(user_id, project_id, order_start, order_end)
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

            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours

            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours

            missed_hours = total_hours - total_worked_hours
            filtered_data = {
                "date_range":{"start":order_start.strftime(r"%Y/%m/%d"), "end":order_end.strftime(r"%Y/%m/%d")},
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

    
@ensure_csrf_cookie
def get_user_pro_act_report(request, pk):
    try:
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = int(pk)

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            user = CustomUser.objects.get(id=user_id)
            total_hours:int = 0
            users_count = 1

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime())
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

            activity_logs = get_activity_logs(user_id, "all", order_start, order_end)

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

            filtered_data = {"report": []}

            # Append project and activity to filtered data
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
    

@ensure_csrf_cookie
def get_manager_activities(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        project_id = request.GET.get("project")
        user_id = request.GET.get("user")
        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    department=user.department.id,
                    location=user.location.id,
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    id=int(user_id),
                    department=user.department.id,
                    location=user.location.id,
                )

            logs = {"activity_logs":[]}

            for user in users:
                activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)
                for log in activity_logs:
                    project_name = log.project.project_name
                    logs["activity_logs"].append({
                        'time_added':log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                        'username': log.user.username,
                        'project': project_name,
                        'activity':log.activity.activity_name,
                        'department':log.user.department.dept_name,
                        'date':log.date.strftime(f'%Y-%m-%d'),
                        "hours_worked":Decimal(log.hours_worked),
                        "details":log.details,
                    })

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)
    

@ensure_csrf_cookie
def get_manager_project_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        project_id = request.GET.get("project")
        user_id = request.GET.get("user")
        order_start = date.today()
        order_end = date.today()

        if month and year and user_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    department=user.department.id,
                    location=user.location.id,
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    id=int(user_id),
                    department=user.department.id,
                    location=user.location.id,
                )

            projects = defaultdict(lambda: {"project":"", "department":"", "location":"", "worked_hours":0})
            logs = {"projects":[]}

            for user in users:
                activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)

                dept = user.department.dept_name
                loc = user.location.loc_name

                for log in activity_logs:
                    project_name = log.project.project_name
                    projects[project_name]["project"] = project_name
                    projects[project_name]["department"] = dept
                    projects[project_name]["location"] = loc
                    projects[project_name]["worked_hours"] += log.hours_worked

            # Convert defaultdict to list of dictionaries
            logs["projects"] = list(projects.values())
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


@ensure_csrf_cookie
def get_manager_leave_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        order_start = date.today()
        order_end = date.today()

        if month and year and user_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    department=user.department.id,
                    location=user.location.id,
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    id=user_id,
                    department=user.department.id,
                    location=user.location.id,
                )

            leaves = []
            logs = {"leaves": []}

            for user in users:
                leaves_queryset = Leave.objects.filter(
                    from_user_id=user.id,
                    start_date__lte=order_end,  # Leave starts before or on order_end
                    end_date__gte=order_start  # Leave ends after or on order_start
                )

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
            return JsonResponse(logs)
        else:
            messages.error(request, "Invalid request")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, "Something went wrong")
        return JsonResponse({"error": str(e)}, status=500)
    

@ensure_csrf_cookie
def get_manager_overview_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        project_id = request.GET.get("project")
        user_id = request.GET.get("user")

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and project_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    department=user.department.id,
                    location=user.location.id,
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    id=user_id,
                    department=user.department.id,
                    location=user.location.id,
                )
            

            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count
            hours_leave_days:int = 0
            project_data = defaultdict(lambda: {'total':0, 'percentage': 0})
            total_worked_hours:float = 0

            for user in users:
                approved_leave_requests = Leave.objects.filter(
                    from_user=user.id,
                    is_approved=True,
                    start_date__lte=order_end,  # Leave starts before or on order_end
                    end_date__gte=order_start  # Leave ends after or on order_start
                )
                for leave_request in approved_leave_requests:
                    # Find the intersection of leave dates and the range (order_start, order_end)
                    leave_start = max(leave_request.start_date, order_start)
                    leave_end = min(leave_request.end_date, order_end)
                    filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
                    hours_leave_days += len(filtered_dates) * 8

                
                activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)
                for activity_log in activity_logs:
                    project_name = activity_log.project.project_name

                    project_data[project_name]['total'] += activity_log.hours_worked
                    total_worked_hours+=activity_log.hours_worked


            hours_pub_holiday:int = calculate_public_holidays(order_start, order_end, users_count)
            total_hours -= hours_pub_holiday

            projects:Project
            if project_id == "all":
                projects = Project.objects.all()
            else:
                projects = Project.objects.filter(id=int(project_id))

            for project in projects:
                project_data[project.project_name]['percentage'] = project_data[project.project_name]['total']*100 / total_hours

            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours

            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours

            missed_hours = total_hours - total_worked_hours
            filtered_data = {
                "date_range":{"start":order_start.strftime(r"%Y/%m/%d"), "end":order_end.strftime(r"%Y/%m/%d")},
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


@ensure_csrf_cookie
def get_manager_pro_act_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    department=user.department.id,
                    location=user.location.id,
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    is_admin=False,
                    id=user_id,
                    department=user.department.id,
                    location=user.location.id,
                )

            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime())
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

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
                activity_logs = get_activity_logs(user.id, "all", order_start, order_end)
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

            filtered_data = {"report": []}

            # Append project and activity to filtered data
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


@ensure_csrf_cookie
def get_admin_activities(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        project_id = request.GET.get("project")
        department_id = request.GET.get("department")
        user_id = request.GET.get("user")
        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and project_id and department_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    id=int(user_id)
                )
            if department_id != "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id
                )

            logs = {"activity_logs":[]}

            for user in users:
                activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)
                for log in activity_logs:
                    project_name = log.project.project_name
                    logs["activity_logs"].append({
                        'time_added':log.updated.strftime(f'%Y-%m-%d [%H:%M:%S]'),
                        'username': log.user.username,
                        'project': project_name,
                        'activity':log.activity.activity_name,
                        'department':log.user.department.dept_name,
                        'date':log.date.strftime(f'%Y-%m-%d'),
                        "hours_worked":Decimal(log.hours_worked),
                        "details":log.details,
                    })

            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)
    

@ensure_csrf_cookie
def get_admin_project_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        project_id = request.GET.get("project")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        order_start = date.today()
        order_end = date.today()

        if month and year and user_id and project_id and department_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year)+1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month)+1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    id=int(user_id)
                )
            if department_id != "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id
                )


            projects = defaultdict(lambda: {"project":"", "department":"", "location":"", "worked_hours":0})

            _projects = Project.objects.all()
            for project in _projects:
                pro_name = project.project_name
                projects[pro_name]["project"] = pro_name

            logs = {"projects":[]}

            if len(users) > 0:
                for user in users:
                    activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)

                    dept = user.department.dept_name
                    loc = user.location.loc_name
                    if len(activity_logs):
                        for log in activity_logs:
                            project_name = log.project.project_name
                            projects[project_name]["project"] = project_name
                            if not dept in projects[project_name]["department"]:
                                projects[project_name]["department"] += dept + ", "
                            if not loc in projects[project_name]["location"]:
                                projects[project_name]["location"] += loc + ", "
                            projects[project_name]["worked_hours"] += log.hours_worked
                    else:
                        for project in _projects:
                            pro_name = project.project_name
                            projects[pro_name]["department"] = dept + ", "

            else:
                for project in _projects:
                    pro_name = project.project_name
                    projects[pro_name]["department"] = Department.objects.get(id=department_id).dept_name

            # Convert defaultdict to list of dictionaries
            logs["projects"] = list(projects.values())
            return JsonResponse(logs)
        else:
            messages.error(request, "Something wrong :(")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except:
        messages.error(request, "Something went wrong :(")
        return JsonResponse({"error": "Invalid request"}, status=405)


@ensure_csrf_cookie
def get_admin_leave_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")
        order_start = date.today()
        order_end = date.today()

        if month and year and user_id and department_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    id=int(user_id)
                )
            if department_id != "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id
                )

            leaves = []
            logs = {"leaves": []}

            for user in users:
                leaves_queryset = Leave.objects.filter(
                    from_user_id=user.id,
                    start_date__lte=order_end,  # Leave starts before or on order_end
                    end_date__gte=order_start  # Leave ends after or on order_start
                )

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
            return JsonResponse(logs)
        else:
            messages.error(request, "Invalid request")
            return JsonResponse({"error": "Invalid request"}, status=405)
    except Exception as e:
        messages.error(request, "Something went wrong")
        return JsonResponse({"error": str(e)}, status=500)


@ensure_csrf_cookie
def get_admin_overview_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        project_id = request.GET.get("project")
        department_id = request.GET.get("department")
        user_id = request.GET.get("user")

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and project_id and department_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    id=int(user_id)
                )
            if department_id != "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id
                )
            

            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime(), False)
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count
            hours_leave_days:int = 0
            project_data = defaultdict(lambda: {'total':0, 'percentage': 0})
            total_worked_hours:float = 0

            for user in users:
                approved_leave_requests = Leave.objects.filter(
                    from_user=user.id,
                    is_approved=True,
                    start_date__lte=order_end,  # Leave starts before or on order_end
                    end_date__gte=order_start  # Leave ends after or on order_start
                )
                for leave_request in approved_leave_requests:
                    # Find the intersection of leave dates and the range (order_start, order_end)
                    leave_start = max(leave_request.start_date, order_start)
                    leave_end = min(leave_request.end_date, order_end)
                    filtered_dates = get_filtered_dates(leave_start.ctime(), leave_end.ctime())
                    hours_leave_days += len(filtered_dates) * 8

                
                activity_logs = get_activity_logs(user.id, project_id, order_start, order_end)
                for activity_log in activity_logs:
                    project_name = activity_log.project.project_name

                    project_data[project_name]['total'] += activity_log.hours_worked
                    total_worked_hours+=activity_log.hours_worked


            hours_pub_holiday:int = calculate_public_holidays(order_start, order_end, users_count)
            total_hours -= hours_pub_holiday

            projects:Project
            if project_id == "all":
                projects = Project.objects.all()
            else:
                projects = Project.objects.filter(id=int(project_id))

            for project in projects:
                project_data[project.project_name]['percentage'] = project_data[project.project_name]['total']*100 / total_hours

            hours_leave_days_percentage = 0
            if total_hours > 0:
                hours_leave_days_percentage = hours_leave_days*100 / total_hours

            percent_complete = 0
            if total_hours > 0:
                percent_complete = (total_worked_hours*100) / total_hours

            missed_hours = total_hours - total_worked_hours
            filtered_data = {
                "date_range":{"start":order_start.strftime(r"%Y/%m/%d"), "end":order_end.strftime(r"%Y/%m/%d")},
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


@ensure_csrf_cookie
def get_admin_pro_act_report(request, pk):
    try:
        user = CustomUser.objects.get(id=pk)
        month = request.GET.get("month")
        year = request.GET.get("year")
        user_id = request.GET.get("user")
        department_id = request.GET.get("department")

        order_start = date.today()
        order_end = date.today()
        if month and year and user_id and department_id:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)

            users: CustomUser
            if user_id == "all":
                users = CustomUser.objects.filter(
                    is_superuser = False
                )
            else:
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    id=user_id
                )
            if department_id != "all":
                users = CustomUser.objects.filter(
                    is_superuser = False,
                    department=department_id
                )

            total_hours:int = 0
            users_count = len(users)

            filtered_dates_satge1 = get_filtered_dates(order_start.ctime(), order_end.ctime())
            total_days = len(filtered_dates_satge1)
            total_hours = 8 * total_days * users_count

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
                activity_logs = get_activity_logs(user.id, "all", order_start, order_end)
                for activity_log in activity_logs:
                    project_name = activity_log.project.project_name
                    activity_name = activity_log.activity.activity_name
                    hours_worked = activity_log.hours_worked

                    project_totals[project_name] += hours_worked
                    activity_totals[activity_name] += hours_worked

                    project_activities[project_name][activity_name] += hours_worked

            # Calculate percentages
            if len(users):
                project_percentages = {project_name: (hours / total_hours) * 100 for project_name, hours in project_totals.items()}
                activity_percentages = {activity_name: (hours / total_hours) * 100 for activity_name, hours in activity_totals.items()}
            else:
                project_percentages = {project_name: 0 for project_name, hours in project_totals.items()}
                activity_percentages = {activity_name: 0 for activity_name, hours in activity_totals.items()}

            filtered_data = {"report": []}

            # Append project and activity to filtered data
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


def get_holiday_report(request):
    try:

        month = request.GET.get("month")
        year = request.GET.get("year")

        order_start = date.today()
        order_end = date.today()
        if month and year:
            if month == "all":
                order_start = date(int(year), 1, 1)
                order_end = date(int(year), 12, 31)
            else:
                order_start = date(int(year), int(month), 1)
                if month == "12":
                    last_month_day = date(int(year) + 1, 1, 1) - order_start
                else:
                    last_month_day = date(int(year), int(month) + 1, 1) - order_start
                order_end = date(int(year), int(month), last_month_day.days)


            _holidays = Holiday.objects.filter(
                holiday_date__range = [order_start, order_end]
            )

            print(_holidays)
            
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
