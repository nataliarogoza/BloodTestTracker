import os
from dotenv import load_dotenv
import psycopg2
from PyQt6.QtWidgets import QMessageBox

load_dotenv()

class DatabaseManager():
    """ Connects to app's database and enables basic operations on table storing blood test results
        (insert, update, delete, select) """
    def __init__(self):
        """ Initialize DatabaseManager instance based on .env file content """
        self.dbname = os.getenv("DB_NAME", "tracker")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.host = os.getenv("DB_HOST", "localhost") # Default to localhost
        self.port = os.getenv("DB_PORT", "5432") # Default to 5432
        self.table_name = "results_schema.results" 

        # Validate required environment variables
        if not all([self.dbname, self.user, self.password]):
            raise ValueError("Missing required environment variables (DB_NAME, DB_USER, or DB_PASSWORD)!")

    def connect_to_db(self):
        """ Establish connection to the database """
        try:
            conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port)
            return conn
        except Exception as e:
            QMessageBox.critical(None, "Connection Error", str(e))
            return None
        
    def insert(self, test_name, result_value, unit, result_date):
        """ Insert data into the results table in the database """
        conn = self.connect_to_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            sql = f"""
            INSERT INTO {self.table_name} (test_name, result_value, unit, test_date)
            VALUES (%s, %s, %s, %s);
            """
            cur.execute(sql, (test_name, result_value, unit, result_date))
            conn.commit()
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))
        finally:
            conn.close()

    def delete(self, result_id):
        """ Delete data from the specified table in the database by ID """
        conn = self.connect_to_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            sql = f"DELETE FROM {self.table_name} WHERE id = %s;"
            cur.execute(sql, (result_id,))
            conn.commit()
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))
        finally:
            conn.close()

    def get_result_id(self, test_name, result_value, unit, test_date):
        """ Get the result ID from the database based on the row data """
        conn = self.connect_to_db()
        if not conn:
            return None
        try:
            cur = conn.cursor()
            sql = f"""
            SELECT id FROM {self.table_name} 
            WHERE test_name = %s AND result_value = %s AND unit = %s AND test_date = %s
            LIMIT 1;
            """
            cur.execute(sql, (test_name, result_value, unit, test_date))
            result = cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))
            return None
        finally:
            conn.close()
        
    def update(self, result_id, test_name, result_value, unit, result_date):
        """ Update data in the results table """
        conn = self.connect_to_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            sql = f"""
            UPDATE {self.table_name}
            SET test_name = %s, result_value = %s, unit = %s, test_date = %s
            WHERE id = %s;
            """
            cur.execute(sql, (test_name, result_value, unit, result_date, result_id))
            conn.commit()
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))
        finally:
            conn.close()

    def select_all(self):
        """ Select all results table content """
        conn = self.connect_to_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            sql = f"SELECT test_name, result_value, unit, test_date FROM {self.table_name} ORDER BY id;"
            cur.execute(sql)
            results = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))
        finally:
            conn.close()
        return results
    
    def select_chosen_all(self, test_name):
        """ Select all avaiable data for one specified test_name of results table """
        conn = self.connect_to_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            sql = f"SELECT result_value, unit, test_date FROM {self.table_name} WHERE test_name = %s ORDER BY test_date"
            cur.execute(sql, (test_name,))
            results = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))
        finally:
            conn.close()
        return results
    
    def select_chosen_column(self, column_name):
        """ Select only values from specified column of results table """
        conn = self.connect_to_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT {column_name} FROM {self.table_name}")
            results = sorted(set([res[0] for res in cur]))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()
        return results