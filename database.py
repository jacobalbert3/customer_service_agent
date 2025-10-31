"""SQLite database setup and operations for customer service chatbot"""
import sqlite3
import os
from typing import List, Dict, Optional

# Database file path
DB_PATH = "customer_service.db"

def init_database():
    """Initialize SQLite db with users and tickets tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    #users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY
        )
    """)
    
    # Create tickets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
            description TEXT NOT NULL,
            priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    """)
    
    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tickets_username 
        ON tickets (username)
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def add_user(username: str) -> bool:
    """Add a new user to the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

def add_ticket(ticket_id: str, username: str, status: str, description: str, priority: str) -> bool:
    """Add a new ticket to the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (ticket_id, username, status, description, priority)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket_id, username, status, description, priority))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding ticket: {e}")
        return False

def lookup_ticket(ticket_id: str, username: str) -> Optional[Dict]:
    """Look up a ticket by ticket_id and username"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_id, username, status, description, priority, created_at, updated_at
            FROM tickets 
            WHERE ticket_id = ? AND username = ?
        """, (ticket_id, username))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'ticket_id': result[0],
                'username': result[1],
                'status': result[2],
                'description': result[3],
                'priority': result[4],
                'created_at': result[5],
                'updated_at': result[6]
            }
        return None
    except Exception as e:
        print(f"Error looking up ticket: {e}")
        return None

def get_user_tickets(username: str) -> List[Dict]:
    """Get all tickets for a specific user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_id, status, description, priority, created_at, updated_at
            FROM tickets 
            WHERE username = ?
            ORDER BY created_at DESC
        """, (username,))
        
        results = cursor.fetchall()
        conn.close()
        
        tickets = []
        for result in results:
            tickets.append({
                'ticket_id': result[0],
                'status': result[1],
                'description': result[2],
                'priority': result[3],
                'created_at': result[4],
                'updated_at': result[5]
            })
        return tickets
    except Exception as e:
        print(f"Error getting user tickets: {e}")
        return []


if __name__ == "__main__":
    init_database()
