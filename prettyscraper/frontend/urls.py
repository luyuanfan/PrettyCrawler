# from django.urls import path
# from django.shortcuts import render
# from ./prettyscraper import views

# # Views and Urls for frontend are combined for simplicity.
# def index(request, *args, **kwargs):
#     return render(request, 'frontend/index.html')

# # urls here
# urlpatterns = [
#     path('', index),
#     path('', views.home, name='home'),
#     path('scrape/', views.scrape, name='scrape'),
#     path('download/', views.download, name='download'),
#     path('verify_user_id/', views.verify_user_id, name='verify_user_id'),
# ]