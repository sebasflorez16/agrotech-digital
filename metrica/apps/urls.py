from django.urls import path

from .views import (calendar_view, chat_view, contact_list_view, invoice_view, analytics_customer_view, analytics_reports_view,
                   crypto_exchange_view, crypto_wallet_view, crypto_news_view, crypto_list_view, crypto_settings_view, crm_contact_view, crm_opportunities_view,
                   crm_leads_view, crm_customers_view, project_client_view , team_view, project_view, kanbanboard_view, task_view , users_view, chat_view,
                   create_view, product_view, list_view, details_view, cart_view, checkout_view, tickets_view, reports_view, agents_view, all_appointment_view,
                   dr_schedule_view, all_doctors_View, add_doctors_view, doctor_edit_view, doctor_profile_view, all_patients_view, patients_edit_view,
                   add_patients_view, patients_profile_view, all_payment_view, payment_invoice_view, cashless_payment_view, inbox_view, read_view, all_staff_view,
                   add_member_view , edit_member_view, member_profile_view, salary_view, all_rooms_view, expenses_view, department_view, insurance_co_view,
                   events_view, leave_View, holidays_view, attendance_view ,general_chat_view)
                   

app_name = "apps"
urlpatterns =[
    path("analytics-customer", view=analytics_customer_view, name="analytics-customer"),
    path("analytics-reports", view=analytics_reports_view, name="analytics-reports"),
    path("crypto-exchange", view=crypto_exchange_view, name="crypto-exchange"),

    path("crypto-wallet", view=crypto_wallet_view, name="crypto-wallet"),
    path("crypto-news", view=crypto_news_view, name="crypto-news"),
    path("crypto-list", view=crypto_list_view, name="crypto-list"),
    path("crypto-settings", view=crypto_settings_view, name="crypto-settings"),

    path("crm-contact", view=crm_contact_view, name="crm-contact"),
    path("crm-opportunities", view=crm_opportunities_view, name="crm-opportunities"),
    path("crm-leads", view=crm_leads_view, name="crm-leads"),
    path("crm-customers", view=crm_customers_view, name="crm-customers"),

    path("projects-client", view=project_client_view, name="projects-client"),
    path("projects-team", view=team_view, name="projects-team"),
    path("projects-project", view=project_view, name="projects-project"),
    path("projects-task", view=task_view, name="projects-task"),
    path("projects-kanbanboard", view=kanbanboard_view, name="projects-kanbanboard"),
    path("projects-users", view=users_view, name="projects-users"),
    path("projects-chat", view=chat_view, name="projects-chat"),
    path("projects-create", view=create_view, name="projects-create"),

    path("ecommerce-product", view=product_view, name="ecommerce-product"),
    path("ecommerce-list", view=list_view, name="ecommerce-list"),
    path("ecommerce-details", view=details_view, name="ecommerce-details"),
    path("ecommerce-cart", view=cart_view, name="ecommerce-cart"),
    path("ecommerce-checkout", view=checkout_view, name="ecommerce-checkout"),

    path("helpdesk-tickets", view=tickets_view, name="helpdesk-tickets"),
    path("helpdesk-reports", view=reports_view, name="helpdesk-reports"),
    path("helpdesk-agents", view=agents_view, name="helpdesk-agents"),

    path("hospital-all-appointment", view=all_appointment_view, name="hospital-all-appointment"),
    path("hospital-dr-schedule", view=dr_schedule_view, name="hospital-dr-schedule"),
    path("hospital-all-doctors", view=all_doctors_View, name="hospital-all-doctors"),
    path("hospital-add-doctors", view=add_doctors_view, name="hospital-add-doctors"),
    path("hospital-doctor-edit", view=doctor_edit_view, name="hospital-doctor-edit"),
    path("hospital-doctor-profile", view=doctor_profile_view, name="hospital-doctor-profile"),
    path("hospital-all-patients", view=all_patients_view, name="hospital-all-patients"),
    path("hospital-patients-edit", view=patients_edit_view, name="hospital-patients-edit"),
    path("hospital-add-patients", view=add_patients_view, name="hospital-add-patients"),
    path("hospital-patient-profile", view=patients_profile_view, name="hospital-patient-profile"),
    path("hospital-all-paymnets", view=all_payment_view, name="hospital-all-paymnets"),
    path("hospital-payment-invoice", view=payment_invoice_view, name="hospital-payment-invoice"),
    path("hospital-cashless-payment", view=cashless_payment_view, name="hospital-cashless-payment"),
    path("hospital-staff-all", view=all_staff_view, name="hospital-staff-all"),
    path("hospital-staff-member", view=add_member_view, name="hospital-staff-member"),
    path("hospital-staff-edit-member", view=edit_member_view, name="hospital-staff-edit-member"),
    path("hospital-staff-profile", view=member_profile_view, name="hospital-staff-profile"),
    path("hospital-staff-salary", view=salary_view, name="hospital-staff-salary"),
    path("hospital-all-room", view=all_rooms_view, name="hospital-all-room"),
    path("hospital-expenses", view=expenses_view, name="hospital-expenses"),
    path("hospital-department", view=department_view, name="hospital-department"),
    path("hospital-insurance-company", view=insurance_co_view, name="hospital-insurance-company"),
    path("hospital-events", view=events_view, name="hospital-events"),
    path("hospital-leaves", view=leave_View, name="hospital-leaves"),
    path("hospital-holidays", view=holidays_view, name="hospital-holidays"),
    path("hospital-attendance", view=attendance_view, name="hospital-attendance"),
    path("hospital-chat", view=general_chat_view, name="hospital-chat"),

    path("hospital-email-inbox", view=inbox_view, name="hospital-email-inbox"),
    path("hospital-email-read", view=read_view, name="hospital-email-read"),

    path("contact-list", view=contact_list_view, name="contact-list"),
    path("calendar", view=calendar_view, name="calendar"),
    path("chat", view=chat_view, name="chat"),
    path("invoice", view=invoice_view, name="invoice"),
]