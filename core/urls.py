from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [

    path('', views.home, name='home'),

    path('upload/', views.upload, name='upload'),

    path('note/<int:id>/', views.note_detail, name='note_detail'),

    path(
        'login/',
        views.CustomLoginView.as_view(),
        name='login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),
]