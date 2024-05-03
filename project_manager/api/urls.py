from django.urls import path
from . import views

urlpatterns = [
    

    # calendar
    path('get_calendar_data/', views.calendar_data_view, name='calendar_data_view'),
    path('calendar_holiday_data/', views.calendar_holiday_data, name='calendar_holiday_data'),
    path('calendar_leave_data/', views.calendar_leave_data, name='calendar_leave_data'),

    # register hours
    path('post_activity_data/', views.post_activity_data, name='post_activity_data'),

    # overview
    path('overview_data/', views.overview_data, name='overview_data'),
    path('overview_manager_data/', views.overview_manager_data, name='overview_manager_data'),
    path('overview_user_data/<str:pk>', views.overview_user_data, name='overview_user_data'),

    # REPORTS
    # user reports
    path('report/project/user/<str:pk>', views.get_user_project_report, name='get_user_project_report'),
    path('report/activity/user/<str:pk>', views.get_user_activity_report, name='get_user_activity_report'),
    path('report/leave/user/<str:pk>', views.get_user_leave_report, name='get_user_leave_report'),
    path('report/expectedhours/user/<str:pk>', views.get_user_overview_report, name='get_user_overview_report'),
    path('report/project-for-activity/user/<str:pk>', views.get_user_pro_act_report, name='get_user_pro_act_report'),

    # manager reports
    path('report/activity/manager/<str:pk>', views.get_manager_activity_report, name='get_manager_activities'),
    path('report/project/manager/<str:pk>', views.get_manager_project_report, name='get_manager_project_report'),
    path('report/leave/manager/<str:pk>', views.get_manager_leave_report, name='get_manager_leave_report'),
    path('report/expected_hours/manager/<str:pk>', views.get_manager_overview_report, name='get_manager_overview_report'),
    path('report/project-for-activity/manager/<str:pk>', views.get_manager_pro_act_report, name='get_manager_pro_act_report'),

    # admin reports
    path('report/activity/admin/<str:pk>', views.get_admin_activity_report, name='get_admin_activity_report'),
    path('report/project/admin/<str:pk>', views.get_admin_project_report, name='get_admin_project_report'),
    path('report/leave/admin/<str:pk>', views.get_admin_leave_report, name='get_admin_leave_report'),
    path('report/expected_hours/admin/<str:pk>', views.get_admin_overview_report, name='get_admin_overview_report'),
    path('report/project-for-activity/admin/<str:pk>', views.get_admin_pro_act_report, name='get_admin_pro_act_report'),
    path('report/holiday/', views.get_holiday_report, name='get_holiday_report'),
]
