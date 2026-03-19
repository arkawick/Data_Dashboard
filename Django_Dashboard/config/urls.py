from django.urls import path
from dashboard import views, views2

urlpatterns = [
    path('',                  views.home,             name='home'),
    path('index/',            views.index,            name='index'),
    path('index2/',           views2.index2,          name='index2'),
    path('filter_by_domain/', views.filter_by_domain, name='filter_by_domain'),
]
