from django.urls import path
from . import views
from . import views_admin
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
    path('profile/<str:pk>/', views.profile, name='profile'),
    path('upload-profile-image/', views.upload_profile_image, name='upload_profile_image'),
    #USER REPORTS
    path("report-activity-user/<str:pk>", views.report_user_activity, name="report_user_activity"),
    path("report-project-user/<str:pk>", views.report_user_project, name="report_user_project"),
    path("report-leave-user/<str:pk>", views.report_user_leave, name="report_user_leave"),
    path("report-expected-hours-user/<str:pk>", views.report_user_expectedhours, name="report_user_expectedhours"),
    path("report-project-activity-user/<str:pk>", views.report_user_pro_act, name="report_user_pro_act"),
    path("report-project-user-user/<str:pk>", views.report_user_pro_user, name="report_user_pro_user"),
    

    #AUTH
    path("password_reset/",
        views_auth.PasswordResetView.as_view(
            template_name="project_manager/auth/password_reset.html",
            email_template_name='project_manager/auth/password_reset_email.html',
            form_class=CustomPasswordResetForm),
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

    #ADMIN REPORTS
    path("report-admin-activities/<str:pk>", views_admin.report_admin_act, name="report_admin_act"),
    path("report-admin-projects/<str:pk>", views_admin.report_admin_pro, name="report_admin_pro"),
    path("report-admin-leaves/<str:pk>", views_admin.report_admin_leave, name="report_admin_leave"),
    path("report-admin-overview/<str:pk>", views_admin.report_admin_overview, name="report_admin_overview"),
    path("report-project-activity-admin/<str:pk>", views_admin.report_admin_pro_act, name="report_admin_pro_act"),
    path("report-project-user-admin/<str:pk>", views_admin.report_admin_pro_user, name="report_admin_pro_user"),
    path("report-missed-hours-admin/<str:pk>", views_admin.report_admin_missed_hours, name="report_admin_missed_hours"),
    path("report-holiday/", views_admin.report_holiday, name="report_holiday"),

    #MANAGER
    path("manager-overview/", views_manager.manager_overview, name="manager_overview"),
    #MANAGER REPORTS
    path("report-manager-activities/<str:pk>", views_manager.report_manager_act, name="report_manager_act"),
    path("report-manager-projects/<str:pk>", views_manager.report_manager_pro, name="report_manager_pro"),
    path("report-manager-leaves/<str:pk>", views_manager.report_manager_leave, name="report_manager_leave"),
    path("report-manager-overview/<str:pk>", views_manager.report_manager_overview, name="report_manager_overview"),
    path("report-project-activity-manager/<str:pk>", views_manager.report_manager_pro_act, name="report_manager_pro_act"),
    path("report-project-user-manager/<str:pk>", views_manager.report_manager_pro_user, name="report_manager_pro_user"),
    path("report-missed-hours-manager/<str:pk>", views_manager.report_manager_missed_hours, name="report_manager_missed_hours"),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)