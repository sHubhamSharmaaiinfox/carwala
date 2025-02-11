from django.contrib import admin
from django.urls import path,include
from . import views
urlpatterns = [
    path('',views.home),
    path('fetch_models',views.fetch_models),
    path('fetch_brands',views.fetch_brands),
    path('process_row_and_form_data',views.process_row_and_form_data),
    path('update_table_data',views.update_table_data),
    path('api/insurance',views.add_insurence),
    path('show-data',views.show_data),
    path('update',views.update_data),
    path('update/<int:id>/',views.update_data),
    path('delete',views.delete)
]
