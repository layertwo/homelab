#!/bin/bash
set -e

echo "Starting OpenTAKServer..."
echo "Environment check:"
echo "SQLALCHEMY_DATABASE_URI: ${SQLALCHEMY_DATABASE_URI}"
echo "OTS_RABBITMQ_SERVER_ADDRESS: ${OTS_RABBITMQ_SERVER_ADDRESS}"
echo "OTS_LISTENER_ADDRESS: ${OTS_LISTENER_ADDRESS}"
echo "OTS_LISTENER_PORT: ${OTS_LISTENER_PORT}"

# Create CA if it does not exist
if [ ! -d /var/lib/opentakserver/ca ]; then
  echo "Creating CA certificates..."
  python -m flask --app opentakserver.app ots create-ca
fi

# Initialize database
echo "Initializing database..."
python -m flask --app opentakserver.app ots init-db || echo "Database already initialized or init-db command not available"

exec opentakserver
