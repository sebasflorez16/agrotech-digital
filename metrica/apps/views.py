from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import TemplateView

# Create your views here.
class AppsView(LoginRequiredMixin, TemplateView):
     pass

# Analytics
analytics_customer_view = AppsView.as_view(template_name = "apps/analytics/customer.html")
analytics_reports_view = AppsView.as_view(template_name ="apps/analytics/reports.html")

# Crypto
crypto_exchange_view = AppsView.as_view(template_name = "apps/crypto/exchange.html")
crypto_wallet_view =  AppsView.as_view(template_name = "apps/crypto/wallet.html")
crypto_news_view = AppsView.as_view(template_name = "apps/crypto/news.html")
crypto_list_view = AppsView.as_view(template_name = "apps/crypto/list.html")
crypto_settings_view = AppsView.as_view(template_name = "apps/crypto/settings.html")

# CRM
crm_contact_view = AppsView.as_view(template_name = "apps/crm/contact.html")
crm_opportunities_view = AppsView.as_view(template_name = "apps/crm/opportunities.html")
crm_leads_view = AppsView.as_view(template_name = "apps/crm/leads.html")
crm_customers_view = AppsView.as_view(template_name = "apps/crm/customer.html")

# Projects 
project_client_view = AppsView.as_view(template_name = "apps/projects/client.html")
team_view = AppsView.as_view(template_name = "apps/projects/team.html")
project_view = AppsView.as_view(template_name = "apps/projects/project.html")
task_view = AppsView.as_view(template_name = "apps/projects/task.html")
kanbanboard_view = AppsView.as_view(template_name = "apps/projects/kanbanboard.html")
chat_view = AppsView.as_view(template_name = "apps/projects/chat.html")
users_view = AppsView.as_view(template_name = "apps/projects/users.html")
create_view = AppsView.as_view(template_name = "apps/projects/create.html")

# Ecommerce 
product_view = AppsView.as_view(template_name = "apps/ecommerce/product.html")
list_view = AppsView.as_view(template_name = "apps/ecommerce/list.html")
details_view = AppsView.as_view(template_name = "apps/ecommerce/details.html")
cart_view = AppsView.as_view(template_name = "apps/ecommerce/cart.html")
checkout_view = AppsView.as_view(template_name = "apps/ecommerce/checkout.html")

# Helpdesk 
tickets_view = AppsView.as_view(template_name = "apps/helpdesk/tickets.html")
reports_view = AppsView.as_view(template_name = "apps/helpdesk/reports.html")
agents_view = AppsView.as_view(template_name = "apps/helpdesk/agents.html")

# Hospital 
all_appointment_view = AppsView.as_view(template_name = "apps/hospital/appointment/all-appointments.html")
dr_schedule_view = AppsView.as_view(template_name = "apps/hospital/appointment/dr-schedule.html")
all_doctors_View = AppsView.as_view(template_name = "apps/hospital/doctors/all-doctors.html")
add_doctors_view = AppsView.as_view(template_name = "apps/hospital/doctors/add-doctor.html")
doctor_edit_view = AppsView.as_view(template_name = "apps/hospital/doctors/doctor-edit.html")
doctor_profile_view = AppsView.as_view(template_name = "apps/hospital/doctors/profile.html")
all_patients_view = AppsView.as_view(template_name = "apps/hospital/patients/all-patients.html")
patients_edit_view = AppsView.as_view(template_name = "apps/hospital/patients/patients-edit.html")
add_patients_view = AppsView.as_view(template_name = "apps/hospital/patients/add-patients.html")
patients_profile_view = AppsView.as_view(template_name = "apps/hospital/patients/profile.html")
all_payment_view = AppsView.as_view(template_name = "apps/hospital/payments/all-payment.html")
payment_invoice_view = AppsView.as_view(template_name = "apps/hospital/payments/payment-invoice.html")
cashless_payment_view = AppsView.as_view(template_name = "apps/hospital/payments/cashless.html")
all_staff_view = AppsView.as_view(template_name = "apps/hospital/staff/all-staff.html")
add_member_view = AppsView.as_view(template_name = "apps/hospital/staff/member.html")
edit_member_view = AppsView.as_view(template_name = "apps/hospital/staff/edit-member.html")
member_profile_view = AppsView.as_view(template_name = "apps/hospital/staff/profile.html")
salary_view = AppsView.as_view(template_name = "apps/hospital/staff/salary.html")
all_rooms_view = AppsView.as_view(template_name = "apps/hospital/general/all-rooms.html")
expenses_view = AppsView.as_view(template_name = "apps/hospital/general/expenses.html")
department_view = AppsView.as_view(template_name = "apps/hospital/general/departments.html")
insurance_co_view = AppsView.as_view(template_name = "apps/hospital/general/insurance-company.html")
events_view = AppsView.as_view(template_name = "apps/hospital/general/events.html")
leave_View = AppsView.as_view(template_name = "apps/hospital/general/leave.html")
holidays_view = AppsView.as_view(template_name = "apps/hospital/general/holidays.html")
attendance_view = AppsView.as_view(template_name = "apps/hospital/general/attendance.html")
general_chat_view = AppsView.as_view(template_name = "apps/hospital/general/chat.html")
# Email 
inbox_view = AppsView.as_view(template_name = "apps/hospital/email/inbox.html")
read_view = AppsView.as_view(template_name = "apps/hospital/email/read-email.html")

contact_list_view = AppsView.as_view(template_name = "apps/contact-list.html")
calendar_view = AppsView.as_view(template_name = "apps/calendar.html")
invoice_view = AppsView.as_view(template_name = "apps/invoice.html")