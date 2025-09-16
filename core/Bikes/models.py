from django.db import models


class VeturiloAloneBike(models.Model):
    uid = models.IntegerField(primary_key=True)
    lat = models.DecimalField(max_digits=9, decimal_places=7)
    lng = models.DecimalField(max_digits=9, decimal_places=7)
    name = models.CharField(max_length=32)
    bike_number = models.CharField(max_length=8)
    bike_type = models.IntegerField()
    is_active = models.BooleanField()
    state = models.CharField(max_length=16, null=True)


class VeturiloBikeStation(models.Model):
    uid = models.IntegerField(primary_key=True)
    lat = models.DecimalField(max_digits=9, decimal_places=7)
    lon = models.DecimalField(max_digits=9, decimal_places=7)
    name = models.CharField(max_length=128)
    number = models.IntegerField()
    available_bikes = models.IntegerField()


class BikeStation(models.Model):
    id = models.IntegerField(primary_key=True)
    lat = models.DecimalField(max_digits=9, decimal_places=7)
    lon = models.DecimalField(max_digits=9, decimal_places=7)
    is_veturilo = models.BooleanField()
    name = models.CharField(max_length=128, null=True)