from rest_framework import serializers

class CalendarSerializer(serializers.Serializer):
    date = serializers.DateField()
    hours_worked = serializers.IntegerField()