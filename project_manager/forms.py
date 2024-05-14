from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, ActivityLogs
from django import forms
from .models import CustomUser, Project, Activity, Department, Location, Holiday, Profile, Role
from django.core.exceptions import ValidationError
from PIL import Image


class CustomUserForm(UserCreationForm):
    role = forms.ModelChoiceField(queryset=Role.objects.all())
    class Meta:
        model = CustomUser
        fields = ['username','first_name','last_name', 'email', 'password1', 'password2', 'daily_hours', 'department', 'location', 'disabled','ov', 'role']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['email'].help_text = "Required"
        self.fields['daily_hours'].help_text = "default is 8, can't be lower than 5."
    def clean_daily_hours(self):
        daily_hours = self.cleaned_data.get('daily_hours')
        if daily_hours is None or daily_hours <= 5:
            raise forms.ValidationError("Daily hours must be greater than 5.")
        return daily_hours


class CustomUserUpdateForm(UserChangeForm):
    role = forms.ModelChoiceField(queryset=Role.objects.all())
    class Meta:
        model = CustomUser
        fields = ['username','first_name','last_name', 'email', 'daily_hours', 'department', 'location', 'disabled', 'ov', 'role']
    def clean_daily_hours(self):
        daily_hours = self.cleaned_data.get('daily_hours')
        if daily_hours is None or daily_hours <= 5:
            raise forms.ValidationError("Daily hours must be greater than 5.")
        return daily_hours

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ["project_name"]


class ActivityForm(ModelForm):
    class Meta:
        model = Activity
        fields = ["activity_name"]

class DepartmentForm(ModelForm):
    class Meta:
        model = Department
        fields = ["dept_name"]

class LocationForm(ModelForm):
    class Meta:
        model = Location
        fields = ["loc_name"]

class HolidayForm(ModelForm):
    class Meta:
        model = Holiday
        fields = ["holiday_name", "holiday_date"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['holiday_date'].required = True
        self.fields['holiday_name'].help_text = "must not be numerical"
        self.fields['holiday_name'].error = "Holiday name must not be numerical."
    def clean_name(self):
        name = self.cleaned_data.get('holiday_name')
        name = str(name)
        if name.isdigit():
            raise forms.ValidationError("Holiday name must not be numerical.")
        return name


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_img']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_img'].required = True
        self.fields['profile_img'].help_text = "Only JPEG, JPG, and PNG formats are allowed."



from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
UserModel = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not UserModel.objects.filter(email=email).exists():
            raise ValidationError("This email address doesn't exist in our system.")
        return email