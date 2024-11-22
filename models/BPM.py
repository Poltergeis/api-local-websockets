from tortoise import fields
from tortoise.models import Model
import json

class BPMModel(Model):
    id = fields.IntField(pk=True)
    bpm = fields.IntField()
    fecha = fields.DateField()
    
    class Meta:
        table = "bpm"
        
    def as_dict(self):
        return { "id": self.id, "bpm": self.bpm, "fecha": self.fecha }
    
    def as_json(self):
        return json.dumps(self.as_dict())