from django.db import models
from datetime import datetime, timedelta

# Create your models here.

class UserPayment(models.Model):
    username = models.CharField(max_length=100, unique=True)
    last_payment_date = models.DateField()
    next_payment_date = models.DateField()
    is_active = models.BooleanField(default=True)
    auto_disconnect = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.next_payment_date:
            self.next_payment_date = self.last_payment_date + timedelta(days=30)
        super().save(*args, **kwargs)
    
    def check_payment_status(self):
        today = datetime.now().date()
        if today > self.next_payment_date:
            self.is_active = False
            self.save()
            return False
        return True
    
    def __str__(self):
        return f"{self.username} - {'Activo' if self.is_active else 'Inactivo'}"
