from django.contrib import admin
from .models import CustomUser, Project, Activity, Holiday, Leave, Notification, ActivityLogs, Department, Location, Profile, Role
# Register your models here.

class LeaveAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Leave._meta.fields if field.name != "id"]

admin.site.register(CustomUser)
admin.site.register(Project)
admin.site.register(Activity)
admin.site.register(Holiday)
admin.site.register(Leave, LeaveAdmin)
admin.site.register(ActivityLogs)
admin.site.register(Notification)
admin.site.register(Department)
admin.site.register(Location)
admin.site.register(Profile)
admin.site.register(Role)