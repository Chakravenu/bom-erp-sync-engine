from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from services.etl_service import ETLService
from config import Config

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AVILUS BOM-ERP Sync API",
    description="S1000D to Sage 100 synchronization service",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single ETL service instance
etl = ETLService()

@app.get("/")
def root():
    return {"status": "running", "service": "AVILUS BOM-ERP Sync"}


@app.post("/api/sync")
def trigger_sync():
    """
    Trigger BOM synchronization from S1000D to Sage 100
    This is the main endpoint called when BOM changes
    """
    try:
        logger.info("API: Sync requested")
        result = etl.run_sync()
        return result.to_dict()
    except Exception as e:
        logger.error(f"API: Sync failed - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bom/tree")
def get_bom_tree():
    """Get hierarchical BOM tree structure (for tree view)"""
    try:
        tree = etl.get_source_bom_tree()
        
        # Convert to dict for JSON serialization
        def tree_to_dict(node):
            return {
                "id": node.id,
                "part_number": node.part_number,
                "description": node.description,
                "category": node.category,
                "quantity": node.quantity,
                "unit_price": node.unit_price,
                "bom_level": node.bom_level,
                "is_assembly": node.is_assembly,
                "supplier": node.supplier,
                "children": [tree_to_dict(c) for c in node.children]
            }
        
        return {
            "tree": [tree_to_dict(root) for root in tree],
            "count": len(tree)
        }
    except Exception as e:
        logger.error(f"API: Get BOM tree failed - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sage100/articles")
def get_sage100_articles():
    """Get all articles from Sage 100 database"""
    try:
        articles = etl.get_target_articles()
        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        logger.error(f"API: Get articles failed - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_statistics():
    """Get BOM statistics"""
    try:
        stats = etl.get_bom_statistics()
        return stats
    except Exception as e:
        logger.error(f"API: Get stats failed - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/history")
def get_sync_history():
    """Get sync operation history"""
    try:
        history = etl.get_sync_history(20)
        return {"history": history}
    except Exception as e:
        logger.error(f"API: Get history failed - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sage100/clear")
def clear_sage100():
    """Clear Sage 100 database (testing only)"""
    try:
        etl.clear_target_database()
        return {"status": "cleared"}
    except Exception as e:
        logger.error(f"API: Clear failed - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
def startup():
    """Validate configuration on startup"""
    Config.validate()
    logger.info("API server started")


@app.on_event("shutdown")
def shutdown():
    """Cleanup on shutdown"""
    etl.target.close()
    logger.info("API server stopped")