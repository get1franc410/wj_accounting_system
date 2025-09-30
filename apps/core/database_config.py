# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\database_config.py
import os
import json
import psycopg2
from django.conf import settings
from django.core.management import execute_from_command_line

class DatabaseConfigurator:
    """Handle database configuration for standalone installations"""
    
    CONFIG_FILE = 'database_config.json'
    
    @staticmethod
    def test_postgresql_connection(config):
        """Test PostgreSQL connection"""
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['name'],
                user=config['user'],
                password=config['password']
            )
            conn.close()
            return True
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}")
            return False
    
    @staticmethod
    def save_database_config(config):
        """Save database configuration to file"""
        config_path = os.path.join(settings.BASE_DIR, DatabaseConfigurator.CONFIG_FILE)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Update Django settings dynamically
        DatabaseConfigurator.update_django_settings(config)
    
    @staticmethod
    def load_database_config():
        """Load database configuration from file"""
        config_path = os.path.join(settings.BASE_DIR, DatabaseConfigurator.CONFIG_FILE)
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        
        return None
    
    @staticmethod
    def update_django_settings(config):
        """Update Django database settings"""
        if config['type'] == 'postgresql':
            settings.DATABASES['default'] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config['name'],
                'USER': config['user'],
                'PASSWORD': config['password'],
                'HOST': config['host'],
                'PORT': config['port'],
            }
        
        # Run migrations after database change
        try:
            execute_from_command_line(['manage.py', 'migrate'])
        except Exception as e:
            print(f"Migration failed: {e}")
    
    @staticmethod
    def setup_postgresql_installer():
        """Generate PostgreSQL installation script"""
        script = """
        @echo off
        echo Installing PostgreSQL for Accounting System...
        
        REM Download PostgreSQL installer
        curl -L -o postgresql-installer.exe "https://get.enterprisedb.com/postgresql/postgresql-13.7-1-windows-x64.exe"
        
        REM Install PostgreSQL silently
        postgresql-installer.exe --mode unattended --unattendedmodeui none --superpassword "admin123" --servicename "postgresql" --servicepassword "admin123"
        
        REM Create database
        "C:\\Program Files\\PostgreSQL\\13\\bin\\createdb.exe" -U postgres accounting_system
        
        echo PostgreSQL installation complete!
        pause
        """
        
        with open('install_postgresql.bat', 'w') as f:
            f.write(script)
        
        return 'install_postgresql.bat'
