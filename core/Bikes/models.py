from django.db import models


class VeturiloAloneBike(models.Model):
    class BikeTypeChoice(models.IntegerChoices):
        DEFAULT = 71
        ELECTRIC = 183
        TANDEM = 228

    uid = models.IntegerField(primary_key=True)
    lat = models.DecimalField(max_digits=9, decimal_places=7)
    lng = models.DecimalField(max_digits=9, decimal_places=7)
    name = models.CharField(max_length=32)
    number = models.CharField(max_length=8)
    bike_type = models.IntegerField(choices=BikeTypeChoice)
    active = models.BooleanField()
    state = models.CharField(max_length=16, null=True)
    percentage = models.IntegerField(null=True)

    class Meta:
        db_table = 'Bikes_Veturilo_Alone_Bikes'


class VeturiloStation(models.Model):
    uid = models.IntegerField(primary_key=True)
    lat = models.DecimalField(max_digits=9, decimal_places=7)
    lng = models.DecimalField(max_digits=9, decimal_places=7)
    name = models.CharField(max_length=128)
    number = models.IntegerField()
    bikes_available_to_rent = models.IntegerField()

    class Meta:
        db_table = 'Bikes_Veturilo_Stations'

class ScooterCompany(models.Model):
    company_name = models.CharField(max_length=64)

    class Meta:
        db_table = 'Bikes_Scooter_Companies'


class Scooter(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    company = models.ForeignKey(ScooterCompany, on_delete=models.CASCADE)
    lat = models.DecimalField(max_digits=17, decimal_places=15)
    lng = models.DecimalField(max_digits=17, decimal_places=15)
    percentage = models.IntegerField()
    distance_on_charge = models.IntegerField()
    is_disabled = models.BooleanField(null=True)
    last_reported = models.DateTimeField(null=True)

    class Meta:
        db_table = 'Bikes_Scooters'
