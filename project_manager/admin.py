from django.contrib import admin
from .models import CustomUser, Project, Activity, Holiday, Leave, Notification, ActivityLogs, Department, Location, Profile
# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Project)
admin.site.register(Activity)
admin.site.register(Holiday)
admin.site.register(Leave)
admin.site.register(ActivityLogs)
admin.site.register(Notification)
admin.site.register(Department)
admin.site.register(Location)
admin.site.register(Profile)
