#!/bin/bash
set -e

echo "🔍 Starting Sentinel..."

# Create data directory if it doesn't exist
mkdir -p /app/data

# Run database migrations
echo "📦 Running database migrations..."

# Count migration files (excluding __pycache__ and .gitkeep)
MIGRATION_COUNT=$(find /app/alembic/versions -name "*.py" -not -name "__init__.py" 2>/dev/null | wc -l)

if [ "$MIGRATION_COUNT" -eq 0 ]; then
    echo "⚠️  No migrations found. Creating database schema directly..."
    python -c "
from app.database import engine, Base
from app.models import Company, Tag, Sync, Setting, IPOEntry
Base.metadata.create_all(bind=engine)
print('✓ Database schema created')
"
else
    echo "Found $MIGRATION_COUNT migration(s). Running alembic upgrade..."
    # Always run migrations - alembic will skip already-applied ones
    if alembic upgrade head; then
        echo "✓ Database migrations applied successfully"
    else
        echo "❌ Migration failed! Attempting fallback schema creation..."
        python -c "
from app.database import engine, Base
from app.models import Company, Tag, Sync, Setting, IPOEntry
Base.metadata.create_all(bind=engine)
print('⚠️  Fallback schema created - you may need to manually fix migrations')
"
    fi
fi

# Initialize default settings if database is new
echo "⚙️  Initializing settings..."
python -c "
from app.database import SessionLocal
from app.models import Setting

db = SessionLocal()

# Check if settings exist
if db.query(Setting).count() == 0:
    print('Setting up default configuration...')
    defaults = [
        Setting(key='news_count', value='${NEWS_ARTICLE_COUNT:-10}'),
    ]
    for setting in defaults:
        db.add(setting)
    db.commit()
    print('✓ Default settings configured')
else:
    print('✓ Settings already configured')

db.close()
"

# Start the server
echo "🚀 Starting Sentinel API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
