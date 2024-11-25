import datetime
from typing import Dict, Any
from tortoise.models import Model
from models.BPM import BPMModel
from models.TempModel import TempModel
from datetime import datetime, timedelta
from tortoise.queryset import QuerySet

async def insertBpm(message_data):
    return await insert_record(message_data, BPMModel, "bpm")

async def insertTemp(message_data):
    return await insert_record(message_data, TempModel, "temperatura")

async def getBPMRecords(time : str, message_data):
    if time == "dia":
        return await search_per_day(message_data, BPMModel, "bpm")
    
    if time == "semana":
        return await search_per_week(message_data, BPMModel, "bpm")
    
    if time == "mes":
        return await search_per_month(message_data, BPMModel, "bpm")
        
async def getTempRecords(time : str, message_data):
    if time == "dia":
        return await search_per_day(message_data, TempModel, "temperatura")
    
    if time == "semana":
        return await search_per_week(message_data, TempModel, "temperatura")
    
    if time == "mes":
        return await search_per_month(message_data, TempModel, "temperatura")

async def insert_record(message_data: Dict[str, Any], type_model: Model, fieldname: str) -> Dict[str, Any]:
    try:
        print(message_data)
        valor = message_data.get('body').get('valor')

        if valor is None:
            return {
                'success': False,
                'message': "El valor no fue encontrado"
            }

        try:
            safe_valor = float(valor)
        except (TypeError, ValueError):
            return {
                'success': False,
                'message': "El valor proporcionado no es válido"
            }

        # Obtener la fecha actual
        now = datetime.now()
        
        # Crear un nuevo registro
        new_record: Model = None
        
        if fieldname == "bpm":
            new_record = type_model.create(bpm = valor, fecha = now)
            
        if fieldname == "temperatura":
            new_record = type_model.create(temperatura = valor, fecha = now)

        if not new_record:
            return {
                'success': False,
                'message': "No se pudo guardar el nuevo registro"
            }

        return {
            'success': True,
            'message': "Registro guardado exitosamente"
        }

    except Exception as error:
        return {
            'success': False,
            'message': str(error)
        }
        

from typing import Dict, Any
from datetime import datetime, timedelta
from tortoise.queryset import QuerySet

def calculate_mean(records: QuerySet, value_field_name: str) -> float:
    if not records:
        return 0.0
    
    values = [getattr(record, value_field_name) for record in records]
    return sum(values) / len(values)

import calendar
from typing import Dict, Any, List
from datetime import datetime
from tortoise import fields
import locale

def calculate_mean1(records: List[Any], value_field_name: str) -> float:
    """
    Calcula la media de los registros para un campo específico.
    """
    if not records:
        return 0.0
    
    try:
        values = [float(getattr(record, value_field_name)) for record in records]
        return sum(values) / len(values)
    except Exception as e:
        print(f"Error en calculate_mean: {str(e)}")
        return 0.0

async def search_per_month(message_data: Dict[str, Any], type_model: Any, value_field_name: str) -> Dict[str, Any]:
    try:
        print(f"Buscando último registro...")
        last_record = await type_model.filter().order_by('-fecha').first()

        if not last_record:
            return {
                'success': False,
                'message': "No se encontraron datos"
            }

        print(f"Último registro encontrado: {last_record}")
        fecha = last_record.fecha
        print(f"Fecha extraída: {fecha}")

        last_year = fecha.year
        last_month = fecha.month
        print(f"Año: {last_year}, Mes: {last_month}")

        # Crear fechas de inicio y fin para el mes actual
        current_month_start = datetime(last_year, last_month, 1).date()
        if last_month == 12:
            next_month = datetime(last_year + 1, 1, 1).date()
        else:
            next_month = datetime(last_year, last_month + 1, 1).date()

        # Buscar registros del mes actual usando comparación de fechas
        current_month_records = await type_model.filter(
            fecha__gte=current_month_start,
            fecha__lt=next_month
        ).all()
        
        print(f"Registros mes actual encontrados: {len(current_month_records)}")

        # Calcular mes anterior
        if last_month == 1:
            prev_month = 12
            prev_year = last_year - 1
        else:
            prev_month = last_month - 1
            prev_year = last_year

        # Crear fechas de inicio y fin para el mes anterior
        prev_month_start = datetime(prev_year, prev_month, 1).date()
        prev_month_end = current_month_start

        prev_month_records = await type_model.filter(
            fecha__gte=prev_month_start,
            fecha__lt=prev_month_end
        ).all()
        
        print(f"Registros mes anterior encontrados: {len(prev_month_records)}")

        # Calcular medias
        prom_actual = round(calculate_mean1(current_month_records, value_field_name), 2)
        prom_anterior = round(calculate_mean1(prev_month_records, value_field_name), 2)
        print(f"Promedios calculados - Actual: {prom_actual}, Anterior: {prom_anterior}")

        # Obtener nombres de los meses
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
            except:
                pass

        current_month_name = current_month_start.strftime("%B %Y")
        prev_month_name = prev_month_start.strftime("%B %Y")

        print(f"Nombres de meses obtenidos - Actual: {current_month_name}, Anterior: {prev_month_name}")

        return {
            'success': True,
            'fechaActual': current_month_name,
            'fechaAnterior': prev_month_name,
            'promActual': prom_actual,
            'promAnterior': prom_anterior,
            'tiempo': 'mes',
            'tipo': value_field_name
        }

    except Exception as error:
        print(f"Error general en search_per_month: {str(error)}")
        print(f"Tipo de error: {type(error)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return {
            'success': False,
            'message': "Error interno",
            'error': str(error)
        }
        
