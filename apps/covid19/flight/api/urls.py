from django.urls import path

from apps.covid19.flight.api.views import FlightListAPIView, FlightDetailCreateAPIView, UpdateFlightDetails, FlightDetailDeleteView, \
    QuestionsecondListAPIView, QuestionfirstListAPIView, UseranswerListCreateAPIView

urlpatterns = [

    path('list-carrier/', FlightListAPIView.as_view(), name='flight_list_view'),
    path('add-list-flightdetails/', FlightDetailCreateAPIView.as_view(), name='flightdetails_list_create'),
    path("user-flightdetails/<int:flightdetail_id>/update/", UpdateFlightDetails.as_view(), name="update_user_flightdetails"),
    path("<int:flightdetail_id>/delete/", FlightDetailDeleteView.as_view(), name="delete_user_flightdetails"),
    path("user-details/first-section/", QuestionfirstListAPIView.as_view(), name="list_question_firstsection"),
    path("user-details/second-section/", QuestionsecondListAPIView.as_view(), name="list_question_secondsection"),
    path('addlist-question-answers/', UseranswerListCreateAPIView.as_view(), name='useranswer_list_create'),
]