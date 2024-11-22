import os
from loguru import logger
from dotenv import load_dotenv
from tortoise import Tortoise

load_dotenv()

async def connectToDatabase():
    try:
        async def init_orm():
            db_user = os.getenv("DB_USER", "root")
            db_password = os.getenv("DB_PASSWORD", "")
            db_host = os.getenv("DB_HOST", "localhost")
            db_name = os.getenv("DB_NAME", "vitalGuard")

            db_url = f"mysql://{db_user}:{db_password}@{db_host}/{db_name}"

            await Tortoise.init(
                db_url=db_url,
                modules={"models": ["models.BPM", "models.TempModel"]}
            )
            await Tortoise.generate_schemas()
            logger.info("Conexión a la base de datos establecida.")
            
        await init_orm()
    
    except Exception as e:
        logger.error(f"La conexión a la base de datos falló.\n{e}")
        return None