async def search_per_day(message_data: Dict[str, Any], type_model: Model, value_field_name: str) -> Dict[str, Any]:
    try:
        # Obtener el último registro
        last_record = await type_model.filter().order_by('-fecha').first()

        if not last_record:
            return {
                'success': False,
                'message': "No se encontraron datos"
            }

        last_date = last_record.fecha

        # Buscar registros del día actual
        current_day_records = await type_model.filter(
            fecha=last_date
        )

        # Buscar registros del día anterior
        prev_date = last_date - timedelta(days=1)
        prev_day_records = await type_model.filter(
            fecha=prev_date
        )

        # Calcular medias
        prom_actual = calculate_mean(current_day_records, value_field_name)
        prom_anterior = calculate_mean(prev_day_records, value_field_name)

        # Formatear fechas
        fecha_actual = last_date.strftime('%d-%m-%Y')
        fecha_anterior = prev_date.strftime('%d-%m-%Y')

        return {
            'success': True,
            'fechaActual': fecha_actual,
            'fechaAnterior': fecha_anterior,
            'promActual': prom_actual,
            'promAnterior': prom_anterior,
            'tiempo': 'dia',
            'tipo': value_field_name
        }

    except Exception as error:
        return {
            'success': False,
            'message': "Error interno",
            'error': str(error)
        }
        
def get_week_of_month(date: datetime) -> int:
    """Calcular la semana del mes."""
    start_of_month = date.replace(day=1)
    return (date.day + start_of_month.weekday()) // 7 + 1

async def search_per_week(message_data: Dict[str, Any], type_model: Any, value_field_name: str) -> Dict[str, Any]:
    try:
        last_record = await type_model.filter().order_by('-fecha').first()

        if not last_record:
            return {
                'success': False,
                'message': "No se encontraron datos"
            }

        last_date = last_record.fecha
        
        # Calculate week start and end for current week
        current_week_start = last_date - timedelta(days=last_date.weekday())
        current_week_end = current_week_start + timedelta(days=6)

        # Calculate week start and end for previous week
        prev_week_start = current_week_start - timedelta(days=7)
        prev_week_end = prev_week_start + timedelta(days=6)

        # Buscar registros de la semana actual 
        current_week_records = await type_model.filter(
            fecha__gte=current_week_start,
            fecha__lte=current_week_end
        )

        # Buscar registros de la semana anterior
        prev_week_records = await type_model.filter(
            fecha__gte=prev_week_start,
            fecha__lte=prev_week_end
        )

        # Calcular medias
        prom_actual = calculate_mean(current_week_records, value_field_name)
        prom_anterior = calculate_mean(prev_week_records, value_field_name)

        return {
            'success': True,
            'fechaActual': f'{current_week_start.strftime("%d-%m-%Y")} a {current_week_end.strftime("%d-%m-%Y")}',
            'fechaAnterior': f'{prev_week_start.strftime("%d-%m-%Y")} a {prev_week_end.strftime("%d-%m-%Y")}',
            'promActual': prom_actual,
            'promAnterior': prom_anterior,
            'tiempo': 'semana',
            'tipo': value_field_name
        }

    except Exception as error:
        return {
            'success': False,
            'message': "Error interno",
            'error': str(error)
        }