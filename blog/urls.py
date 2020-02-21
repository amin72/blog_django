from django.urls import path
from . import views


app_name = 'blog'

urlpatterns = [
    # post list
    path('', views.PostListView.as_view(), name='post_list'),

    # post detail
    path('<int:year>/<int:month>/<int:day>/<slug:slug>/',
        views.post_detail,
        name='post_detail'),
]
