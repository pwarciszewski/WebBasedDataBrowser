from django.urls import path
from . import views


urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('getdatatree/', views.getDataTree, name='getDataTree'),
    path('upload/', views.upload_file, name='upload'),
    path('download/', views.download_files, name='download'),
    path('do/', views.performOperation, name='perform'),
    path('fetchdata/', views.fetchRequestedData, name='fetchdata'),
    path('fetchOps/', views.fetchOps, name='fetchOps'),
    path('getnewestid/', views.getNewestID, name='getNewestID'),
    path('fetchRoutine/', views.fetchRoutine, name='fetchRoutine'),
    path('setRoutine/', views.setRoutine, name='setRoutine')
]
