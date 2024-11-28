import os
import subprocess
import getpass

ENV_TEMPLATE_FILE = ".env.template"
ENV_FILE = ".env"
REQUIREMENTS_FILE = "requirements.txt"

def setup_env():
    """ Set up .env file - enable user to use their own name, password, database name """
    print("Starting th app setup")

    print("Configuring .env file")
    if os.path.exists(ENV_FILE):
        print(".env file already exists. Setup has already been completed. If not, try to delete .env file and run setup.py again.")
        return
    if not os.path.exists(ENV_TEMPLATE_FILE):
        print(".env.template file is missing. Please make sure it is included in the app package.")
        return
    
    db_user = input("Enter your database username: ").strip()
    db_password = input("Enter your database password: ").strip()
    db_name = input("Enter your database name: ").strip()

    with open(ENV_TEMPLATE_FILE, "r") as template_file:
        content = template_file.read()
    content = content.replace("DB_USER=", f"DB_USER={db_user}")
    content = content.replace("DB_PASSWORD=", f"DB_PASSWORD={db_password}")
    content = content.replace("DB_NAME=", f"DB_NAME={db_name}")

    with open(ENV_FILE, "w") as env_file:
        env_file.write(content)

    print(".env file has been created!\n")
    setup_postgres(db_user, db_password, db_name)
    install_requirements()

def install_requirements():
    """ Install missing python libraries in virtual environment """
    if os.path.exists(REQUIREMENTS_FILE):
        print("Installing requirements from requirements.txt...")
        subprocess.run(["pip", "install", "-r", REQUIREMENTS_FILE], check=True)
        print("Requirements installed successfully.")
    else:
        print("requirements.txt not found. Please make sure it is included in the app package. Installation was skipped.")

def install_postgres():
    """ Install PostgreSQL """
    print("Installing PostgreSQL")
    subprocess.run(["sudo", "apt-get", "update"], check=True)
    subprocess.run(["sudo", "apt-get", "install", "-y", "postgresql", "postgresql-contrib"], check=True)
    print("PostgreSQL installation completed.\n")

def setup_postgres(db_user, db_password, db_name):
    """ Set up postgres database (permissions, create user, database) """
    current_dir = os.getcwd()
    username = getpass.getuser()

    print(f"Ensuring PostgreSQL can access directory with application: {current_dir}")
    # Add 'postgres' to the user group
    try:
        subprocess.run(["sudo", "usermod", "-aG", username, "postgres"], check=True)
        print(f"Successfully added 'postgres' to {username} group.")
    except subprocess.CalledProcessError as e:
        print(f"Error adding 'postgres' to {username} group: {e}")
        return

    # Update file permissions
    try:
        subprocess.run(["sudo", "chmod", "o+rx", current_dir], check=True)
        print(f"Permissions updated for directory: {current_dir}.\n")
    except subprocess.CalledProcessError as e:
        print(f"Error setting permissions: {e}")
        return

    install_postgres()

    print("Starting PostgreSQL service\n")
    subprocess.run(["sudo", "systemctl", "start", "postgresql"])

    print("Creating PostgreSQL user and database")
    try:
        # Create user if not exists
        subprocess.run([
            "sudo", "-u", "postgres", "psql", "-c",
            f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{db_user}') THEN " +
            f"CREATE USER {db_user} WITH PASSWORD '{db_password}'; END IF; END $$;"
        ], check=True)
        print(f"User '{db_user}' created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating user '{db_user}': {e}")

    try:
        # Create database
        subprocess.run([
            "sudo", "-u", "postgres", "psql", "-c",
            f"CREATE DATABASE {db_name} OWNER {db_user};"
        ], check=True)
        print(f"Database '{db_name}' created successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"Error creating database '{db_name}': {e}")

    initialize_database(db_name, db_user)

def initialize_database(db_name, db_user):
    """ Create schema, table, grant privileges """
    print("Initializing database schema")
    
    sql_commands = f"""
    -- Create schema if it doesn't exist
    CREATE SCHEMA IF NOT EXISTS results_schema;

    -- Create table if it doesn't exist
    CREATE TABLE IF NOT EXISTS results_schema.results (
        id SERIAL PRIMARY KEY,
        test_name VARCHAR(255) NOT NULL,
        result_value VARCHAR(255) NOT NULL,
        unit VARCHAR(50),
        test_date DATE NOT NULL
    );

    -- Grant all privileges to the user on the schema
    GRANT ALL PRIVILEGES ON SCHEMA results_schema TO {db_user};

    -- Grant all privileges to the user on the table
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA results_schema TO {db_user};

    -- Grant usage on the sequence used for id
    GRANT USAGE, SELECT ON SEQUENCE results_schema.results_id_seq TO {db_user};

    -- Grant usage on the schema if the user might need to create objects
    GRANT USAGE ON SCHEMA results_schema TO {db_user};
    """

    # Run the SQL commands using psql
    try:
        subprocess.run(["sudo", "-u", "postgres", "psql", "-d", db_name, "-c", sql_commands], check=True)
        print("Database initialized successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"Error initializing the database schema: {e}")

if __name__ == "__main__":
    setup_env()