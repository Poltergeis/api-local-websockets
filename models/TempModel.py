from tortoise import fields
from tortoise.models import Model
import json

class TempModel(Model):
    id = fields.IntField(pk=True)
    temperatura = fields.IntField()
    fecha = fields.DateField()
    
    class Meta:
        table = "temperaturas"
        
    def as_dict(self):
        return { "id": self.id, "temperatura": self.temperatura, "fecha": self.fecha }
    
    def as_json(self):
        return json.dumps(self.as_dict())