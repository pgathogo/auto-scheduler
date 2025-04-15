import pyodbc


class MSSQLData:
    def __init__(self, server, database, username, password):
        self._server = server      # localhost
        self._database = database  # CitizenFM
        self._username = username  # sa
        self._password = password  # abc123

        self.conn_str = (
            r'DRIVER={ODBC Driver 17 for SQL Server};'
            r'SERVER=' + self._server + ';'
            r'DATABASE=' + self._database + ';'
            r'UID=' + self._username + ';'
            r'PWD=' + self._password + ';'
        )
        self.conn = None

    def connect(self):
        try:
            self.conn = pyodbc.connect(self.conn_str)
            return True
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error connecting to database: {sqlstate}")
            return False

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, query: str):
        if not self.conn:
            if not self.connect():
                return None
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error executing query: {sqlstate}")
            return None

    def execute_non_query(self, query):
        print(query)
        if not self.conn:
            if not self.connect():
                return False
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            self.conn.commit()
            return True
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error executing non-query: {sqlstate}")
            return False
            