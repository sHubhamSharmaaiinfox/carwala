from django.db import models

# Create your models here.
class Brand(models.Model):
    year = models.IntegerField(null=True, blank=True)
    insurance_company = models.CharField(max_length=100)
    name = models.CharField(max_length=250, null=True, blank=True)
    model = models.CharField(max_length=100)
    zd = models.FloatField(null=True, blank=True)   
    con = models.FloatField(null=True, blank=True)
    engine = models.FloatField(null=True, blank=True)  
    tyre = models.FloatField(null=True, blank=True)  
    rti = models.FloatField(null=True, blank=True)  

    def __str__(self):
        return f"Brand('{self.name}')"
    class Meta:
        db_table='brand'