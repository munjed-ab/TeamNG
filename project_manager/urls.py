from django.urls import path
from . import views
from . import views_admin
from . import views_api
from . import views_manager
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as views_auth
from .forms import CustomPasswordResetForm

urlpatterns = [
    path("", views.login_view, name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("notifications/", views.notifications, name="notifications"),
    path("logout/", views.logout_view, name="logout"),

    #MAIN PAGES
    path("register-hours/<str:date_picked>", views.registerhours, name="registerhours"),
    path("add-leave/", views.addleave, name="addleave"),
    path("activity-logs/", views.activity_log, name="activitylogs"),
    path("update-entry/<str:pk>", views.update_entry, name="update_entry"),
    path("delete-entry/<str:pk>", views.delete_entry, name="delete_entry"),
    path("leave-logs/", views.leave_log, name="leave_logs"),
    path("update-leave/<str:pk>", views.update_leave, name="update_leave"),
    path("delete-leave/<str:pk>", views.delete_leave, name="delete_leave"),

    #AUTH
    path("password_reset/",
        views_auth.PasswordResetView.as_view(
            template_name="project_manager/auth/password_reset.html",
            email_template_name='project_manager/auth/password_reset_email.html',
            form_class=CustomPasswordResetForm),  # Specify the custom form here
        name="password_reset"),
    path("password_reset_done/",
        views_auth.PasswordResetDoneView.as_view(template_name="project_manager/auth/password_reset_sent.html"),
        name="password_reset_done"),
    path("password_reset_confirm/<uidb64>/<token>/",
        views_auth.PasswordResetConfirmView.as_view(template_name="project_manager/auth/password_reset_confirm.html"),
        name="password_reset_confirm"),
    path("password_reset_complete",
        views_auth.PasswordResetCompleteView.as_view(template_name="project_manager/auth/password_reset_complete.html"),
        name="password_reset_complete"),

    #ADMIN
    path("users/", views_admin.users, name="users"),
    path("users/<str:pk>", views_admin.edit_user, name="edit_user"),
    path("create-user/", views_admin.create_new_user, name="create_user"),
    
    path("projects/", views_admin.projects, name="projects"),
    path("projects/<str:pk>", views_admin.edit_project, name="edit_project"),
    path("create-project/", views_admin.create_project, name="create_project"),

    path("activities/", views_admin.activities, name="activities"),
    path("activities/<str:pk>", views_admin.edit_activity, name="edit_activity"),
    path("create-activity/", views_admin.create_activity, name="create_activity"),

    path("departments/", views_admin.departments, name="departments"),
    path("departments/<str:pk>", views_admin.edit_dept, name="edit_dept"),
    path("create-department/", views_admin.create_dept, name="create_dept"),
    
    path("locations/", views_admin.locations, name="locations"),
    path("locations/<str:pk>", views_admin.edit_loc, name="edit_loc"),
    path("create-location/", views_admin.create_loc, name="create_loc"),

    path("holidays/", views_admin.holidays, name="holidays"),
    path("holidays/<str:pk>", views_admin.edit_holiday, name="edit_holiday"),
    path("create-holiday/", views_admin.create_holiday, name="create_holiday"),    

    path("analysis-overview/", views_admin.overview, name="overview"),

    #MANAGER
    path("manager-overview/", views_manager.manager_overview, name="manager_overview"),
    #APIs
    path('api/get_calendar_data/', views_api.CalendarDataView.as_view(), name='get_calendar_data'),
    path('api/get_holiday_data/', views_api.get_holiday_data, name='get_holiday_data'),
    path('api/post_activity_data/', views_api.post_activity_data, name='post_activity_data'),
    path("api/overview_data/", views_api.overview_data, name="overview_data"),
    path("api/overview_manager_data/", views_api.overview_manager_data, name="overview_manager_data"),
    path("api/overview_user_data/", views_api.overview_user_data, name="overview_user_data"),
    path('api/get_leave_data/', views_api.get_leave_data, name='get_leave_data'),

    #PROFILE USERS
    path('profile/<str:pk>/', views.profile, name='profile'),
    path('upload-profile-image/', views.upload_profile_image, name='upload_profile_image'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)