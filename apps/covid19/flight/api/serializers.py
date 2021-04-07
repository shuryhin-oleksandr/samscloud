from rest_framework.serializers import ModelSerializer

from apps.covid19.flight.models import Flight, FlightDetails, Questions, UserAnswers


class FlightSerializer(ModelSerializer):
    """
    flight carrier serializer
    """

    class Meta:
        model = Flight
        fields = [
            'id',
            'name',
        ]


class FlightDetailsSerializer(ModelSerializer):
    """
    User flight detail serializer
    """

    class Meta:
        model = FlightDetails
        fields = "__all__"
        read_only_fields = ("id", "user",)


class FlightDetailsReadonlySerializer(ModelSerializer):
    """
    User flight detail serializer
    """

    flight = FlightSerializer(read_only=True)

    class Meta:
        model = FlightDetails
        fields = "__all__"
        read_only_fields = ("id", "user",)


class QuestionSerializer(ModelSerializer):
    """
    question serializer
    """

    class Meta:
        model = Questions
        fields = [
            'id',
            'question',
        ]


class UserAnswerSerializer(ModelSerializer):
    """
    User answer detail serializer
    """

    class Meta:
        model = UserAnswers
        fields = "__all__"
        read_only_fields = ("id", "user",)
