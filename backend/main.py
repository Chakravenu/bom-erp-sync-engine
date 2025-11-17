import uvicorn
import logging
from config import Config
from api.routes import app

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("AVILUS BOM-ERP Sync Service")
    logger.info("=" * 50)
    logger.info(f"API: http://{Config.API_HOST}:{Config.API_PORT}")
    logger.info(f"Docs: http://{Config.API_HOST}:{Config.API_PORT}/docs")
    logger.info("=" * 50)
    
    uvicorn.run(
        app,
        host=Config.API_HOST,
        port=Config.API_PORT,
        log_level="info"
    )