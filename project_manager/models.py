from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.core.files.storage import FileSystemStorage

image_storage = FileSystemStorage(location='/var/www/http/media')

def custom_upload_path(instance, filename):
    # Define your absolute path here
    absolute_path = "/var/www/http/media"
    return f"{absolute_path}/{filename}"

class Department(models.Model):
    dept_name = models.CharField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated", "-created"]


    def __str__(self):
        return str(self.dept_name[:50])

class Location(models.Model):
    loc_name = models.CharField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated", "-created"]

    def __str__(self):
        return str(self.loc_name[:50])

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name[:50]

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email, and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_manager = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    daily_hours = models.DecimalField(max_digits=5, decimal_places=2, default=8)
    has_notification = models.BooleanField(default = False)
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING, null=True)
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING, null=True)
    disabled = models.BooleanField(default = False)
    ov = models.BooleanField(default = False)
    role = models.ForeignKey(Role, on_delete=models.DO_NOTHING, null=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    profile_img = models.ImageField(default='user_def.png', storage=image_storage)

    def __str__(self):
        return f'{self.user.username} Profile'

class Activity(models.Model):
    activity_name = models.CharField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated", "-created"]

    def __str__(self):
        return str(self.activity_name[:50])


class Project(models.Model):
    project_name = models.CharField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-updated", "-created"]

    def __str__(self):
        return str(self.project_name)


class Leave(models.Model):
    from_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leaves_sent', null=True)
    to_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leaves_received', null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    total_leave_days = models.IntegerField(null=True)
    leave_type = models.CharField(max_length=100, default="Casual")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated", "-created"]

    def __str__(self):
        return str(self.from_user) + " to " + str(self.to_user)


class Holiday(models.Model):
    holiday_name = models.CharField(max_length=100)
    holiday_date = models.DateField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated", "-created"]

    def __str__(self):
        return self.holiday_name


class ActivityLogs(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    date = models.DateField()
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return f'{self.user.username} on {self.date.strftime(r'%Y-%m-%d')}: {self.hours_worked} h'

    class Meta:
        ordering = ["-updated", "-created"]

class Notification(models.Model):
    to_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    notification_type = models.CharField(max_length=100)
    class Meta:
        ordering = ["-created"]

