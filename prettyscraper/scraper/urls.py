from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('scrape/', views.scrape, name='scrape'),
    path('download/', views.download, name='download'),
    path('verify_user_id/', views.verify_user_id, name='verify_user_id'),
]