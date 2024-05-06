from django.test import TestCase
from django.urls import reverse
from project_manager.models import CustomUser, Department, Project, ActivityLogs, Activity, Leave
import json
from django.test.client import RequestFactory

class OverviewDataTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test_user', password='123123@3qe3', email = 'toto@snso.cc')
        self.dept = Department.objects.create(dept_name='test_department')
        self.pro = Project.objects.create(project_name='test_pro')
        self.act = Activity.objects.create(activity_name='test_activity')
        self.log = ActivityLogs.objects.create(user=self.user, activity=self.act, project=self.pro, date="2024-04-04", hours_worked=4)

    def test_overview_data_endpoint(self):

        url = reverse('overview_data')
        data = {
            'month': '4',
            'year': '2024',
            'user': str(self.user.id),
            'department': str(self.dept.id),
            'project': str(self.pro.id)
        }

        # send a GET request to the endpoint
        response = self.client.get(url, data)

        self.assertEqual(response.status_code, 200)

        # check that the response contains expected data
        response_data = json.loads(response.content)
        self.assertIn('projects', response_data)

    def test_overview_data_endpoint_values(self):

        url = reverse('overview_data')
        data = {
            'month': '4',
            'year': '2024',
            'user': str(self.user.id),
            'department': "all",
            'project': "all"
        }

        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertEqual(4.0, float(response_data['projects'][0]['total']))
