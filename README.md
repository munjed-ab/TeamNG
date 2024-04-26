# Employee Management System

This Employee Management System is a web application designed for a company to manage employee work hours, project activities, leave requests, and analysis overview. It provides functionality for employees to log their work hours, request leave, and view their work statistics. Managers can oversee the work of employees within their department and location, while admins have access to all user data for monitoring and reporting purposes. The system also includes features for generating reports (still under development) and resetting passwords via email confirmation.

## Features

- User Auth: Allows users to log in, view their profiles, and reset passwords via email confirmation.
- Work Hour Logging: Users can log their work hours for different projects and activity types.
- Leave Management: Users can request leave, which must be approved by their manager or admin.
- Manager Overview: Managers can view and manage the work hours of employees within their department and location.
- Admin Overview: Provides admins with access to all user data and extensive reporting capabilities.
- Reporting: Allows users to generate reports with statistics and insights.

## Tech Stack

**Django:** The web framework used for building the application.

**PostgreSQL:** The relational database management system used for storing user and application data.

**Celery:** An asynchronous task queue used for handling background tasks such as sending emails and generating reports.

**Redis:** An in-memory data structure store used as a message broker for Celery.

**Chart.js:** A JavaScript library for creating interactive charts and graphs used for data analysis and visualization.

**FullCalendar:** A JavaScript event calendar plugin used for displaying work hours and scheduling leave days.

**FlatPicker:** a lightweight and powerful datetime picker.

**SB Admin 2 Template:** A free Bootstrap admin template used as a base for the application's UI.

## License

Redis: [RSALV2](https://redis.io/legal/rsalv2-agreement/) License

Chart.js: [MIT](https://github.com/chartjs/Chart.js/blob/master/LICENSE.md) License

FullCalendar: [MIT](https://fullcalendar.io/license) License

SB Admin 2 Template: [MIT](https://github.com/twbs/bootstrap/blob/main/LICENSE) License

## Authors

- [@munjed-ab](https://www.github.com/munjed-ab)
