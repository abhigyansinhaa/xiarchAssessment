import sys
import uvicorn
from backend.config import HOST, PORT
from backend.data.seed_db import seed_database
from backend.models.database import init_db

if __name__ == "__main__":
    print("=" * 65)
    print("🚀 Starting Xiarch Bharat Autonomous AI Enterprise Agent...")
    print("=" * 65)

    # 1. Initialize schema & seed database if needed
    init_db()
    seed_database()

    print(f"📡 Web Chat UI & REST API available at: http://{HOST}:{PORT}")
    print(f"📖 Swagger OpenAPI Documentation: http://{HOST}:{PORT}/docs")
    print("=" * 65)

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
