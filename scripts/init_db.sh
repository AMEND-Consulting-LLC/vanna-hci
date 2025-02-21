#!/bin/bash

# Wait for PostgreSQL to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h db -U $POSTGRES_USER -d $POSTGRES_DB -c '\q'; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - executing database initialization"

# Create initial admin API key
ADMIN_KEY=$(openssl rand -hex 32)
echo "Generated initial admin API key: $ADMIN_KEY"

# Store the admin key securely (you might want to implement your own secure storage)
echo $ADMIN_KEY > /app/data/admin_key.txt

# Initialize database schema and create admin key
python3 << END
from vanna.flask.db_models import init_db, create_initial_admin_key
from flask import Flask

app = Flask(__name__)
app.config['DATABASE_URL'] = 'postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}'

Session = init_db(app.config)
session = Session()

try:
    # Create initial admin key
    create_initial_admin_key(session, '$ADMIN_KEY')
    print("Successfully created initial admin API key")
except Exception as e:
    print(f"Error creating admin key: {str(e)}")
finally:
    session.close()
END 