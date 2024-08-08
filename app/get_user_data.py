import sqlite3
from passlib.hash import sha256_crypt

# Path to your SQLite database
DATABASE_PATH = 'blog.db'

def verify_passwords():
    # Connect to the SQLite database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Query to select all usernames and hashed passwords
    query = "SELECT username, password FROM users"
    
    try:
        cursor.execute(query)
        users = cursor.fetchall()
        
        # Debug: Print the number of rows fetched
        print(f"Number of users fetched: {len(users)}")
        
        if users:
            print("User Data:")
            for username, hashed_password in users:
                print(f"Username: {username}, Password: {hashed_password}")
        else:
            print("No users found.")
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    verify_passwords()
