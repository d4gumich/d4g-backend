# -*- coding: utf-8 -*-
"""

@author: XabUG47
"""


import psycopg2



def ask_owl(query_body: dict):
    # Credentials
    
    # Direct DB connection info
    DB_HOST = 'D4GUMSI-4679.postgres.pythonanywhere-services.com'
    DB_PORT = 14679
    DB_USER = 'super'
    DB_NAME = 'postgres'
    DB_PASSWORD = 'ADD_YOUR_PASSWORD_HERE'
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        

        print("Database connection successful!")
        # Your queries here
    
        cur = conn.cursor()
        
    
        # Read from a simple table as an example
        cur.execute("SELECT * FROM phone;")
    
        rows = cur.fetchall()
    
    
        cur.close()
    finally:
        if 'conn' in locals() and conn and not conn.closed:
            conn.close()
            print("Connection closed.")
            

        

        
    return {"data": rows, "query": query_body}



if __name__ == "__main__":
    print(ask_owl({"query": "Hello World!"}))